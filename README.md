# PDF 주문/통관번호 + 아이템코드 매칭/주석 도구

아래 요구를 자동화하는 스크립트입니다.

- PDF에서 주문번호/통관번호가 전달 파일(텍스트/엑셀)에 있는지 확인
- 엑셀 **B열(아이템코드)** 를 PDF에서 우선 매칭
- 매칭된 항목 하이라이트
- 매칭된 항목 옆에 작은 글씨로 **`N개 반송`** 기재 (`N`은 엑셀 E열 수량)
- 전달한 주문/통관번호가 PDF에서 발견되면 옆에 **`이 상품 있음`** 기재

## 설치

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 실행

```bash
python pdf_match_annotate.py \
  --pdf input.pdf \
  --excel items.xlsx \
  --sheet 0 \
  --numbers numbers.txt \
  --output output_annotated.pdf
```

### 인자 설명

- `--pdf`: 원본 PDF
- `--excel`: 기준 엑셀 (`B열=아이템코드`, `E열=수량`)
- `--sheet`: 시트 인덱스(숫자) 또는 시트명
- `--numbers`: 주문번호/통관번호 파일 (`.txt`, `.csv`, `.xlsx`)
- `--output`: 결과 PDF

## 동작 메모

- PDF 내 `30 모델ㆍ규격` 텍스트를 찾으면, 해당 위치 **아래쪽**에서 아이템코드를 우선 매칭합니다.
- 해당 영역에서 못 찾으면 페이지 전체 매칭으로 보완합니다.
- PDF 표 구조를 완전하게 인식하지는 않으므로, 스캔 품질/폰트 깨짐이 큰 문서는 OCR 전처리가 필요할 수 있습니다.
