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
    "보고서": "pages/07_보고서.py",
}
with st.sidebar:
    st.title("분석 메뉴")
    st.caption("데이터 분석 단계를 선택하세요.")

    selected_page = st.radio(
        "페이지 이동",
        list(pages.keys()),
        label_visibility="collapsed"
    )

    st.divider()

    st.caption("사용 흐름")
    st.write(
        """
        1. 데이터 업로드
        2. 품질 점검
        3. 데이터 정제
        4. 시각화
        5. 통계 분석
        6. 보고서
        """
    )

if pages[selected_page] is not None:
    page_path = os.path.join(BASE_DIR, pages[selected_page])
    runpy.run_path(page_path, run_name="__main__")
    st.stop()


st.title("자동 데이터 분석 대시보드")

st.write(
    """
    CSV, Excel 파일을 업로드하면 데이터 품질 점검, 정제, 시각화, 통계 분석까지
    단계별로 진행할 수 있는 Streamlit 기반 대시보드입니다.
    """
)

st.info("왼쪽 분석 메뉴에서 원하는 단계를 선택하세요.")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("데이터 업로드")
    st.write("CSV, Excel 파일을 업로드하고 여러 파일을 결합할 수 있습니다.")

with col2:
    st.subheader("품질 점검")
    st.write("결측치, 중복, 데이터 타입, 고유값 정보를 확인합니다.")

with col3:
    st.subheader("데이터 정제")
    st.write("중복 제거, 결측치 처리, 컬럼 삭제, 타입 변경을 적용합니다.")

col4, col5, col6 = st.columns(3)

with col4:
    st.subheader("시각화")
    st.write("분포, 비교, 관계, 추세를 다양한 차트로 확인합니다.")

with col5:
    st.subheader("통계 분석")
    st.write("상관분석과 가설검정 등 통계 기능을 확장할 수 있습니다.")

with col6:
    st.subheader("보고서")
    st.write("분석 결과를 파일로 저장하거나 공유할 수 있습니다.")
