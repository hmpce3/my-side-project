import streamlit as st
import pandas as pd
import importlib

from helpers import my_data

# Streamlit은 실행 중인 프로세스에서 import된 helper 모듈을 계속 들고 있을 수 있습니다.
# helper에 새 함수를 추가한 직후에도 이전 모듈을 참조해 AttributeError가 나는 것을 막습니다.
my_data = importlib.reload(my_data)

LARGE_FILE_MB = 150
LARGE_FILE_BYTES = LARGE_FILE_MB * 1024 * 1024
TOTAL_UPLOAD_WARNING_MB = 300


# 업로드한 파일을 한 번만 읽도록 캐싱합니다.
# (파일을 여러 개 올렸을 때, 위젯을 조작할 때마다 전부 다시 읽는 것을 방지)
# file_key(파일명+크기)로만 캐시를 구분하고, 파일 객체(_uploaded_file)는
# 언더스코어 접두사로 해싱에서 제외합니다. (Streamlit 버전과 무관하게 안전)
@st.cache_data(show_spinner=False)
def _cached_read(file_key, _uploaded_file):
    return my_data.read_data_file(_uploaded_file)


def _read_uploaded_file(file_key, uploaded_file):
    """대용량 파일은 캐시를 피해서 Streamlit Cloud 메모리 사용량을 줄입니다."""
    if uploaded_file.size >= LARGE_FILE_BYTES:
        return my_data.read_data_file(uploaded_file)
    return _cached_read(file_key, uploaded_file)


st.title("데이터 업로드 / 결합")

st.write("파일을 업로드하면 데이터를 불러오고, 여러 파일을 결합할 수 있습니다.")

st.caption(
    "배포 링크에서는 파일당 최대 1GB까지 업로드를 허용하도록 설정했습니다. "
    "다만 150MB 이상 파일은 분석 중 메모리를 많이 사용하므로 로딩 시간이 길어지거나 서버가 재시작될 수 있습니다."
)

uploaded_files = st.file_uploader(
    "데이터 파일을 선택하세요",
    type=["csv", "xlsx", "xls", "json"],
    accept_multiple_files=True
)


if uploaded_files:
    dataframes = []
    file_information = []
    failed_files = []

    total_upload_mb = sum(file.size for file in uploaded_files) / 1024 / 1024
    large_files = [
        file.name for file in uploaded_files
        if file.size >= LARGE_FILE_BYTES
    ]

    if large_files:
        st.warning(
            f"{LARGE_FILE_MB}MB 이상 파일 {len(large_files)}개는 대용량 모드로 읽습니다. "
            "업로드 캐시는 사용하지 않아 메모리 중복을 줄이지만, 전체 분석에는 시간이 걸릴 수 있습니다."
        )

    if total_upload_mb >= TOTAL_UPLOAD_WARNING_MB:
        st.warning(
            f"현재 업로드한 전체 파일 크기가 약 {total_upload_mb:,.1f}MB입니다. "
            "Streamlit Cloud에서는 파일을 읽은 뒤 실제 메모리 사용량이 업로드 크기보다 훨씬 커질 수 있습니다."
        )

    # 파일이 많을 때 진행 상황을 보여주고, 한 파일이 깨져도 전체를 멈추지 않습니다.
    progress = st.progress(0.0, text="파일을 읽는 중...")

    for index, uploaded_file in enumerate(uploaded_files):
        try:
            # _cached_read는 복사본을 돌려주므로 안전하게 변형할 수 있습니다.
            file_key = f"{uploaded_file.name}::{uploaded_file.size}"
            file_data, file_info = _read_uploaded_file(file_key, uploaded_file)
        except Exception as error:
            failed_files.append({
                "파일명": uploaded_file.name,
                "오류": str(error),
            })
            continue

        # 컬럼명을 문자열로 통일 (숫자/혼합 컬럼명에서의 .str / join 크래시 방지)
        file_data.columns = file_data.columns.map(str)

        if len(uploaded_files) > 1:
            file_data["__source_file__"] = uploaded_file.name

        file_data = file_data.loc[
            :,
            ~file_data.columns.str.startswith("Unnamed")
        ]

        dataframes.append(file_data)

        file_information.append({
            "파일명": uploaded_file.name,
            "인코딩": file_info,
            "행 개수": file_data.shape[0],
            "열 개수": file_data.shape[1],
            "컬럼": ", ".join(file_data.columns)
        })

        progress.progress(
            (index + 1) / len(uploaded_files),
            text=f"파일을 읽는 중... ({index + 1}/{len(uploaded_files)})",
        )

    progress.empty()

    # 읽지 못한 파일은 건너뛰고, 어떤 파일이 실패했는지 표로 알려줍니다.
    if failed_files:
        st.warning(f"{len(failed_files)}개 파일을 읽지 못해 건너뛰었습니다.")
        st.dataframe(pd.DataFrame(failed_files), use_container_width=True)

    if not dataframes:
        st.error("읽을 수 있는 파일이 없습니다. 파일 형식이나 인코딩을 확인해주세요.")
        st.stop()

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

    # 컬럼명을 문자열로 통일하고 중복 컬럼을 제거합니다.
    # (숫자형/중복 컬럼명이 이후 분석에서 일으키는 크래시를 근본적으로 방지)
    data.columns = data.columns.map(str)
    data = data.loc[:, ~data.columns.duplicated()]

    st.success(
        f"최종 데이터는 {len(data):,}행, {len(data.columns):,}열입니다."
    )

    # 결합 데이터의 메모리 크기를 보여주고, 너무 크면 안내합니다.
    memory_mb = data.memory_usage(deep=True).sum() / 1024 / 1024
    st.caption(f"메모리 사용량: 약 {memory_mb:,.1f} MB")

    if memory_mb > 150 or len(data) > 1_000_000:
        st.warning(
            "데이터가 큽니다. 시각화·통계는 '빠른 분석용 샘플 데이터'로 보는 것을 권장합니다. "
            "(배포 환경은 메모리가 제한적이라 큰 데이터에서는 느려지거나 멈출 수 있어요.)"
        )

    st.subheader("데이터 기본 정보")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("행 개수", data.shape[0])

    with col2:
        st.metric("열 개수", data.shape[1])

    st.subheader("데이터 미리보기")
    st.dataframe(data.head())

    sample_data = my_data.make_sample_data(
        data,
        sample_size=5000
    )

    if "__source_file__" in sample_data.columns:
        st.subheader("샘플 데이터 파일별 구성")

        sample_source_summary = (
            sample_data["__source_file__"]
            .value_counts()
            .reset_index()
        )

        sample_source_summary.columns = ["파일명", "샘플 행 개수"]

        st.dataframe(
            sample_source_summary,
            use_container_width=True
        )
        
    st.session_state["data"] = data
    st.session_state["sample_data"] = sample_data
    try:
        summary_text, recommendation_table, recommendation_notes = (
            my_data.recommend_analysis_flow(data)
        )
    except Exception as error:
        summary_text = ""
        recommendation_table = pd.DataFrame()
        recommendation_notes = [f"추천 분석 흐름을 만들지 못했습니다: {error}"]

    st.session_state["analysis_recommendations"] = recommendation_table

    if "cleaned_data" in st.session_state:
        del st.session_state["cleaned_data"]

    st.success(
        "데이터가 저장되었습니다. 이제 다른 페이지에서 사용할 수 있습니다."
    )

    if not recommendation_table.empty:
        st.subheader("추천 분석 흐름")
        st.write(summary_text)

        st.dataframe(
            recommendation_table,
            use_container_width=True,
            hide_index=True,
        )

        if recommendation_notes:
            for note in recommendation_notes:
                st.warning(note)

        st.caption("추천은 데이터 구조를 기준으로 만든 안내입니다. 분석 목적에 따라 순서를 바꿔도 됩니다.")

        def go(page_name):
            st.session_state["nav"] = page_name

        shortcut_pages = []
        for page_name in recommendation_table["추천 페이지"].tolist():
            if page_name not in shortcut_pages:
                shortcut_pages.append(page_name)

        st.write("바로 이동")
        shortcut_columns = st.columns(min(4, len(shortcut_pages)))
        for index, page_name in enumerate(shortcut_pages[:4]):
            with shortcut_columns[index]:
                st.button(
                    page_name,
                    key=f"recommend_go_{page_name}",
                    on_click=go,
                    args=(page_name,),
                    use_container_width=True,
                )
    elif recommendation_notes:
        for note in recommendation_notes:
            st.warning(note)
