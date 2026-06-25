import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.figure_factory as ff
from helpers import my_plot


# ------------------------------------------------------------
# 1. 페이지 제목
# ------------------------------------------------------------
st.title("시각화")


# ------------------------------------------------------------
# 2. 데이터 업로드 여부 확인
# ------------------------------------------------------------
# 시각화는 데이터가 있어야만 가능합니다.
# 데이터 업로드 페이지에서 st.session_state["data"]에 저장한 데이터를 사용합니다.
# ------------------------------------------------------------
if "data" not in st.session_state:
    st.warning("먼저 '데이터 업로드 / 결합' 페이지에서 CSV 파일을 업로드해주세요.")
    st.stop()

# ------------------------------------------------------------
# 시각화에 사용할 데이터 선택
# ------------------------------------------------------------
# 정제 데이터가 있으면 정제 데이터를 기본값으로 먼저 보여줍니다.
# 직접 시각화는 사용자가 실제 분석에 쓸 데이터를 보는 화면이므로
# 원본보다 정제 데이터가 우선되는 편이 자연스럽습니다.
# ------------------------------------------------------------
if "cleaned_data" in st.session_state:
    data_options = {
        "정제 데이터": st.session_state["cleaned_data"],
        "원본 데이터": st.session_state["data"],
    }
else:
    data_options = {
        "원본 데이터": st.session_state["data"],
    }

st.caption("시각화에 사용할 데이터")

data_source = st.radio(
    "시각화에 사용할 데이터를 선택하세요",
    list(data_options.keys()),
    horizontal=True,
    label_visibility="collapsed",
)

selected_data = data_options[data_source]


# ------------------------------------------------------------
# 원본 데이터는 샘플/전체를 선택할 수 있게 합니다.
# 정제 데이터는 현재 저장된 정제 데이터 전체를 사용합니다.
# ------------------------------------------------------------
if data_source == "원본 데이터" and "sample_data" in st.session_state:
    data_scope = st.radio(
        "원본 데이터 범위",
        ["빠른 분석용 샘플 데이터", "전체 데이터"],
        horizontal=True,
    )

    if data_scope == "빠른 분석용 샘플 데이터":
        data = st.session_state["sample_data"]
        data_source_name = "원본 데이터 - 샘플"

    else:
        data = st.session_state["data"]
        data_source_name = "원본 데이터 - 전체"

else:
    data = selected_data
    data_source_name = data_source

st.caption(
    f"현재 {len(data):,}행의 {data_source_name}로 직접 시각화를 생성합니다."
)

# ------------------------------------------------------------
# 직접 시각화에서 제외할 관리용 컬럼 설정
# ------------------------------------------------------------
# __source_file__은 여러 파일을 결합했을 때
# 각 행이 어느 파일에서 왔는지 확인하기 위한 컬럼입니다.
#
# 직접 시각화에서 축, 색상, 필터 후보로 계속 보이면
# 분석용 변수와 헷갈릴 수 있으므로 기본 후보에서는 제외합니다.
# ------------------------------------------------------------
exclude_columns = ["__source_file__"]

chart_data = data.drop(
    columns=exclude_columns,
    errors="ignore"
)

# ------------------------------------------------------------
# 3. 색상 팔레트 관련 함수
# ------------------------------------------------------------
# Plotly에서 제공하는 색상 팔레트를 사용합니다.
# 사용자는 기본 팔레트를 고르거나, 일부 그래프에서 직접 색상을 지정할 수 있습니다.
# ------------------------------------------------------------
def get_color_palette(palette_name):
    palette_map = {
        "Set2": px.colors.qualitative.Set2,
        "Pastel": px.colors.qualitative.Pastel,
        "Bold": px.colors.qualitative.Bold,
        "Dark2": px.colors.qualitative.Dark2,
        "Plotly": px.colors.qualitative.Plotly,
        "D3": px.colors.qualitative.D3,
        "G10": px.colors.qualitative.G10,
        "Safe": px.colors.qualitative.Safe,
    }

    return palette_map.get(palette_name, px.colors.qualitative.Set2)


def rgb_to_hex(color):
    # Plotly 팔레트 색상이 rgb(102, 197, 204) 형태일 때
    # Streamlit color_picker에서 사용할 수 있는 #66C5CC 형태로 바꿉니다.
    if color.startswith("#"):
        return color

    if color.startswith("rgb"):
        rgb_values = (
            color
            .replace("rgb(", "")
            .replace(")", "")
            .split(",")
        )

        r = int(rgb_values[0].strip())
        g = int(rgb_values[1].strip())
        b = int(rgb_values[2].strip())

        return f"#{r:02X}{g:02X}{b:02X}"

    return "#66C5CC"


def make_color_map(data, color_column, palette_colors, key_prefix):
    # 범례가 있는 그래프에서 범례값마다 색상을 직접 지정할 수 있게 합니다.
    # 예: 지역 컬럼이 색상 기준이면 서울, 부산, 대구 각각 색상을 고를 수 있습니다.
    color_map = {}

    if color_column is None:
        return color_map

    unique_values = (
        data[color_column]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    use_custom_colors = st.checkbox(
        "범례별 색상을 직접 지정합니다",
        key=f"{key_prefix}_use_custom_colors",
    )

    if use_custom_colors:
        columns_per_row = 4

        for start_index in range(0, len(unique_values), columns_per_row):
            row_values = unique_values[start_index:start_index + columns_per_row]
            color_columns = st.columns(len(row_values))

            for column_index, value in enumerate(row_values):
                with color_columns[column_index]:
                    color_index = start_index + column_index
                    default_color = rgb_to_hex(
                        palette_colors[color_index % len(palette_colors)]
                    )

                    selected_color = st.color_picker(
                        value,
                        value=default_color,
                        key=f"{key_prefix}_color_{value}",
                    )

                    color_map[value] = selected_color

    return color_map


def choose_single_color(default_color, key_prefix):
    # 범례가 없는 그래프에서 사용할 단일 색상을 선택합니다.
    return st.color_picker(
        "그래프 색상",
        value=rgb_to_hex(default_color),
        key=f"{key_prefix}_single_color",
    )





# ------------------------------------------------------------
# 현재 데이터 정보
# ------------------------------------------------------------
# 큰 metric 카드 대신 한 줄 요약으로 보여줘서
# 그래프 설정 영역까지 내려가는 거리를 줄입니다.
# ------------------------------------------------------------
st.caption(
    f"현재 데이터: {data_source_name} | 행 {data.shape[0]:,}개 | 열 {data.shape[1]:,}개"
)

# ------------------------------------------------------------
# 6. 데이터 필터
# ------------------------------------------------------------
# 필터는 필요할 때만 열어보는 보조 기능이므로
# 기본 상태에서는 접어두어 화면을 더 간결하게 만듭니다.
# 필터를 적용한 결과는 filtered_data에 저장됩니다.
# ------------------------------------------------------------
filtered_data = data.copy()

with st.expander("데이터 필터", expanded=False):
    filter_columns = st.multiselect(
        "필터를 적용할 컬럼",
        data.columns.tolist(),
    )

    for column in filter_columns:
        if pd.api.types.is_numeric_dtype(filtered_data[column]):
            min_value = float(filtered_data[column].min())
            max_value = float(filtered_data[column].max())

            if min_value == max_value:
                st.info(f"{column} 컬럼은 모든 값이 같아서 범위 필터를 적용할 수 없습니다.")
                continue

            selected_range = st.slider(
                f"{column} 범위",
                min_value=min_value,
                max_value=max_value,
                value=(min_value, max_value),
            )

            filtered_data = filtered_data[
                filtered_data[column].between(
                    selected_range[0],
                    selected_range[1],
                )
            ]

        else:
            unique_values = (
                filtered_data[column]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )

            selected_values = st.multiselect(
                f"{column}에서 포함할 값",
                unique_values,
                default=unique_values,
            )

            filtered_data = filtered_data[
                filtered_data[column].astype(str).isin(selected_values)
            ]

    st.caption(
        f"전체 {len(data):,}행 중 {len(filtered_data):,}행이 선택되었습니다."
    )

# 필터가 접혀 있어도 현재 선택 행 수는 화면에서 바로 확인할 수 있게 작게 표시합니다.
st.caption(
    f"분석 대상: {len(filtered_data):,}행"
)

if filtered_data.empty:
    st.warning("필터 결과가 비어 있습니다. 필터 조건을 다시 선택해주세요.")
    st.stop()


# ------------------------------------------------------------
# 7. 컬럼 타입 분류
# ------------------------------------------------------------
# 그래프마다 필요한 컬럼 타입이 다르기 때문에 미리 분류해둡니다.
# ------------------------------------------------------------
numeric_columns = chart_data.select_dtypes(include="number").columns.tolist()

categorical_columns = chart_data.select_dtypes(
    include=["object", "category"]
).columns.tolist()

datetime_columns = chart_data.select_dtypes(
    include=["datetime", "datetimetz"]
).columns.tolist()


st.subheader("시각화 만들기")

# ------------------------------------------------------------
# 공통 그래프 설정
# ------------------------------------------------------------
# 가장 먼저 차트 종류만 선택합니다.
# 색상 팔레트는 차트별 옵션 흐름에 맞게 아래쪽에서 선택하도록 합니다.
# ------------------------------------------------------------
chart_type = st.selectbox(
    "차트 종류",
    [
        "히스토그램",
        "KDE 플롯",
        "막대그래프",
        "지도",
        "산점도",
        "회귀선 산점도",
        "선그래프",
        "박스플롯",
        "바이올린 플롯",
        "상관관계 히트맵",
        "Pair Plot",
        "파이 차트",
        "도넛 차트",
        "누적 막대그래프",
        "카운트 플롯"
    ],
)

# 다른 그래프 블록에서 palette_name을 계속 사용하므로 기본값은 유지합니다.
# 막대그래프처럼 색상 옵션을 따로 둔 차트에서는 아래에서 다시 선택합니다.
palette_name = "Set2"
palette_colors = get_color_palette(palette_name)


# ------------------------------------------------------------
# 9. 히스토그램
# ------------------------------------------------------------
# 숫자형 컬럼 하나의 분포를 확인합니다.
# 색상 기준 컬럼을 선택하면 범주별로 색상이 나뉩니다.
# ------------------------------------------------------------
if chart_type == "히스토그램":
    if not numeric_columns:
        st.warning("히스토그램을 만들 숫자형 컬럼이 없습니다.")

    else:
        selected_column = st.selectbox(
            "분포를 확인할 숫자형 컬럼",
            numeric_columns,
        )

        color_column = st.selectbox(
            "색상 기준 컬럼",
            ["선택 안 함"] + categorical_columns,
        )

        if color_column == "선택 안 함":
            selected_color = choose_single_color(palette_colors[0], "histogram")

            fig = px.histogram(
                filtered_data,
                x=selected_column,
                title=f"{selected_column} 분포",
                color_discrete_sequence=[selected_color],
            )

        else:
            color_map = make_color_map(
                filtered_data,
                color_column,
                palette_colors,
                "histogram",
            )

            fig = px.histogram(
                filtered_data,
                x=selected_column,
                color=color_column,
                title=f"{selected_column} 분포",
                color_discrete_sequence=palette_colors,
                color_discrete_map=color_map,
            )

        st.plotly_chart(fig, use_container_width=True)


# ------------------------------------------------------------
# 10. KDE 플롯
# ------------------------------------------------------------
# 숫자형 컬럼의 부드러운 분포선을 보여줍니다.
# ------------------------------------------------------------
elif chart_type == "KDE 플롯":
    if not numeric_columns:
        st.warning("KDE 플롯을 만들 숫자형 컬럼이 없습니다.")

    else:
        selected_column = st.selectbox(
            "분포를 확인할 숫자형 컬럼",
            numeric_columns,
        )

        selected_color = choose_single_color(palette_colors[0], "kde")

        values = filtered_data[selected_column].dropna()

        if values.empty:
            st.warning("선택한 컬럼에 표시할 값이 없습니다.")

        else:
            fig = ff.create_distplot(
                [values],
                [selected_column],
                show_hist=False,
                show_rug=False,
                colors=[selected_color],
            )

            fig.update_layout(
                title=f"{selected_column} KDE 플롯",
                xaxis_title=selected_column,
                yaxis_title="density",
            )

            st.plotly_chart(fig, use_container_width=True)


# ------------------------------------------------------------
# 11. 막대그래프
# ------------------------------------------------------------
# 범주별 개수, 합계, 평균, 최댓값, 최솟값을 비교합니다.
# ------------------------------------------------------------
elif chart_type == "막대그래프":
    if not categorical_columns:
        st.warning("막대그래프의 기준이 될 범주형 컬럼이 없습니다.")

    else:
        # ----------------------------------------------------
        # 1) 핵심 설정
        # ----------------------------------------------------
        # 막대그래프에서 가장 먼저 정해야 하는 것은
        # 기준 컬럼과 집계 방식입니다.
        # ----------------------------------------------------
        basic_col1, basic_col2 = st.columns(2)

        with basic_col1:
            x_column = st.selectbox(
                "막대그래프 기준 컬럼",
                categorical_columns,
            )

        with basic_col2:
            aggregation_method = st.selectbox(
                "집계 방식",
                ["개수", "합계", "평균", "최댓값", "최솟값"],
            )

        if aggregation_method != "개수":
            if not numeric_columns:
                st.warning("집계할 숫자형 컬럼이 없습니다.")
                st.stop()

            y_column = st.selectbox(
                "집계할 숫자형 컬럼",
                numeric_columns,
            )

        # ----------------------------------------------------
        # 2) 표시 옵션
        # ----------------------------------------------------
        # 범주가 많을 때는 Top N으로 줄여서 보고,
        # 정렬 방식으로 그래프의 읽는 순서를 조정합니다.
        # ----------------------------------------------------
        display_col1, display_col2 = st.columns(2)

        with display_col1:
            top_n_option = st.selectbox(
                "표시할 범주 수",
                ["전체", "Top 5", "Top 10", "Top 20", "Top 30"],
                index=0,
            )

        with display_col2:
            sort_option = st.selectbox(
                "정렬 방식",
                [
                    "값 큰 순",
                    "값 작은 순",
                    "이름 오름차순",
                    "이름 내림차순",
                ],
                index=0,
            )

        # ----------------------------------------------------
        # 3) 색상 옵션
        # ----------------------------------------------------
        # 색상은 그래프의 보조 설정이므로
        # 컬럼과 집계 방식을 정한 뒤에 선택하게 배치합니다.
        # ----------------------------------------------------
        color_col1, color_col2 = st.columns(2)

        with color_col1:
            use_category_colors = st.checkbox(
                "막대별 색상 구분",
                value=True,
                key="bar_use_category_colors",
            )

        with color_col2:
            palette_name = st.selectbox(
                "색상 팔레트",
                ["Set2", "Pastel", "Bold", "Dark2", "Plotly", "D3", "G10", "Safe"],
                index=0,
                key="bar_palette_name",
            )

        palette_colors = get_color_palette(palette_name)

        # ----------------------------------------------------
        # 4) 그래프용 데이터 만들기
        # ----------------------------------------------------
        # 개수는 value_counts로 계산하고,
        # 합계/평균/최댓값/최솟값은 groupby 집계로 계산합니다.
        # ----------------------------------------------------
        if aggregation_method == "개수":
            chart_data = (
                filtered_data[x_column]
                .fillna("결측치")
                .astype(str)
                .value_counts()
                .reset_index()
            )

            chart_data.columns = [x_column, "개수"]
            y_column = "개수"

        else:
            agg_map = {
                "합계": "sum",
                "평균": "mean",
                "최댓값": "max",
                "최솟값": "min",
            }

            chart_data = (
                filtered_data
                .groupby(x_column, dropna=False, as_index=False)[y_column]
                .agg(agg_map[aggregation_method])
            )

            chart_data[x_column] = chart_data[x_column].fillna("결측치").astype(str)

        # ----------------------------------------------------
        # 5) 정렬 적용
        # ----------------------------------------------------
        if sort_option == "값 큰 순":
            chart_data = chart_data.sort_values(y_column, ascending=False)

        elif sort_option == "값 작은 순":
            chart_data = chart_data.sort_values(y_column, ascending=True)

        elif sort_option == "이름 오름차순":
            chart_data = chart_data.sort_values(x_column, ascending=True)

        elif sort_option == "이름 내림차순":
            chart_data = chart_data.sort_values(x_column, ascending=False)

        # ----------------------------------------------------
        # 6) Top N 적용
        # ----------------------------------------------------
        if top_n_option != "전체":
            top_n = int(top_n_option.replace("Top ", ""))
            chart_data = chart_data.head(top_n)

        # ----------------------------------------------------
        # 7) 그래프 생성
        # ----------------------------------------------------
        if use_category_colors:
            color_map = make_color_map(
                chart_data,
                x_column,
                palette_colors,
                "bar",
            )

            fig = px.bar(
                chart_data,
                x=x_column,
                y=y_column,
                color=x_column,
                title=f"{x_column}별 {y_column} {aggregation_method}",
                color_discrete_sequence=palette_colors,
                color_discrete_map=color_map,
            )

        else:
            selected_color = choose_single_color(palette_colors[0], "bar")

            fig = px.bar(
                chart_data,
                x=x_column,
                y=y_column,
                title=f"{x_column}별 {y_column} {aggregation_method}",
                color_discrete_sequence=[selected_color],
            )

            fig.update_traces(marker_color=selected_color)

        # ----------------------------------------------------
        # 정렬된 순서가 그래프에도 그대로 보이게 합니다.
        # ----------------------------------------------------
        fig.update_layout(
            xaxis={
                "categoryorder": "array",
                "categoryarray": chart_data[x_column].tolist(),
            }
        )

        st.plotly_chart(fig, use_container_width=True)

        # ----------------------------------------------------
        # 막대그래프 해석 요약
        # ----------------------------------------------------
        # 현재 화면에 표시된 chart_data를 기준으로
        # 최댓값/최솟값과 동률 여부를 간단히 설명합니다.
        # 값이 모두 같은 경우에는 비교 차이가 없다는 문구를 보여줍니다.
        # ----------------------------------------------------
        if not chart_data.empty:
            max_value = chart_data[y_column].max()
            min_value = chart_data[y_column].min()

            max_categories = (
                chart_data.loc[chart_data[y_column] == max_value, x_column]
                .astype(str)
                .tolist()
            )

            min_categories = (
                chart_data.loc[chart_data[y_column] == min_value, x_column]
                .astype(str)
                .tolist()
            )

            if max_value == min_value:
                summary_text = (
                    f"요약: 현재 표시된 {len(chart_data):,}개 범주의 "
                    f"{y_column} 값이 모두 동일합니다({max_value:,.2f})."
                )

            else:
                max_category_text = ", ".join(max_categories[:3])
                min_category_text = ", ".join(min_categories[:3])

                if len(max_categories) > 3:
                    max_category_text += f" 외 {len(max_categories) - 3}개"

                if len(min_categories) > 3:
                    min_category_text += f" 외 {len(min_categories) - 3}개"

                summary_text = (
                    f"요약: 현재 표시된 {len(chart_data):,}개 범주 중 "
                    f"{max_category_text}의 {y_column} 값이 가장 크고({max_value:,.2f}), "
                    f"{min_category_text}의 {y_column} 값이 가장 작습니다({min_value:,.2f})."
                )

            st.markdown(f"**{summary_text}**")


# ------------------------------------------------------------
# 12. 카운트 플롯
# ------------------------------------------------------------
# 범주형 컬럼의 값 개수를 확인합니다.
# 색상 기준 컬럼을 추가하면 그룹별 개수를 나누어 볼 수 있습니다.
# ------------------------------------------------------------
elif chart_type == "카운트 플롯":
    if not categorical_columns:
        st.warning("카운트 플롯을 만들 범주형 컬럼이 없습니다.")

    else:
        x_column = st.selectbox(
            "개수를 확인할 범주형 컬럼",
            categorical_columns,
        )

        color_column = st.selectbox(
            "색상 기준 컬럼",
            ["선택 안 함"] + categorical_columns,
        )

        if color_column == "선택 안 함":
            color_column = x_column

        color_map = make_color_map(
            filtered_data,
            color_column,
            palette_colors,
            "count",
        )

        fig = px.histogram(
            filtered_data,
            x=x_column,
            color=color_column,
            barmode="group",
            title=f"{x_column} 카운트 플롯",
            color_discrete_sequence=palette_colors,
            color_discrete_map=color_map,
        )

        st.plotly_chart(fig, use_container_width=True)


# ------------------------------------------------------------
# 13. 산점도
# ------------------------------------------------------------
# 숫자형 컬럼 2개의 관계를 확인합니다.
# 범주형 컬럼을 색상 기준으로 선택하면 그룹별 패턴을 볼 수 있습니다.
# ------------------------------------------------------------
elif chart_type == "산점도":
    if len(numeric_columns) < 2:
        st.warning("산점도를 만들려면 숫자형 컬럼이 2개 이상 필요합니다.")

    else:
        x_column = st.selectbox(
            "X축 숫자형 컬럼",
            numeric_columns,
        )

        y_column = st.selectbox(
            "Y축 숫자형 컬럼",
            numeric_columns,
            index=1,
        )

        color_column = st.selectbox(
            "색상 기준 컬럼",
            ["선택 안 함"] + categorical_columns,
        )

        if color_column == "선택 안 함":
            selected_color = choose_single_color(palette_colors[0], "scatter")

            fig = px.scatter(
                filtered_data,
                x=x_column,
                y=y_column,
                title=f"{x_column}와 {y_column}의 관계",
                color_discrete_sequence=[selected_color],
            )

            fig.update_traces(marker_color=selected_color)

        else:
            color_map = make_color_map(
                filtered_data,
                color_column,
                palette_colors,
                "scatter",
            )

            fig = px.scatter(
                filtered_data,
                x=x_column,
                y=y_column,
                color=color_column,
                title=f"{x_column}와 {y_column}의 관계",
                color_discrete_sequence=palette_colors,
                color_discrete_map=color_map,
            )

        st.plotly_chart(fig, use_container_width=True)


# ------------------------------------------------------------
# 14. 회귀선 산점도
# ------------------------------------------------------------
# 산점도에 회귀선을 함께 표시합니다.
# trendline="ols"는 statsmodels 패키지가 필요합니다.
# ------------------------------------------------------------
elif chart_type == "회귀선 산점도":
    if len(numeric_columns) < 2:
        st.warning("회귀선 산점도를 만들려면 숫자형 컬럼이 2개 이상 필요합니다.")

    else:
        x_column = st.selectbox(
            "X축 숫자형 컬럼",
            numeric_columns,
        )

        y_column = st.selectbox(
            "Y축 숫자형 컬럼",
            numeric_columns,
            index=1,
        )

        color_column = st.selectbox(
            "색상 기준 컬럼",
            ["선택 안 함"] + categorical_columns,
        )

        try:
            if color_column == "선택 안 함":
                selected_color = choose_single_color(palette_colors[0], "lm")

                fig = px.scatter(
                    filtered_data,
                    x=x_column,
                    y=y_column,
                    trendline="ols",
                    title=f"{x_column}와 {y_column}의 관계와 회귀선",
                    color_discrete_sequence=[selected_color],
                )

                fig.update_traces(marker_color=selected_color)

            else:
                color_map = make_color_map(
                    filtered_data,
                    color_column,
                    palette_colors,
                    "lm",
                )

                fig = px.scatter(
                    filtered_data,
                    x=x_column,
                    y=y_column,
                    color=color_column,
                    trendline="ols",
                    title=f"{x_column}와 {y_column}의 관계와 회귀선",
                    color_discrete_sequence=palette_colors,
                    color_discrete_map=color_map,
                )

            st.plotly_chart(fig, use_container_width=True)

        except ModuleNotFoundError:
            st.error("회귀선을 그리려면 statsmodels 패키지가 필요합니다.")
            st.code(".\\.venv\\Scripts\\python.exe -m pip install statsmodels")


# ------------------------------------------------------------
# 15. 선그래프
# ------------------------------------------------------------
# 시간 흐름이나 순서에 따른 숫자값 변화를 확인합니다.
# ------------------------------------------------------------
elif chart_type == "선그래프":
    if not numeric_columns:
        st.warning("선그래프의 Y축에 사용할 숫자형 컬럼이 없습니다.")

    else:
        st.write("시간 흐름이나 순서에 따른 숫자형 값의 변화를 확인합니다.")

        possible_x_columns = datetime_columns + categorical_columns + numeric_columns

        x_column = st.selectbox(
            "X축 컬럼을 선택하세요",
            possible_x_columns
        )

        y_column = st.selectbox(
            "Y축 숫자형 컬럼을 선택하세요",
            numeric_columns
        )

        color_column = st.selectbox(
            "선 색상으로 구분할 컬럼을 선택하세요",
            ["선택 안 함"] + categorical_columns
        )

        if color_column == "선택 안 함":
            color_column = None

        chart_data = filtered_data.copy()

        # ----------------------------------------------------
        # 날짜형 X축일 경우 날짜 단위와 집계 방식을 선택할 수 있게 합니다.
        # ----------------------------------------------------
        is_datetime_x = pd.api.types.is_datetime64_any_dtype(chart_data[x_column])

        if is_datetime_x:
            st.subheader("선그래프 집계 옵션")

            date_unit = st.selectbox(
                "날짜 단위를 선택하세요",
                ["원본 그대로", "일별", "주별", "월별", "연도별"]
            )

            aggregation_method = st.selectbox(
                "집계 방식을 선택하세요",
                ["평균", "합계", "최댓값", "최솟값"]
            )

            agg_map = {
                "평균": "mean",
                "합계": "sum",
                "최댓값": "max",
                "최솟값": "min"
            }

            # 원본 그대로가 아니면 날짜를 선택한 단위로 변환합니다.
            if date_unit != "원본 그대로":
                if date_unit == "일별":
                    chart_data["날짜_단위"] = chart_data[x_column].dt.to_period("D").dt.to_timestamp()

                elif date_unit == "주별":
                    chart_data["날짜_단위"] = chart_data[x_column].dt.to_period("W").dt.start_time

                elif date_unit == "월별":
                    chart_data["날짜_단위"] = chart_data[x_column].dt.to_period("M").dt.to_timestamp()

                elif date_unit == "연도별":
                    chart_data["날짜_단위"] = chart_data[x_column].dt.to_period("Y").dt.to_timestamp()

                group_columns = ["날짜_단위"]

                if color_column is not None:
                    group_columns.append(color_column)

                chart_data = (
                    chart_data
                    .groupby(group_columns, as_index=False)[y_column]
                    .agg(agg_map[aggregation_method])
                )

                x_column_for_chart = "날짜_단위"

            else:
                x_column_for_chart = x_column

            chart_data = chart_data.sort_values(by=x_column_for_chart)

        else:
            st.info(
                "X축이 날짜형이 아니므로 날짜 단위 집계 옵션은 적용하지 않습니다."
            )

            x_column_for_chart = x_column
            chart_data = chart_data.sort_values(by=x_column_for_chart)

        default_colors = my_plot.get_color_palette(palette_name)

        color_map = make_color_map(
            chart_data,
            color_column,
            default_colors,
            key_prefix="line"
        )

        fig = my_plot.make_line(
            chart_data,
            x_column_for_chart,
            y_column,
            color_column,
            palette_name,
            color_map
        )

        st.plotly_chart(fig, use_container_width=True)


# ------------------------------------------------------------
# 16. 박스플롯
# ------------------------------------------------------------
# 숫자형 데이터의 분포와 이상치를 확인합니다.
# 그룹 컬럼을 선택하면 그룹별 색상이 적용됩니다.
# ------------------------------------------------------------
elif chart_type == "박스플롯":
    if not numeric_columns:
        st.warning("박스플롯을 만들 숫자형 컬럼이 없습니다.")

    else:
        y_column = st.selectbox(
            "분포를 확인할 숫자형 컬럼",
            numeric_columns,
        )

        x_column = st.selectbox(
            "그룹 컬럼",
            ["선택 안 함"] + categorical_columns,
        )

        if x_column == "선택 안 함":
            selected_color = choose_single_color(palette_colors[0], "box")

            fig = px.box(
                filtered_data,
                y=y_column,
                points="outliers",
                title=f"{y_column} 박스플롯",
                color_discrete_sequence=[selected_color],
            )

            fig.update_traces(marker_color=selected_color)

        else:
            color_map = make_color_map(
                filtered_data,
                x_column,
                palette_colors,
                "box",
            )

            fig = px.box(
                filtered_data,
                x=x_column,
                y=y_column,
                color=x_column,
                points="outliers",
                title=f"{x_column}별 {y_column} 박스플롯",
                color_discrete_sequence=palette_colors,
                color_discrete_map=color_map,
            )

        st.plotly_chart(fig, use_container_width=True)


# ------------------------------------------------------------
# 17. 바이올린 플롯
# ------------------------------------------------------------
# 숫자형 데이터의 분포 형태를 더 자세히 확인합니다.
# ------------------------------------------------------------
elif chart_type == "바이올린 플롯":
    if not numeric_columns:
        st.warning("바이올린 플롯을 만들 숫자형 컬럼이 없습니다.")

    else:
        y_column = st.selectbox(
            "분포를 확인할 숫자형 컬럼",
            numeric_columns,
        )

        x_column = st.selectbox(
            "그룹 컬럼",
            ["선택 안 함"] + categorical_columns,
        )

        color_column = st.selectbox(
            "색상 기준 컬럼",
            ["선택 안 함"] + categorical_columns,
        )

        if x_column == "선택 안 함":
            x_column = None

        if color_column == "선택 안 함":
            color_column = x_column

        if color_column is None:
            selected_color = choose_single_color(palette_colors[0], "violin")

            fig = px.violin(
                filtered_data,
                y=y_column,
                box=True,
                points="outliers",
                title=f"{y_column} 바이올린 플롯",
                color_discrete_sequence=[selected_color],
            )

            fig.update_traces(marker_color=selected_color)

        else:
            color_map = make_color_map(
                filtered_data,
                color_column,
                palette_colors,
                "violin",
            )

            fig = px.violin(
                filtered_data,
                x=x_column,
                y=y_column,
                color=color_column,
                box=True,
                points="outliers",
                title=f"{y_column} 바이올린 플롯",
                color_discrete_sequence=palette_colors,
                color_discrete_map=color_map,
            )

        st.plotly_chart(fig, use_container_width=True)


# ------------------------------------------------------------
# 18. 상관관계 히트맵
# ------------------------------------------------------------
# 숫자형 컬럼 사이의 상관관계를 색으로 보여줍니다.
# ------------------------------------------------------------
elif chart_type == "상관관계 히트맵":
    if len(numeric_columns) < 2:
        st.warning("상관관계 히트맵을 만들려면 숫자형 컬럼이 2개 이상 필요합니다.")

    else:
        selected_columns = st.multiselect(
            "상관관계를 확인할 숫자형 컬럼",
            numeric_columns,
            default=numeric_columns,
        )

        color_scale = st.selectbox(
            "히트맵 색상",
            ["RdBu_r", "Viridis", "Blues", "Greens", "Oranges", "Plasma"],
        )

        if len(selected_columns) < 2:
            st.warning("최소 2개 이상의 숫자형 컬럼을 선택해야 합니다.")

        else:
            correlation = filtered_data[selected_columns].corr()

            fig = px.imshow(
                correlation,
                text_auto=".2f",
                title="상관관계 히트맵",
                color_continuous_scale=color_scale,
                zmin=-1,
                zmax=1,
                aspect="auto",
            )

            st.plotly_chart(fig, use_container_width=True)


# ------------------------------------------------------------
# 19. Pair Plot
# ------------------------------------------------------------
# 여러 숫자형 컬럼의 관계를 한 번에 확인합니다.
# ------------------------------------------------------------
elif chart_type == "Pair Plot":
    if len(numeric_columns) < 2:
        st.warning("Pair Plot을 만들려면 숫자형 컬럼이 2개 이상 필요합니다.")

    else:
        selected_columns = st.multiselect(
            "비교할 숫자형 컬럼",
            numeric_columns,
            default=numeric_columns[:min(4, len(numeric_columns))],
        )

        color_column = st.selectbox(
            "색상 기준 컬럼",
            ["선택 안 함"] + categorical_columns,
        )

        if len(selected_columns) < 2:
            st.warning("최소 2개 이상의 숫자형 컬럼을 선택해야 합니다.")

        else:
            if color_column == "선택 안 함":
                selected_color = choose_single_color(palette_colors[0], "pair")

                fig = px.scatter_matrix(
                    filtered_data,
                    dimensions=selected_columns,
                    title="Pair Plot",
                    color_discrete_sequence=[selected_color],
                )

                fig.update_traces(marker_color=selected_color)

            else:
                color_map = make_color_map(
                    filtered_data,
                    color_column,
                    palette_colors,
                    "pair",
                )

                fig = px.scatter_matrix(
                    filtered_data,
                    dimensions=selected_columns,
                    color=color_column,
                    title="Pair Plot",
                    color_discrete_sequence=palette_colors,
                    color_discrete_map=color_map,
                )

            fig.update_traces(diagonal_visible=False)

            st.plotly_chart(fig, use_container_width=True)


# ------------------------------------------------------------
# 20. 파이 차트
# ------------------------------------------------------------
# 범주형 컬럼의 비율을 확인합니다.
# ------------------------------------------------------------
elif chart_type == "파이 차트":
    if not categorical_columns:
        st.warning("파이 차트를 만들 범주형 컬럼이 없습니다.")

    else:
        selected_column = st.selectbox(
            "비율을 확인할 범주형 컬럼",
            categorical_columns,
        )

        chart_data = (
            filtered_data[selected_column]
            .fillna("결측치")
            .astype(str)
            .value_counts()
            .reset_index()
        )

        chart_data.columns = [selected_column, "개수"]

        color_map = make_color_map(
            chart_data,
            selected_column,
            palette_colors,
            "pie",
        )

        fig = px.pie(
            chart_data,
            names=selected_column,
            values="개수",
            title=f"{selected_column} 비율",
            color=selected_column,
            color_discrete_sequence=palette_colors,
            color_discrete_map=color_map,
        )

        st.plotly_chart(fig, use_container_width=True)


# ------------------------------------------------------------
# 21. 도넛 차트
# ------------------------------------------------------------
# 파이 차트와 같지만 가운데가 비어 있어 여러 범주를 조금 더 편하게 볼 수 있습니다.
# ------------------------------------------------------------
elif chart_type == "도넛 차트":
    if not categorical_columns:
        st.warning("도넛 차트를 만들 범주형 컬럼이 없습니다.")

    else:
        selected_column = st.selectbox(
            "비율을 확인할 범주형 컬럼",
            categorical_columns,
        )

        chart_data = (
            filtered_data[selected_column]
            .fillna("결측치")
            .astype(str)
            .value_counts()
            .reset_index()
        )

        chart_data.columns = [selected_column, "개수"]

        color_map = make_color_map(
            chart_data,
            selected_column,
            palette_colors,
            "donut",
        )

        fig = px.pie(
            chart_data,
            names=selected_column,
            values="개수",
            hole=0.4,
            title=f"{selected_column} 비율",
            color=selected_column,
            color_discrete_sequence=palette_colors,
            color_discrete_map=color_map,
        )

        st.plotly_chart(fig, use_container_width=True)


# ------------------------------------------------------------
# 22. 누적 막대그래프
# ------------------------------------------------------------
# 두 개의 범주형 컬럼과 하나의 숫자형 컬럼을 사용해 누적 비교를 합니다.
# ------------------------------------------------------------
elif chart_type == "누적 막대그래프":
    if len(categorical_columns) < 2:
        st.warning("누적 막대그래프를 만들려면 범주형 컬럼이 2개 이상 필요합니다.")

    elif not numeric_columns:
        st.warning("누적 막대그래프의 값으로 사용할 숫자형 컬럼이 필요합니다.")

    else:
        x_column = st.selectbox(
            "X축 범주형 컬럼",
            categorical_columns,
        )

        color_candidates = [
            column for column in categorical_columns
            if column != x_column
        ]

        color_column = st.selectbox(
            "누적으로 구분할 컬럼",
            color_candidates,
        )

        y_column = st.selectbox(
            "값으로 사용할 숫자형 컬럼",
            numeric_columns,
        )

        aggregation_method = st.selectbox(
            "집계 방식",
            ["합계", "평균", "개수"],
        )

        agg_map = {
            "합계": "sum",
            "평균": "mean",
            "개수": "count",
        }

        chart_data = (
            filtered_data
            .groupby([x_column, color_column], dropna=False, as_index=False)[y_column]
            .agg(agg_map[aggregation_method])
        )

        chart_data[x_column] = chart_data[x_column].astype(str)
        chart_data[color_column] = chart_data[color_column].astype(str)

        color_map = make_color_map(
            chart_data,
            color_column,
            palette_colors,
            "stacked",
        )

        fig = px.bar(
            chart_data,
            x=x_column,
            y=y_column,
            color=color_column,
            title=f"{x_column}별 {y_column} {aggregation_method} 누적 막대그래프",
            color_discrete_sequence=palette_colors,
            color_discrete_map=color_map,
        )

        st.plotly_chart(fig, use_container_width=True)

elif chart_type == "지도":
    st.write("위도와 경도 컬럼을 이용해 지도 위에 데이터를 표시합니다.")

    if len(numeric_columns) < 2:
        st.warning("지도 시각화를 만들려면 위도와 경도에 해당하는 숫자형 컬럼이 필요합니다.")

    else:
        lat_column = st.selectbox(
            "위도 컬럼을 선택하세요",
            numeric_columns
        )

        lon_column = st.selectbox(
            "경도 컬럼을 선택하세요",
            numeric_columns
        )

        color_column = st.selectbox(
            "색상으로 구분할 컬럼을 선택하세요",
            ["선택 안 함"] + categorical_columns
        )

        if color_column == "선택 안 함":
            color_column = None

        size_column = st.selectbox(
            "점 크기로 사용할 숫자형 컬럼을 선택하세요",
            ["선택 안 함"] + numeric_columns
        )

        if size_column == "선택 안 함":
            size_column = None

        hover_column = st.selectbox(
            "마우스오버에 표시할 컬럼을 선택하세요",
            ["선택 안 함"] + data.columns.tolist()
        )

        if hover_column == "선택 안 함":
            hover_column = None

        map_data = filtered_data.dropna(
            subset=[lat_column, lon_column]
        )

        st.subheader("지도 표시 옵션")

        max_points = st.selectbox(
            "지도에 표시할 최대 데이터 수를 선택하세요",
            [500, 1000, 3000, 5000, "전체"],
            index=1
        )

        map_data = filtered_data.dropna(
            subset=[lat_column, lon_column]
        )

        original_map_count = len(map_data)

        if max_points != "전체" and original_map_count > max_points:
            map_data = map_data.sample(
                n=max_points,
                random_state=42
            )

            st.info(
                f"지도 성능을 위해 전체 {original_map_count:,}개 중 "
                f"{max_points:,}개를 랜덤으로 표시합니다."
            )
        else:
            st.info(
                f"지도에 {original_map_count:,}개 데이터를 표시합니다."
            )

        fig = my_plot.make_map(
            map_data,
            lat_column,
            lon_column,
            color_column,
            size_column,
            hover_column,
            palette_name
        )

        st.plotly_chart(fig, use_container_width=True)