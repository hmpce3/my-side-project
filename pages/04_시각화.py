import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.figure_factory as ff


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
# 4. 사용할 데이터 선택
# ------------------------------------------------------------
# 정제 데이터가 있으면 원본 데이터와 정제 데이터 중 선택할 수 있습니다.
# 정제 데이터가 없으면 원본 데이터를 사용합니다.
# ------------------------------------------------------------
if "cleaned_data" in st.session_state:
    data_source = st.radio(
        "시각화에 사용할 데이터",
        ["원본 데이터", "정제 데이터"],
        horizontal=True,
    )

    if data_source == "원본 데이터":
        data = st.session_state["data"]
    else:
        data = st.session_state["cleaned_data"]

else:
    st.info("정제 데이터가 아직 없어서 원본 데이터를 사용합니다.")
    data = st.session_state["data"]


# ------------------------------------------------------------
# 5. 현재 데이터 정보
# ------------------------------------------------------------
# 사용자가 어떤 데이터를 보고 있는지 확인할 수 있게 행/열 개수를 보여줍니다.
# ------------------------------------------------------------
st.subheader("현재 데이터 정보")

info_col1, info_col2 = st.columns(2)

with info_col1:
    st.metric("행 개수", data.shape[0])

with info_col2:
    st.metric("열 개수", data.shape[1])


# ------------------------------------------------------------
# 6. 데이터 필터
# ------------------------------------------------------------
# 그래프를 그리기 전에 일부 데이터만 골라서 볼 수 있게 합니다.
# 필터가 적용된 결과는 filtered_data에 저장됩니다.
# ------------------------------------------------------------
st.subheader("데이터 필터")

filtered_data = data.copy()

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

st.write(
    f"전체 {len(data):,}행 중 **{len(filtered_data):,}행**이 선택되었습니다."
)

if filtered_data.empty:
    st.warning("필터 결과가 비어 있습니다. 필터 조건을 다시 선택해주세요.")
    st.stop()


# ------------------------------------------------------------
# 7. 컬럼 타입 분류
# ------------------------------------------------------------
# 그래프마다 필요한 컬럼 타입이 다르기 때문에 미리 분류해둡니다.
# ------------------------------------------------------------
numeric_columns = filtered_data.select_dtypes(include="number").columns.tolist()

categorical_columns = filtered_data.select_dtypes(
    include=["object", "category"]
).columns.tolist()

datetime_columns = filtered_data.select_dtypes(
    include=["datetime", "datetimetz"]
).columns.tolist()

all_columns = filtered_data.columns.tolist()


# ------------------------------------------------------------
# 8. 공통 그래프 설정
# ------------------------------------------------------------
# 그래프 종류와 색상 팔레트를 먼저 선택합니다.
# 이 팔레트는 범례 색상, 막대 색상, 파이 조각 색상 등에 사용됩니다.
# ------------------------------------------------------------
st.subheader("시각화 만들기")

chart_type = st.selectbox(
    "차트 종류",
    [
        "히스토그램",
        "KDE 플롯",
        "막대그래프",
        "카운트 플롯",
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
    ],
)

palette_name = st.selectbox(
    "색상 팔레트",
    ["Set2", "Pastel", "Bold", "Dark2", "Plotly", "D3", "G10", "Safe"],
    index=0,
)

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
        x_column = st.selectbox(
            "막대그래프 기준 컬럼",
            categorical_columns,
        )

        aggregation_method = st.selectbox(
            "집계 방식",
            ["개수", "합계", "평균", "최댓값", "최솟값"],
        )

        use_category_colors = st.checkbox(
            "막대별 색상 구분",
            value=True,
            key="bar_use_category_colors",
        )

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
            if not numeric_columns:
                st.warning("집계할 숫자형 컬럼이 없습니다.")
                st.stop()

            y_column = st.selectbox(
                "집계할 숫자형 컬럼",
                numeric_columns,
            )

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
                .sort_values(y_column, ascending=False)
            )

            chart_data[x_column] = chart_data[x_column].astype(str)

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

        st.plotly_chart(fig, use_container_width=True)


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
        possible_x_columns = datetime_columns + categorical_columns + numeric_columns

        x_column = st.selectbox(
            "X축 컬럼",
            possible_x_columns,
        )

        y_column = st.selectbox(
            "Y축 숫자형 컬럼",
            numeric_columns,
        )

        color_column = st.selectbox(
            "선 색상 기준 컬럼",
            ["선택 안 함"] + categorical_columns,
        )

        chart_data = filtered_data.sort_values(by=x_column)

        if color_column == "선택 안 함":
            selected_color = choose_single_color(palette_colors[0], "line")

            fig = px.line(
                chart_data,
                x=x_column,
                y=y_column,
                title=f"{x_column}별 {y_column} 변화",
                color_discrete_sequence=[selected_color],
            )

            fig.update_traces(line_color=selected_color)

        else:
            color_map = make_color_map(
                chart_data,
                color_column,
                palette_colors,
                "line",
            )

            fig = px.line(
                chart_data,
                x=x_column,
                y=y_column,
                color=color_column,
                title=f"{x_column}별 {y_column} 변화",
                color_discrete_sequence=palette_colors,
                color_discrete_map=color_map,
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