import streamlit as st
import pandas as pd
import plotly.express as px
import importlib

from helpers import my_data

importlib.reload(my_data)


st.title("자동 데이터 분석 대시보드")
st.write("CSV 파일을 업로드하면 데이터를 분석하고 시각화합니다.")

uploaded_files = st.file_uploader(
    "CSV 파일을 선택하세요",
    type=["csv"],
    accept_multiple_files=True
)

if uploaded_files:
    dataframes = []
    file_information = []

    for uploaded_file in uploaded_files:
        try:
            file_data, detected_encoding = my_data.read_csv_auto(
                uploaded_file)

        except Exception as error:
            st.error(
                f"{uploaded_file.name} 파일을 읽을 수 없습니다.\n\n"
                f"오류 내용: {error}"
            )
            st.stop()

        file_data = file_data.loc[
            :,
            ~file_data.columns.str.startswith("Unnamed")
        ]

        dataframes.append(file_data)

        file_information.append({
            "파일명": uploaded_file.name,
            "인코딩": detected_encoding,
            "행 개수": file_data.shape[0],
            "열 개수": file_data.shape[1],
            "컬럼": ", ".join(file_data.columns)
})

    st.subheader("업로드 파일 정보")
    st.dataframe(
        pd.DataFrame(file_information),
        use_container_width=True
    )

    # 파일이 하나인 경우
    if len(dataframes) == 1:
        data = dataframes[0]

    # 파일이 여러 개인 경우
    else:
        first_columns = dataframes[0].columns.tolist()

        same_columns = all(
            set(df.columns) == set(first_columns)
            for df in dataframes[1:]
        )

        # 컬럼 구성이 모두 같은 경우
        if same_columns:
            aligned_dataframes = [
                df[first_columns]
                for df in dataframes
            ]

            data = pd.concat(
                aligned_dataframes,
                ignore_index=True
            )

            st.success(
                "모든 파일의 컬럼 구성이 같아서 "
                "행 방향으로 자동 결합했습니다."
            )

        # 컬럼 구성이 다른 경우
        else:
            st.warning(
                "파일들의 컬럼 구성이 서로 다릅니다. "
                "결합 방법을 선택해주세요."
            )

            combine_method = st.radio(
                "결합 방법",
                [
                    "모든 컬럼 유지",
                    "공통 컬럼만 사용",
                    "공통 열을 기준으로 옆으로 결합",
                    "결합하지 않기"
                ]
            )

            if combine_method == "모든 컬럼 유지":
                data = pd.concat(
                    dataframes,
                    ignore_index=True,
                    sort=False
                )

                st.info(
                    "일부 파일에 없는 컬럼은 결측치로 표시됩니다."
                )

            elif combine_method == "공통 컬럼만 사용":
                common_columns = [
                    column for column in first_columns
                    if all(
                        column in df.columns
                        for df in dataframes[1:]
                    )
                ]

                if not common_columns:
                    st.error("모든 파일에 공통으로 존재하는 컬럼이 없습니다.")
                    st.stop()

                selected_common_columns = st.multiselect(
                    "사용할 공통 컬럼을 선택하세요",
                    options=common_columns,
                    default=common_columns
                )

                if not selected_common_columns:
                    st.warning("최소 한 개의 컬럼을 선택해야 합니다.")
                    st.stop()

                data = pd.concat(
                    [
                        df[selected_common_columns]
                        for df in dataframes
                    ],
                    ignore_index=True
                )

            elif combine_method == "공통 열을 기준으로 옆으로 결합":
                if len(dataframes) != 2:
                    st.error(
                        "옆으로 결합하는 기능은 현재 CSV 2개만 지원합니다."
                    )
                    st.stop()

                common_columns = [
                    column for column in first_columns
                    if column in dataframes[1].columns
                ]

                if not common_columns:
                    st.error("두 파일에 공통으로 존재하는 열이 없습니다.")
                    st.stop()

                merge_column = st.selectbox(
                    "연결 기준 열을 선택하세요",
                    common_columns
                )

                merge_type_label = st.selectbox(
                    "연결 범위를 선택하세요",
                    [
                        "양쪽 파일에 모두 있는 값",
                        "첫 번째 파일의 값 전체",
                        "두 번째 파일의 값 전체",
                        "양쪽 파일의 값 전체"
                    ]
                )

                merge_type_map = {
                    "양쪽 파일에 모두 있는 값": "inner",
                    "첫 번째 파일의 값 전체": "left",
                    "두 번째 파일의 값 전체": "right",
                    "양쪽 파일의 값 전체": "outer"
                }

                try:
                    data = pd.merge(
                        dataframes[0],
                        dataframes[1],
                        on=merge_column,
                        how=merge_type_map[merge_type_label],
                        suffixes=("_파일1", "_파일2")
                    )

                except Exception as error:
                    st.error(f"파일 결합에 실패했습니다: {error}")
                    st.stop()

            else:
                st.info("다른 파일을 선택하거나 결합 방법을 변경해주세요.")
                st.stop()

    st.success(
        f"최종 데이터는 {len(data):,}행, "
        f"{len(data.columns):,}열입니다."
    )

    # 여기부터 기존 데이터 기본 정보 코드
    st.subheader("데이터 기본 정보")
    col1, col2 = st.columns(2)

    with col1:
        st.metric("행 개수", data.shape[0])

    with col2:
        st.metric("열 개수", data.shape[1])

    st.subheader("데이터 미리보기")
    st.dataframe(data.head())

#===========================
    
    st.subheader("데이터 품질 확인")

    missing_count = data.isnull().sum().sum()
    duplicate_count = data.duplicated().sum()

    col1, col2 = st.columns(2)

    with col1:
        st.metric("전체 결측치", missing_count)

    with col2:
        st.metric("중복 행", duplicate_count)

    column_info = pd.DataFrame({
        "열 이름": data.columns,
        "데이터 타입": data.dtypes.astype(str).values,
        "결측치 개수": data.isnull().sum().values,
        "고유값 개수": data.nunique().values
    })


#===========================


    st.subheader("열별 정보")
    st.dataframe(column_info, use_container_width=True)
    # 원본은 유지하고 분석용 데이터를 별도로 생성
    analysis_data = data.copy()
    st.subheader("반복 구조 탐지")

    repetition_results = []

    if len(data) > 0 and len(data.columns) > 1:
        for column in data.columns:
            data_without_column = data.drop(columns=[column])

            repeated_rows = data_without_column.duplicated(
                keep=False
            ).sum()

            repeated_ratio = repeated_rows / len(data) * 100

            if repeated_rows > 0:
                repetition_results.append({
                    "검사한 열": column,
                    "해당 열 제외 후 반복 행": repeated_rows,
                    "반복 비율(%)": round(repeated_ratio, 2),
                    "해당 열 제외 후 고유 행": (
                        data_without_column.drop_duplicates().shape[0]
                    )
                })

    if repetition_results:
        repetition_df = pd.DataFrame(repetition_results)
        repetition_df = repetition_df.sort_values(
            "반복 비율(%)",
            ascending=False
        )

        st.dataframe(repetition_df, use_container_width=True)

        suspicious_columns = repetition_df[
            repetition_df["반복 비율(%)"] >= 80
        ]["검사한 열"].tolist()

        if suspicious_columns:
            st.warning(
                "반복 구조가 의심되는 열: "
                + ", ".join(suspicious_columns)
                + "\n\n이 열을 제외하면 나머지 데이터 대부분이 반복됩니다."
            )

            selected_suspicious_column = st.selectbox(
                "제외할 의심 열을 선택하세요",
                suspicious_columns
            )

            apply_cleaning = st.checkbox(
                "선택한 열을 제외하고 반복 데이터를 정리합니다"
            )

            if apply_cleaning:
                analysis_data = (
                    data
                    .drop(columns=[selected_suspicious_column])
                    .drop_duplicates()
                    .reset_index(drop=True)
                )

                st.success(
                    f"정제 완료: {len(data):,}행 → "
                    f"{len(analysis_data):,}행"
                )

                st.subheader("정제 결과 미리보기")
                st.dataframe(
                    analysis_data.head(),
                    use_container_width=True
                )

                cleaned_csv = analysis_data.to_csv(
                    index=False
                ).encode("utf-8-sig")

                st.download_button(
                    "정제한 CSV 다운로드",
                    data=cleaned_csv,
                    file_name="cleaned_data.csv",
                    mime="text/csv"
                )
    else:
        st.success("특정 열만 다른 반복 구조가 발견되지 않았습니다.")

#===========================
    st.subheader("데이터 필터")

    all_columns = analysis_data.columns.tolist()
    numeric_columns = my_data.get_number_column_names(
    analysis_data)

    filtered_data = analysis_data.copy()

    filter_column = st.selectbox(
        "필터를 적용할 열을 선택하세요",
        ["필터 사용 안 함"] + all_columns
    )

    if filter_column != "필터 사용 안 함":

        # 숫자형 열 필터
        if filter_column in numeric_columns:
            minimum = float(analysis_data[filter_column].min())
            maximum = float(analysis_data[filter_column].max())

            if minimum == maximum:
                st.info("이 열은 모든 값이 같아서 범위 필터를 적용할 수 없습니다.")

            else:
                selected_range = st.slider(
                    "값의 범위를 선택하세요",
                    min_value=minimum,
                    max_value=maximum,
                    value=(minimum, maximum)
                )

                filtered_data = analysis_data[
                    analysis_data[filter_column].between(
                        selected_range[0],
                        selected_range[1]
                    )
                ]

        # 문자형 열 필터
        else:
            options = sorted(
                analysis_data[filter_column]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )

            selected_values = st.multiselect(
                "표시할 값을 선택하세요",
                options=options,
                default=options
            )

            filtered_data = analysis_data[
                analysis_data[filter_column]
                .astype(str)
                .isin(selected_values)
            ]

    st.write(
        f"전체 {len(analysis_data):,}행 중 "
        f"**{len(filtered_data):,}행**이 선택되었습니다."
    )

#===========================

    st.subheader("시각화 만들기")

    chart_type = st.selectbox(
    "차트 종류를 선택하세요",
    [
        "히스토그램",
        "막대그래프",
        "산점도",
        "선그래프",
        "박스플롯",
        "상관관계 히트맵"
    ])

    numeric_columns = analysis_data.select_dtypes(include="number").columns.tolist()
    all_columns = analysis_data.columns.tolist()

    if chart_type == "히스토그램":
        if numeric_columns:
            selected_column = st.selectbox(
                "분포를 확인할 숫자 열을 선택하세요",
                numeric_columns
            )

            fig = px.histogram(
                filtered_data,
                x=selected_column,
                title=f"{selected_column} 분포"
            )

            st.plotly_chart(fig, use_container_width=True)

        else:
            st.warning("히스토그램을 만들 수 있는 숫자 열이 없습니다.")


    elif chart_type == "막대그래프":
        x_column = st.selectbox(
            "항목을 구분할 열을 선택하세요",
            all_columns
        )

        aggregation = st.selectbox(
            "집계 방식을 선택하세요",
            ["개수", "합계", "평균", "최댓값", "최솟값"]
        )

        if aggregation == "개수":
            chart_data = (
                filtered_data[x_column]
                .fillna("결측치")
                .value_counts()
                .head(30)
                .reset_index()
            )

            chart_data.columns = [x_column, "개수"]
            y_column = "개수"

        else:
            y_column = st.selectbox(
                "계산할 숫자 열을 선택하세요",
                numeric_columns
            )

            aggregation_functions = {
                "합계": "sum",
                "평균": "mean",
                "최댓값": "max",
                "최솟값": "min"
            }

            chart_data = (
                filtered_data
                .groupby(x_column, dropna=False)[y_column]
                .agg(aggregation_functions[aggregation])
                .reset_index()
                .sort_values(y_column, ascending=False)
                .head(30)
            )

        fig = px.bar(
            chart_data,
            x=x_column,
            y=y_column,
            title=f"{x_column}별 {y_column} {aggregation}"
        )

        st.plotly_chart(fig, use_container_width=True)


    elif chart_type == "산점도":
        if len(numeric_columns) >= 2:
            x_column = st.selectbox(
                "X축 숫자 열을 선택하세요",
                numeric_columns
            )

            y_column = st.selectbox(
                "Y축 숫자 열을 선택하세요",
                numeric_columns,
                index=1
            )

            fig = px.scatter(
                filtered_data,
                x=x_column,
                y=y_column,
                title=f"{x_column}와 {y_column}의 관계"
            )

            st.plotly_chart(fig, use_container_width=True)

        else:
            st.warning("산점도에는 숫자 열이 최소 2개 필요합니다.")


    elif chart_type == "선그래프":
        if numeric_columns:
            x_column = st.selectbox(
                "X축 열을 선택하세요",
                all_columns
            )

            y_column = st.selectbox(
                "Y축 숫자 열을 선택하세요",
                numeric_columns
            )

            fig = px.line(
                filtered_data,
                x=x_column,
                y=y_column,
                title=f"{x_column}에 따른 {y_column} 변화"
            )

            st.plotly_chart(fig, use_container_width=True)

        else:
            st.warning("선그래프를 만들 수 있는 숫자 열이 없습니다.")

    elif chart_type == "박스플롯":
        if numeric_columns:
            y_column = st.selectbox(
                "분포를 확인할 숫자 열을 선택하세요",
                numeric_columns
            )

            category_columns = [
                column for column in all_columns
                if column not in numeric_columns
                and filtered_data[column].nunique() <= 30
            ]

            category_column = st.selectbox(
                "그룹을 구분할 열을 선택하세요",
                ["그룹 구분 안 함"] + category_columns
            )

            if category_column == "그룹 구분 안 함":
                fig = px.box(
                    filtered_data,
                    y=y_column,
                    points="outliers",
                    title=f"{y_column} 박스플롯"
                )

            else:
                fig = px.box(
                    filtered_data,
                    x=category_column,
                    y=y_column,
                    points="outliers",
                    title=f"{category_column}별 {y_column} 분포"
                )

            st.plotly_chart(fig, use_container_width=True)

        else:
            st.warning("박스플롯을 만들 수 있는 숫자 열이 없습니다.")

    elif chart_type == "상관관계 히트맵":
        if len(numeric_columns) >= 2:
            correlation = filtered_data[numeric_columns].corr()

            fig = px.imshow(
                correlation,
                text_auto=".2f",
                color_continuous_scale="RdBu_r",
                zmin=-1,
                zmax=1,
                aspect="auto",
                title="숫자 열 간 상관관계"
            )

            st.plotly_chart(fig, use_container_width=True)

            st.caption(
                "1에 가까울수록 함께 증가하고, "
                "-1에 가까울수록 반대로 움직이며, "
                "0에 가까울수록 선형 관계가 약합니다."
            )

        else:
            st.warning(
                "상관관계 히트맵에는 숫자 열이 최소 2개 필요합니다."
            )
