import streamlit as st
import pandas as pd

from helpers import my_stats
from helpers import my_plot
from helpers import my_report


# ------------------------------------------------------------
# 1. 페이지 제목
# ------------------------------------------------------------
st.title("회귀분석")

st.caption(
    "상관분석이 '관계가 있나?'까지 답한다면, 회귀분석은 "
    "'X가 1만큼 변하면 Y는 얼마나 변하나?', '이 변수들이 Y를 얼마나 설명하나(R²)?'까지 답합니다."
)


# ------------------------------------------------------------
# 2. 데이터 존재 여부 확인
# ------------------------------------------------------------
if "data" not in st.session_state:
    st.warning("먼저 '데이터 업로드 / 결합' 페이지에서 데이터 파일을 업로드해주세요.")
    st.stop()


# ------------------------------------------------------------
# 3. 분석에 사용할 데이터 선택 (정제 데이터 우선)
# ------------------------------------------------------------
if "cleaned_data" in st.session_state:
    data_source = st.radio(
        "회귀분석에 사용할 데이터를 선택하세요",
        ["정제 데이터", "원본 데이터"],
        horizontal=True
    )
    data = (
        st.session_state["cleaned_data"]
        if data_source == "정제 데이터"
        else st.session_state["data"]
    )
else:
    st.info("정제 데이터가 아직 없어 원본 데이터를 사용합니다.")
    data = st.session_state["data"]

# 결합 출처 관리 컬럼은 분석에서 제외합니다.
reg_data = data.drop(columns=["__source_file__"], errors="ignore")


# ------------------------------------------------------------
# 4. 컬럼 분류
# ------------------------------------------------------------
numeric_columns = reg_data.select_dtypes(include="number").columns.tolist()
categorical_columns = reg_data.select_dtypes(
    include=["object", "category"]
).columns.tolist()

if len(numeric_columns) < 1:
    st.warning("회귀분석을 하려면 종속변수로 쓸 숫자형 컬럼이 최소 1개 필요합니다.")
    st.stop()


# ------------------------------------------------------------
# 5. 변수 선택
# ------------------------------------------------------------
st.subheader("변수 선택")

alpha = st.selectbox(
    "유의수준을 선택하세요",
    [0.01, 0.05, 0.10],
    index=1
)

y_column = st.selectbox(
    "종속변수 Y (예측·설명하려는 숫자형 변수)",
    numeric_columns
)

# 설명변수 후보: 종속변수를 제외한 숫자형 + 범주형
x_candidates = [c for c in numeric_columns if c != y_column] + categorical_columns

if not x_candidates:
    st.warning("설명변수로 쓸 컬럼이 없습니다. 컬럼이 더 필요합니다.")
    st.stop()

x_columns = st.multiselect(
    "설명변수 X (1개면 단순회귀, 여러 개면 다중회귀 · 범주형은 자동으로 더미변수 변환)",
    x_candidates,
    default=x_candidates[:1]
)

st.info(
    f"**귀무가설(H0)**: 모든 설명변수의 회귀계수는 0이다(설명력 없음).  \n"
    f"**대립가설(H1)**: 적어도 하나의 설명변수는 `{y_column}`에 영향을 준다."
)


# ------------------------------------------------------------
# 6. 회귀분석 실행
# ------------------------------------------------------------
if not x_columns:
    st.warning("설명변수를 1개 이상 선택해주세요.")

elif st.button("회귀분석 실행"):
    try:
        coef_table, metrics, resid_df = my_stats.linear_regression_for_app(
            reg_data,
            y_column=y_column,
            x_columns=x_columns,
            alpha=alpha,
        )
    except Exception as error:
        st.error(f"회귀분석을 수행할 수 없습니다: {error}")
        st.stop()

    # --- 모델 요약 지표 ---
    st.subheader("모델 요약")

    metric_col1, metric_col2, metric_col3 = st.columns(3)
    with metric_col1:
        st.metric("R² (설명력)", f"{metrics['r2']:.3f}")
    with metric_col2:
        st.metric("수정 R²", f"{metrics['adj_r2']:.3f}")
    with metric_col3:
        st.metric("표본 수 n", f"{metrics['n']:,}")

    st.caption(
        f"모델 전체 유의성(F검정) p-value: {my_stats.format_p_value(metrics['f_pvalue'])} · "
        f"설명변수 개수: {metrics['k']}개"
    )

    # --- 회귀계수표 ---
    st.subheader("회귀계수")
    st.caption(
        "계수는 '해당 변수가 1단위 늘 때 Y의 평균 변화량'입니다(다른 변수 고정). "
        "p-value가 유의수준보다 작은 변수만 의미 있는 영향으로 봅니다."
    )

    coef_display = coef_table.copy()
    numeric_cols_to_round = [
        c for c in coef_display.columns
        if c not in ("변수", "유의성")
    ]
    coef_display[numeric_cols_to_round] = coef_display[numeric_cols_to_round].round(4)

    st.dataframe(coef_display, use_container_width=True, hide_index=True)

    # --- 다중공선성(VIF) 진단 ---
    vif_display = None
    vif_interpretation = ""
    if len(x_columns) >= 2:
        st.subheader("다중공선성 진단 (VIF)")
        st.caption(
            "VIF는 설명변수끼리 정보가 얼마나 겹치는지 보는 지표입니다. "
            "보통 5 이상이면 주의, 10 이상이면 회귀계수 해석이 불안정할 수 있습니다."
        )

        try:
            vif_table = my_stats.compute_regression_vif(
                reg_data,
                x_columns=x_columns,
            )
            vif_display = vif_table.copy()
            if not vif_display.empty:
                def format_vif(value):
                    value = pd.to_numeric(value, errors="coerce")
                    if pd.isna(value):
                        return "-"
                    if value == float("inf"):
                        return "∞"
                    return round(float(value), 3)

                vif_display["VIF"] = vif_display["VIF"].apply(format_vif)
                st.dataframe(vif_display, use_container_width=True, hide_index=True)
            else:
                st.info("VIF를 계산하려면 서로 다른 숫자형 설명변수가 2개 이상 필요합니다.")

            vif_interpretation = my_stats.make_vif_interpretation(vif_table)
            st.info(vif_interpretation)
        except Exception as error:
            vif_interpretation = f"VIF 진단을 수행할 수 없습니다: {error}"
            st.warning(vif_interpretation)

    # --- 잔차 진단 플롯 ---
    st.subheader("잔차 진단")
    st.caption(
        "점들이 0 기준선 주변에 특별한 패턴 없이 고르게 퍼져 있어야 좋은 모델입니다. "
        "깔때기 모양이나 곡선 패턴이 보이면 모델 가정을 다시 살펴봐야 합니다."
    )

    resid_fig = my_plot.make_residual_plot(resid_df)
    st.plotly_chart(resid_fig, use_container_width=True)

    # --- 단순회귀일 때만 회귀선 산점도 ---
    show_scatter = (
        len(x_columns) == 1
        and x_columns[0] in numeric_columns
    )
    scatter_fig = None
    if show_scatter:
        st.subheader("회귀선 산점도")
        scatter_fig = my_plot.make_scatter_with_trendline(
            reg_data[[x_columns[0], y_column]].dropna(),
            x_columns[0],
            y_column,
        )
        st.plotly_chart(scatter_fig, use_container_width=True)

    # --- 결과 해석 ---
    st.subheader("결과 해석")
    interpretation = my_stats.make_regression_interpretation(
        coef_table, metrics, y_column, alpha=alpha
    )
    report_text = interpretation
    if vif_interpretation:
        report_text += "\n\n[VIF 다중공선성 진단]\n" + vif_interpretation
    st.info(report_text)

    # 보고서 담기용으로 결과를 저장합니다.
    report_table = coef_display
    if vif_display is not None and not vif_display.empty:
        report_table = pd.concat(
            [
                coef_display,
                pd.DataFrame([{}]),
                pd.DataFrame({"변수": ["[VIF 진단 결과]"]}),
                vif_display.rename(columns={"판정": "유의성"}),
            ],
            ignore_index=True,
            sort=False,
        )

    st.session_state["regression_candidate"] = {
        "title": f"회귀분석 - {y_column} ~ {', '.join(x_columns)}",
        "table": report_table,
        "text": report_text,
    }


# ------------------------------------------------------------
# 7. 보고서에 담기 (마지막으로 실행한 회귀분석 결과)
# ------------------------------------------------------------
_candidate = st.session_state.get("regression_candidate")

if _candidate:
    st.divider()
    st.subheader("보고서")

    my_report.report_button(
        "stat",
        _candidate["title"],
        "회귀분석",
        {"table": _candidate["table"], "text": _candidate["text"]},
        key="add_regression",
        label=f"📌 '{_candidate['title']}' 결과 리포트에 담기",
    )
