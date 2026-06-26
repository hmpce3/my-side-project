import streamlit as st
import pandas as pd

from helpers import my_data


st.title("데이터 품질 점검")


# ------------------------------------------------------------
# 1. 업로드된 데이터가 있는지 확인
# ------------------------------------------------------------
# 이 페이지는 업로드된 데이터가 있어야 작동합니다.
# 데이터 업로드 페이지에서 아래처럼 저장한 데이터를 사용합니다.
#
# st.session_state["data"] = data
# ------------------------------------------------------------
if "data" not in st.session_state:
    st.warning("먼저 '데이터 업로드 / 결합' 페이지에서 데이터 파일을 업로드해주세요.")
    st.stop()

# ------------------------------------------------------------
# 분석에 사용할 데이터 범위 선택
# ------------------------------------------------------------
# sample_data가 없으면 현재 전체 데이터에서 샘플 데이터를 새로 만듭니다.
# 이렇게 하면 업로드 페이지에서 sample_data 저장이 누락되어도 선택창이 표시됩니다.
# ------------------------------------------------------------
if "sample_data" not in st.session_state:
    st.session_state["sample_data"] = my_data.make_sample_data(
        st.session_state["data"],
        sample_size=5000
    )

data_scope = st.radio(
    "품질 점검에 사용할 데이터 범위를 선택하세요",
    ["빠른 분석용 샘플 데이터", "전체 데이터"],
    horizontal=True
)

if data_scope == "빠른 분석용 샘플 데이터":
    data = st.session_state["sample_data"]

    st.info(
        f"현재 {len(data):,}행의 샘플 데이터로 품질 점검을 수행합니다."
    )

else:
    data = st.session_state["data"]

    st.warning(
        f"현재 {len(data):,}행의 전체 데이터로 품질 점검을 수행합니다. "
        "데이터가 크면 시간이 오래 걸릴 수 있습니다."
    )


# ------------------------------------------------------------
# 데이터 기본 정보
# ------------------------------------------------------------
st.subheader("데이터 기본 정보")


# ------------------------------------------------------------
# 4. 데이터 미리보기
# ------------------------------------------------------------
st.subheader("데이터 미리보기")
st.dataframe(data.head(), use_container_width=True)


# ------------------------------------------------------------
# 5. 데이터 품질 요약
# ------------------------------------------------------------
# 전체 결측치:
# - 데이터 전체에서 비어 있는 값의 개수
#
# 중복 행:
# - 모든 컬럼 값이 완전히 같은 행의 개수
# ------------------------------------------------------------
st.subheader("데이터 품질 요약")

missing_count = data.isnull().sum().sum()
duplicate_count = data.duplicated().sum()

col1, col2 = st.columns(2)

with col1:
    st.metric("전체 결측치", missing_count)

with col2:
    st.metric("중복 행", duplicate_count)


# ------------------------------------------------------------
# 6. 열별 정보
# ------------------------------------------------------------
# 각 컬럼별로 데이터 타입, 결측치, 고유값 개수를 확인합니다.
#
# 이 표를 보면:
# - 숫자로 보여야 하는데 object로 잡힌 컬럼
# - 결측치가 많은 컬럼
# - 고유값이 너무 많은 컬럼
# 등을 빠르게 확인할 수 있습니다.
# ------------------------------------------------------------
st.subheader("열별 정보")

column_info = pd.DataFrame({
    "열 이름": data.columns,
    "데이터 타입": data.dtypes.astype(str).values,
    "결측치 개수": data.isnull().sum().values,
    "결측치 비율(%)": (data.isnull().mean() * 100).round(2).values,
    "고유값 개수": data.nunique().values
})

st.dataframe(column_info, use_container_width=True)


# ------------------------------------------------------------
# 7. 숫자형 기술통계량
# ------------------------------------------------------------
# 기존에는 data.describe().T를 사용했습니다.
# 이제는 helpers/my_data.py에 이미 만들어둔 numerical_summary()를 사용합니다.
#
# 이 함수는 기본 describe 값뿐만 아니라:
# - IQR
# - 이상치 개수
# - 이상치 비율
# - 왜도
# - 첨도
# - 로그 변환 필요 여부
# 등을 함께 계산합니다.
# ------------------------------------------------------------
st.subheader("숫자형 기술통계량")

numeric_summary = my_data.numerical_summary(data)

if numeric_summary.empty:
    st.info("숫자형 컬럼이 없습니다.")
else:
    st.dataframe(
        numeric_summary.round(3),
        use_container_width=True
    )


# ------------------------------------------------------------
# 8. 문자형 / 범주형 데이터 요약
# ------------------------------------------------------------
# 기존 categorical_summary() 함수는 수업/노트북용이라
# print(), display()가 포함되어 있습니다.
#
# Streamlit 화면에서는 categorical_summary_for_app()을 사용하는 것이 좋습니다.
#
# 이 함수는:
# - 열 이름
# - 데이터 타입
# - 고유값 개수
# - 결측치 개수
# - 결측치 비율
# - 최빈값
# - 최빈값 빈도
# 를 표로 반환합니다.
# ------------------------------------------------------------
st.subheader("범주형 데이터 요약")

categorical_summary = my_data.categorical_summary_for_app(data)

if categorical_summary.empty:
    st.info("문자형 또는 카테고리형 컬럼이 없습니다.")
else:
    st.dataframe(
        categorical_summary,
        use_container_width=True
    )