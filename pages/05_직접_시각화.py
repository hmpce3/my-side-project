import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.figure_factory as ff
from helpers import my_plot
from helpers import my_report


# 그린 차트와 그 아래 표시되는 요약 인사이트를 보고서 담기용으로 함께 수집합니다.
_page_charts = []


def _show(fig):
    st.plotly_chart(fig, use_container_width=True, key=f"viz_chart_{len(_page_charts)}")
    _page_charts.append({"fig": fig, "insight": ""})


def _insight(md):
    """차트 아래 요약 인사이트를 표시하고, 직전 차트에 함께 저장합니다."""
    st.markdown(md)
    if _page_charts:
        # 보고서에는 ** 강조 기호 없이 저장합니다.
        _page_charts[-1]["insight"] = str(md).replace("**", "").strip()


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
    "막대그래프",
    "산점도",
    "LM Plot",
    "박스플롯",
    "상관관계 히트맵",
    "선그래프",
    "KDE 플롯",
    "바이올린 플롯",
    "카운트 플롯",
    "Pair Plot",
    "누적 막대그래프",
    "파이 차트",
    "도넛 차트",
    "지도",
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

        _show(fig)
        histogram_values = filtered_data[selected_column].dropna()
        

        if histogram_values.empty:
            _insight(
                "**요약: 선택한 컬럼에 계산 가능한 숫자 값이 없습니다.**"
            )

        else:
            mean_value = histogram_values.mean()
            median_value = histogram_values.median()
            min_value = histogram_values.min()
            max_value = histogram_values.max()

            # ----------------------------------------------------
            # 왜도와 꼬리 방향 해석
            # ----------------------------------------------------
            # 왜도(skewness)가 양수이면 오른쪽 꼬리,
            # 음수이면 왼쪽 꼬리 형태로 해석합니다.
            # 표본 수가 너무 적으면 왜도 해석은 생략합니다.
            # ----------------------------------------------------
            skew_value = histogram_values.skew()

            if len(histogram_values) < 3 or pd.isna(skew_value):
                tail_text = "표본 수가 적어 꼬리 방향 해석은 생략합니다"
            elif skew_value >= 0.5:
                tail_text = f"분포는 오른쪽 꼬리 형태를 보입니다(왜도 {skew_value:.2f})"
            elif skew_value <= -0.5:
                tail_text = f"분포는 왼쪽 꼬리 형태를 보입니다(왜도 {skew_value:.2f})"
            else:
                tail_text = f"분포는 대체로 좌우 균형에 가깝습니다(왜도 {skew_value:.2f})"

            if min_value == max_value:
                _insight(
                    f"**요약: {selected_column}의 값은 모두 동일합니다"
                    f"({min_value:,.2f}). 결측치를 제외한 데이터는 {len(histogram_values):,}개입니다.**"
                )

            else:
                _insight(
                    f"**요약: {selected_column}의 평균은 {mean_value:,.2f}, "
                    f"중앙값은 {median_value:,.2f}입니다. "
                    f"값의 범위는 {min_value:,.2f}부터 {max_value:,.2f}까지이며, "
                    f"결측치를 제외한 데이터는 {len(histogram_values):,}개입니다. "
                    f"{tail_text}.**"
                )


# ------------------------------------------------------------
# 10. KDE 플롯
# ------------------------------------------------------------
# 숫자형 컬럼의 부드러운 분포선을 보여줍니다.
# ------------------------------------------------------------
elif chart_type == "KDE 플롯":
    if not numeric_columns:
        st.warning("KDE 플롯을 만들 숫자형 컬럼이 없습니다.")

    else:
        selected_columns = st.multiselect(
            "분포를 확인할 숫자형 컬럼",
            numeric_columns,
            default=numeric_columns[:min(3, len(numeric_columns))],
        )

        if not selected_columns:
            st.warning("KDE 플롯을 만들 숫자형 컬럼을 1개 이상 선택해주세요.")

        else:
            kde_values = []
            kde_labels = []
            skipped_columns = []

            for column in selected_columns:
                column_values = filtered_data[column].dropna()

                # KDE는 분포 곡선을 추정하는 그래프라
                # 값이 너무 적거나 모두 같으면 해당 컬럼은 제외합니다.
                if len(column_values) < 3:
                    skipped_columns.append(f"{column}(값 3개 미만)")
                    continue

                if column_values.nunique() <= 1:
                    skipped_columns.append(f"{column}(값이 모두 같음)")
                    continue

                kde_values.append(column_values)
                kde_labels.append(column)

            if not kde_values:
                st.warning(
                    "KDE 플롯을 그릴 수 있는 숫자형 컬럼이 없습니다. "
                    "각 컬럼에는 서로 다른 값이 3개 이상 필요합니다."
                )

            else:
                fig = ff.create_distplot(
                    kde_values,
                    kde_labels,
                    show_hist=False,
                    show_rug=False,
                    colors=palette_colors[:len(kde_values)],
                )

                fig.update_layout(
                    title="숫자형 컬럼별 KDE 플롯",
                    xaxis_title="값",
                    yaxis_title="density",
                )

                _show(fig)

                # ----------------------------------------------------
                # KDE 플롯 해석 요약
                # ----------------------------------------------------
                # 여러 숫자형 컬럼을 한 번에 볼 수 있으므로
                # 컬럼별 평균, 중앙값, 왜도를 간단한 표로 보여줍니다.
                # ----------------------------------------------------
                summary_rows = []

                for column in kde_labels:
                    column_values = filtered_data[column].dropna()
                    skew_value = column_values.skew()

                    if len(column_values) < 3 or pd.isna(skew_value):
                        tail_text = "해석 생략"
                    elif skew_value >= 0.5:
                        tail_text = "오른쪽 꼬리"
                    elif skew_value <= -0.5:
                        tail_text = "왼쪽 꼬리"
                    else:
                        tail_text = "좌우 균형"

                    summary_rows.append(
                        {
                            "컬럼": column,
                            "개수": len(column_values),
                            "평균": round(column_values.mean(), 2),
                            "중앙값": round(column_values.median(), 2),
                            "최솟값": round(column_values.min(), 2),
                            "최댓값": round(column_values.max(), 2),
                            "왜도": round(skew_value, 2) if pd.notna(skew_value) else None,
                            "꼬리 방향": tail_text,
                        }
                    )

                summary_df = pd.DataFrame(summary_rows)

                _insight(
                    f"**요약: 선택한 {len(kde_labels):,}개 숫자형 컬럼의 KDE 플롯을 함께 표시했습니다. "
                    "컬럼별 분포 특성은 아래 표에서 확인할 수 있습니다.**"
                )

                st.dataframe(
                    summary_df,
                    use_container_width=True,
                    hide_index=True,
                )

                if skipped_columns:
                    st.caption(
                        "제외된 컬럼: " + ", ".join(skipped_columns)
                    )


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

        _show(fig)

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

            _insight(f"**{summary_text}**")


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

        _show(fig)


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

        # 색상 선택 여부와 상관없이 그래프를 그리고 요약을 표시합니다.
        _show(fig)

        #----------------------------------------------------
        # 산점도 해석 요약
        # ----------------------------------------------------
        # 선택한 두 숫자형 컬럼의 상관계수를 계산해서
        # 양의 관계, 음의 관계, 거의 관계 없음 중 하나로 설명합니다.
        # X축과 Y축에 같은 컬럼을 선택한 경우도 오류 없이 처리합니다.
        # ----------------------------------------------------
        scatter_summary_data = filtered_data[[x_column, y_column]].dropna()

        if len(scatter_summary_data) < 2:
            _insight(
                "**요약: 상관관계를 계산하려면 결측치를 제외한 데이터가 2행 이상 필요합니다.**"
            )

        elif x_column == y_column:
            _insight(
                f"**요약: X축과(와) Y축에 같은 컬럼({x_column})이 선택되어 완전한 양의 관계를 보입니다. "
                "상관계수는 1.00입니다.**"
            )

        else:
            x_values = scatter_summary_data[x_column]
            y_values = scatter_summary_data[y_column]

            if x_values.nunique() <= 1 or y_values.nunique() <= 1:
                _insight(
                    "**요약: 선택한 컬럼 중 하나의 값이 모두 같아서 상관관계를 계산하기 어렵습니다.**"
                )

            else:
                correlation_value = x_values.corr(y_values)
                abs_correlation = abs(correlation_value)

                if abs_correlation >= 0.7:
                    strength_text = "강한"
                elif abs_correlation >= 0.4:
                    strength_text = "중간 정도의"
                elif abs_correlation >= 0.2:
                    strength_text = "약한"
                else:
                    strength_text = "거의 없는"

                if correlation_value > 0:
                    direction_text = "양의 관계"
                elif correlation_value < 0:
                    direction_text = "음의 관계"
                else:
                    direction_text = "관계"

                _insight(
                    f"**요약: {x_column}와 {y_column}의 상관계수는 "
                    f"{correlation_value:.2f}로, {strength_text} {direction_text}를 보입니다.**"
                )


# ------------------------------------------------------------
# 14. LM Plot
# ------------------------------------------------------------
# 산점도에 LM Plot을 함께 표시합니다.
# trendline="ols"는 statsmodels 패키지가 필요합니다.
# ------------------------------------------------------------
elif chart_type == "LM Plot":
    if len(numeric_columns) < 2:
        st.warning("LM Plot를 만들려면 숫자형 컬럼이 2개 이상 필요합니다.")

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
                    title=f"{x_column}와 {y_column}의 LM Plot",
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
                    title=f"{x_column}와 {y_column}의 LM Plot",
                    color_discrete_sequence=palette_colors,
                    color_discrete_map=color_map,
                )

            _show(fig)

        except ModuleNotFoundError:
            st.error("LM Plot을 그리려면 statsmodels 패키지가 필요합니다.")
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
            try:
                chart_data = chart_data.sort_values(by=x_column_for_chart)
            except TypeError:
                # X축 값에 여러 타입이 섞여 정렬이 안 되면 문자열 기준으로 정렬합니다.
                chart_data = chart_data.sort_values(
                    by=x_column_for_chart,
                    key=lambda values: values.astype(str),
                )

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

        _show(fig)


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

        _show(fig)
        # ----------------------------------------------------
        # 박스플롯 해석 요약
        # ----------------------------------------------------
        # 그룹 컬럼이 없으면 전체 숫자형 컬럼의 분포를 요약합니다.
        # 그룹 컬럼이 있으면 그룹별 중앙값을 비교합니다.
        # ----------------------------------------------------
        if x_column not in filtered_data.columns:
            box_values = filtered_data[y_column].dropna()

            if box_values.empty:
                _insight(
                    "**요약: 선택한 숫자형 컬럼에 계산 가능한 값이 없습니다.**"
                )

            else:
                median_value = box_values.median()
                min_value = box_values.min()
                max_value = box_values.max()

                _insight(
                    f"**요약: {y_column}의 중앙값은 {median_value:,.2f}이며, "
                    f"값의 범위는 {min_value:,.2f}부터 {max_value:,.2f}까지입니다.**"
                )

        else:
            group_summary = (
                filtered_data
                .dropna(subset=[x_column, y_column])
                .groupby(x_column)[y_column]
                .median()
                .reset_index()
            )

            if group_summary.empty:
                _insight(
                    "**요약: 그룹별 중앙값을 계산할 수 있는 데이터가 없습니다.**"
                )

            else:
                max_median = group_summary[y_column].max()
                min_median = group_summary[y_column].min()

                max_groups = (
                    group_summary.loc[group_summary[y_column] == max_median, x_column]
                    .astype(str)
                    .tolist()
                )

                min_groups = (
                    group_summary.loc[group_summary[y_column] == min_median, x_column]
                    .astype(str)
                    .tolist()
                )

                if max_median == min_median:
                    _insight(
                        f"**요약: 모든 그룹의 {y_column} 중앙값이 동일합니다({max_median:,.2f}).**"
                    )

                else:
                    max_group_text = ", ".join(max_groups[:3])
                    min_group_text = ", ".join(min_groups[:3])

                    if len(max_groups) > 3:
                        max_group_text += f" 외 {len(max_groups) - 3}개"

                    if len(min_groups) > 3:
                        min_group_text += f" 외 {len(min_groups) - 3}개"

                    _insight(
                        f"**요약: {max_group_text}의 {y_column} 중앙값이 가장 높고"
                        f"({max_median:,.2f}), {min_group_text}의 중앙값이 가장 낮습니다"
                        f"({min_median:,.2f}).**"
                    )


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

        _show(fig)


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

            _show(fig)
                        # ----------------------------------------------------
            # 상관관계 히트맵 해석 요약
            # ----------------------------------------------------
            # 자기 자신과의 상관관계는 항상 1이므로 제외하고,
            # 서로 다른 컬럼 조합 중 가장 강한 양의 상관관계와
            # 가장 강한 음의 상관관계를 찾아 보여줍니다.
            # ----------------------------------------------------
            pair_rows = []

            for i, column1 in enumerate(correlation.columns):
                for column2 in correlation.columns[i + 1:]:
                    corr_value = correlation.loc[column1, column2]

                    if pd.notna(corr_value):
                        pair_rows.append(
                            {
                                "컬럼1": column1,
                                "컬럼2": column2,
                                "상관계수": corr_value,
                            }
                        )

            pair_data = pd.DataFrame(pair_rows)

            summary_messages = [
                f"요약: 선택한 {len(selected_columns):,}개 숫자형 컬럼의 상관관계를 확인했습니다."
            ]

            if pair_data.empty:
                summary_messages.append(
                    "계산 가능한 컬럼 조합이 부족해서 가장 강한 상관관계를 찾기 어렵습니다."
                )

            else:
                positive_pairs = pair_data[pair_data["상관계수"] > 0]
                negative_pairs = pair_data[pair_data["상관계수"] < 0]

                if not positive_pairs.empty:
                    strongest_positive = positive_pairs.loc[
                        positive_pairs["상관계수"].idxmax()
                    ]

                    summary_messages.append(
                        f"가장 강한 양의 상관관계는 "
                        f"{strongest_positive['컬럼1']}와 {strongest_positive['컬럼2']} "
                        f"사이에서 나타났습니다({strongest_positive['상관계수']:.2f})."
                    )

                if not negative_pairs.empty:
                    strongest_negative = negative_pairs.loc[
                        negative_pairs["상관계수"].idxmin()
                    ]

                    summary_messages.append(
                        f"가장 강한 음의 상관관계는 "
                        f"{strongest_negative['컬럼1']}와 {strongest_negative['컬럼2']} "
                        f"사이에서 나타났습니다({strongest_negative['상관계수']:.2f})."
                    )

                if positive_pairs.empty and negative_pairs.empty:
                    summary_messages.append(
                        "서로 다른 컬럼 간 뚜렷한 양의/음의 상관관계가 확인되지 않았습니다."
                    )

            _insight("**" + " ".join(summary_messages) + "**")


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

            _show(fig)


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

        _show(fig)


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

        _show(fig)


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

        _show(fig)

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

        _show(fig)


# ------------------------------------------------------------
# 보고서에 담기
# ------------------------------------------------------------
if _page_charts:
    st.divider()
    st.subheader("보고서")

    if st.button("📌 이 그래프를 리포트에 담기", key="add_viz_chart"):
        for chart in _page_charts:
            my_report.add_item(
                "chart",
                my_report.chart_title(chart["fig"], chart_type),
                "직접 시각화",
                chart["fig"],
                caption=chart["insight"],
            )
        st.toast("그래프를 리포트에 담았습니다.")