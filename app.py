import streamlit as st
import runpy
import os

st.set_page_config(
    page_title="자동 데이터 분석 대시보드",
    page_icon="📊",
    layout="wide",
)

BASE_DIR = os.path.dirname(__file__)

pages = {
    "홈": None,
    "데이터 업로드 / 결합": "pages/01_데이터_업로드.py",
    "데이터 품질 점검": "pages/02_품질_점검.py",
    "데이터 정제": "pages/03_데이터_정제.py",
    "자동 시각화": "pages/04_자동_시각화.py",
    "직접 시각화": "pages/05_직접_시각화.py",
    "그룹별 집계": "pages/08_그룹_집계.py",
    "통계 분석": "pages/06_통계_분석.py",
    "회귀분석": "pages/09_회귀분석.py",
    "시계열 분석": "pages/10_시계열_분석.py",
    "보고서": "pages/07_보고서.py",
}

with st.sidebar:
    st.title("분석 메뉴")
    st.caption("데이터 분석 단계를 선택하세요.")

    # key="nav" : 홈 화면 카드 버튼으로도 페이지를 이동할 수 있게 합니다.
    selected_page = st.radio(
        "페이지 이동",
        list(pages.keys()),
        label_visibility="collapsed",
        key="nav",
    )

    st.divider()

    st.caption("분석 흐름")
    st.write(
        """
        1. 데이터 업로드 / 결합
        2. 품질 점검 (+ 상관관계)
        3. 데이터 정제
        4. 자동 / 직접 시각화
        5. 그룹별 집계
        6. 통계 분석 (모수 / 비모수)
        7. 회귀분석
        8. 시계열 분석
        9. 보고서
        """
    )

if pages[selected_page] is not None:
    page_path = os.path.join(BASE_DIR, pages[selected_page])
    runpy.run_path(page_path, run_name="__main__")
    st.stop()


# ============================================================
# 홈 화면
# ============================================================
st.title("📊 자동 데이터 분석 대시보드")

st.write(
    """
    CSV·Excel·JSON 파일을 올리면 **품질 점검 → 정제 → 시각화 → 그룹 집계 → 통계 분석 → 보고서**까지
    한 곳에서 진행할 수 있는 데이터 분석 대시보드입니다.
    상관관계 자동 인사이트, 교차분석, HTML 보고서 내보내기까지 지원합니다.
    """
)

st.info(
    "**처음이라면 이렇게 시작하세요**\n\n"
    "1. **데이터 업로드**에서 파일을 올립니다.\n"
    "2. **품질 점검 · 정제**로 데이터를 다듬습니다.\n"
    "3. **시각화 · 통계 분석**으로 살펴보고, **보고서**로 정리합니다.",
    icon="🚀",
)

st.divider()
st.subheader("기능 바로가기")


# 홈 카드를 누르면 해당 페이지로 이동합니다(사이드바 메뉴와 동일하게 동작).
def go(page_name):
    st.session_state["nav"] = page_name


cards = [
    ("📤", "데이터 업로드", "CSV·Excel·JSON을 올리고 여러 파일을 결합합니다.", "데이터 업로드 / 결합"),
    ("📋", "품질 점검", "결측·중복·타입 확인 + 주요 상관관계 자동 인사이트.", "데이터 품질 점검"),
    ("🧹", "데이터 정제", "결측·중복 처리, 타입 변경, 날짜 파생, 형태 변환.", "데이터 정제"),
    ("⚡", "자동 시각화", "데이터 구조를 감지해 그래프를 자동으로 생성합니다.", "자동 시각화"),
    ("🎨", "직접 시각화", "15종 차트를 직접 고르고 요약 해석을 자동 제공.", "직접 시각화"),
    ("🧮", "그룹별 집계", "그룹·피벗으로 집계합니다 (지역별 평균 매출 등).", "그룹별 집계"),
    ("📈", "통계 분석", "t검정·ANOVA·상관·교차·비모수 검정을 자동으로 골라 수행.", "통계 분석"),
    ("📉", "회귀분석", "단순·다중 선형회귀로 영향력과 설명력(R²)을 확인.", "회귀분석"),
    ("⏱️", "시계열 분석", "추세·이동평균·기간별 리샘플링으로 흐름을 분석.", "시계열 분석"),
    ("📝", "보고서", "분석 결과를 모아 HTML 보고서로 내보냅니다.", "보고서"),
]

cards_per_row = 4

for start in range(0, len(cards), cards_per_row):
    row = cards[start:start + cards_per_row]
    columns = st.columns(len(row))

    for column, (emoji, title, description, page_key) in zip(columns, row):
        with column:
            st.subheader(f"{emoji} {title}")
            st.write(description)
            st.button(
                "바로 가기 →",
                key=f"home_go_{page_key}",
                on_click=go,
                args=(page_key,),
                use_container_width=True,
            )
