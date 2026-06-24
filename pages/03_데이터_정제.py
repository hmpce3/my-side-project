import streamlit as st
import pandas as pd
import importlib

from helpers import my_data


# ------------------------------------------------------------
# 개발 중 helpers/my_data.py를 수정했을 때 Streamlit이 이전 코드를
# 기억하는 경우가 있어서 reload로 최신 코드를 다시 불러옵니다.
# ------------------------------------------------------------
importlib.reload(my_data)


# ------------------------------------------------------------
# 페이지 제목
# ------------------------------------------------------------
st.title("데이터 정제")


# ------------------------------------------------------------
# 1. 업로드된 데이터 확인
# ------------------------------------------------------------
# 이 페이지는 업로드된 데이터가 있어야만 작동합니다.
# 데이터 업로드 페이지에서 st.session_state["data"]에 저장한 데이터를
# 여기서 불러와 사용합니다.
# ------------------------------------------------------------
if "data" not in st.session_state:
    st.warning("먼저 '데이터 업로드 / 결합' 페이지에서 CSV 파일을 업로드해주세요.")
    st.stop()


# ------------------------------------------------------------
# 2. 원본 데이터 준비
# ------------------------------------------------------------
# original_data:
# - 사용자가 업로드한 원본 데이터입니다.
# - 정제 작업을 하더라도 원본은 직접 수정하지 않습니다.
#
# cleaned_data:
# - 정제 작업을 적용할 임시 데이터입니다.
# - 사용자가 선택한 정제 옵션에 따라 이 복사본만 변경됩니다.
# ------------------------------------------------------------
original_data = st.session_state["data"]
cleaned_data = original_data.copy()

if "is_cleaned" not in st.session_state:
    st.session_state["is_cleaned"] = False


# ------------------------------------------------------------
# 3. 정제 적용 여부 기록
# ------------------------------------------------------------
# cleaning_applied가 False이면 아직 실제 정제 작업이 적용되지 않은 상태입니다.
# 이 값이 True가 된 경우에만 아래쪽에 정제 결과 미리보기, 비교표,
# 저장/다운로드 영역을 보여줍니다.
# ------------------------------------------------------------
cleaning_applied = False
applied_steps = []


# ------------------------------------------------------------
# 4. 현재 데이터 상태 요약
# ------------------------------------------------------------
# 사용자가 정제를 시작하기 전에 현재 데이터 크기와 결측치 규모를
# 먼저 확인할 수 있게 보여줍니다.
# ------------------------------------------------------------
st.write("업로드한 데이터를 기준으로 중복, 결측치, 컬럼, 데이터 타입을 정리할 수 있습니다.")

st.subheader("현재 데이터 상태")

status_col1, status_col2, status_col3 = st.columns(3)

with status_col1:
    st.metric("행 개수", original_data.shape[0])

with status_col2:
    st.metric("열 개수", original_data.shape[1])

with status_col3:
    st.metric("전체 결측치", original_data.isnull().sum().sum())

st.dataframe(original_data.head(), use_container_width=True)

# ------------------------------------------------------------
# 4-1. 추천 정제 가이드
# ------------------------------------------------------------
# 설명이 너무 길면 화면이 복잡해지므로,
# 기본 안내는 짧게 보여주고 자세한 설명은 expander 안에 넣습니다.
# ------------------------------------------------------------
st.subheader("추천 정제 가이드")

numeric_columns_for_guide = original_data.select_dtypes(
    include="number"
).columns.tolist()

date_name_candidates = [
    column for column in original_data.columns
    if any(
        keyword in str(column).lower()
        for keyword in [
            "날짜",
            "일자",
            "년월",
            "월일",
            "기준일",
            "등록일",
            "수정일",
            "date",
            "time",
            "created",
            "updated"
        ]
    )
]

has_many_numeric_columns = len(numeric_columns_for_guide) >= 2
has_possible_date_column = len(date_name_candidates) >= 1

if has_many_numeric_columns:
    st.info(
        "숫자형 컬럼이 여러 개 있습니다. "
        "비슷한 의미의 컬럼이라면 `여러 컬럼을 하나로 합치기 (wide → long)` 작업을 고려해볼 수 있습니다."
    )

    if has_possible_date_column:
        st.success(
            "날짜로 보이는 컬럼도 있습니다. "
            "날짜형으로 변경하면 시간 흐름 시각화에 활용할 수 있습니다."
        )

        with st.expander("시계열 데이터 정제 순서 보기"):
            st.write("""
            시계열 데이터라면 다음 순서를 추천합니다.

            1. `데이터 타입 변경`에서 날짜 컬럼을 `날짜형`으로 변경합니다.
            2. `여러 컬럼을 하나로 합치기 (wide → long)` 작업을 선택합니다.
            3. 기준 컬럼에는 날짜 컬럼을 선택합니다.
            4. 하나로 합칠 값 컬럼에는 비교하고 싶은 숫자 컬럼들을 선택합니다.
            5. 새 구분 컬럼 이름은 `구분`, `키워드`, `지역`, `항목`처럼 입력합니다.
            6. 새 값 컬럼 이름은 `값`, `점수`, `매출`, `검색지수`처럼 입력합니다.
            7. 정제 결과를 확인한 뒤 `정제 데이터를 앱에 저장`합니다.
            """)

else:
    st.info(
        "여러 컬럼을 하나로 합칠 만한 숫자형 컬럼이 많지 않습니다. "
        "필요한 정제 작업을 선택해서 진행하세요."
    )


# ------------------------------------------------------------
# 5. 정제 작업 선택
# ------------------------------------------------------------
# 사용자가 원하는 정제 작업만 펼쳐서 볼 수 있게 multiselect를 사용합니다.
# 아무 작업도 선택하지 않으면 아래 결과 영역도 표시하지 않습니다.
# ------------------------------------------------------------
st.subheader("정제 작업 선택")

cleaning_options = st.multiselect(
    "필요한 정제 작업을 선택하세요",
    [
        "중복 행 제거",
        "결측치 있는 행 제거",
        "결측치 채우기",
        "컬럼 삭제",
        "데이터 타입 변경",
        "여러 컬럼을 하나로 합치기 (wide → long)",
    ],
)


# ------------------------------------------------------------
# 6. 중복 행 제거
# ------------------------------------------------------------
# duplicated()는 모든 컬럼 값이 완전히 같은 행을 True로 표시합니다.
# drop_duplicates()는 그런 중복 행을 제거합니다.
# ------------------------------------------------------------
if "중복 행 제거" in cleaning_options:
    st.subheader("중복 행 제거")

    duplicate_count = cleaned_data.duplicated().sum()

    st.write(f"현재 중복 행은 **{duplicate_count:,}개**입니다.")

    if duplicate_count == 0:
        st.info("제거할 중복 행이 없습니다.")

    else:
        apply_duplicate_removal = st.checkbox(
            "중복 행 제거 적용",
            key="apply_duplicate_removal",
        )

        if apply_duplicate_removal:
            cleaned_data = cleaned_data.drop_duplicates().reset_index(drop=True)
            cleaning_applied = True
            applied_steps.append("중복 행 제거")

            st.success(f"중복 행 {duplicate_count:,}개를 제거했습니다.")


# ------------------------------------------------------------
# 7. 결측치 있는 행 제거
# ------------------------------------------------------------
# 결측치가 하나라도 포함된 행을 제거합니다.
# 간단하지만 데이터가 많이 줄어들 수 있으므로 제거될 행 수를 먼저 보여줍니다.
# ------------------------------------------------------------
if "결측치 있는 행 제거" in cleaning_options:
    st.subheader("결측치 있는 행 제거")

    missing_row_count = cleaned_data.isnull().any(axis=1).sum()

    st.write(f"결측치가 하나라도 있는 행은 **{missing_row_count:,}개**입니다.")

    if missing_row_count == 0:
        st.info("제거할 결측 행이 없습니다.")

    else:
        apply_missing_row_removal = st.checkbox(
            "결측치가 있는 행 제거 적용",
            key="apply_missing_row_removal",
        )

        if apply_missing_row_removal:
            cleaned_data = cleaned_data.dropna().reset_index(drop=True)
            cleaning_applied = True
            applied_steps.append("결측치 있는 행 제거")

            st.success(f"결측치가 있는 행 {missing_row_count:,}개를 제거했습니다.")


# ------------------------------------------------------------
# 8. 결측치 채우기
# ------------------------------------------------------------
# 선택한 컬럼의 결측치를 특정 값으로 채웁니다.
#
# 숫자형 컬럼:
# - 평균값
# - 중앙값
# - 0
#
# 문자형/범주형 컬럼:
# - 최빈값
# - 직접 입력값
# ------------------------------------------------------------
if "결측치 채우기" in cleaning_options:
    st.subheader("결측치 채우기")

    missing_columns = cleaned_data.columns[
        cleaned_data.isnull().sum() > 0
    ].tolist()

    if not missing_columns:
        st.info("결측치가 있는 컬럼이 없습니다.")

    else:
        fill_column = st.selectbox(
            "결측치를 채울 컬럼",
            missing_columns,
            key="fill_column",
        )

        missing_count = cleaned_data[fill_column].isnull().sum()

        st.write(f"선택한 컬럼의 결측치는 **{missing_count:,}개**입니다.")

        is_numeric_column = pd.api.types.is_numeric_dtype(cleaned_data[fill_column])

        if is_numeric_column:
            fill_method = st.selectbox(
                "채우기 방법",
                ["평균값", "중앙값", "0으로 채우기"],
                key="numeric_fill_method",
            )

            if fill_method == "평균값":
                fill_value = cleaned_data[fill_column].mean()

            elif fill_method == "중앙값":
                fill_value = cleaned_data[fill_column].median()

            else:
                fill_value = 0

            st.caption(f"적용될 값: {fill_value}")

        else:
            fill_method = st.selectbox(
                "채우기 방법",
                ["최빈값", "직접 입력"],
                key="text_fill_method",
            )

            if fill_method == "최빈값":
                mode_values = cleaned_data[fill_column].mode()

                if mode_values.empty:
                    fill_value = None
                    st.warning("최빈값을 계산할 수 없습니다.")

                else:
                    fill_value = mode_values.iloc[0]
                    st.caption(f"적용될 값: {fill_value}")

            else:
                fill_value = st.text_input(
                    "결측치 대신 넣을 값",
                    key="custom_fill_value",
                )

        apply_missing_fill = st.checkbox(
            "결측치 채우기 적용",
            key="apply_missing_fill",
        )

        if apply_missing_fill:
            if fill_value is None or fill_value == "":
                st.warning("결측치를 채울 값을 먼저 정해주세요.")

            else:
                cleaned_data[fill_column] = cleaned_data[fill_column].fillna(fill_value)
                cleaning_applied = True
                applied_steps.append(f"{fill_column} 결측치 채우기")

                st.success(
                    f"{fill_column} 컬럼의 결측치 {missing_count:,}개를 채웠습니다."
                )


# ------------------------------------------------------------
# 9. 컬럼 삭제
# ------------------------------------------------------------
# 분석에 필요 없는 컬럼을 제거합니다.
# 예: 의미 없는 ID 컬럼, 결측치가 너무 많은 컬럼, 중복 정보 컬럼
# ------------------------------------------------------------
if "컬럼 삭제" in cleaning_options:
    st.subheader("컬럼 삭제")

    delete_columns = st.multiselect(
        "삭제할 컬럼",
        cleaned_data.columns.tolist(),
        key="delete_columns",
    )

    if not delete_columns:
        st.info("삭제할 컬럼을 선택해주세요.")

    else:
        st.write(f"선택한 컬럼 **{len(delete_columns)}개**가 삭제됩니다.")

        apply_column_delete = st.checkbox(
            "선택한 컬럼 삭제 적용",
            key="apply_column_delete",
        )

        if apply_column_delete:
            cleaned_data = cleaned_data.drop(columns=delete_columns)
            cleaning_applied = True
            applied_steps.append("컬럼 삭제")

            st.success(f"{len(delete_columns)}개 컬럼을 삭제했습니다.")


# ------------------------------------------------------------
# 9. 데이터 타입 변경
# ------------------------------------------------------------
# CSV를 읽으면 숫자처럼 보이는 값이 문자로 들어오거나,
# 날짜처럼 보이는 값이 문자로 들어오는 경우가 많습니다.
#
# 이 기능은 사용자가 변경할 컬럼만 먼저 선택한 뒤,
# 선택한 컬럼마다 서로 다른 타입을 지정할 수 있게 합니다.
#
# 예:
# 날짜 → 날짜형
# 구분 → 카테고리형
# 값 → 숫자형
#
# 이렇게 컬럼마다 다른 타입을 한 번에 적용할 수 있습니다.
# ------------------------------------------------------------
if "데이터 타입 변경" in cleaning_options:
    st.subheader("데이터 타입 변경")

    st.write("""
    타입을 변경할 컬럼을 먼저 선택한 뒤, 각 컬럼별로 원하는 데이터 타입을 지정합니다.
    변경하지 않을 컬럼은 선택하지 않으면 됩니다.
    """)

    target_columns = st.multiselect(
        "타입을 변경할 컬럼을 선택하세요",
        cleaned_data.columns.tolist()
    )

    type_options = [
        "문자형",
        "숫자형",
        "날짜형",
        "카테고리형"
    ]

    selected_type_map = {}

    if target_columns:
        st.write("컬럼별 변경할 타입을 선택하세요.")

        # 선택한 컬럼들을 한 줄에 2개씩 보여주기 위해 columns를 사용합니다.
        columns_per_row = 2

        for start_index in range(0, len(target_columns), columns_per_row):
            row_columns = target_columns[start_index:start_index + columns_per_row]

            layout_columns = st.columns(len(row_columns))

            for column_index, column in enumerate(row_columns):
                with layout_columns[column_index]:
                    current_type = str(cleaned_data[column].dtype)

                    selected_type = st.selectbox(
                        f"{column} 현재 타입: {current_type}",
                        type_options,
                        key=f"type_change_{column}"
                    )

                    selected_type_map[column] = selected_type

    else:
        st.info("타입을 변경할 컬럼을 선택해주세요.")

    if st.checkbox("선택한 컬럼의 타입 변경을 적용합니다"):
        if not target_columns:
            st.warning("먼저 타입을 변경할 컬럼을 선택해야 합니다.")
            st.stop()

        success_columns = []
        failed_columns = []

        for column, selected_type in selected_type_map.items():
            try:
                if selected_type == "문자형":
                    cleaned_data[column] = cleaned_data[column].astype(str)

                elif selected_type == "숫자형":
                    cleaned_data[column] = pd.to_numeric(
                        cleaned_data[column],
                        errors="coerce"
                    )

                elif selected_type == "날짜형":
                    cleaned_data[column] = pd.to_datetime(
                        cleaned_data[column],
                        errors="coerce"
                    )

                elif selected_type == "카테고리형":
                    cleaned_data[column] = cleaned_data[column].astype("category")

                success_columns.append({
                    "컬럼명": column,
                    "변경 타입": selected_type
                })

            except Exception as error:
                failed_columns.append({
                    "컬럼명": column,
                    "변경 타입": selected_type,
                    "오류 내용": str(error)
                })

        if success_columns:
            st.success(f"{len(success_columns)}개 컬럼의 타입을 변경했습니다.")
            st.dataframe(
                pd.DataFrame(success_columns),
                use_container_width=True
            )

            cleaning_applied = True
            applied_steps.append("데이터 타입 변경")

        if failed_columns:
            st.error("일부 컬럼은 타입 변경에 실패했습니다.")
            st.dataframe(
                pd.DataFrame(failed_columns),
                use_container_width=True
            )

# ------------------------------------------------------------
# 11. 여러 컬럼을 하나로 합치기 (wide → long)
# ------------------------------------------------------------
# 이 작업은 pandas의 melt()를 사용합니다.
#
# 비슷한 의미를 가진 여러 컬럼을 하나의 "구분" 컬럼과 "값" 컬럼으로 정리합니다.
#
# 예:
# 국어, 영어, 수학 → 과목 / 점수
# 만족도, 가격, 디자인 → 평가항목 / 점수
# 서울, 부산, 대구 → 지역 / 값
# ------------------------------------------------------------
if "여러 컬럼을 하나로 합치기 (wide → long)" in cleaning_options:
    st.subheader("여러 컬럼을 하나로 합치기 (wide → long)")

    st.caption(
        "비슷한 의미를 가진 여러 컬럼을 하나의 구분 컬럼과 값 컬럼으로 정리합니다."
    )

    with st.expander("이 기능이 필요한 경우 보기"):
        st.write("""
        여러 컬럼을 하나로 합치기(wide → long)는  
        비슷한 의미를 가진 여러 컬럼을 하나의 `구분` 컬럼과 `값` 컬럼으로 바꾸는 작업입니다.
        """)

        st.write("""
        예를 들어 다음과 같은 경우에 사용할 수 있습니다.

        - `국어`, `영어`, `수학` → `과목`, `점수`
        - `서울`, `부산`, `대구` → `지역`, `값`
        - `만족도`, `가격`, `디자인` → `평가항목`, `점수`
        - `모델A`, `모델B`, `모델C` → `모델`, `점수`
        - `개성주악`, `탕후루`, `말차` → `키워드`, `검색지수`
        """)

        st.warning(
            "단, 서로 단위가 완전히 다른 컬럼을 무작정 합치면 해석이 어려울 수 있습니다. "
            "예: 나이, 키, 소득"
        )

    with st.expander("변환 예시 보기"):
        example_before = pd.DataFrame({
            "응답자ID": [1, 2],
            "만족도": [5, 4],
            "가격": [3, 2],
            "디자인": [4, 5]
        })

        example_after = pd.DataFrame({
            "응답자ID": [1, 1, 1, 2, 2, 2],
            "평가항목": ["만족도", "가격", "디자인", "만족도", "가격", "디자인"],
            "점수": [5, 3, 4, 4, 2, 5]
        })

        before_col, after_col = st.columns(2)

        with before_col:
            st.caption("변환 전")
            st.dataframe(example_before, use_container_width=True)

        with after_col:
            st.caption("변환 후")
            st.dataframe(example_after, use_container_width=True)

    column_names = cleaned_data.columns.tolist()

    suggested_id_columns = cleaned_data.select_dtypes(
        include=["object", "category", "datetime", "datetimetz"]
    ).columns.tolist()

    if not suggested_id_columns and column_names:
        suggested_id_columns = [column_names[0]]

    id_columns = st.multiselect(
        "그대로 둘 기준 컬럼",
        column_names,
        default=suggested_id_columns[:2],
        help="예: 날짜, 응답자ID, 학생ID, 상품명, 매장명",
        key="melt_id_columns",
    )

    value_column_candidates = [
        column for column in column_names
        if column not in id_columns
    ]

    numeric_candidates = cleaned_data[value_column_candidates].select_dtypes(
        include="number"
    ).columns.tolist()

    value_columns = st.multiselect(
        "하나로 합칠 값 컬럼",
        value_column_candidates,
        default=numeric_candidates,
        help="예: 국어/영어/수학, 만족도/가격/디자인, 서울/부산/대구",
        key="melt_value_columns",
    )

    name_col1, name_col2 = st.columns(2)

    with name_col1:
        var_name = st.text_input(
            "새 구분 컬럼 이름",
            value="구분",
            help="예: 과목, 평가항목, 지역, 모델, 키워드",
            key="melt_var_name",
        )

    with name_col2:
        value_name = st.text_input(
            "새 값 컬럼 이름",
            value="값",
            help="예: 점수, 매출, 인구, 검색지수, 비율",
            key="melt_value_name",
        )

    can_make_melt_preview = bool(
        id_columns and value_columns and var_name and value_name
    )

    if can_make_melt_preview:
        preview_data = pd.melt(
            cleaned_data,
            id_vars=id_columns,
            value_vars=value_columns,
            var_name=var_name,
            value_name=value_name,
        )

        st.write(
            f"변환 후 예상 크기: **{preview_data.shape[0]:,}행**, "
            f"**{preview_data.shape[1]:,}열**"
        )

        before_col, after_col = st.columns(2)

        with before_col:
            st.caption("변환 전")
            st.dataframe(cleaned_data.head(), use_container_width=True)

        with after_col:
            st.caption("변환 후 미리보기")
            st.dataframe(preview_data.head(), use_container_width=True)

        apply_melt = st.checkbox(
            "여러 컬럼을 하나로 합치기 적용",
            key="apply_melt",
        )

        if apply_melt:
            cleaned_data = preview_data
            cleaning_applied = True
            applied_steps.append("여러 컬럼을 하나로 합치기 (wide → long)")

            st.success(
                f"여러 컬럼을 하나로 합쳤습니다. "
                f"현재 데이터는 {cleaned_data.shape[0]:,}행, "
                f"{cleaned_data.shape[1]:,}열입니다."
            )

    else:
        st.info("기준 컬럼, 값 컬럼, 새 컬럼 이름을 모두 입력하면 미리보기가 표시됩니다.")


# ------------------------------------------------------------
# 12. 정제 결과 영역
# ------------------------------------------------------------
# 사용자가 실제로 정제 작업을 적용한 경우에만 결과를 보여줍니다.
#
# 이 조건이 중요한 이유:
# - 정제를 하지 않았는데 "정제 결과"가 보이면 사용자가 헷갈릴 수 있습니다.
# - 그래서 cleaning_applied가 True일 때만 결과, 비교, 저장, 다운로드 영역을 표시합니다.
# ------------------------------------------------------------
st.divider()

if not cleaning_options:
    st.info("정제 작업을 선택하면 설정 화면이 표시됩니다.")

elif not cleaning_applied:
    st.info("아직 적용된 정제 작업이 없습니다. 위에서 작업을 선택하고 적용하면 결과가 표시됩니다.")

else:
    # --------------------------------------------------------
    # 12-1. 적용된 작업 요약
    # --------------------------------------------------------
    # 사용자가 어떤 정제 작업을 실제로 적용했는지 확인할 수 있게 보여줍니다.
    # --------------------------------------------------------
    st.subheader("적용된 정제 작업")

    for step in applied_steps:
        st.write(f"- {step}")

    # --------------------------------------------------------
    # 12-2. 정제 결과 미리보기
    # --------------------------------------------------------
    # 실제 정제 작업이 적용된 데이터의 행/열/결측치 규모를 보여줍니다.
    # --------------------------------------------------------
    st.subheader("정제 결과 미리보기")

    result_col1, result_col2, result_col3 = st.columns(3)

    with result_col1:
        st.metric("정제 후 행 개수", cleaned_data.shape[0])

    with result_col2:
        st.metric("정제 후 열 개수", cleaned_data.shape[1])

    with result_col3:
        st.metric("정제 후 전체 결측치", cleaned_data.isnull().sum().sum())

    st.dataframe(cleaned_data.head(), use_container_width=True)

    # --------------------------------------------------------
    # 12-3. 정제 전/후 비교
    # --------------------------------------------------------
    # 원본 데이터와 정제 후 데이터를 숫자로 비교합니다.
    # --------------------------------------------------------
    st.subheader("정제 전/후 비교")

    before_missing_count = original_data.isnull().sum().sum()
    after_missing_count = cleaned_data.isnull().sum().sum()

    before_duplicate_count = original_data.duplicated().sum()
    after_duplicate_count = cleaned_data.duplicated().sum()

    comparison_data = pd.DataFrame({
        "항목": ["행 개수", "열 개수", "전체 결측치", "중복 행"],
        "정제 전": [
            original_data.shape[0],
            original_data.shape[1],
            before_missing_count,
            before_duplicate_count,
        ],
        "정제 후": [
            cleaned_data.shape[0],
            cleaned_data.shape[1],
            after_missing_count,
            after_duplicate_count,
        ],
    })

    st.dataframe(comparison_data, use_container_width=True)

    # --------------------------------------------------------
    # 12-4. 정제 후 열별 정보
    # --------------------------------------------------------
    # 타입 변경, 컬럼 삭제, 결측치 처리 결과를 컬럼 단위로 확인합니다.
    # --------------------------------------------------------
    st.subheader("정제 후 열별 정보")

    column_info = pd.DataFrame({
        "열 이름": cleaned_data.columns,
        "데이터 타입": cleaned_data.dtypes.astype(str).values,
        "결측치 개수": cleaned_data.isnull().sum().values,
        "결측치 비율(%)": (cleaned_data.isnull().mean() * 100).round(2).values,
        "고유값 개수": cleaned_data.nunique().values,
    })

    st.dataframe(column_info, use_container_width=True)

    # --------------------------------------------------------
    # 12-5. 정제 후 숫자형 기술통계량
    # --------------------------------------------------------
    # 숫자형 컬럼이 있는 경우 평균, 표준편차, 사분위수, 이상치 정보 등을 보여줍니다.
    # --------------------------------------------------------
    st.subheader("정제 후 숫자형 기술통계량")

    numeric_summary = my_data.numerical_summary(cleaned_data)

    if numeric_summary.empty:
        st.info("숫자형 컬럼이 없습니다.")
    else:
        st.dataframe(
            numeric_summary.round(3),
            use_container_width=True,
        )

    # --------------------------------------------------------
    # 12-6. 정제 후 범주형 요약
    # --------------------------------------------------------
    # 문자형/카테고리형 컬럼의 고유값, 결측치, 최빈값 정보를 보여줍니다.
    # --------------------------------------------------------
    st.subheader("정제 후 범주형 요약")

    categorical_summary = my_data.categorical_summary_for_app(cleaned_data)

    if categorical_summary.empty:
        st.info("문자형 또는 카테고리형 컬럼이 없습니다.")
    else:
        st.dataframe(
            categorical_summary,
            use_container_width=True,
        )

    # --------------------------------------------------------
    # 12-7. 정제 데이터 앱에 저장
    # --------------------------------------------------------
    # 이 버튼은 파일 다운로드가 아닙니다.
    # 정제된 데이터를 st.session_state["cleaned_data"]에 저장해서
    # 시각화 페이지와 통계 분석 페이지에서 사용할 수 있게 합니다.
    # --------------------------------------------------------
    st.subheader("정제 데이터 적용")

    st.write(
        "정제한 데이터를 앱에 저장하면 이후 시각화와 통계 분석 페이지에서 사용할 수 있습니다."
    )

    if st.button("정제 데이터를 앱에 저장", type="primary"):
        st.session_state["cleaned_data"] = cleaned_data

        st.success(
            "정제 데이터가 앱에 저장되었습니다. 이제 시각화와 통계 분석에서 사용할 수 있습니다."
        )

    # --------------------------------------------------------
    # 12-8. 정제 결과 다운로드
    # --------------------------------------------------------
    # 다운로드는 내 컴퓨터에 CSV 파일로 저장하는 기능입니다.
    # 앱 내부 저장과 파일 다운로드는 서로 다른 작업입니다.
    # --------------------------------------------------------
    st.subheader("정제 결과 파일 다운로드")

    st.caption("아래 버튼은 정제 결과를 CSV 파일로 다운로드합니다.")

    download_col1, download_col2, download_col3 = st.columns(3)

    with download_col1:
        cleaned_csv = cleaned_data.to_csv(
            index=False,
            encoding="utf-8-sig",
        )

        st.download_button(
            label="정제 데이터 다운로드",
            data=cleaned_csv,
            file_name="cleaned_data.csv",
            mime="text/csv",
        )

    with download_col2:
        numeric_summary = my_data.numerical_summary(cleaned_data)

        if not numeric_summary.empty:
            numeric_summary_csv = numeric_summary.to_csv(
                encoding="utf-8-sig",
            )

            st.download_button(
                label="숫자형 요약 다운로드",
                data=numeric_summary_csv,
                file_name="numeric_summary.csv",
                mime="text/csv",
            )
        else:
            st.info("숫자형 요약 없음")

    with download_col3:
        categorical_summary = my_data.categorical_summary_for_app(cleaned_data)

        if not categorical_summary.empty:
            categorical_summary_csv = categorical_summary.to_csv(
                index=False,
                encoding="utf-8-sig",
            )

            st.download_button(
                label="범주형 요약 다운로드",
                data=categorical_summary_csv,
                file_name="categorical_summary.csv",
                mime="text/csv",
            )
        else:
            st.info("범주형 요약 없음")