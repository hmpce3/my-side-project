"""
auto-detect — 업로드한 데이터가 '어떤 종류'인지 컬럼을 보고 판별합니다.

사용자가 컬럼을 고르지 않아도, 여러 파일을 한꺼번에 올리면 각 파일이
장서목록인지·월별대출인지·인기대출인지 알아서 분류해 알맞은 진단에 연결합니다.
판별 기준은 데이터 카탈로그(docs/데이터_카탈로그.md)의 컬럼 신호를 따릅니다.
"""


# 데이터 종류(family)별 한글 이름 — 화면에 "무엇으로 인식했는지" 보여줄 때 사용
FAMILY_LABELS = {
    "collection": "장서 대출목록",
    "monthly": "월별 대출(시계열)",
    "popular": "인기대출 도서",
    "surge": "대출 급상승 도서",
    "libraries": "참여도서관 목록",
    "keywords": "이달의 키워드",
    "unknown": "알 수 없음",
}


def classify(df):
    """DataFrame의 컬럼만 보고 데이터 종류를 판별합니다(가장 구체적인 것부터)."""
    columns = [str(c) for c in df.columns]

    def has(*keywords):
        return all(any(k in c for c in columns) for k in keywords)

    if has("위도", "경도"):
        return "libraries"
    if has("키워드", "Score"):
        return "keywords"
    # 급상승: '상승폭'은 다른 데이터엔 없는 고유 신호
    if has("상승폭"):
        return "surge"
    # 장서목록: 공급(도서권수)·수요(대출건수)·분류를 모두 가진 책 단위 표
    if has("도서권수", "대출건수") and (has("주제분류") or has("KDC")):
        return "collection"
    # 월별 대출: 월/연월 + 대출, 단 책 단위(ISBN·도서권수)는 아님
    if (has("대출월") or has("연월")) and has("대출") and not has("ISBN") and not has("도서권수"):
        return "monthly"
    # 인기대출: 순위/부가기호 + ISBN + 대출건수 (도서권수 없음)
    if has("ISBN") and has("대출") and (has("순위") or has("부가기호") or has("KDC")):
        return "popular"
    return "unknown"
