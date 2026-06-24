import streamlit as st
import pandas as pd
import importlib

from helpers import my_plot

importlib.reload(my_plot)

#=================
def find_datetime_candidates(data):
    """
    날짜형으로 변환하면 좋을 것 같은 컬럼을 찾습니다.

    기준:
    1. 컬럼명에 날짜 관련 단어가 포함되어 있음
    2. 현재 타입이 날짜형이 아님
    3. 실제 값의 80% 이상이 날짜로 변환 가능함
    """

    date_keywords = [
        "날짜",
        "일자",
        "년월",
        "월일",
        "기준일",
        "등록일",
        "수정일",
        "date",
        "time",
        "created",
        "updated"
    ]

    candidates = []

    for column in data.columns:
        column_lower = str(column).lower()

        has_date_keyword = any(
            keyword in column_lower
            for keyword in date_keywords
        )

        if not has_date_keyword:
            continue

        if pd.api.types.is_datetime64_any_dtype(data[column]):
            continue

        converted = pd.to_datetime(
            data[column],
            errors="coerce"
        )

        success_ratio = converted.notna().mean()

        if success_ratio >= 0.8:
            candidates.append({
                "컬럼명": column,
                "현재 타입": str(data[column].dtype),
                "날짜 변환 가능 비율(%)": round(success_ratio * 100, 2)
            })

    return pd.DataFrame(candidates)
#======================

st.title("자동 시각화")

# ------------------------------------------------------------
# 1. 데이터 존재 여부 확인
# ------------------------------------------------------------
# 자동 시각화는 데이터가 있어야만 가능합니다.
# 원본 데이터는 업로드 페이지에서 st.session_state["data"]에 저장됩니다.
# ------------------------------------------------------------
if "data" not in st.session_state:
    st.warning("먼저 '데이터 업로드 / 결합' 페이지에서 CSV 파일을 업로드해주세요.")
    st.stop()


# ------------------------------------------------------------
# 2. 사용할 데이터 결정
# ------------------------------------------------------------
# 자동 시각화는 정제 데이터를 우선 사용합니다.
#
# 이유:
# - 정제 데이터는 결측치 처리, 타입 변경, 컬럼 삭제 등이 반영된 데이터입니다.
# - 자동 시각화는 사용자가 바로 해석할 수 있어야 하므로 정제 데이터가 더 적합합니다.
#
# 정제 데이터가 없다면 원본 데이터를 사용합니다.
# ------------------------------------------------------------
if "cleaned_data" in st.session_state:
    data = st.session_state["cleaned_data"]
    data_source_name = "정제 데이터"

    st.success("정제 데이터를 기준으로 자동 시각화를 생성합니다.")

else:
    data = st.session_state["data"]
    data_source_name = "원본 데이터"

    st.info("정제 데이터가 아직 없어서 원본 데이터를 기준으로 자동 시각화를 생성합니다.")

# ------------------------------------------------------------
# 2-1. 시각화 전 날짜 타입 점검
# ------------------------------------------------------------
# 자동 시각화에서 선그래프를 만들려면 날짜형 컬럼이 필요합니다.
#
# 그런데 CSV를 읽으면 날짜처럼 보이는 컬럼도 문자열(object)로 들어오는 경우가 많습니다.
# 예:
# - 날짜
# - 일자
# - 기준일
# - date
# - created_at
#
# 이런 컬럼을 찾아서 사용자에게 날짜형 변환을 추천합니다.
# 실제 변환은 데이터 정제 페이지에서 하도록 안내합니다.
# ------------------------------------------------------------
st.subheader("시각화 전 데이터 타입 점검")

datetime_candidates = find_datetime_candidates(data)

if not datetime_candidates.empty:
    st.warning(
        "날짜형으로 변환하면 좋은 컬럼이 있습니다. "
        "해당 컬럼을 날짜형으로 바꾸면 시간 흐름 그래프를 만들 수 있습니다."
    )

    st.dataframe(
        datetime_candidates,
        use_container_width=True
    )

    st.info(
        "데이터 정제 페이지에서 위 컬럼을 날짜형으로 변경한 뒤 "
        "정제 데이터를 저장하면 자동 시각화에서 선그래프를 생성할 수 있습니다."
    )

else:
    st.success("날짜형으로 추가 변환이 필요한 컬럼은 발견되지 않았습니다.")

# ------------------------------------------------------------
# 3. 현재 데이터 정보
# ------------------------------------------------------------
st.subheader("현재 데이터 정보")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("사용 데이터", data_source_name)

with col2:
    st.metric("행 개수", data.shape[0])

with col3:
    st.metric("열 개수", data.shape[1])


# ------------------------------------------------------------
# 4. 컬럼 타입 분류
# ------------------------------------------------------------
# 자동 시각화는 컬럼 타입에 따라 가능한 그래프를 생성합니다.
#
# 숫자형 컬럼:
# - 히스토그램, 산점도, 히트맵, 박스플롯에 사용
#
# 범주형 컬럼:
# - 막대그래프, 박스플롯 그룹, 선그래프 색상 구분에 사용
#
# 날짜형 컬럼:
# - 선그래프 X축에 사용
# ------------------------------------------------------------
numeric_columns = data.select_dtypes(include="number").columns.tolist()

categorical_columns = data.select_dtypes(
    include=["object", "category"]
).columns.tolist()

datetime_columns = data.select_dtypes(
    include=["datetime", "datetimetz"]
).columns.tolist()


col1, col2, col3 = st.columns(3)

with col1:
    st.metric("숫자형 컬럼 수", len(numeric_columns))

with col2:
    st.metric("범주형 컬럼 수", len(categorical_columns))

with col3:
    st.metric("날짜형 컬럼 수", len(datetime_columns))


# ------------------------------------------------------------
# 5. 자동 컬럼 선택 기준
# ------------------------------------------------------------
# 자동 시각화에서는 사용자가 직접 컬럼을 고르지 않습니다.
# 그래서 데이터 특성을 보고 적절한 컬럼을 자동으로 고릅니다.
#
# 숫자형 추천 컬럼:
# - 고유값이 많은 숫자형 컬럼
#
# 범주형 추천 컬럼:
# - 고유값이 2개 이상 20개 이하인 컬럼
#
# 색상 구분 컬럼:
# - 고유값이 2개 이상 10개 이하인 범주형 컬럼
# ------------------------------------------------------------
def get_best_numeric_column(data, numeric_columns):
    if not numeric_columns:
        return None

    return max(
        numeric_columns,
        key=lambda column: data[column].nunique()
    )


def get_best_categorical_column(data, categorical_columns, min_unique=2, max_unique=20):
    candidates = [
        column for column in categorical_columns
        if min_unique <= data[column].nunique() <= max_unique
    ]

    if not candidates:
        return None

    return candidates[0]


def get_best_color_column(data, categorical_columns):
    return get_best_categorical_column(
        data,
        categorical_columns,
        min_unique=2,
        max_unique=10
    )


best_numeric_column = get_best_numeric_column(data, numeric_columns)
best_categorical_column = get_best_categorical_column(data, categorical_columns)
best_color_column = get_best_color_column(data, categorical_columns)

# ------------------------------------------------------------
# 5-1. 데이터 구조 감지
# ------------------------------------------------------------
# 자동 시각화에서 중요한 것은 단순히 컬럼 타입만 보는 것이 아니라,
# 데이터가 어떤 구조인지 파악하는 것입니다.
#
# 여기서는 우선 두 가지 구조만 구분합니다.
#
# 1. 시계열 long 데이터
#    예:
#    날짜 | 구분 | 값
#    날짜 | 상품명 | 매출
#    일자 | 지역 | 인구
#
#    이런 데이터는 시간 흐름 선그래프와 그룹별 분포 그래프가 잘 맞습니다.
#
# 2. 일반 데이터
#    위 조건에 해당하지 않는 대부분의 CSV 데이터입니다.
# ------------------------------------------------------------
is_long_timeseries = (
    len(datetime_columns) >= 1
    and best_categorical_column is not None
    and best_numeric_column is not None
)

if is_long_timeseries:
    detected_data_type = "시계열 long 데이터"
else:
    detected_data_type = "일반 데이터"


st.subheader("감지된 데이터 구조")

st.write(f"현재 데이터는 **{detected_data_type}**로 판단되었습니다.")

if is_long_timeseries:
    st.info(
        "날짜형 컬럼, 범주형 컬럼, 숫자형 컬럼이 모두 있어 "
        "시간 흐름과 그룹별 비교 중심의 그래프를 생성합니다."
    )
else:
    st.info(
        "일반적인 데이터 구조로 판단되어 분포, 비교, 관계 중심의 그래프를 생성합니다."
    )

# ------------------------------------------------------------
# 6. 자동 시각화 생성
# ------------------------------------------------------------
# 감지된 데이터 구조에 따라 다른 그래프 세트를 보여줍니다.
#
# 시계열 long 데이터:
# - 시간 흐름
# - 그룹별 분포
# - 그룹별 평균
# - 전체 값 분포
#
# 일반 데이터:
# - 숫자형 분포
# - 범주형 개수
# - 숫자형 관계
# - 상관관계
# - 그룹별 분포
# ------------------------------------------------------------
st.subheader("자동 생성 그래프")

st.write("""
데이터 구조와 컬럼 타입을 기준으로 분석에 자주 사용하는 그래프를 자동 생성합니다.
조건에 맞는 그래프만 표시합니다.
""")


# ------------------------------------------------------------
# 6-A. 시계열 long 데이터용 자동 시각화
# ------------------------------------------------------------
if is_long_timeseries:
    date_column = datetime_columns[0]
    category_column = best_categorical_column
    value_column = best_numeric_column

    chart_data = data.sort_values(by=date_column)

    # --------------------------------------------------------
    # 1. 시간 흐름 선그래프
    # --------------------------------------------------------
    st.markdown("### 1. 시간 흐름 확인")

    st.caption(
        f"X축: {date_column}, Y축: {value_column}, 색상 구분: {category_column} / "
        "시간에 따라 값이 어떻게 변하는지 확인합니다."
    )

    fig = my_plot.make_line(
        chart_data,
        date_column,
        value_column,
        category_column
    )

    st.plotly_chart(fig, use_container_width=True)

    # --------------------------------------------------------
    # 2. 그룹별 분포 박스플롯
    # --------------------------------------------------------
    st.markdown("### 2. 그룹별 분포 확인")

    st.caption(
        f"그룹 컬럼: {category_column}, 값 컬럼: {value_column} / "
        "그룹별 값의 분포와 이상치를 확인합니다."
    )

    fig = my_plot.make_box(
        chart_data,
        value_column,
        category_column
    )

    st.plotly_chart(fig, use_container_width=True)

    # --------------------------------------------------------
    # 3. 그룹별 평균 막대그래프
    # --------------------------------------------------------
    st.markdown("### 3. 그룹별 평균 비교")

    st.caption(
        f"그룹 컬럼: {category_column}, 값 컬럼: {value_column} / "
        "그룹별 평균값을 비교합니다."
    )

    fig = my_plot.make_bar_aggregation(
        chart_data,
        category_column,
        value_column,
        "평균"
    )

    st.plotly_chart(fig, use_container_width=True)

    # --------------------------------------------------------
    # 4. 전체 값 분포 히스토그램
    # --------------------------------------------------------
    st.markdown("### 4. 전체 값 분포 확인")

    st.caption(
        f"값 컬럼: {value_column} / "
        "전체 값이 어떤 범위에 많이 분포하는지 확인합니다."
    )

    fig = my_plot.make_histogram(
        chart_data,
        value_column
    )

    st.plotly_chart(fig, use_container_width=True)


# ------------------------------------------------------------
# 6-B. 일반 데이터용 자동 시각화
# ------------------------------------------------------------
else:
    # --------------------------------------------------------
    # 1. 숫자형 분포 히스토그램
    # --------------------------------------------------------
    if best_numeric_column is not None:
        st.markdown("### 1. 숫자형 분포 확인")

        st.caption(
            f"선택 컬럼: {best_numeric_column} / "
            "숫자형 값이 어떻게 분포되어 있는지 확인합니다."
        )

        fig = my_plot.make_histogram(
            data,
            best_numeric_column
        )

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("숫자형 컬럼이 없어 히스토그램을 생성하지 않았습니다.")

    # --------------------------------------------------------
    # 2. 범주별 개수 막대그래프
    # --------------------------------------------------------
    if best_categorical_column is not None:
        st.markdown("### 2. 범주별 개수 비교")

        st.caption(
            f"선택 컬럼: {best_categorical_column} / "
            "범주별 데이터 개수를 비교합니다."
        )

        fig = my_plot.make_bar_count(
            data,
            best_categorical_column
        )

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("적절한 범주형 컬럼이 없어 막대그래프를 생성하지 않았습니다.")

    # --------------------------------------------------------
    # 3. 숫자형 변수 관계 산점도
    # --------------------------------------------------------
    if len(numeric_columns) >= 2:
        st.markdown("### 3. 숫자형 변수 관계 확인")

        scatter_columns = sorted(
            numeric_columns,
            key=lambda column: data[column].nunique(),
            reverse=True
        )[:2]

        x_column = scatter_columns[0]
        y_column = scatter_columns[1]

        st.caption(
            f"X축: {x_column}, Y축: {y_column} / "
            "두 숫자형 변수 사이의 관계를 확인합니다."
        )

        fig = my_plot.make_scatter(
            data,
            x_column,
            y_column,
            best_color_column
        )

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("숫자형 컬럼이 2개 미만이라 산점도를 생성하지 않았습니다.")

    # --------------------------------------------------------
    # 4. 상관관계 히트맵
    # --------------------------------------------------------
    if len(numeric_columns) >= 2:
        st.markdown("### 4. 상관관계 확인")

        heatmap_columns = sorted(
            numeric_columns,
            key=lambda column: data[column].nunique(),
            reverse=True
        )[:8]

        st.caption(
            f"선택 컬럼: {', '.join(heatmap_columns)} / "
            "숫자형 변수들 사이의 상관관계를 확인합니다."
        )

        fig = my_plot.make_correlation_heatmap(
            data,
            heatmap_columns
        )

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("숫자형 컬럼이 2개 미만이라 상관관계 히트맵을 생성하지 않았습니다.")

    # --------------------------------------------------------
    # 5. 그룹별 분포 박스플롯
    # --------------------------------------------------------
    if best_numeric_column is not None and best_categorical_column is not None:
        st.markdown("### 5. 그룹별 분포 확인")

        st.caption(
            f"그룹 컬럼: {best_categorical_column}, 값 컬럼: {best_numeric_column} / "
            "그룹별 분포와 이상치를 확인합니다."
        )

        fig = my_plot.make_box(
            data,
            best_numeric_column,
            best_categorical_column
        )

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("숫자형 컬럼과 적절한 범주형 컬럼이 부족해 박스플롯을 생성하지 않았습니다.")