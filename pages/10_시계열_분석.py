import streamlit as st
import pandas as pd

from helpers import my_data
from helpers import my_plot
from helpers import my_report


# ------------------------------------------------------------
# 1. 페이지 제목
# ------------------------------------------------------------
st.title("시계열 분석")

st.caption(
    "날짜를 기준으로 데이터를 기간별로 묶어 흐름과 추세를 봅니다. "
    "이동평균으로 단기 변동(노이즈)을 부드럽게 만들어 추세를 더 명확히 볼 수 있어요."
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
        "시계열 분석에 사용할 데이터를 선택하세요",
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

ts_source = data.drop(columns=["__source_file__"], errors="ignore")


# ------------------------------------------------------------
# 4. 날짜 컬럼 / 값 컬럼 선택
# ------------------------------------------------------------
# 이미 datetime 타입인 컬럼을 우선 추천하되, 문자열 날짜도 고를 수 있게
# 모든 컬럼을 후보로 보여줍니다. (선택한 컬럼은 자동으로 날짜 변환을 시도)
# ------------------------------------------------------------
datetime_columns = my_data.detect_datetime_columns(ts_source)
numeric_columns = ts_source.select_dtypes(include="number").columns.tolist()

if not numeric_columns:
    st.warning("시계열로 집계할 숫자형 컬럼이 없습니다.")
    st.stop()

if datetime_columns:
    st.success(
        f"날짜 타입으로 인식된 컬럼: {', '.join(datetime_columns)} "
        "(다른 컬럼을 날짜로 쓰려면 '데이터 정제'에서 날짜 타입으로 바꾸는 것이 가장 정확합니다.)"
    )
else:
    st.info(
        "날짜 타입 컬럼이 없어 보입니다. 아래에서 날짜 컬럼을 고르면 자동으로 변환을 시도합니다. "
        "정확한 분석을 위해 '데이터 정제'에서 날짜 타입으로 변환해두는 것을 권장합니다."
    )

st.subheader("설정")

date_candidates = datetime_columns + [
    c for c in ts_source.columns if c not in datetime_columns
]

date_column = st.selectbox(
    "날짜로 사용할 컬럼을 선택하세요",
    date_candidates,
)

value_column = st.selectbox(
    "분석할 숫자형 값 컬럼을 선택하세요",
    numeric_columns,
)

col1, col2, col3 = st.columns(3)

with col1:
    period = st.selectbox(
        "집계 기간",
        list(my_data.RESAMPLE_RULES.keys()),
        index=2,  # 월별
    )

with col2:
    agg = st.selectbox(
        "집계 방법",
        ["평균", "합계", "건수"],
    )

with col3:
    ma_window = st.number_input(
        "이동평균 구간(개)",
        min_value=1,
        max_value=24,
        value=3,
        help="예: 월별 데이터에서 3이면 최근 3개월 이동평균",
    )


# ------------------------------------------------------------
# 5. 시계열 분석 실행
# ------------------------------------------------------------
if st.button("시계열 분석 실행"):
    try:
        ts_df = my_data.resample_timeseries(
            ts_source,
            date_column=date_column,
            value_column=value_column,
            period=period,
            agg=agg,
        )
    except Exception as error:
        st.error(f"시계열 분석을 수행할 수 없습니다: {error}")
        st.stop()

    if len(ts_df) < 2:
        st.warning("집계 결과 구간이 너무 적습니다. 기간을 더 짧게(예: 월별 → 일별) 바꿔보세요.")
        st.stop()

    # 이동평균 컬럼 추가
    ts_df = my_data.add_moving_average(
        ts_df,
        value_column=value_column,
        window=int(ma_window),
    )

    # --- 시계열 그래프 ---
    st.subheader("시계열 추이")
    fig = my_plot.make_timeseries_line(
        ts_df,
        date_column=date_column,
        value_columns=[value_column, "이동평균"],
        title=f"{period} {value_column} {agg} 추이",
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- 집계 표 ---
    with st.expander("기간별 집계 표 보기"):
        st.dataframe(ts_df, use_container_width=True, hide_index=True)

    # --- 추세 해석 ---
    st.subheader("추세 해석")
    insight = my_data.timeseries_trend_insight(ts_df, date_column, value_column)
    st.info(insight)

    # 보고서 담기용 저장
    st.session_state["timeseries_candidate"] = {
        "title": f"시계열 분석 - {value_column} ({period} {agg})",
        "fig": fig,
        "table": ts_df,
        "text": insight,
    }


# ------------------------------------------------------------
# 6. 보고서에 담기
# ------------------------------------------------------------
_candidate = st.session_state.get("timeseries_candidate")

if _candidate:
    st.divider()
    st.subheader("보고서")

    col_chart, col_stat = st.columns(2)

    with col_chart:
        my_report.report_button(
            "chart",
            _candidate["title"],
            "시계열 분석",
            _candidate["fig"],
            key="add_timeseries_chart",
            caption=_candidate["text"],
            label="📈 그래프 리포트에 담기",
        )

    with col_stat:
        my_report.report_button(
            "stat",
            _candidate["title"] + " (추세 해석)",
            "시계열 분석",
            {"table": _candidate["table"], "text": _candidate["text"]},
            key="add_timeseries_stat",
            label="📌 추세 해석 리포트에 담기",
        )
