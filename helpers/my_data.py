import numpy as np
import json
from io import BytesIO
from pandas import to_datetime, DataFrame, ExcelWriter
import pandas as pd

def set_type(data, as_int=[], as_float=[], as_string=[], as_category=[], as_datetime=[]):

    """
    데이터프레임의 컬럼 타입을 변경하고 변경된 데이터프레임의 정보를 출력하는 함수

    Args:
        data (DataFrame) : 타입을 변경할 데이터프레임
        as_int (list) : int 타입으로 변경할 컬럼 리스트
        as_float (list) : float 타입으로 변경할 컬럼 리스트
        as_string (list) : string 타입으로 변경할 컬럼 리스트
        as_category (list) : category 타입으로 변경할 컬럼 리스트
        as_datetime (list) : datetime 타입으로 변경할 컬럼 리스트

    Return:
        DataFrame: 타입이 변경된 데이터프레임
    """

    df = data.copy()

    for col in as_int:
        df[col] =df[col].astype(int)
    for col in as_float:
        df[col] =df[col].astype(float)
    for col in as_string:
        df[col] =df[col].astype(str)
    for col in as_category:
        df[col] =df[col].astype('category')
    for col in as_datetime:
        df[col] =to_datetime(df[col])

    df.info()

    return df

def get_number_column_names(data):
    """
    데이터프레임에서 숫자형 컬럼의 이름을 리스트로 반환하는 함수

    Args:
        data(DataFrame): 숫자형 컬럼의 이름을 추출할 데이터프레임
    
    Returns:
        list: 숫자형 컬럼의 이름 리스트
    """

    return data.select_dtypes(include="number").columns.to_list()   
# 데이터프레임에서 숫자형 타입만 선택해서 이름 가져오기 > 리스트 반환

def get_categorical_column_names(data):
    """
    데이터프레임에서 범주형 컬럼의 이름을 리스트로 반환하는 함수

    Args:
        data(DataFrame): 범주형 컬럼의 이름을 추출할 데이터프레임
    
    Returns:
        list: 범주형 컬럼의 이름 리스트    
    
    """
    return data.select_dtypes(include="category").columns.to_list()
# 데이터프레임에서 범주형 타입만 선택해서 이름 가져오기 > 리스트 반환


def check_duplicates(data, drop=True):
    """
    데이터프레임에서 행 단위 중복을 검사하고, 중복된 행을 제거하는 함수

    Args:
        data (pd.DataFrame) : 중복을 검사할 데이터프레임
        drop (bool) : 중복된 행을 제거할지 여부(기본값:True)

    Returns:
        DataFrame: 중복이 제거된 데이터 프레임
    """

    df= data.copy()
    duplicate_rows = df.duplicated()  # 중복 여부 True/False
    num_duplicates = duplicate_rows.sum() # 중복 개수 계산
    print(f"중복된 행의 수: {num_duplicates}")

    if drop and num_duplicates > 0:
        df= df.drop_duplicates() # 중복 제거
        print("중복된 행이 제거되었습니다.")

    return df

def check_missing_values(data):
    """
    데이터프레임에서 컬럼별 결측치 개수와 비율을 계산하여 데이터프레임으로 반환하는 함수

    Args:
        data(pd.DataFrame): 결측치를 점검할 데이터프레임
    
    Returns:
        DataFrame: 컬럼별 결측치 개수와 비율이 포함된 데이터프레임
    """

    na_count = data.isna().sum()
    na_ratio = (na_count / len(data)) * 100

    return DataFrame({
        'Missing Count': na_count,
        'Missing Ratio (%)' : na_ratio
    })

def categorical_summary(data, columns=None, value_counts=True, save_path=None):
    """
    데이터프레임의 범주형 컬럼에 대한 요약 통계를 반환하는 함수

    Args:
        data (pd.DataFrame): 범주형 컬럼의 요약 통계를 출력할 데이터프레임
        columns (list): 요약 통계를 출력할 범주형 컬럼 리스트
        value_counts (bool) : 각 범주형 컬럼의 value_counts()를 출력할지 여부 (기본값: True)
        save_path (str) : 요약 통계 결과를 CSV 파일로 저장할 경로 (기본값: None, 저장하지 않음)

    Returns:
        DataFrame: 범주형 컬럼에 대한 요약 통계가 포함된 데이터 프레임
    """

    # columns가 비어있으면 데이터프레임에서 범주형 컬럼의 이름을 가져옴
    if not columns:
        columns = get_categorical_column_names(data)

    # 대상 컬럼으로 데이터프레임 생성
    df= data[columns].copy()

    # 명목형 변수의 기술 통계량 계산
    desc_df=df.describe(include="category")

    # 저장될 파일 경로가 전달된 경우 기술 통계량을 Excel 파일로 저장
    if save_path:
        desc_df.to_excel(save_path, sheet_name='Summary', index=True)

    # 각 범주형 컬럼의 value_counts()를 출력해야 한다면?
    if value_counts:
        for col in columns:
            cdf = DataFrame(data[col].value_counts())
            cdf.index.name = col
            cdf.sort_index(inplace=True)
            print(f"컬럼 '{col}'의 value_counts():")
            display(cdf)

            # 저장될 파일 경로가 전달된 경우 value_counts 결과를 Excel 파일로 저장
            if save_path:
                # 기존 파일에 이어 쓰기를 수행하기 위해 ExcelWriter를 사용하여 시트별로 저장
                with ExcelWriter(save_path, mode='a') as excel_writer:
                    cdf.to_excel(excel_writer, sheet_name=col, index=True)
                    
    return desc_df

def numerical_summary(data, columns=None, save_path=None):
    """
    데이터프레임의 숫자형 컬럼에 대한 요약 통계를 반환하는 함수
    
    Args:
        data (DataFrame): 숫자형 컬럼의 요약 통계를 출력할 데이터프레임
        columns(list): 요약 통계를 출력할 숫자형 컬럼 리스트
        save_path(str): 요약 통계 결과를 CSV 파일로 저장할 경로 (기본값: None, 저장하지 않음)

    Returns:
        DataFrame: 숫자형 컬럼에 대한 요약 통계가 포함된 데이터프레임    
    """

    #----------------------------------------------------------------
    # 1) columns가 비어있으면 데이터 프레임에서 숫자형 컬럼의 이름을 가져옴
    #----------------------------------------------------------------
    if not columns:
        columns = get_number_column_names(data)

    # 숫자형 컬럼이 없으면 빈 결과를 반환합니다.
    # (빈 컬럼 목록으로 describe()를 호출하면 "Cannot describe a DataFrame without columns" ValueError가 납니다.)
    if not columns:
        return DataFrame()

    desc_df = data[columns].describe().T

    #----------------------------------------------------------------
    # 2) 평균-중앙값의 상대 차이율을 계산하여 중심 수준 파악
    #----------------------------------------------------------------
    # '평균-중앙값 상대 차이율 = |평균 - 중앙값| / 중앙값' 컬럼 추가
    desc_df['rel_diff'] = abs(desc_df['mean'] - desc_df['50%']) / desc_df['50%']

    # 상대 차이율 의미 컬럼 추가
    conditions = [desc_df['rel_diff'] < 0.1, desc_df['rel_diff'] <0.5]
    choices = ['similar', 'diff']
    desc_df['rdiff_flag'] = np.select(conditions, choices, default='large_diff')

    #----------------------------------------------------------------
    # 3) IQR, 이상치 경계값 계산
    #----------------------------------------------------------------   
    # iqr
    desc_df['iqr'] = desc_df['75%'] - desc_df['25%']

    # 상한 이상치 경계
    desc_df['upper_bound'] = desc_df['75%'] +1.5*desc_df['iqr']

    # 하한 이상치 경계
    desc_df['lower_bound'] = desc_df['25%'] -1.5*desc_df['iqr']

    #----------------------------------------------------------------
    # 4) 명목형 변수를 제외한 데이터 프레임 생성
    #---------------------------------------------------------------- 
    df = data[columns].copy()

    #----------------------------------------------------------------
    # 5) 상한 이상치 탐지
    #---------------------------------------------------------------- 
    # 상한 이상치 수
    desc_df['upper_outliers'] =((df > desc_df['upper_bound'])).sum()

    # 상한 이상치 비율
    desc_df['upper_outliers_ratio'] = desc_df['upper_outliers'] / df.shape[0]

    #----------------------------------------------------------------
    # 6) 하한 이상치 탐지
    #---------------------------------------------------------------- 
    # 하한 이상치 수
    desc_df['lower_outliers'] =((df < desc_df['lower_bound'])).sum()

    # 하한 이상치 비율
    desc_df['lower_outliers_ratio'] = desc_df['lower_outliers'] / df.shape[0]

    #----------------------------------------------------------------
    # 7) 전체 이상치 집계
    #----------------------------------------------------------------    
    # 통합 이상치 수
    desc_df['outliers'] = desc_df['upper_outliers'] + desc_df['lower_outliers']

    # 통합 이상치 비율
    desc_df['outliers_ratio'] = desc_df['outliers'] / df.shape[0]

    #----------------------------------------------------------------
    # 8) 왜도 점검
    #----------------------------------------------------------------  
    # 왜도 계산
    desc_df['skew'] = df.skew()

    # 왜도를 통한 분포 형태 해석
    conditions_skew = [(desc_df['skew'] < -0.5), (desc_df['skew'] >0.5)]
    choices_skew = ['left_tail', 'right_tail']
    desc_df['skew_interpret'] = np.select(conditions_skew, choices_skew, default='symmetric')

    #----------------------------------------------------------------
    # 9) 첨도 점검
    #----------------------------------------------------------------  
    # 첨도 계산
    desc_df['kurt'] = df.kurt()

    # 첨도를 통한 분포 형태 해석
    conditions_kurt = [(desc_df['kurt'] < 0), (desc_df['kurt'] > 0)]
    choices_kurt = ['platykurtic', 'leptokurtic']
    desc_df['kurt_interpret'] = np.select(conditions_kurt, choices_kurt, default='mesokurtic')

    #----------------------------------------------------------------
    # 10) 로그 변환 필요성 판단 함수 정의
    #----------------------------------------------------------------  
    def judge_log_transform(skew, kurt):
        if skew >=1: # 강한 우측 꼬리 분포
            return "log1p"
        elif skew > 0.5 and kurt > 0: # 우측 꼬리 분포이면서 첨도가 높은 경우
            return "log1p"
        elif skew <= -1: # 강한 좌측 꼬리 분포
            return "reverse_log1p"
        elif skew < -0.5 and kurt > 0: # 좌측 꼬리 분포이면서 첨도가 높은 경우
            return "reverse_log1p"
        else: # 대칭분포
            return "none"

    #----------------------------------------------------------------
    # 11) 로그 변환 필요성 판정
    #----------------------------------------------------------------  
    desc_df['log_need'] = desc_df.apply(lambda row: judge_log_transform(row['skew'], row['kurt']), axis=1)

    #----------------------------------------------------------------
    # 12) 기술 통계량 표 저장
    #---------------------------------------------------------------- 
    # 저장 경로 파라미터가 전달되었다면 기술 통계량 표를 Excel 파일로 저장
    if save_path:
        desc_df.to_excel(save_path, index=True)

    #----------------------------------------------------------------
    # 13) 결과 리턴
    #----------------------------------------------------------------
    return desc_df

def read_csv_auto(uploaded_file):
    """
    여러 인코딩을 차례대로 시도해서 CSV 파일을 읽습니다.

    Returns:
        DataFrame: 읽은 데이터
        str: 사용된 인코딩
    """

    file_bytes = uploaded_file.getvalue()

    # 파일의 시작 부분을 확인해 우선순위 결정
    if file_bytes.startswith(b"\xef\xbb\xbf"):
        encodings = [
            "utf-8-sig",
            "utf-8",
            "cp949",
            "euc-kr",
            "utf-16"
        ]

    elif file_bytes.startswith((b"\xff\xfe", b"\xfe\xff")):
        encodings = [
            "utf-16",
            "utf-8-sig",
            "utf-8",
            "cp949",
            "euc-kr"
        ]

    else:
        encodings = [
            "utf-8",
            "cp949",
            "euc-kr",
            "utf-16"
        ]

    last_error = None

    for encoding in encodings:
        try:
            data = pd.read_csv(
                BytesIO(file_bytes),
                encoding=encoding
            )

            return data, encoding

        except (
            UnicodeError,
            pd.errors.ParserError
        ) as error:
            last_error = error

    raise ValueError(
        "지원하는 인코딩으로 CSV 파일을 읽을 수 없습니다. "
        f"마지막 오류: {last_error}"
    )


#====================
def read_data_file(uploaded_file):
    """
    업로드한 파일을 DataFrame으로 읽어오는 함수입니다.

    지원 파일:
    - CSV
    - Excel(xlsx, xls)
    - JSON

    Returns
    -------
    data : DataFrame
        읽어온 데이터
    file_info : str
        읽은 파일 형식 또는 인코딩 정보
    """

    file_name = uploaded_file.name.lower()

    if file_name.endswith(".csv"):
        data, encoding = read_csv_auto(uploaded_file)
        return data, f"CSV / encoding={encoding}"

    elif file_name.endswith((".xlsx", ".xls")):
        data = pd.read_excel(uploaded_file)
        return data, "Excel"

    elif file_name.endswith(".json"):
        json_data = json.load(uploaded_file)

        if isinstance(json_data, list):
            data = pd.DataFrame(json_data)

        elif isinstance(json_data, dict):
            data = pd.json_normalize(json_data)

        else:
            raise ValueError("지원하지 않는 JSON 구조입니다.")

        return data, "JSON"

    else:
        raise ValueError("지원하지 않는 파일 형식입니다.")


def make_sample_data(data, sample_size=5000, random_state=42):
    """
    대용량 데이터 분석 속도를 높이기 위해 샘플 데이터를 만드는 함수입니다.

    전체 데이터가 sample_size보다 작으면 전체 데이터를 그대로 반환합니다.
    전체 데이터가 sample_size보다 크면 sample_size만큼 무작위 샘플을 추출합니다.
    """

    if data is None or data.empty:
        return data

    if len(data) <= sample_size:
        return data.copy()

    return data.sample(
        n=sample_size,
        random_state=random_state
    ).reset_index(drop=True)



#==============================
def categorical_summary_for_app(data):
    """
    Streamlit 화면 표시용 범주형 요약 함수입니다.

    기존 categorical_summary()는 수업/노트북용 출력이 포함되어 있어서
    Streamlit에서는 이 함수를 사용하는 것이 더 안정적입니다.
    """

    categorical_data = data.select_dtypes(
        include=["object", "category"]
    )

    if categorical_data.empty:
        return DataFrame()

    summary_rows = []

    for column in categorical_data.columns:
        mode_values = categorical_data[column].mode()

        if mode_values.empty:
            most_common_value = None
            most_common_count = 0
        else:
            most_common_value = mode_values.iloc[0]
            most_common_count = categorical_data[column].value_counts().iloc[0]

        summary_rows.append({
            "열 이름": column,
            "데이터 타입": str(data[column].dtype),
            "고유값 개수": categorical_data[column].nunique(),
            "결측치 개수": data[column].isnull().sum(),
            "결측치 비율(%)": round(data[column].isnull().mean() * 100, 3),
            "최빈값": most_common_value,
            "최빈값 빈도": most_common_count
        })

    return DataFrame(summary_rows)


def correlation_overview(data, top_n=8, min_abs=0.3):
    """수치형 변수 쌍의 상관관계를 강한 순으로 정리하고 해석 문장을 만듭니다.

    데이터셋에 어떤 관계가 숨어 있는지 빠르게 훑어 '분석 주제'를 잡는 데 도움을 줍니다.

    Args:
        data (DataFrame): 분석할 데이터
        top_n (int): 표에 보여줄 상위 쌍 개수
        min_abs (float): 이 값 이상의 |상관계수|만 '주목할 관계'로 해석

    Returns:
        ranked (DataFrame): [변수1, 변수2, 상관계수, 강도, 방향] (강한 순)
        insight (str): 해석 문장
    """
    empty = DataFrame(columns=["변수1", "변수2", "상관계수", "강도", "방향"])

    numeric = data.select_dtypes(include="number")
    # 값이 하나뿐인(상수) 컬럼은 상관 계산 불가라 제외
    numeric = numeric.loc[:, numeric.nunique(dropna=True) > 1]

    if numeric.shape[1] < 2:
        return empty, "상관관계를 볼 수치형 변수가 2개 미만이라 분석할 수 없습니다."

    corr = numeric.corr()

    # 상삼각만 추출(자기 자신·중복 쌍 제외)
    rows = []
    cols = list(corr.columns)
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            r = corr.iloc[i, j]
            if pd.isna(r):
                continue
            rows.append({
                "변수1": cols[i],
                "변수2": cols[j],
                "상관계수": round(float(r), 3),
            })

    if not rows:
        return empty, "계산 가능한 상관관계가 없습니다(결측이 너무 많을 수 있어요)."

    ranked = DataFrame(rows)
    abs_corr = ranked["상관계수"].abs()

    conditions = [abs_corr >= 0.7, abs_corr >= 0.4, abs_corr >= 0.2]
    labels = ["강함", "중간", "약함"]
    ranked["강도"] = np.select(conditions, labels, default="매우 약함")
    ranked["방향"] = np.select(
        [ranked["상관계수"] > 0, ranked["상관계수"] < 0],
        ["양(+)", "음(-)"],
        default="없음",
    )

    ranked = (
        ranked.reindex(abs_corr.sort_values(ascending=False).index)
        .reset_index(drop=True)
        .head(top_n)
    )

    # --- 해석 문장 ---
    notable = ranked[ranked["상관계수"].abs() >= min_abs]

    if notable.empty:
        insight = (
            f"수치형 변수 {numeric.shape[1]}개 사이에 뚜렷한 상관관계(|r| ≥ {min_abs})가 보이지 않습니다. "
            "변수들이 비교적 독립적이에요. 이런 데이터는 '관계 분석'보다 그룹별 비교나 분포 분석이 더 어울릴 수 있어요."
        )
    else:
        top = notable.iloc[0]
        increase = "커지는" if top["상관계수"] > 0 else "작아지는"
        direction = "같이 커지는(양의)" if top["상관계수"] > 0 else "반대로 움직이는(음의)"

        lines = [
            f"가장 주목할 관계는 **{top['변수1']} ↔ {top['변수2']}** 입니다 "
            f"(상관계수 {top['상관계수']}, {top['강도']} {direction} 관계). "
            f"`{top['변수1']}`가 커질 때 `{top['변수2']}`도 {increase} 경향이 있어요."
        ]

        others = notable.iloc[1:4]
        if not others.empty:
            parts = [f"{row['변수1']}↔{row['변수2']}({row['상관계수']})" for _, row in others.iterrows()]
            lines.append("그 외 주목할 관계: " + ", ".join(parts) + ".")

        lines.append(
            "⚠️ 상관관계가 곧 인과관계는 아니에요 — 관계가 보이면 '왜 그런지'를 도메인 지식으로 따져봐야 합니다."
        )
        insight = "\n\n".join(lines)

    return ranked, insight