"""
처방(處方) 엔진 — 진단 결과를 '맞춤 해결책'으로 바꿉니다.

진단은 "무엇이 문제인가"(사실)를 말하고, 처방은 "그래서 무엇을 하라"(행동)를 말합니다.
도서관마다 진단 결과가 다르므로, 같은 규칙을 돌려도 처방은 도서관마다 달라집니다.

처방 종류(데이터 카탈로그의 문제→해결책 매핑):
  - 수서 추천 : 수요>공급인 분야·독자층 → 전국 인기도서 중 '우리가 없는' 책 구입 목록
  - 복본 추천 : 회전율이 매우 높은(대기 긴) 단일권 도서 → 같은 책 추가 구입
  - 정리 후보 : 공급>수요 + 미대출 → 큐레이션·전시 또는 제적 검토
"""

import pandas as pd

from diagnosis import GAP_THRESHOLD_PP


def _normalize_isbn(series):
    """ISBN을 비교 가능한 문자열로 통일합니다(소수점·공백 제거)."""
    return series.astype(str).str.split(".").str[0].str.strip()


def under_supplied_segments(gap_result, threshold=GAP_THRESHOLD_PP):
    """진단 결과에서 '보강 필요'(수요비중 - 공급비중 >= 임계) 세그먼트를 모읍니다."""
    segments = {}
    for label in ("분야", "독자대상"):
        table = gap_result[label]["table"]
        segments[label] = table.loc[table["격차"] >= threshold, label].tolist()
    return segments


def recommend_acquisitions(prepared, popular, gap_result, top_n=10, threshold=GAP_THRESHOLD_PP):
    """
    수서 추천: '전국 인기도서 중 우리 도서관에 없는 책'을, 부족한 분야·독자층 위주로.

    prepared : diagnosis.prepare()를 거친 우리 장서(분야·독자대상 컬럼 포함, ISBN 보유)
    popular  : loader.load_popular/ load_sample_popular()로 표준화한 전국 인기대출
    """
    owned = set(_normalize_isbn(prepared["ISBN"])) if "ISBN" in prepared.columns else set()
    candidates = popular[~_normalize_isbn(popular["ISBN"]).isin(owned)].copy()

    # 부족한 분야 또는 독자층에 속하는 책을 우선합니다.
    unders = under_supplied_segments(gap_result, threshold)
    in_gap = candidates["분야"].isin(unders["분야"]) | candidates["독자대상"].isin(unders["독자대상"])
    targeted = candidates[in_gap]

    chosen = targeted if not targeted.empty else candidates
    chosen = (
        chosen.sort_values("전국대출건수", ascending=False)
        .drop_duplicates(subset="ISBN")
        .head(top_n)
    )
    return chosen[["서명", "분야", "독자대상", "전국대출건수", "ISBN"]].reset_index(drop=True)


def recommend_rising(prepared, surge, top_n=10):
    """
    선제 수서: '대출이 급상승 중인데 우리 도서관엔 없는 책'.

    인기대출(이미 인기)과 달리 급상승은 '떠오르는 수요'라, 남들이 다 찾기 전에
    미리 갖추자는 선제적 구입 신호입니다.
    """
    owned = set(_normalize_isbn(prepared["ISBN"])) if "ISBN" in prepared.columns else set()
    candidates = surge[~_normalize_isbn(surge["ISBN"]).isin(owned)].copy()
    return (
        candidates.sort_values("상승폭", ascending=False)
        .drop_duplicates(subset="ISBN")
        .head(top_n)[["서명", "상승폭", "ISBN"]]
        .reset_index(drop=True)
    )


def recommend_duplicates(prepared, top_n=10):
    """복본 추천: 회전율(대출÷권수)이 높은데 1권뿐인 도서 → 추가 구입 후보."""
    df = prepared.copy()
    df["회전율"] = df["대출건수"] / df["도서권수"].replace(0, pd.NA)
    single = df[(df["도서권수"] == 1) & (df["대출건수"] > 0)]
    cols = [c for c in ["도서명", "분야", "독자대상", "대출건수", "회전율"] if c in single.columns]
    return single.sort_values("회전율", ascending=False).head(top_n)[cols].reset_index(drop=True)


def weeding_candidates(prepared, top_n=10):
    """정리 후보: 등록된 지 오래됐는데 대출이 0인 도서 → 큐레이션/제적 검토."""
    df = prepared.copy()
    df["대출건수"] = pd.to_numeric(df["대출건수"], errors="coerce").fillna(0)
    year = pd.to_numeric(df.get("발행년도"), errors="coerce")
    never_borrowed = df[(df["대출건수"] == 0)].copy()
    never_borrowed["발행년도"] = year
    cols = [c for c in ["도서명", "분야", "독자대상", "발행년도", "대출건수"] if c in never_borrowed.columns]
    return never_borrowed.sort_values("발행년도", na_position="last")[cols].head(top_n).reset_index(drop=True)
