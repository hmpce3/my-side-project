"""
도서관 운영 지표(KPI) 계산.

도서관 도메인에서만 의미 있는 지표라 library_app 안에 둡니다.
대표 지표인 '장서 회전율'은 장서 수 데이터가 있어야 정확히 계산되므로,
지금은 대출 로그만으로 계산 가능한 지표를 우선 제공합니다.
"""

import pandas as pd


def _find_column(data, candidates):
    """후보 이름들 중 데이터에 실제로 있는 첫 번째 컬럼명을 돌려줍니다(없으면 None)."""
    for name in candidates:
        if name in data.columns:
            return name
    return None


def compute_loan_kpis(loans):
    """
    데이터 모양에 상관없이 가능한 핵심 지표만 골라 계산합니다.

    두 가지 흔한 형태를 모두 지원합니다.
      - 순위/집계형 : 한 행 = 도서, '대출건수' 컬럼 있음 (예: 인기대출도서 목록)
      - 로그형      : 한 행 = 대출 1건, '대출건수' 컬럼 없음

    없는 컬럼은 건너뛰므로 KeyError로 멈추지 않습니다.
    """
    kpis = {}
    n_rows = len(loans)

    loan_col = _find_column(loans, ["대출건수", "대출횟수", "대출 건수"])
    title_col = _find_column(loans, ["서명", "도서명", "제목", "title"])
    date_col = _find_column(loans, ["대출일", "날짜", "date"])
    field_col = _find_column(loans, ["KDC분류", "주제분류", "분야"])

    # 1) 총 대출 건수
    if loan_col is not None:
        total = pd.to_numeric(loans[loan_col], errors="coerce").sum()
        kpis["총 대출 건수"] = int(total) if pd.notna(total) else 0
        kpis["도서 수"] = n_rows
    else:
        # 로그형: 한 행이 대출 1건
        kpis["총 대출 건수"] = n_rows

    # 2) 고유 도서 수
    if title_col is not None:
        kpis["고유 도서 수"] = int(loans[title_col].nunique())

    # 3) 날짜가 있으면 분석 기간 / (로그형이면) 일평균
    if date_col is not None:
        dates = pd.to_datetime(loans[date_col], errors="coerce").dropna()
        if not dates.empty:
            kpis["분석 기간"] = f"{dates.min().date()} ~ {dates.max().date()}"
            span_days = (dates.max() - dates.min()).days + 1
            if span_days > 0 and loan_col is None:
                kpis["일평균 대출"] = round(n_rows / span_days, 1)

    # 4) 가장 많이 대출된 도서 (순위/집계형)
    if title_col is not None and loan_col is not None:
        numeric_loans = pd.to_numeric(loans[loan_col], errors="coerce")
        if numeric_loans.notna().any():
            top_idx = numeric_loans.idxmax()
            kpis["최다 대출 도서"] = str(loans.loc[top_idx, title_col])

    # 5) 최다 분야 (분야 컬럼이 라벨 형태일 때)
    if field_col is not None and n_rows > 0:
        top_field = loans[field_col].astype(str).value_counts().idxmax()
        kpis["최다 분야"] = top_field

    return kpis


def turnover_rate(total_loans, collection_size):
    """
    장서 회전율 = 대출 건수 ÷ 장서 수.

    책 한 권이 평균 몇 번 대출되었는지를 나타내는 도서관 운영 핵심 지표.
    장서 수 데이터가 확보되면 이 함수로 회전율을 계산해 KPI에 추가합니다.
    """
    if not collection_size:
        return None
    return round(total_loans / collection_size, 2)
