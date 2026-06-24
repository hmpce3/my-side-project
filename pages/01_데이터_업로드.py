import streamlit as st
import pandas as pd
import importlib

from helpers import my_data

importlib.reload(my_data)


st.title("데이터 업로드 / 결합")

st.write("CSV 파일을 업로드하면 데이터를 불러오고, 여러 파일을 결합할 수 있습니다.")

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
            file_data, detected_encoding = my_data.read_csv_auto(uploaded_file)

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

    if len(dataframes) == 1:
        data = dataframes[0]

    else:
        first_columns = dataframes[0].columns.tolist()

        same_columns = all(
            set(df.columns) == set(first_columns)
            for df in dataframes[1:]
        )

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
                "모든 파일의 컬럼 구성이 같아서 아래 방향으로 자동 결합했습니다."
            )

        else:
            st.warning(
                "파일들의 컬럼 구성이 서로 다릅니다. 결합 방법을 선택해주세요."
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
                    st.warning("최소 1개 이상의 컬럼을 선택해야 합니다.")
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
        f"최종 데이터는 {len(data):,}행, {len(data.columns):,}열입니다."
    )

    st.subheader("데이터 기본 정보")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("행 개수", data.shape[0])

    with col2:
        st.metric("열 개수", data.shape[1])

    st.subheader("데이터 미리보기")
    st.dataframe(data.head())

    st.session_state["data"] = data

    st.success(
        "데이터가 저장되었습니다. 이제 다른 페이지에서 사용할 수 있습니다."
    )