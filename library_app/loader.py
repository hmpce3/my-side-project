"""
도서관 대시보드 전용 데이터 로더.

- 내 파일 업로드: CSV/Excel/JSON을 올리면 공용 엔진 read_data_file()로 읽습니다.
- 샘플 데이터: data/ 폴더의 '실제' 도서관정보나루 파일(2.28도서관 장서목록,
  테마요청 월별 대출)을 읽어, 업로드 없이도 진짜 데이터로 둘러볼 수 있게 합니다.
  (가짜로 지어낸 데이터는 쓰지 않습니다 — 데이터 활용 공모전 취지에 맞춤)

여기(loader)는 '도서관 도메인'에만 해당하는 부분이라 library_app 안에만 둡니다.
공용 엔진(helpers)에는 도메인 단어가 들어가지 않습니다.
"""

import glob
import io
import os
import re
import sys

import pandas as pd

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GENERIC_DASHBOARD_DIR = os.path.join(ROOT_DIR, "generic_dashboard")
if GENERIC_DASHBOARD_DIR not in sys.path:
    sys.path.insert(0, GENERIC_DASHBOARD_DIR)

from helpers import my_data

# 업로드 파일의 헤더 행을 찾을 때 쓰는 앵커(이 단어가 든 행이 진짜 헤더).
# 주의: '키워드'처럼 제목 줄("이달의 키워드_100건")에도 들어가는 단어는 제외.
_HEADER_ANCHORS = (
    "순위", "번호", "도서명", "서명", "대출월", "연월",
    "도서관명", "참여연도", "주제분류번호", "대출건수", "상승폭",
)


# KDC(한국십진분류) 대분류 — 도서관 도메인 지식
KDC_MAIN = {
    0: "총류",
    1: "철학",
    2: "종교",
    3: "사회과학",
    4: "자연과학",
    5: "기술과학",
    6: "예술",
    7: "언어",
    8: "문학",
    9: "역사",
}

# ISBN 부가기호 '독자대상기호'(맨 앞자리) → 독자층. (진단·처방이 공유)
READER_TARGET = {
    "0": "교양",
    "1": "실용",
    "2": "(여성)",
    "3": "(예비)",
    "4": "청소년",
    "5": "학습참고서",
    "7": "아동",
    "9": "전문",
}

# data/ 폴더 위치 — 샘플(실제) 데이터를 여기서 읽습니다.
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def _find_data_file(*patterns):
    """data/ 폴더에서 패턴에 맞는 첫 파일 경로를 찾습니다(없으면 None)."""
    for pattern in patterns:
        matches = sorted(glob.glob(os.path.join(DATA_DIR, pattern)))
        if matches:
            return matches[0]
    return None


def load_uploaded_file(uploaded_file):
    """업로드한 파일을 공용 엔진으로 읽어 DataFrame으로 돌려줍니다."""
    data, info = my_data.read_data_file(uploaded_file)
    return data, info


def smart_read(uploaded_file):
    """
    업로드 파일을 '헤더 위치 자동 감지'로 깔끔하게 읽습니다.

    도서관정보나루 다운로드는 위에 메타 줄(검색조건·제공기관 등)이 붙어 있어서
    그냥 읽으면 컬럼이 엉킵니다. 진짜 헤더 행을 찾아 그 아래만 표로 읽습니다.
    여러 파일을 한꺼번에 올려 종류를 자동 판별할 때 입구가 되는 함수입니다.
    """
    name = str(getattr(uploaded_file, "name", "")).lower()

    if name.endswith(".csv"):
        text = uploaded_file.getvalue().decode("utf-8-sig", errors="replace")
        header_row = 0
        for i, line in enumerate(text.splitlines()[:30]):
            if any(a in line for a in _HEADER_ANCHORS):
                header_row = i
                break
        return pd.read_csv(io.StringIO(text), skiprows=header_row, on_bad_lines="skip")

    if name.endswith((".xlsx", ".xls")):
        probe = pd.read_excel(uploaded_file, header=None, nrows=25, dtype=str)
        header_row = 0
        for i in range(len(probe)):
            cells = [str(x) for x in probe.iloc[i].dropna()]
            if any(a in c for a in _HEADER_ANCHORS for c in cells):
                header_row = i
                break
        uploaded_file.seek(0)
        return pd.read_excel(uploaded_file, skiprows=header_row)

    data, _ = my_data.read_data_file(uploaded_file)
    return data


def list_sample_libraries():
    """
    data/ 폴더의 '장서 대출목록' 파일들을 {표시이름: 경로}로 돌려줍니다.

    선택형 대시보드의 핵심: 도서관을 바꿔 끼우면 같은 엔진이 다른 진단을 낸다.
    파일명 '2.28도서관 장서 대출목록 (2026년 05월).csv' → 표시이름 '2.28도서관'.
    """
    paths = sorted(glob.glob(os.path.join(DATA_DIR, "*장서 대출목록*.csv")))
    libraries = {}
    for path in paths:
        name = os.path.basename(path)
        label = name.split("장서 대출목록")[0].strip() or name
        libraries[label] = path
    return libraries


def load_sample_collection(path=None):
    """
    data/ 폴더의 '실제' 장서 대출목록을 읽어 돌려줍니다.

    path가 없으면 첫 번째 장서 파일을 읽습니다(기존 동작 유지).
    선택형 화면에서는 list_sample_libraries()가 준 경로를 그대로 넘깁니다.
    (도서관정보나루 데이터는 출처표시(BY) 라이선스라 동봉·사용 가능)
    """
    if path is None:
        path = _find_data_file("*장서 대출목록*.csv", "*장서*.csv")
    if path is None:
        raise FileNotFoundError(
            "data/ 폴더에서 장서 대출목록 CSV를 찾지 못했습니다. "
            "파일을 넣거나 '내 도서관 파일 올리기'를 사용하세요."
        )
    # ISBN·부가기호·권은 섞인 타입이 있어 문자열 손실을 막으려 low_memory=False.
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


# ------------------------------------------------------------
# 전국 도서관 마스터 (참여도서관목록) — 선택형/지도 인프라의 기반
# ------------------------------------------------------------
def load_library_master():
    """
    data/ 폴더의 '참여도서관목록'을 읽어 전국 도서관 마스터로 돌려줍니다.

    위경도·도서관코드를 담고 있어 지도 표시와 API 연동(libCode)의 기반이 됩니다.
    파일 상단에 메타 줄이 붙어 있어 '도서관명' 헤더 행을 찾아 그 아래만 읽습니다.
    """
    path = _find_data_file("*참여도서관목록*.xlsx", "*참여도서관*.xlsx", "*도서관목록*.xlsx")
    if path is None:
        raise FileNotFoundError("data/ 폴더에서 참여도서관목록 파일을 찾지 못했습니다.")

    probe = pd.read_excel(path, header=None, dtype=str)
    header_row = 0
    for i in range(min(20, len(probe))):
        if any(str(x).strip() == "도서관명" for x in probe.iloc[i].tolist()):
            header_row = i
            break

    df = pd.read_excel(path, header=header_row, dtype=str)
    df.columns = [str(c).strip() for c in df.columns]
    df["위도"] = pd.to_numeric(df.get("위도"), errors="coerce")
    df["경도"] = pd.to_numeric(df.get("경도"), errors="coerce")
    return df.dropna(subset=["위도", "경도"]).reset_index(drop=True)


# ------------------------------------------------------------
# 월별 대출 추세용 데이터 (도서관정보나루 '테마요청' 형식)
# ------------------------------------------------------------
def _parse_korean_month(value):
    """'2020년 7월' 같은 한글 연월 문자열을 그 달 1일 Timestamp로 바꿉니다."""
    match = re.match(r"(\d{4})\D+(\d{1,2})", str(value))
    if match:
        return pd.Timestamp(int(match.group(1)), int(match.group(2)), 1)
    return pd.NaT


def _normalize_monthly(raw):
    """원본 표를 [연월(datetime), 대출건수] 형태로 정리합니다."""
    month_col = next((c for c in raw.columns if "연월" in str(c) or "월" in str(c)), raw.columns[0])
    # 건수 컬럼은 월 컬럼을 제외하고 찾습니다('대출월'에도 '대출'이 들어 있어 혼동 방지).
    count_col = next(
        (c for c in raw.columns if c != month_col and ("건수" in str(c) or "대출" in str(c))),
        next((c for c in raw.columns if c != month_col), raw.columns[-1]),
    )
    return pd.DataFrame({
        "연월": raw[month_col].map(_parse_korean_month),
        "대출건수": pd.to_numeric(raw[count_col], errors="coerce"),
    }).dropna().sort_values("연월").reset_index(drop=True)


def normalize_monthly(raw):
    """이미 읽은 표(raw)를 월별 대출 표준 형태로 정리합니다(멀티 업로드 경로용)."""
    return _normalize_monthly(raw)


def normalize_popular(raw):
    """이미 읽은 표(raw)를 인기대출 표준 형태로 정리합니다(멀티 업로드 경로용)."""
    return _normalize_popular(raw)


def load_monthly_loans(uploaded_file):
    """업로드한 월별 대출 파일을 [연월, 대출건수]로 정리합니다('대출월·대출건수' 형식)."""
    raw, info = my_data.read_data_file(uploaded_file)
    return _normalize_monthly(raw), info


def load_sample_monthly():
    """data/ 폴더의 '실제' 월별 대출(테마요청 결과) 파일을 읽어 정리합니다."""
    path = _find_data_file("*테마요청*.xlsx", "*월별*.xlsx", "*테마요청*.csv")
    if path is None:
        raise FileNotFoundError("data/ 폴더에서 월별 대출(테마요청) 파일을 찾지 못했습니다.")
    return _normalize_monthly(pd.read_excel(path))


# ------------------------------------------------------------
# 인기대출도서 (전국 순위) — 수서 처방의 '바깥 수요' 기준
# ------------------------------------------------------------
def _read_table_with_header(path, anchors):
    """도서관정보나루 다운로드처럼 위에 메타 줄이 붙은 파일에서
    실제 헤더 행을 찾아 그 아래만 표로 읽습니다."""
    header_row = 0
    if path.lower().endswith(".csv"):
        # CSV는 메타 줄의 필드 수가 들쭉날쭉이라, 텍스트로 헤더 줄을 찾습니다.
        with open(path, encoding="utf-8-sig") as f:
            for i, line in enumerate(f):
                if i > 30:
                    break
                if any(a in line for a in anchors):
                    header_row = i
                    break
        return pd.read_csv(path, encoding="utf-8-sig", skiprows=header_row, on_bad_lines="skip")

    probe = pd.read_excel(path, header=None, nrows=25, dtype=str)
    for i in range(len(probe)):
        cells = {str(x).strip() for x in probe.iloc[i].dropna()}
        if cells & set(anchors):
            header_row = i
            break
    return pd.read_excel(path, skiprows=header_row)


def _normalize_popular(raw):
    """인기대출 류 표를 [서명, ISBN, 분야, 독자대상, 전국대출건수]로 표준화합니다."""
    raw = raw.loc[:, ~raw.columns.astype(str).str.startswith("Unnamed")].copy()

    def find(keywords):
        return next((c for c in raw.columns if any(k in str(c) for k in keywords)), None)

    title_col = find(["서명", "도서명", "제목"])
    isbn_col = find(["ISBN", "isbn"])
    kdc_col = find(["KDC", "주제분류"])
    addl_col = find(["부가기호"])
    loan_col = find(["대출건수", "대출"])

    out = pd.DataFrame()
    out["서명"] = raw[title_col].astype(str) if title_col else ""
    # ISBN은 문자열로(소수점/공백 제거) — 소장 목록과 대조하려면 형식이 같아야 함
    out["ISBN"] = (
        raw[isbn_col].astype(str).str.split(".").str[0].str.strip() if isbn_col else ""
    )
    # 분야: KDC(813.62)의 맨 앞자리 → 대분류
    if kdc_col is not None:
        out["분야"] = (pd.to_numeric(raw[kdc_col], errors="coerce") // 100).map(KDC_MAIN).fillna("미분류")
    else:
        out["분야"] = "미분류"
    # 독자대상: 부가기호는 앞 0이 떨어질 수 있어 5자리로 채운 뒤 맨 앞자리
    if addl_col is not None:
        first = raw[addl_col].astype(str).str.split(".").str[0].str.zfill(5).str[0]
        out["독자대상"] = first.map(READER_TARGET).fillna("기타/미상")
    else:
        out["독자대상"] = "기타/미상"
    # 전국대출건수: '22,800' 같은 콤마 제거
    if loan_col is not None:
        out["전국대출건수"] = pd.to_numeric(
            raw[loan_col].astype(str).str.replace(",", "", regex=False), errors="coerce"
        )
    else:
        out["전국대출건수"] = pd.NA

    return out.dropna(subset=["ISBN"]).reset_index(drop=True)


def load_popular(uploaded_file):
    """업로드한 인기대출 파일을 표준화해 돌려줍니다."""
    raw, info = my_data.read_data_file(uploaded_file)
    return _normalize_popular(raw), info


def load_sample_popular():
    """data/ 폴더의 '실제' 인기대출도서(BestLoanList)를 읽어 표준화합니다."""
    path = _find_data_file("BestLoanList*.csv", "*인기대출*.csv", "*인기대출*.xlsx")
    if path is None:
        raise FileNotFoundError("data/ 폴더에서 인기대출(BestLoanList) 파일을 찾지 못했습니다.")
    raw = _read_table_with_header(path, anchors=("순위", "서명"))
    return _normalize_popular(raw)


def _normalize_surge(raw):
    """대출 급상승 도서 표를 [서명, ISBN, 상승폭]으로 표준화합니다."""
    raw = raw.loc[:, ~raw.columns.astype(str).str.startswith("Unnamed")].copy()

    def find(*keywords):
        return next((c for c in raw.columns if all(k in str(c) for k in keywords)), None)

    title_col = find("서명") or find("도서명")
    isbn_col = find("ISBN")
    surge_col = find("상승폭")

    out = pd.DataFrame()
    out["서명"] = raw[title_col].astype(str) if title_col else ""
    out["ISBN"] = (
        raw[isbn_col].astype(str).str.split(".").str[0].str.strip() if isbn_col else ""
    )
    out["상승폭"] = pd.to_numeric(raw[surge_col], errors="coerce") if surge_col else pd.NA
    return out.dropna(subset=["ISBN"]).reset_index(drop=True)


def normalize_surge(raw):
    """이미 읽은 표(raw)를 급상승 표준 형태로 정리합니다(멀티 업로드 경로용)."""
    return _normalize_surge(raw)


def load_sample_surge():
    """data/ 폴더의 '실제' 대출 급상승 도서 파일을 읽어 표준화합니다."""
    path = _find_data_file("*급상승*.xlsx", "*급상승*.csv")
    if path is None:
        raise FileNotFoundError("data/ 폴더에서 대출 급상승 도서 파일을 찾지 못했습니다.")
    raw = _read_table_with_header(path, anchors=("번호", "상승폭", "서명"))
    return _normalize_surge(raw)
