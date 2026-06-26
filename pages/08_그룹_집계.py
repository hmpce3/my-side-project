import streamlit as st
import pandas as pd
import plotly.express as px

from helpers import my_report


st.title("그룹별 집계")

st.write(
    "범주(차원)별로 데이터를 묶어 합계·평균·개수 등을 계산합니다. "
    "엑셀 피벗테이블처럼 '어느 그룹이 더 큰가'를 빠르게 비교할 수 있어요."
)


# ------------------------------------------------------------
# 1. 데이터 확인 및 선택
# ------------------------------------------------------------
if "data" not in st.session_state:
    st.warning("먼저 '데이터 업로드 / 결합' 페이지에서 데이터를 업로드해주세요.")
    st.stop()

if "cleaned_data" in st.session_state:
    data_source = st.radio(
        "사용할 데이터",
        ["정제 데이터", "원본 데이터"],
        horizontal=True,
    )
    data = (
        st.session_state["cleaned_data"]
        if data_source == "정제 데이터"
        else st.session_state["data"]
    )
else:
    data = st.session_state["data"]

# 관리용 컬럼은 집계 후보에서 제외
data = data.drop(columns=["__source_file__"], errors="ignore")

all_columns = data.columns.tolist()
numeric_columns = data.select_dtypes(include="number").columns.tolist()


# ------------------------------------------------------------
# 2. 집계 설정
# ------------------------------------------------------------
st.subheader("집계 설정")

group_columns = st.multiselect(
    "그룹 기준 컬럼 (1~2개)",
    all_columns,
    help="예: 지역, 월, 등급. 2개 선택하면 행×열 피벗표로 보여줍니다.",
)

agg_label = st.selectbox(
    "집계 방식",
    ["개수", "합계", "평균", "중앙값", "최솟값", "최댓값"],
)

agg_map = {
    "합계": "sum",
    "평균": "mean",
    "중앙값": "median",
    "최솟값": "min",
    "최댓값": "max",
}

# 개수는 값 컬럼이 필요 없습니다.
if agg_label == "개수":
    value_column = None
else:
    if not numeric_columns:
        st.warning(
            "합계·평균 등을 계산할 숫자형 컬럼이 없습니다. "
            "'개수'를 선택하거나 데이터 정제에서 타입을 숫자형으로 바꿔주세요."
        )
        st.stop()
    value_column = st.selectbox("집계할 숫자형 컬럼", numeric_columns)

# 그룹 컬럼 검증
if not group_columns:
    st.info("그룹 기준 컬럼을 1개 이상 선택하면 결과가 표시됩니다.")
    st.stop()

if len(group_columns) > 2:
    st.warning("그룹 기준 컬럼은 최대 2개까지 선택할 수 있습니다.")
    st.stop()

# 집계할 값 컬럼이 그룹 기준에 포함되면 의미도 없고 오류가 납니다.
if value_column is not None and value_column in group_columns:
    st.warning("집계할 '값 컬럼'은 '그룹 기준 컬럼'과 다르게 선택해주세요. (같은 컬럼끼리는 집계할 수 없어요)")
    st.stop()

# 카디널리티(고유값) 경고 — 그룹이 너무 많으면 표가 의미 없어집니다.
for column in group_columns:
    unique_count = data[column].nunique(dropna=True)
    if unique_count > 50:
        st.warning(
            f"`{column}` 컬럼의 고유값이 {unique_count:,}개로 너무 많습니다. "
            "연속형 숫자나 ID 컬럼은 그룹 기준으로 적절하지 않을 수 있어요."
        )


# ------------------------------------------------------------
# 3. 집계 실행
# ------------------------------------------------------------
st.subheader("집계 결과")

report_table = None
report_fig = None

# --- 그룹 컬럼이 1개: groupby 표 + 막대그래프 ---
if len(group_columns) == 1:
    group = group_columns[0]

    if agg_label == "개수":
        result = (
            data.groupby(group, dropna=False)
            .size()
            .reset_index(name="개수")
        )
        value_name = "개수"
    else:
        # 시리즈 이름을 미리 value_name으로 바꿔, reset_index에서 컬럼명이
        # 그룹명과 겹쳐 충돌하는 것을 방지합니다.
        value_name = f"{value_column} {agg_label}"
        result = (
            data.groupby(group, dropna=False)[value_column]
            .agg(agg_map[agg_label])
            .rename(value_name)
            .reset_index()
        )

    result = result.sort_values(value_name, ascending=False).reset_index(drop=True)

    st.dataframe(result, use_container_width=True)
    report_table = result

    # 막대그래프
    chart_df = result.copy()
    chart_df[group] = chart_df[group].astype(str)

    report_fig = px.bar(
        chart_df,
        x=group,
        y=value_name,
        title=f"{group}별 {value_name}",
    )
    report_fig.update_layout(xaxis={"categoryorder": "total descending"})
    st.plotly_chart(report_fig, use_container_width=True)

    # 간단 인사이트(최대 그룹) — 결과가 비어 있지 않을 때만
    if not result.empty:
        top_row = result.iloc[0]
        top_value = top_row[value_name]
        top_value_text = f"{top_value:,.2f}" if pd.notna(top_value) else "계산 불가"
        st.info(
            f"`{top_row[group]}` 그룹의 {value_name}가 "
            f"{top_value_text}로 가장 큽니다."
        )

# --- 그룹 컬럼이 2개: 피벗표 + 히트맵 ---
else:
    g1, g2 = group_columns[0], group_columns[1]

    if agg_label == "개수":
        pivot = pd.crosstab(data[g1], data[g2])
        value_name = "개수"
    else:
        pivot = pd.pivot_table(
            data,
            index=g1,
            columns=g2,
            values=value_column,
            aggfunc=agg_map[agg_label],
        )
        value_name = f"{value_column} {agg_label}"

    st.caption(f"행: {g1} · 열: {g2} · 값: {value_name}")
    st.dataframe(pivot, use_container_width=True)
    report_table = pivot.reset_index()

    # 히트맵 (값 크기를 색으로 비교)
    try:
        report_fig = px.imshow(
            pivot,
            text_auto=".1f",
            aspect="auto",
            color_continuous_scale="Blues",
            title=f"{g1} × {g2} {value_name}",
        )
        st.plotly_chart(report_fig, use_container_width=True)
    except Exception:
        report_fig = None


# ------------------------------------------------------------
# 4. 다운로드 + 보고서 담기
# ------------------------------------------------------------
st.divider()

download_col, report_col = st.columns(2)

with download_col:
    if report_table is not None:
        csv_bytes = report_table.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            "집계 결과 CSV 다운로드",
            data=csv_bytes,
            file_name="group_aggregation.csv",
            mime="text/csv",
        )

with report_col:
    report_title = " × ".join(group_columns) + f" · {value_name}"

    if report_table is not None:
        my_report.report_button(
            "table",
            report_title,
            "그룹별 집계",
            report_table,
            key="add_group_table",
            label="📌 표 리포트에 담기",
        )

    if report_fig is not None:
        my_report.report_button(
            "chart",
            report_title,
            "그룹별 집계",
            report_fig,
            key="add_group_chart",
            label="📌 그래프 리포트에 담기",
        )
