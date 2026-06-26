import streamlit as st
import pandas as pd

from helpers import my_stats
from helpers import my_plot
from helpers import my_report

def get_first_p_value(result_df):
    """
    검정 결과표에서 p-value 컬럼을 찾아 첫 번째 p-value를 가져옵니다.
    """

    p_columns = [
        column for column in result_df.columns
        if "p" in str(column).lower()
    ]

    if not p_columns:
        return None

    p_value = pd.to_numeric(
        result_df[p_columns[0]],
        errors="coerce"
    ).dropna()

    if p_value.empty:
        return None

    return p_value.iloc[0]


# ------------------------------------------------------------
# 1. 페이지 제목
# ------------------------------------------------------------
st.title("통계 분석")


# ------------------------------------------------------------
# 2. 데이터 존재 여부 확인
# ------------------------------------------------------------
if "data" not in st.session_state:
    st.warning("먼저 '데이터 업로드 / 결합' 페이지에서 CSV 파일을 업로드해주세요.")
    st.stop()


# ------------------------------------------------------------
# 통계 분석에 사용할 데이터 선택
# ------------------------------------------------------------
# 통계 분석은 정제된 분석용 데이터를 기준으로 수행하는 것이 좋습니다.
# 정제 데이터가 있으면 정제 데이터를 기본값으로 사용하고,
# 필요하면 원본 데이터도 선택할 수 있게 합니다.
# ------------------------------------------------------------
if "cleaned_data" in st.session_state:
    data_source = st.radio(
        "통계 분석에 사용할 데이터를 선택하세요",
        ["정제 데이터", "원본 데이터"],
        horizontal=True
    )

    if data_source == "정제 데이터":
        data = st.session_state["cleaned_data"]
    else:
        data = st.session_state["data"]

else:
    st.info("정제 데이터가 아직 없어 원본 데이터를 사용합니다.")
    data_source = "원본 데이터"
    data = st.session_state["data"]

# ------------------------------------------------------------
# 통계 분석에서 제외할 관리용 컬럼 설정
# ------------------------------------------------------------
# __source_file__은 여러 파일을 결합했을 때
# 각 행이 어느 파일에서 왔는지 확인하기 위한 컬럼입니다.
#
# 통계 분석에서는 종속변수, 집단변수, 상관분석 변수로 사용하기 부적절하므로
# 통계용 데이터에서는 제외합니다.
# ------------------------------------------------------------
exclude_columns = ["__source_file__"]

stats_data = data.drop(
    columns=exclude_columns,
    errors="ignore"
)

# ------------------------------------------------------------
# 4. 데이터 기본 정보
# ------------------------------------------------------------
st.subheader("현재 데이터 정보")

col1, col2 = st.columns(2)

with col1:
    st.metric("행 개수", data.shape[0])

with col2:
    st.metric("열 개수", data.shape[1])


# ------------------------------------------------------------
# 5. 기본 컬럼 분류
# ------------------------------------------------------------
# 통계 검정에서 사용할 수 있는 컬럼을 미리 나눕니다.
#
# 숫자형 컬럼:
# - 평균을 계산할 수 있는 변수
# - 예: 평점, 매출, 점수, 검색지수
#
# 범주형 컬럼:
# - 집단을 나누는 변수
# - 예: 성별, 지역, 요일, 브랜드, 구분
# ------------------------------------------------------------
numeric_columns = stats_data.select_dtypes(include="number").columns.tolist()

categorical_columns = stats_data.select_dtypes(
    include=["object", "category"]
).columns.tolist()

if not numeric_columns:
    st.warning("통계 검정을 수행할 숫자형 컬럼이 없습니다.")
    st.stop()


# ------------------------------------------------------------
# 6. 공통 설정
# ------------------------------------------------------------
st.subheader("검정 설정")

alpha = st.selectbox(
    "유의수준을 선택하세요",
    [0.01, 0.05, 0.10],
    index=1
)

test_type = st.selectbox(
    "수행할 통계 검정을 선택하세요",
    [
        "단일표본 T-TEST",
        "대응표본 T-TEST",
        "독립표본 T-TEST",
        "일원분산분석 ANOVA",
        "상관분석",
        "교차분석 (카이제곱)"
    ]
)


# ------------------------------------------------------------
# 7. 단일표본 T-TEST
# ------------------------------------------------------------
# 목적:
# 하나의 숫자형 변수 평균이 특정 기준값과 다른지 확인합니다.
#
# 예:
# - 평균 평점이 9.5와 다른가?
# - 평균 만족도가 3점과 다른가?
# - 평균 검색지수가 50과 다른가?
# ------------------------------------------------------------
if test_type == "단일표본 T-TEST":
    st.subheader("단일표본 T-TEST")

    selected_column = st.selectbox(
        "검정할 숫자형 변수를 선택하세요",
        numeric_columns
    )

    popmean = st.number_input(
        "비교할 기준값을 입력하세요",
        value=0.0
    )

    st.info(
        "단일표본 T-TEST는 선택한 변수의 평균이 "
        "사용자가 입력한 기준값과 다른지 확인하는 검정입니다."
    )

    st.write(f"""
    **귀무가설(H0)**: `{selected_column}`의 평균은 `{popmean}`이다.  
    **대립가설(H1)**: `{selected_column}`의 평균은 `{popmean}`이 아니다.
    """)

    if st.button("단일표본 T-TEST 실행"):
        # 단일표본 검정에서는 선택한 변수 하나의 정규성을 확인합니다.
        assumption_result = my_stats.test_assumptions(
            stats_data,
            columns=selected_column,
            alpha=alpha
        )

        st.subheader("가정 검정 결과")
        st.caption("선택한 숫자형 변수가 정규분포를 따르는지 확인합니다.")

        assumption_result = my_stats.format_stat_result_for_app(
            assumption_result.reset_index()
        )

        st.dataframe(
            assumption_result,
            use_container_width=True
        )

        # 기존 수업 함수 사용
        test_result = my_stats.test_1sample(
            stats_data,
            column=selected_column,
            popmean=popmean,
            alpha=alpha
        )

        st.subheader("검정 결과")

        test_result = my_stats.format_stat_result_for_app(
            test_result.reset_index()
        )

        st.dataframe(
            test_result,
            use_container_width=True
        )

        p_value = get_first_p_value(test_result)

        if p_value is not None:
            interpretation = my_stats.make_test_interpretation(
                "단일표본 T-TEST",
                p_value,
                alpha
            )

            st.info(interpretation)

        st.session_state["stat_candidate"] = {
            "title": "통계 분석 - 단일표본 T-TEST",
            "table": test_result,
            "text": interpretation if p_value is not None else "",
        }


# ------------------------------------------------------------
# 8. 대응표본 T-TEST
# ------------------------------------------------------------
# 목적:
# 같은 대상에서 측정한 두 값의 평균 차이가 있는지 확인합니다.
#
# 예:
# - 교육 전 점수와 교육 후 점수가 다른가?
# - 광고 전 매출과 광고 후 매출이 다른가?
# - 같은 날짜의 A키워드와 B키워드 검색지수가 다른가?
# ------------------------------------------------------------
elif test_type == "대응표본 T-TEST":
    st.subheader("대응표본 T-TEST")

    col1, col2 = st.columns(2)

    with col1:
        before_column = st.selectbox(
            "비교할 첫 번째 숫자형 변수를 선택하세요",
            numeric_columns
        )

    with col2:
        after_column = st.selectbox(
            "비교할 두 번째 숫자형 변수를 선택하세요",
            numeric_columns,
            index=1 if len(numeric_columns) > 1 else 0
        )

    st.info(
        "대응표본 T-TEST는 같은 대상에서 측정된 두 값의 평균 차이를 확인합니다."
    )

    st.write(f"""
    **귀무가설(H0)**: `{before_column}`와 `{after_column}`의 평균 차이는 0이다.  
    **대립가설(H1)**: `{before_column}`와 `{after_column}`의 평균 차이는 0이 아니다.
    """)

    if before_column == after_column:
        st.warning("서로 다른 두 숫자형 변수를 선택해주세요.")

    elif st.button("대응표본 T-TEST 실행"):
        # 대응표본 검정에서는 두 변수의 차이값이 정규분포를 따르는지 확인합니다.
        paired_data = data[[before_column, after_column]].dropna()
        diff_data = pd.DataFrame({
            "차이값": paired_data[after_column] - paired_data[before_column]
        })

        assumption_result = my_stats.test_assumptions(
            diff_data,
            columns="차이값",
            alpha=alpha
        )

        st.subheader("가정 검정 결과")
        st.caption("두 변수의 차이값이 정규분포를 따르는지 확인합니다.")

        assumption_result = my_stats.format_stat_result_for_app(
            assumption_result.reset_index()
        )

        st.dataframe(
            assumption_result,
            use_container_width=True
        )

        

        # 기존 수업 함수 사용
        test_result = my_stats.test_paired(
            stats_data,
            before=before_column,
            after=after_column,
            alpha=alpha,
            plot=False
        )

        st.subheader("검정 결과")

        test_result = my_stats.format_stat_result_for_app(
            test_result.reset_index()
        )

        st.dataframe(
            test_result,
            use_container_width=True
        )

        p_value = get_first_p_value(test_result)

        if p_value is not None:
            interpretation = my_stats.make_test_interpretation(
                "대응표본 T-TEST",
                p_value,
                alpha
            )

            st.info(interpretation)

        st.session_state["stat_candidate"] = {
            "title": "통계 분석 - 대응표본 T-TEST",
            "table": test_result,
            "text": interpretation if p_value is not None else "",
        }


# ------------------------------------------------------------
# 9. 독립표본 T-TEST
# ------------------------------------------------------------
# 목적:
# 서로 다른 두 집단의 평균이 다른지 확인합니다.
#
# 예:
# - 남성과 여성의 평균 구매금액이 다른가?
# - A지역과 B지역의 평균 매출이 다른가?
# - 두 브랜드의 평균 평점이 다른가?
# ------------------------------------------------------------
elif test_type == "독립표본 T-TEST":
    st.subheader("독립표본 T-TEST")

    if not categorical_columns:
        st.warning("집단을 나눌 범주형 컬럼이 없습니다.")
        st.stop()

    group_column = st.selectbox(
        "집단을 나눌 범주형 컬럼을 선택하세요",
        categorical_columns
    )

    group_values = data[group_column].dropna().unique().tolist()

    selected_groups = st.multiselect(
        "비교할 두 집단을 선택하세요",
        group_values,
        default=group_values[:2]
    )

    value_column = st.selectbox(
        "비교할 숫자형 변수를 선택하세요",
        numeric_columns
    )

    st.info(
        "독립표본 T-TEST는 서로 다른 두 집단의 평균 차이를 확인합니다."
    )

    if len(selected_groups) == 2:
        st.write(f"""
        **귀무가설(H0)**: `{selected_groups[0]}` 집단과 `{selected_groups[1]}` 집단의 `{value_column}` 평균은 같다.  
        **대립가설(H1)**: 두 집단의 `{value_column}` 평균은 다르다.
        """)

    if len(selected_groups) != 2:
        st.warning("독립표본 T-TEST는 비교할 집단을 정확히 2개 선택해야 합니다.")

    elif st.button("독립표본 T-TEST 실행"):
        filtered_data = data[
            data[group_column].isin(selected_groups)
        ][[group_column, value_column]].dropna()

        # 결측 제거 후 한 집단의 데이터가 부족하면 검정할 수 없습니다.
        group_sizes = filtered_data[group_column].value_counts()
        if len(group_sizes) < 2 or group_sizes.min() < 2:
            st.warning("결측치를 제외하면 한 집단의 데이터가 부족합니다. 다른 변수나 집단을 선택해주세요.")
            st.stop()

        group_summary = (
            filtered_data
            .groupby(group_column)[value_column]
            .agg(["count", "mean", "std", "min", "max"])
            .reset_index()
        )

        st.subheader("집단별 요약")

        st.dataframe(
            group_summary,
            use_container_width=True
        )

        group1_name = selected_groups[0]
        group2_name = selected_groups[1]

        # 기존 test_independent 함수는 group1, group2를 컬럼명으로 받는 구조입니다.
        # 그래서 집단 컬럼을 기준으로 wide 형태로 바꿔서 넣어줍니다.
        group1_name = selected_groups[0]
        group2_name = selected_groups[1]

        group1_data = filtered_data[
            filtered_data[group_column] == group1_name
        ][value_column].reset_index(drop=True)

        group2_data = filtered_data[
            filtered_data[group_column] == group2_name
        ][value_column].reset_index(drop=True)

        wide_data = pd.DataFrame({
            str(group1_name): group1_data,
            str(group2_name): group2_data
        })

        # 두 집단 각각의 정규성과 두 집단 간 등분산성을 확인합니다.
        assumption_result = my_stats.test_assumptions(
            wide_data,
            columns=[str(group1_name), str(group2_name)],
            alpha=alpha
        )

        st.subheader("가정 검정 결과")
        st.caption("각 집단의 정규성과 두 집단의 등분산성을 확인합니다.")

        assumption_result = my_stats.format_stat_result_for_app(
            assumption_result.reset_index()
        )

        st.dataframe(
            assumption_result,
            use_container_width=True
        )

        # 기존 수업 함수 사용
        test_result = my_stats.test_independent(
            wide_data,
            group1=str(group1_name),
            group2=str(group2_name),
            alpha=alpha,
            plot=False
        )

        st.subheader("검정 결과")

        test_result = my_stats.format_stat_result_for_app(
            test_result.reset_index()
        )

        st.dataframe(
            test_result,
            use_container_width=True
        )

        p_value = get_first_p_value(test_result)

        if p_value is not None:
            interpretation = my_stats.make_test_interpretation(
                "독립표본 T-TEST",
                p_value,
                alpha
            )

            st.info(interpretation)

        st.session_state["stat_candidate"] = {
            "title": "통계 분석 - 독립표본 T-TEST",
            "table": test_result,
            "text": interpretation if p_value is not None else "",
        }


# ------------------------------------------------------------
# 10. 일원분산분석 ANOVA
# ------------------------------------------------------------
# 목적:
# 3개 이상 집단의 평균이 모두 같은지 확인합니다.
#
# 예:
# - 요일별 평균 평점이 다른가?
# - 지역별 평균 매출이 다른가?
# - 브랜드별 평균 가격이 다른가?
# ------------------------------------------------------------
elif test_type == "일원분산분석 ANOVA":
    st.subheader("일원분산분석 ANOVA")

    if not categorical_columns:
        st.warning("집단을 나눌 범주형 컬럼이 없습니다.")
        st.stop()

    group_column = st.selectbox(
        "집단을 나눌 범주형 컬럼을 선택하세요",
        categorical_columns
    )

    value_column = st.selectbox(
        "비교할 숫자형 변수를 선택하세요",
        numeric_columns
    )

    group_values = data[group_column].dropna().unique().tolist()

    selected_groups = st.multiselect(
        "분석에 포함할 집단을 선택하세요",
        group_values,
        default=group_values[:min(5, len(group_values))]
    )

    st.info(
        "분산분석은 3개 이상 집단의 평균 차이가 있는지 확인합니다."
    )

    st.write(f"""
    **귀무가설(H0)**: 선택한 모든 집단의 `{value_column}` 평균은 같다.  
    **대립가설(H1)**: 적어도 하나의 집단 평균은 다르다.
    """)

    if len(selected_groups) < 3:
        st.warning("분산분석은 최소 3개 이상의 집단이 필요합니다.")

    elif st.button("일원분산분석 ANOVA 실행"):
        # ------------------------------------------------------------
        # 1) 선택한 집단과 숫자형 변수만 남깁니다.
        # ------------------------------------------------------------
        filtered_data = data[
            data[group_column].isin(selected_groups)
        ][[group_column, value_column]].dropna()

        # 결측 제거 후 집단이 3개 미만으로 줄거나 표본이 부족하면 분산분석 불가
        anova_group_sizes = filtered_data[group_column].value_counts()
        if len(anova_group_sizes) < 3 or anova_group_sizes.min() < 2:
            st.warning("결측치를 제외하면 집단이 3개 미만이거나 일부 집단의 데이터가 부족합니다. 다른 변수나 집단을 선택해주세요.")
            st.stop()

        # ------------------------------------------------------------
        # 2) 집단별 요약 확인
        # ------------------------------------------------------------
        # ANOVA 결과를 해석하기 전에 각 집단의 표본 수, 평균, 표준편차를 확인합니다.
        # 이 표는 "실제 검정에 사용된 데이터" 기준입니다.
        # ------------------------------------------------------------
        group_summary = (
            filtered_data
            .groupby(group_column)[value_column]
            .agg(["count", "mean", "std", "min", "max"])
            .reset_index()
        )

        with st.expander("집단별 요약 보기"):
            st.dataframe(
                group_summary,
                use_container_width=True
            )

        # ------------------------------------------------------------
        # 3) 가정 검정을 위해 wide 형태로 변환
        # ------------------------------------------------------------
        # test_assumptions() 함수는 여러 숫자형 컬럼을 받아
        # 각 컬럼의 정규성과 컬럼 간 등분산성을 확인합니다.
        #
        # 그래서 long 형태:
        #   집단 | 값
        #
        # 을 wide 형태:
        #   D10 | F11 | Q15
        #
        # 로 바꿔줍니다.
        # ------------------------------------------------------------
        wide_data = {}

        for group in selected_groups:
            wide_data[str(group)] = (
                filtered_data[
                    filtered_data[group_column] == group
                ][value_column]
                .reset_index(drop=True)
            )

        wide_data = pd.DataFrame(wide_data)

        # ------------------------------------------------------------
        # 4) 정규성 / 등분산성 가정 검정
        # ------------------------------------------------------------
        assumption_result = my_stats.test_assumptions(
            wide_data,
            columns=wide_data.columns.tolist(),
            alpha=alpha
        )

        st.subheader("가정 검정 결과")
        st.caption("각 집단의 정규성과 집단 간 등분산성을 확인합니다.")

        assumption_result_display = my_stats.format_stat_result_for_app(
            assumption_result.reset_index()
        )

        st.dataframe(
            assumption_result_display,
            use_container_width=True
        )

        # ------------------------------------------------------------
        # 5) 어떤 ANOVA가 사용되는지 안내
        # ------------------------------------------------------------
        # anova_oneway() 함수 안에서 가정 검정 결과에 따라
        # 일반 ANOVA 또는 Welch ANOVA를 선택합니다.
        # ------------------------------------------------------------
        normality_rows = assumption_result[
            assumption_result["test"] == "normaltest"
        ]

        equal_var_rows = assumption_result[
            assumption_result["test"] == "equal_var"
        ]

        normality_ok = normality_rows["result"].all()

        if not equal_var_rows.empty:
            equal_var_ok = bool(equal_var_rows["result"].iloc[0])
        else:
            equal_var_ok = False

        if normality_ok and equal_var_ok:
            st.info(
                "정규성과 등분산성 가정을 모두 만족하여 "
                "일반 One-way ANOVA를 사용합니다."
            )
        elif normality_ok and not equal_var_ok:
            st.info(
                "정규성은 만족하지만 등분산성을 만족하지 않아 "
                "Welch ANOVA를 사용합니다."
            )
        else:
            st.warning(
                "정규성 가정을 만족하지 않는 집단이 있습니다. "
                "현재 함수는 참고용으로 Welch ANOVA 결과를 표시합니다. "
                "엄밀한 비모수 검정은 추후 Kruskal-Wallis 검정으로 확장할 수 있습니다."
            )

        # ------------------------------------------------------------
        # 6) ANOVA 실행
        # ------------------------------------------------------------
        test_result = my_stats.anova_oneway(
            filtered_data,
            y=value_column,
            between=group_column,
            alpha=alpha
        )

        st.subheader("검정 결과")

        test_result_display = my_stats.format_stat_result_for_app(
            test_result.reset_index()
        )

        st.dataframe(
            test_result_display,
            use_container_width=True
        )

        # ------------------------------------------------------------
        # 7) p-value 추출
        # ------------------------------------------------------------
        # pingouin의 anova/welch_anova 결과에서는 p-value 컬럼명이
        # p-unc 또는 p_unc 형태일 수 있습니다.
        # 이미 만들어둔 get_first_p_value() 함수를 사용합니다.
        # ------------------------------------------------------------
        p_value = get_first_p_value(test_result_display)

        # ------------------------------------------------------------
        # 8) 효과크기 추출
        # ------------------------------------------------------------
        effect_size = None

        if "effect_size" in test_result_display.columns:
            effect_size = test_result_display["effect_size"].iloc[0]

        # ------------------------------------------------------------
        # 9) 결과 해석 문구
        # ------------------------------------------------------------
        st.subheader("결과 해석")

        if p_value is None:
            interpretation_text = "p-value를 찾을 수 없어 결과 해석을 표시할 수 없습니다."

        elif p_value < alpha:
            interpretation_text = (
                f"분산분석 결과, p-value는 {p_value:.3f}으로 "
                f"유의수준 {alpha}보다 작습니다. "
                f"따라서 `{group_column}` 집단별 `{value_column}` 평균이 "
                "모두 같다고 보기는 어렵습니다.\n\n"
                "즉, 적어도 하나의 집단 평균은 다른 집단과 차이가 있을 가능성이 있습니다.\n\n"
                "다만 분산분석은 '어떤 집단끼리 차이가 나는지'까지는 알려주지 않습니다. "
                "구체적인 집단 간 차이는 사후검정 결과를 확인해야 합니다."
            )

        else:
            interpretation_text = (
                f"분산분석 결과, p-value는 {p_value:.3f}으로 "
                f"유의수준 {alpha}보다 크거나 같습니다. "
                f"따라서 `{group_column}` 집단별 `{value_column}` 평균에 "
                "통계적으로 유의한 차이가 있다고 보기 어렵습니다."
            )

        if effect_size is not None:
            interpretation_text += (
                f"\n\n효과크기는 `{effect_size}`입니다. "
                "효과크기는 통계적으로 유의한 차이가 실제로 얼마나 큰 차이인지 "
                "판단할 때 참고할 수 있습니다."
            )

        st.info(interpretation_text)

        st.session_state["stat_candidate"] = {
            "title": "통계 분석 - 일원분산분석 ANOVA",
            "table": test_result_display,
            "text": interpretation_text,
        }

        # ------------------------------------------------------------
        # 10) 사후검정
        # ------------------------------------------------------------
        # ANOVA 결과가 유의할 때만 사후검정을 수행합니다.
        # 사후검정은 어떤 집단끼리 차이가 나는지 확인하기 위한 절차입니다.
        # ------------------------------------------------------------
        if p_value is not None and p_value < alpha:
            st.subheader("사후검정 결과")

            st.caption(
                "분산분석 결과가 유의하므로 어떤 집단끼리 차이가 있는지 확인합니다."
            )

            posthoc_result = my_stats.posthoc_oneway(
                filtered_data,
                y=value_column,
                between=group_column,
                alpha=alpha,
                plot=False
            )

            posthoc_result_display = my_stats.format_stat_result_for_app(
                posthoc_result.reset_index()
            )

            st.dataframe(
                posthoc_result_display,
                use_container_width=True
            )

            posthoc_insight = my_stats.make_posthoc_insight(
                posthoc_result,
                alpha=alpha
            )

            st.subheader("사후검정 인사이트")

            st.info(posthoc_insight)

# ------------------------------------------------------------
# 상관분석
# ------------------------------------------------------------
# 목적:
# 두 숫자형 변수가 함께 움직이는 정도를 확인합니다.
#
# 예:
# - 기온이 높을수록 대여량도 증가하는가?
# - 매출액과 방문자 수는 관련이 있는가?
# - 공부시간과 시험점수는 함께 증가하는가?
# ------------------------------------------------------------
elif test_type == "상관분석":
    st.subheader("상관분석")

    if len(numeric_columns) < 2:
        st.warning("상관분석을 수행하려면 숫자형 컬럼이 최소 2개 필요합니다.")
        st.stop()

    col1, col2 = st.columns(2)

    with col1:
        x_column = st.selectbox(
            "첫 번째 숫자형 변수를 선택하세요",
            numeric_columns,
            key="corr_x_column"
        )

    with col2:
        y_column = st.selectbox(
            "두 번째 숫자형 변수를 선택하세요",
            numeric_columns,
            index=1 if len(numeric_columns) > 1 else 0,
            key="corr_y_column"
        )

    st.write(f"""
    **귀무가설(H0)**: `{x_column}`와 `{y_column}` 사이에는 선형 상관관계가 없다.  
    **대립가설(H1)**: `{x_column}`와 `{y_column}` 사이에는 선형 상관관계가 있다.
    """)

    if x_column == y_column:
        st.warning("서로 다른 두 숫자형 변수를 선택해주세요.")

    elif st.button("상관분석 실행"):
        # 결측 제거 후 공통 데이터가 3개 미만이면 상관분석을 할 수 없습니다.
        corr_pair = stats_data[[x_column, y_column]].dropna()
        if len(corr_pair) < 3:
            st.warning("두 변수에서 결측치를 제외한 공통 데이터가 3개 이상이어야 상관분석을 할 수 있습니다.")
            st.stop()

        # ------------------------------------------------------------
        # 1. 상관분석 실행
        # ------------------------------------------------------------
        # my_stats.correlation() 함수는 가정 점검 결과에 따라
        # Pearson 또는 Spearman 상관분석을 자동으로 선택합니다.
        # ------------------------------------------------------------
        result = my_stats.correlation(
            stats_data,
            x=x_column,
            y=y_column,
            alpha=alpha,
            plot=False
        )

        result_display = my_stats.format_stat_result_for_app(
            result.reset_index()
        )

        st.subheader("상관분석 결과")

        st.dataframe(
            result_display,
            use_container_width=True
        )

        # ------------------------------------------------------------
        # 2. 산점도 시각화
        # ------------------------------------------------------------
        # 상관분석은 숫자만 보는 것보다 산점도를 함께 보는 것이 좋습니다.
        # ------------------------------------------------------------
        st.subheader("산점도")

        chart_data = data[[x_column, y_column]].dropna()

        fig = my_plot.make_scatter_with_trendline(
            chart_data,
            x_column,
            y_column
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        # ------------------------------------------------------------
        # 3. 결과 해석
        # ------------------------------------------------------------
        coef = float(result["coef"].iloc[0])
        p_value = float(result["p-value"].iloc[0])
        method = result["method"].iloc[0]
        strength = result["strength"].iloc[0]

        if coef > 0:
            direction_text = "양의 방향"
            relation_text = (
                f"`{x_column}` 값이 커질수록 `{y_column}` 값도 함께 커지는 경향이 있습니다."
            )
        elif coef < 0:
            direction_text = "음의 방향"
            relation_text = (
                f"`{x_column}` 값이 커질수록 `{y_column}` 값은 작아지는 경향이 있습니다."
            )
        else:
            direction_text = "뚜렷한 방향 없음"
            relation_text = "두 변수 사이에 뚜렷한 선형 관계가 보이지 않습니다."

        if p_value < alpha:
            significance_text = (
                f"p-value는 {p_value:.3f}으로 유의수준 {alpha}보다 작습니다. "
                "따라서 두 변수의 상관관계는 통계적으로 유의하다고 볼 수 있습니다."
            )
        else:
            significance_text = (
                f"p-value는 {p_value:.3f}으로 유의수준 {alpha}보다 크거나 같습니다. "
                "따라서 두 변수의 상관관계가 통계적으로 유의하다고 보기 어렵습니다."
            )

        st.subheader("결과 해석")

        correlation_summary = (
            f"{method} 상관분석 결과, 상관계수는 {coef:.3f}입니다. "
            f"상관의 방향은 {direction_text}이며, 강도는 {strength}입니다.\n\n"
            f"{relation_text}\n\n"
            f"{significance_text}\n\n"
            "단, 상관분석은 두 변수가 함께 움직이는 정도를 확인하는 방법이며 "
            "원인과 결과를 의미하지는 않습니다."
        )

        st.info(correlation_summary)

        st.session_state["stat_candidate"] = {
            "title": "통계 분석 - 상관분석",
            "table": result_display,
            "text": correlation_summary,
        }


# ------------------------------------------------------------
# 11. 교차분석 (카이제곱 독립성 검정)
# ------------------------------------------------------------
# 목적:
# 두 범주형 변수가 서로 관계가 있는지(독립이 아닌지) 확인합니다.
#
# 예:
# - 성별과 구매여부는 관계가 있는가?
# - 지역과 이탈여부는 관계가 있는가?
# - 요일과 불량여부는 관계가 있는가?
# ------------------------------------------------------------
elif test_type == "교차분석 (카이제곱)":
    st.subheader("교차분석 (카이제곱 독립성 검정)")

    if len(categorical_columns) < 2:
        st.warning("교차분석을 하려면 범주형 컬럼이 2개 이상 필요합니다.")
        st.stop()

    cross_col1, cross_col2 = st.columns(2)

    with cross_col1:
        row_column = st.selectbox(
            "행 컬럼 (범주형)",
            categorical_columns,
            key="chi_row_column",
        )

    with cross_col2:
        col_column = st.selectbox(
            "열 컬럼 (범주형)",
            categorical_columns,
            index=1 if len(categorical_columns) > 1 else 0,
            key="chi_col_column",
        )

    st.info(
        "카이제곱 독립성 검정은 두 범주형 변수가 서로 관계가 있는지(독립이 아닌지) 확인합니다. "
        "숫자형 변수가 주인공인 t-검정·분산분석과 달리, 범주 ↔ 범주 관계를 봅니다."
    )

    st.write(f"""
    **귀무가설(H0)**: `{row_column}`와(과) `{col_column}`는 서로 관계가 없다(독립).
    **대립가설(H1)**: 두 변수는 서로 관계가 있다.
    """)

    if row_column == col_column:
        st.warning("서로 다른 두 범주형 컬럼을 선택해주세요.")

    elif st.button("교차분석 실행"):
        observed, chi_result, chi_interpretation = my_stats.crosstab_chi2_for_app(
            stats_data,
            row_column,
            col_column,
            alpha=alpha,
        )

        st.subheader("교차표 (관측빈도)")
        st.caption("각 범주 조합에 실제로 몇 건이 있는지 보여줍니다.")
        st.dataframe(observed, use_container_width=True)

        st.subheader("검정 결과")
        st.dataframe(chi_result, use_container_width=True)

        st.subheader("결과 해석")
        st.info(chi_interpretation)

        st.session_state["stat_candidate"] = {
            "title": f"통계 분석 - 교차분석 ({row_column} × {col_column})",
            "table": observed.reset_index(),
            "text": chi_interpretation,
        }


# ============================================================
# 보고서에 담기 (마지막으로 실행한 검정 결과)
# ============================================================
_stat_candidate = st.session_state.get("stat_candidate")

if _stat_candidate:
    st.divider()
    st.subheader("보고서")

    my_report.report_button(
        "stat",
        _stat_candidate["title"],
        "통계 분석",
        {"table": _stat_candidate["table"], "text": _stat_candidate["text"]},
        key="add_stat",
        label=f"📌 '{_stat_candidate['title']}' 결과 리포트에 담기",
    )