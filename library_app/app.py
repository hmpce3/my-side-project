"""
도서관 공공데이터 분석 대시보드 (공모전용 · 도메인 특화 앱)

이 앱은 범용 분석 도구(generic_dashboard/app.py)와 '별개의 앱'이지만,
분석 엔진(generic_dashboard/helpers/)은 그대로 공유합니다.
  - 공용 엔진(generic_dashboard/helpers) : 시계열·통계·시각화·보고서 등 도메인 무관 기능
  - 이 앱(library_app)  : 도서관 도메인 지식(KPI·문제정의·제언)만 담당

실행: 프로젝트 루트의 '실행_도서관.bat' (또는
      streamlit run library_app/app.py)
"""

import os
import sys

# ------------------------------------------------------------
# 공용 엔진(helpers)을 import할 수 있도록 범용 대시보드 폴더를 경로에 추가합니다.
# 이렇게 하면 복제본 없이 generic_dashboard/helpers/를 그대로 재사용합니다.
# ------------------------------------------------------------
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GENERIC_DASHBOARD_DIR = os.path.join(ROOT_DIR, "generic_dashboard")
if GENERIC_DASHBOARD_DIR not in sys.path:
    sys.path.insert(0, GENERIC_DASHBOARD_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(1, ROOT_DIR)

import pandas as pd
import plotly.express as px
import streamlit as st

from datetime import date

from helpers import my_data
from helpers import my_plot
from helpers import my_report

import loader
import metrics
import diagnosis
import prescribe
import detect


st.set_page_config(
    page_title="도서관 데이터 분석 대시보드",
    page_icon="📚",
    layout="wide",
)


def show_analysis_basis(title, question, rationale, criteria, caution=None):
    """도서관 화면마다 분석 질문·근거·판단 기준을 같은 형식으로 보여줍니다."""
    text = (
        f"[분석 질문]\n{question}\n\n"
        f"[분석 근거]\n{rationale}\n\n"
        f"[판단 기준]\n{criteria}"
    )
    if caution:
        text += f"\n\n[해석 주의]\n{caution}"

    with st.expander(f"분석 근거 · {title}", expanded=True):
        st.markdown(f"**분석 질문**  \n{question}")
        st.markdown(f"**왜 이 변수와 지표를 보나요?**  \n{rationale}")
        st.markdown(f"**판단 기준**  \n{criteria}")
        if caution:
            st.caption(f"해석 주의: {caution}")
    return text


# 샘플(실제) 데이터는 매번 다시 읽으면 느리므로 한 번만 읽어 캐시합니다.
# path를 캐시 키로 받으므로, 도서관을 바꾸면 그 파일이 새로 캐시됩니다.
@st.cache_data(show_spinner="샘플 데이터를 불러오는 중...")
def load_sample_collection(path=None):
    return loader.load_sample_collection(path)


@st.cache_data(show_spinner=False)
def load_sample_monthly():
    return loader.load_sample_monthly()


# 전국 인기대출·급상승은 '바깥 수요' 기준 — 어느 도서관을 보든 동일하게 쓰는 벤치마크
@st.cache_data(show_spinner=False)
def load_sample_popular():
    return loader.load_sample_popular()


@st.cache_data(show_spinner=False)
def load_sample_surge():
    return loader.load_sample_surge()


# ============================================================
# 데이터 준비 — 여러 파일을 한꺼번에 올리면 종류를 자동 판별해 알맞은 칸에 채웁니다.
# context(ctx) = {"collection":…, "monthly":…, "popular":…, "libraries":… }
# ============================================================
def route_uploaded(files):
    """업로드된 여러 파일을 읽고 종류를 판별해 ctx에 분류합니다."""
    ctx, detected = {}, []
    for f in files:
        try:
            raw = loader.smart_read(f)
            kind = detect.classify(raw)
        except Exception as error:
            detected.append((f.name, f"읽기 실패: {error}"))
            continue

        if kind == "collection":
            ctx["collection"] = raw
        elif kind == "monthly":
            ctx["monthly"] = loader.normalize_monthly(raw)
        elif kind == "popular":
            ctx["popular"] = loader.normalize_popular(raw)
        elif kind == "surge":
            ctx["surge"] = loader.normalize_surge(raw)
        elif kind == "libraries":
            ctx["libraries"] = raw
        elif kind == "keywords":
            ctx["keywords"] = raw
        detected.append((f.name, detect.FAMILY_LABELS.get(kind, kind)))
    return ctx, detected


def get_context():
    with st.sidebar:
        st.title("📚 도서관 대시보드")
        st.caption("공공데이터로 도서관 운영 문제를 진단합니다.")
        st.divider()

        st.subheader("데이터")
        mode = st.radio(
            "분석할 데이터",
            ["사전 적재 도서관 선택", "내 도서관 파일 올리기"],
            label_visibility="collapsed",
        )

        if mode == "내 도서관 파일 올리기":
            files = st.file_uploader(
                "도서관 데이터 파일 (여러 개를 한 번에 올릴 수 있어요)",
                type=["csv", "xlsx", "xls", "json"],
                accept_multiple_files=True,
            )
            st.caption(
                "장서목록·월별대출·인기대출 등을 함께 올리면 **종류를 자동 인식**해 "
                "알맞은 진단에 연결합니다."
            )
            if not files:
                st.info("파일을 올리면 분석이 시작됩니다.")
                st.stop()

            ctx, detected = route_uploaded(files)
            with st.expander("🔎 인식된 데이터", expanded=True):
                for name, label in detected:
                    st.caption(f"• {name} → **{label}**")
            return ctx, False

        # 선택형: 도서관을 바꾸면 같은 엔진이 다른 진단을 낸다 (범용성 증명의 핵심 데모)
        libraries = loader.list_sample_libraries()
        if not libraries:
            st.error("data/ 폴더에서 장서 대출목록 파일을 찾지 못했습니다.")
            st.stop()
        library = st.selectbox("도서관 선택", list(libraries.keys()))
        st.info(f"**{library} 실제 데이터**로 진단합니다. (도서관정보나루, 출처표시 BY)")

        try:
            ctx = {
                "collection": load_sample_collection(libraries[library]),
                # 인기대출·급상승은 '전국' 벤치마크라 어느 도서관을 보든 공통으로 붙입니다.
                "popular": load_sample_popular(),
                "surge": load_sample_surge(),
                "library": library,
            }
            # 월별 추세(테마요청) 데이터는 출처 도서관이 확정된 경우에만 붙입니다.
            # data/에 검증된 월별 파일이 없으면 추세 화면은 자동 비활성화됩니다.
            try:
                ctx["monthly"] = load_sample_monthly()
            except FileNotFoundError:
                pass
            return ctx, True
        except Exception as error:
            st.error(f"샘플 데이터를 불러오지 못했습니다: {error}")
            st.stop()


ctx, is_demo = get_context()
data = ctx.get("collection")  # 개요·장서진단이 쓰는 기본 장서 데이터


# 사이드바 메뉴
with st.sidebar:
    st.divider()
    section = st.radio(
        "메뉴",
        [
            "개요 · 핵심 지표",
            "장서 진단 · 의사결정",
            "대출 추세 진단",
            "📑 진단 보고서",
        ],
    )
    st.divider()
    st.caption(f"📌 리포트에 담긴 항목: {my_report.count()}개")


# ============================================================
# 섹션 1) 개요 · 핵심 지표
# ============================================================
if section == "개요 · 핵심 지표":
    st.title("도서관 데이터 분석 대시보드")

    if is_demo:
        library_name = ctx.get("library", "샘플 도서관")
        st.info(
            f"지금은 **{library_name} 실제 데이터(샘플)**입니다. 다른 도서관은 사이드바에서 "
            "선택하거나, '내 도서관 파일 올리기'로 직접 올릴 수 있어요.",
            icon="📊",
        )

    # 올린 데이터가 무엇으로 인식됐는지 한눈에
    loaded = [name for name in ("collection", "monthly", "popular", "libraries") if ctx.get(name) is not None]
    if loaded:
        st.caption("현재 연결된 데이터: " + ", ".join(detect.FAMILY_LABELS[name] for name in loaded))

    if data is None:
        st.warning(
            "장서 대출목록 데이터가 없어 핵심 지표를 계산할 수 없습니다. "
            "사이드바에서 '도서권수·대출건수·주제분류번호'가 든 파일을 올려주세요.",
            icon="📂",
        )
        st.stop()

    st.subheader("이 대시보드가 답하는 질문")
    st.markdown(
        """
        - 우리 장서는 **이용자 수요에 맞게** 구성돼 있나? → 보강(수서)·정리 판단
        - 어떤 분야·독자층 책이 **부족하거나 남아도나**?
        - 한정된 예산을 **어디에 먼저** 써야 하나?

        > 위 질문에 대한 진단은 왼쪽 메뉴 **‘장서 진단 · 의사결정’** 에서 볼 수 있어요.
        """
    )

    show_analysis_basis(
        title="도서관 운영 진단의 출발점",
        question="제한된 예산과 공간 안에서 어떤 장서를 우선 보강하거나 재배치해야 하는가?",
        rationale=(
            "`도서권수`는 도서관이 보유한 공급을, `대출건수`는 실제 이용자 수요를 나타냅니다. "
            "두 값을 함께 보면 단순히 책이 많은 분야가 아니라, 많이 찾는 분야와 부족한 분야를 구분할 수 있습니다."
        ),
        criteria=(
            "핵심 지표에서는 전체 규모를 먼저 확인하고, 세부 진단에서는 분야·독자대상별 공급비중과 수요비중을 비교합니다."
        ),
        caution="대출이 적은 분야가 곧 불필요하다는 뜻은 아니며, 공공성·지역 특성·장서 보존 가치도 함께 고려해야 합니다.",
    )

    st.subheader("핵심 지표")
    kpis = metrics.compute_loan_kpis(data)

    kpi_items = list(kpis.items())
    columns = st.columns(len(kpi_items))
    for column, (label, value) in zip(columns, kpi_items):
        display = f"{value:,}" if isinstance(value, (int, float)) else str(value)
        column.metric(label, display)

    st.subheader("데이터 미리보기")
    st.caption("불러온 데이터의 앞부분입니다. 한 행이 책 1권을 뜻합니다.")
    st.dataframe(data.head(20), use_container_width=True)


# ============================================================
# 섹션 2) 장서 진단 · 의사결정 (자기참조 수급 격차 모델)
# ============================================================
elif section == "장서 진단 · 의사결정":
    st.title("장서 진단 · 수급 격차 분석")
    st.caption(
        "이 도서관의 공급(장서 구성)과 수요(대출)를 비교해, "
        "보강(수서)·정리 후보를 자동으로 진단합니다."
    )

    gap_basis = show_analysis_basis(
        title="장서 수급 격차 분석",
        question="우리 도서관의 장서 구성은 실제 대출 수요와 균형을 이루고 있는가?",
        rationale=(
            "`주제분류번호`와 `부가기호`는 책을 분야와 독자대상으로 나누기 위한 기준 변수입니다. "
            "`도서권수`는 공급, `대출건수`는 수요로 보고 두 비중의 차이를 계산합니다."
        ),
        criteria=(
            "`수요비중 - 공급비중`이 양수이면 수요 대비 장서가 부족한 보강 후보, "
            "음수이면 장서 대비 이용이 낮은 큐레이션/정리 검토 후보로 해석합니다."
        ),
        caution="격차는 의사결정 후보를 찾는 탐색 지표이며, 최종 수서·제적 판단은 사서 검토와 정책 기준이 필요합니다.",
    )

    # 이 진단은 '장서 대출목록' 형식(한 행 = 책, 도서권수·대출건수 보유)이 필요합니다.
    required = ["도서권수", "대출건수", "주제분류번호"]
    if data is None or [c for c in required if c not in data.columns]:
        st.warning(
            "이 분석에는 **장서 대출목록** 형식이 필요합니다 "
            f"(필요한 컬럼: {', '.join(required)}).\n\n"
            "사이드바에서 '내 도서관 파일 올리기'로 도서관별 장서/대출 데이터를 "
            "올리면 진단이 시작됩니다.",
            icon="📂",
        )
        st.stop()

    # 전처리 + 진단을 한 번에 (공용 엔진 아닌, 도서관 전용 diagnosis 모듈)
    prepared, result = diagnosis.run_diagnosis(data)

    total_supply = prepared["도서권수"].sum()
    total_demand = prepared["대출건수"].sum()
    c1, c2, c3 = st.columns(3)
    c1.metric("장서 수", f"{total_supply:,.0f}권")
    c2.metric("대출 건수", f"{total_demand:,.0f}건")
    c3.metric("전체 회전율", f"{total_demand / total_supply:.2f}회" if total_supply else "-")

    with st.expander("📖 이 진단을 읽는 법 (처음이라면 펼쳐 보세요)"):
        st.markdown(
            """
            **공급비중** = 우리 장서에서 그 분야·독자층 책이 차지하는 비율 *(가진 것)*
            **수요비중** = 실제 대출에서 그 분야·독자층이 차지하는 비율 *(빌려가는 것)*

            둘을 비교하면 한눈에 처방이 나옵니다.

            | 상황 | 뜻 | 처방 |
            |---|---|---|
            | 📈 수요비중 **>** 공급비중 | 원하는데 책이 부족 | **보강(수서)** |
            | 📉 공급비중 **>** 수요비중 | 책은 많은데 안 빌려감 | **정리/큐레이션** |

            > 왜 '절대 기준(예: 청소년책 10% 이상)'을 안 쓰냐면 — 도서관마다 역할이
            > 다르기 때문입니다. **자기 도서관 안에서** 공급과 수요를 비교하므로,
            > 어린이도서관이든 종합도서관이든 공정하게 진단됩니다.
            """
        )

    for label in ["분야", "독자대상"]:
        st.subheader(f"{label}별 공급 vs 수요")
        table = result[label]["table"]

        # 공급비중·수요비중을 나란히 묶은 그룹 막대그래프
        long = table.melt(
            id_vars=label, value_vars=["공급비중", "수요비중"],
            var_name="구분", value_name="비중(%)",
        )
        fig = px.bar(
            long, x=label, y="비중(%)", color="구분", barmode="group",
            title=f"{label}별 공급·수요 비중 비교",
        )
        st.plotly_chart(fig, use_container_width=True)

        # 자동 진단 문장: 보강은 info(파랑), 정리는 warning(노랑)으로 구분
        for finding in result[label]["findings"]:
            if "보강" in finding:
                st.info(finding)
            elif "정리" in finding or "큐레이션" in finding:
                st.warning(finding)
            else:
                st.write(finding)

        with st.expander(f"{label} 격차표 자세히 보기"):
            st.dataframe(table, use_container_width=True, hide_index=True)

        # 이 진단을 보고서에 담기 (공용 보고서 엔진 재사용)
        summary = " / ".join(f.split("**")[1] for f in result[label]["findings"] if "**" in f)
        my_report.report_button(
            kind="stat",
            title=f"{label}별 수급 격차 진단",
            source="장서 진단",
            payload={"table": table, "text": "\n".join(result[label]["findings"])},
            key=f"report_gap_{label}",
            caption=(
                f"{gap_basis}\n\n[진단 요약]\n{summary}"
                if summary
                else gap_basis
            ),
        )

    # --------------------------------------------------------
    # 💊 처방 — 진단을 '행동'으로 (수서 추천 / 복본 / 정리 후보)
    # --------------------------------------------------------
    st.divider()
    st.header("💊 처방 — 그래서 무엇을 해야 하나")
    st.caption("위 진단(부족·과잉)을 구체적인 행동으로 바꿉니다. 도서관마다 진단이 다르므로 처방도 달라집니다.")

    prescription_basis = show_analysis_basis(
        title="추천 처방",
        question="진단 결과를 실제 수서·복본·큐레이션 의사결정으로 어떻게 연결할 것인가?",
        rationale=(
            "부족한 분야와 독자대상은 `수서 추천`으로, 회전율이 높은 단일권 도서는 `복본 추천`으로, "
            "대출이 없거나 낮은 도서는 `정리·큐레이션 후보`로 연결합니다."
        ),
        criteria=(
            "전국 인기/급상승 도서 중 미소장 도서는 보강 후보, `대출건수 ÷ 도서권수`가 높은 1권 도서는 복본 후보, "
            "대출 0건 도서는 전시·추천·제적 검토 후보로 봅니다."
        ),
        caution="추천 목록은 자동 후보군이므로 구입 가능성, 최신성, 지역 이용자 특성, 예산을 함께 검토해야 합니다.",
    )

    unders = prescribe.under_supplied_segments(result)
    under_text = ", ".join(unders["분야"] + unders["독자대상"]) or "뚜렷한 부족 영역 없음"
    acquisition_count = None
    rising_count = None

    st.subheader("📚 수서 추천 (전국 인기인데 우리 도서관엔 없는 책)")
    st.caption(f"부족 영역({under_text}) 위주로, 전국 인기대출 도서 중 미소장 도서를 추천합니다.")
    try:
        # 인기대출은 '전국 기준'이라 업로드분이 있으면 그걸, 없으면 샘플(전국)을 사용
        popular = ctx.get("popular")
        if popular is None:
            popular = load_sample_popular()
        acquisitions = prescribe.recommend_acquisitions(prepared, popular, result, top_n=10)
        acquisition_count = len(acquisitions)
        st.dataframe(acquisitions, use_container_width=True, hide_index=True)
        my_report.report_button(
            kind="table",
            title="수서 추천 목록 (미소장 인기도서)",
            source="장서 진단 · 처방",
            payload=acquisitions,
            key="report_acq",
            caption=f"{prescription_basis}\n\n부족 영역({under_text}) 보강을 위한 구입 추천",
        )
    except Exception as error:
        st.info(f"수서 추천에는 전국 인기대출 데이터가 필요합니다. ({error})")

    # 급상승 데이터가 있으면 '선제 수서'도 추천 (떠오르는 수요 → 미리 갖추기)
    surge = ctx.get("surge")
    if surge is not None:
        st.subheader("📈 선제 수서 (대출 급상승 중인데 우리는 없는 책)")
        st.caption("이미 인기인 책이 아니라 '떠오르는' 책 — 수요가 몰리기 전에 미리 갖추는 후보입니다.")
        rising = prescribe.recommend_rising(prepared, surge, top_n=10)
        rising_count = len(rising)
        st.dataframe(rising, use_container_width=True, hide_index=True)
        my_report.report_button(
            kind="table",
            title="선제 수서 목록 (급상승 미소장 도서)",
            source="장서 진단 · 처방",
            payload=rising,
            key="report_rising",
            caption=f"{prescription_basis}\n\n대출이 급상승 중인 미소장 도서 — 선제적 구입 후보",
        )

    duplicates = prescribe.recommend_duplicates(prepared, top_n=8)
    weeding = prescribe.weeding_candidates(prepared, top_n=8)

    st.subheader("처방 후보 요약")
    summary_columns = st.columns(4)
    summary_columns[0].metric("수서 후보", "-" if acquisition_count is None else f"{acquisition_count}권")
    summary_columns[1].metric("급상승 후보", "-" if rising_count is None else f"{rising_count}권")
    summary_columns[2].metric("복본 후보", f"{len(duplicates)}권")
    summary_columns[3].metric("정리·큐레이션 후보", f"{len(weeding)}권")

    col_dup, col_weed = st.columns(2)
    with col_dup:
        st.subheader("📗 복본 추천")
        st.caption("회전율이 높은데 1권뿐 → 추가 구입(대기 줄이기) 후보")
        st.dataframe(duplicates, use_container_width=True, hide_index=True)
        my_report.report_button(
            kind="table",
            title="복본 추천 후보",
            source="장서 진단 · 처방",
            payload=duplicates,
            key="report_duplicates",
            caption=f"{prescription_basis}\n\n회전율이 높은 단일권 도서 — 추가 구입 검토 후보",
        )
    with col_weed:
        st.subheader("🗂️ 정리·큐레이션 후보")
        st.caption("대출 0건 → 전시·큐레이션으로 노출↑ 또는 제적 검토")
        st.dataframe(weeding, use_container_width=True, hide_index=True)
        my_report.report_button(
            kind="table",
            title="정리·큐레이션 검토 후보",
            source="장서 진단 · 처방",
            payload=weeding,
            key="report_weeding",
            caption=f"{prescription_basis}\n\n대출 0건 도서 — 전시·큐레이션 또는 정리 검토 후보",
        )


# ============================================================
# 섹션 3) 대출 추세 진단 (공용 시계열 엔진 재사용)
# ============================================================
elif section == "대출 추세 진단":
    st.title("대출 추세 진단")
    st.caption(
        "월별 대출 흐름을 이동평균과 함께 봅니다. "
        "(범용 분석 대시보드의 시계열 엔진을 그대로 재사용)"
    )

    trend_basis = show_analysis_basis(
        title="대출 추세 분석",
        question="최근 대출 흐름은 증가하고 있는가, 감소하고 있는가, 또는 특정 시기에 변동이 큰가?",
        rationale=(
            "`연월`은 시간 흐름을 나타내고, `대출건수`는 도서관 이용 규모를 나타내는 핵심 지표입니다. "
            "월별 흐름을 보면 장서 운영, 프로그램, 계절 요인과 연결될 수 있는 변화를 찾을 수 있습니다."
        ),
        criteria=(
            "선그래프로 월별 변화를 보고, 이동평균으로 단기 변동을 완화해 전반적인 추세를 확인합니다. "
            "급격한 상승·하락 구간은 별도 원인 확인이 필요한 지점입니다."
        ),
        caution="시계열 추세는 원인을 직접 증명하지 않으므로 행사, 방학, 휴관, 지역 이슈 같은 외부 요인과 함께 해석해야 합니다.",
    )

    # 월별 데이터는 ctx에서 가져옵니다. (사이드바에서 월별 파일을 올렸거나 샘플 모드)
    ts = ctx.get("monthly")
    if ts is None:
        st.warning(
            "월별 대출 데이터가 없습니다. 사이드바에서 '대출월·대출건수' 형식의 "
            "파일을 올리면 추세 진단이 시작됩니다.",
            icon="📂",
        )
        st.stop()

    ma_window = st.slider("이동평균 구간(개월)", min_value=1, max_value=12, value=3)

    # 공용 엔진 재사용: 이동평균 추가 → 선그래프 → 추세 해석 문장
    ts = my_data.add_moving_average(ts, "대출건수", window=int(ma_window))
    fig = my_plot.make_timeseries_line(
        ts, date_column="연월", value_columns=["대출건수", "이동평균"],
        title="월별 대출 건수 추이",
    )
    st.plotly_chart(fig, use_container_width=True)

    insight = my_data.timeseries_trend_insight(ts, "연월", "대출건수")
    st.info(insight)

    with st.expander("월별 집계 표 보기"):
        st.dataframe(ts, use_container_width=True, hide_index=True)

    my_report.report_button(
        kind="chart",
        title="월별 대출 추세",
        source="대출 추세 진단",
        payload=fig,
        key="report_trend",
        caption=f"{trend_basis}\n\n[추세 해석]\n{insight}",
    )


# ============================================================
# 섹션 4) 진단 보고서 (공용 보고서 엔진 재사용 → HTML 내보내기)
# ============================================================
elif section == "📑 진단 보고서":
    st.title("진단 보고서")
    st.caption("각 진단 화면에서 '📌 리포트에 담기'로 모은 항목을 HTML 보고서로 내보냅니다.")

    items = my_report.get_items()
    if not items:
        st.info(
            "아직 담긴 항목이 없습니다. '장서 진단'·'대출 추세 진단' 화면에서 "
            "**📌 리포트에 담기** 버튼을 눌러 보세요.",
            icon="🗂️",
        )
        st.stop()

    col_title, col_author = st.columns(2)
    report_title = col_title.text_input("보고서 제목", "도서관 장서 진단 보고서")
    report_author = col_author.text_input("작성자", "")
    overview = st.text_area(
        "분석 개요(머리말)",
        "도서관정보나루 데이터를 바탕으로 장서 수급 격차와 대출 추세를 진단한 결과입니다.",
    )

    st.divider()
    st.subheader(f"담긴 항목 ({len(items)}개)")
    for index, item in enumerate(items):
        cols = st.columns([6, 1, 1, 1])
        cols[0].markdown(f"**{item['title']}**  \n<small>출처: {item['source']}</small>",
                         unsafe_allow_html=True)
        if cols[1].button("▲", key=f"up_{item['id']}", disabled=index == 0):
            my_report.move_item(item["id"], -1)
            st.rerun()
        if cols[2].button("▼", key=f"down_{item['id']}", disabled=index == len(items) - 1):
            my_report.move_item(item["id"], +1)
            st.rerun()
        if cols[3].button("🗑", key=f"del_{item['id']}"):
            my_report.remove_item(item["id"])
            st.rerun()

    st.divider()
    html = my_report.render_report_html({
        "title": report_title,
        "author": report_author,
        "date": date.today().isoformat(),
        "overview": overview,
    })
    st.download_button(
        "📥 HTML 보고서 내려받기",
        data=html,
        file_name="도서관_진단_보고서.html",
        mime="text/html",
    )
    if st.button("담은 항목 모두 비우기"):
        my_report.clear_items()
        st.rerun()
