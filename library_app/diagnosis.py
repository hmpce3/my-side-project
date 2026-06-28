"""
도서관 장서 '건강검진' 진단 엔진 (프로토타입).

핵심 아이디어 — 왜 이렇게 진단하는가
------------------------------------------------
도서관마다 성격이 다르다(어린이도서관 vs 종합도서관 vs 전문도서관).
그래서 "청소년 장서가 10%는 넘어야 한다" 같은 '절대 기준'으로 진단하면
어린이도서관을 무조건 '문제 있음'으로 찍는 멍청한 결과가 나온다.

대신 이 엔진은 '그 도서관 안에서' 두 가지를 비교한다.
    - 공급(供給) : 장서가 어떻게 구성되어 있나   = 도서권수
    - 수요(需要) : 실제로 무엇이 대출되나         = 대출건수
둘의 '비중'이 어긋나는 지점이 곧 의사결정 포인트다.
    - 수요 > 공급  → 보강(수서) 후보   : 사람들은 원하는데 책이 부족
    - 공급 > 수요  → 정리/큐레이션 후보 : 책은 많은데 안 빌려감

이 '자기참조' 방식은 도서관 종류가 달라도 공정하게 작동한다.
(보조로 전국 인기대출 분포를 '바깥 수요' 벤치마크로 얹으면 더 강해진다.)
"""

import numpy as np
import pandas as pd

# KDC 대분류·독자대상 매핑은 도메인 지식이라 loader에 모아둔다 → 재사용.
from loader import KDC_MAIN, READER_TARGET

# 진단 임계값(퍼센트포인트). 수요·공급 비중 차이가 이보다 크면 '어긋남'으로 본다.
GAP_THRESHOLD_PP = 3.0


def prepare(raw):
    """
    2.28 형식(장서 대출목록)의 원본 DataFrame을 진단용으로 정리한다.

    하는 일:
      - 빈 'Unnamed' 컬럼 제거
      - 도서권수·대출건수를 숫자로 강제 변환(콤마/문자 섞여도 안전)
      - 주제분류번호 → KDC 대분류(분야) 라벨
      - 부가기호 → 독자대상 라벨
    """
    df = raw.loc[:, ~raw.columns.astype(str).str.startswith("Unnamed")].copy()

    df["도서권수"] = pd.to_numeric(df.get("도서권수"), errors="coerce").fillna(0)
    df["대출건수"] = pd.to_numeric(df.get("대출건수"), errors="coerce").fillna(0)

    # 813.7 같은 소수 KDC → 맨 앞자리(8=문학)로 대분류.
    kdc_main = pd.to_numeric(df.get("주제분류번호"), errors="coerce") // 100
    df["분야"] = kdc_main.map(KDC_MAIN).fillna("미분류")

    # 부가기호 맨 앞자리 → 독자대상.
    first = df.get("부가기호").astype(str).str.strip().str[0]
    df["독자대상"] = first.map(READER_TARGET).fillna("기타/미상")

    return df


def gap_by_segment(df, segment_column):
    """
    세그먼트(분야 또는 독자대상)별로 공급 vs 수요 비중과 격차를 계산한다.

    반환 컬럼:
        장서수(공급), 대출수(수요), 공급비중(%), 수요비중(%),
        격차(%p) = 수요비중 - 공급비중, 회전율 = 대출수 / 장서수
    """
    grouped = df.groupby(segment_column).agg(
        장서수=("도서권수", "sum"),
        대출수=("대출건수", "sum"),
    )

    total_supply = grouped["장서수"].sum()
    total_demand = grouped["대출수"].sum()

    grouped["공급비중"] = (grouped["장서수"] / total_supply * 100).round(1)
    grouped["수요비중"] = (grouped["대출수"] / total_demand * 100).round(1)
    grouped["격차"] = (grouped["수요비중"] - grouped["공급비중"]).round(1)
    grouped["회전율"] = (grouped["대출수"] / grouped["장서수"].replace(0, np.nan)).round(2)

    return grouped.sort_values("격차", ascending=False).reset_index()


def diagnose(gap_df, segment_label, threshold=GAP_THRESHOLD_PP):
    """
    격차 표를 보고 '진단 문장'을 자동 생성한다(규칙 기반).

    무서운 AI가 아니라, 사서의 판단 규칙을 코드로 옮긴 것:
        격차 > +임계  → 수요 대비 장서 부족(보강/수서 권장)
        격차 < -임계  → 장서 대비 이용 저조(정리/큐레이션 권장)
    """
    findings = []
    for _, row in gap_df.iterrows():
        seg = row[gap_df.columns[0]]
        gap = row["격차"]
        if gap >= threshold:
            findings.append(
                f"📈 [{segment_label}] **{seg}** — 수요비중 {row['수요비중']}% > "
                f"장서비중 {row['공급비중']}% (격차 +{gap}%p). "
                f"수요 대비 장서가 부족 → **보강(수서) 후보**."
            )
        elif gap <= -threshold:
            findings.append(
                f"📉 [{segment_label}] **{seg}** — 장서비중 {row['공급비중']}% > "
                f"수요비중 {row['수요비중']}% (격차 {gap}%p), 회전율 {row['회전율']}. "
                f"책은 많지만 덜 빌려감 → **정리/큐레이션 후보**."
            )
    if not findings:
        findings.append(f"[{segment_label}] 공급과 수요가 대체로 균형적입니다.")
    return findings


def run_diagnosis(raw):
    """원본 → 정리 → 분야/독자대상 진단까지 한 번에. (앱·스크립트 공통 진입점)"""
    df = prepare(raw)
    result = {}
    for label, col in [("분야", "분야"), ("독자대상", "독자대상")]:
        gap = gap_by_segment(df, col)
        result[label] = {"table": gap, "findings": diagnose(gap, label)}
    return df, result
