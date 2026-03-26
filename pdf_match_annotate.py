#!/usr/bin/env python3
"""PDF 내 주문/통관번호 및 아이템코드를 매칭해 하이라이트/주석을 추가하는 도구.

요구사항 요약:
- 전달받은 PDF에서 주문번호/통관번호 존재 여부를 확인
- 엑셀(B열: 아이템코드, E열: 수량) 기준으로 PDF 내 코드 매칭
- 매칭된 코드 하이라이트
- 매칭된 코드 옆 공란에 작은 글씨로 "N개 반송" 기재
- 전달받은 번호(텍스트/엑셀)와 PDF 번호가 일치하면 "이 상품 있음" 기재
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable



ANCHOR_TEXT = "30 모델ㆍ규격"
NEXT_SECTION_RE = re.compile(r"^\s*31[\s\.)].*")


@dataclass
class ItemRow:
    code: str
    qty: str


def normalize_token(value: str) -> str:
    """숫자/영문 비교를 위한 정규화: 공백/특수문자 제거 + 대문자화."""
    value = str(value or "").strip()
    if not value:
        return ""
    return re.sub(r"[^0-9A-Za-z가-힣]", "", value).upper()


def read_item_rows_from_excel(path: Path, sheet: str | int = 0) -> list[ItemRow]:
    import pandas as pd

    df = pd.read_excel(path, sheet_name=sheet, header=None)

    rows: list[ItemRow] = []
    for _, row in df.iterrows():
        code_raw = row[1] if len(row) > 1 else ""  # B열
        qty_raw = row[4] if len(row) > 4 else ""  # E열

        if pd.isna(code_raw):
            continue

        code = str(code_raw).strip()
        if not code:
            continue

        qty = "" if pd.isna(qty_raw) else str(qty_raw).strip()
        rows.append(ItemRow(code=code, qty=qty))

    return rows


def read_reference_numbers(path: Path) -> set[str]:
    import pandas as pd
    """TXT/CSV/XLSX 파일에서 주문/통관번호 후보를 읽어 정규화된 set으로 반환."""
    suffix = path.suffix.lower()
    values: list[str] = []

    if suffix in {".txt", ".log"}:
        values = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    elif suffix in {".csv"}:
        df = pd.read_csv(path, dtype=str)
        values = [str(v) for v in df.fillna("").values.flatten().tolist()]
    elif suffix in {".xlsx", ".xls"}:
        sheets = pd.read_excel(path, sheet_name=None, header=None, dtype=str)
        for df in sheets.values():
            values.extend([str(v) for v in df.fillna("").values.flatten().tolist()])
    else:
        raise ValueError(f"지원하지 않는 번호 파일 형식: {path}")

    return {normalize_token(v) for v in values if normalize_token(v)}


def add_highlight(page, rect) -> None:
    annot = page.add_highlight_annot(rect)
    annot.set_colors(stroke=(1, 1, 0))  # yellow
    annot.update()


def add_small_text(page, rect, text: str) -> None:
    x = rect.x1 + 4
    y = rect.y1 - 1
    page.insert_text((x, y), text, fontsize=6, color=(1, 0, 0))


def find_anchor_y(page) -> float | None:
    rects = page.search_for(ANCHOR_TEXT)
    if rects:
        return max(r.y1 for r in rects)
    return None


def is_below_item_section(page, rect, anchor_y: float | None) -> bool:
    if anchor_y is None:
        return True
    return rect.y0 >= anchor_y


def annotate_pdf(
    pdf_path: Path,
    output_path: Path,
    items: Iterable[ItemRow],
    reference_numbers: set[str] | None = None,
) -> dict[str, int]:
    import fitz  # PyMuPDF

    doc = fitz.open(pdf_path)

    matched_item_count = 0
    matched_number_count = 0

    # 1) 아이템 코드(B열) 우선 매칭
    for page in doc:
        anchor_y = find_anchor_y(page)
        for item in items:
            rects = page.search_for(item.code)
            filtered_rects = [r for r in rects if is_below_item_section(page, r, anchor_y)]

            if not filtered_rects and rects:
                # 앵커 하단 우선이지만 못 찾으면 일반 매칭도 허용
                filtered_rects = rects

            for rect in filtered_rects:
                add_highlight(page, rect)
                qty_label = f"{item.qty}개 반송" if item.qty else "확인필요"
                add_small_text(page, rect, qty_label)
                matched_item_count += 1

    # 2) 주문/통관번호 매칭 + "이 상품 있음" 표기
    if reference_numbers:
        for page in doc:
            words = page.get_text("words")
            for w in words:
                # (x0, y0, x1, y1, word, block_no, line_no, word_no)
                word = str(w[4])
                normalized = normalize_token(word)
                if normalized and normalized in reference_numbers:
                    rect = fitz.Rect(w[0], w[1], w[2], w[3])
                    add_highlight(page, rect)
                    add_small_text(page, rect, "이 상품 있음")
                    matched_number_count += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output_path)
    doc.close()

    return {
        "matched_item_count": matched_item_count,
        "matched_number_count": matched_number_count,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="PDF 아이템코드/번호 매칭 및 주석 도구")
    p.add_argument("--pdf", required=True, type=Path, help="원본 PDF 파일")
    p.add_argument("--excel", required=True, type=Path, help="엑셀 파일 (B열 코드, E열 수량)")
    p.add_argument("--sheet", default=0, help="엑셀 시트명 또는 인덱스")
    p.add_argument("--numbers", type=Path, default=None, help="주문/통관번호 파일(.txt/.csv/.xlsx)")
    p.add_argument("--output", required=True, type=Path, help="결과 PDF 파일")
    return p


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    sheet: str | int
    if isinstance(args.sheet, str) and args.sheet.isdigit():
        sheet = int(args.sheet)
    else:
        sheet = args.sheet

    items = read_item_rows_from_excel(args.excel, sheet=sheet)
    numbers = read_reference_numbers(args.numbers) if args.numbers else None

    result = annotate_pdf(
        pdf_path=args.pdf,
        output_path=args.output,
        items=items,
        reference_numbers=numbers,
    )

    print(f"완료: {args.output}")
    print(f"- 매칭된 아이템 코드 수: {result['matched_item_count']}")
    print(f"- 매칭된 주문/통관번호 수: {result['matched_number_count']}")


if __name__ == "__main__":
    main()
