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

    한국 공공데이터 CSV는 인코딩(utf-8/cp949/euc-kr)과 형식이 제각각이고,
    엑셀/특정 도구에서 내보낸 'BOM 없는 UTF-16', 세미콜론·탭 구분자도 흔합니다.
    그래서 다양한 인코딩 + 구분자 자동탐지까지 시도합니다.

    Returns:
        DataFrame: 읽은 데이터
        str: 사용된 인코딩 설명
    """

    file_bytes = uploaded_file.getvalue()

    # BOM으로 인코딩을 먼저 확정할 수 있으면 그것만 시도합니다.
    if file_bytes.startswith(b"\xef\xbb\xbf"):
        encodings = ["utf-8-sig"]
    elif file_bytes.startswith((b"\xff\xfe", b"\xfe\xff")):
        encodings = ["utf-16"]
    else:
        # BOM이 없으면 후보를 넓게 시도합니다.
        # - utf-16-le/be : BOM 없는 UTF-16 (엑셀 'Unicode Text' 등에서 발생)
        # - cp1252       : 서유럽권 인코딩
        encodings = [
            "utf-8-sig",
            "utf-8",
            "cp949",
            "euc-kr",
            "utf-16",
            "utf-16-le",
            "utf-16-be",
            "cp1252",
        ]

    errors = []

    for encoding in encodings:
        # 1) 먼저 바이트를 텍스트로 디코딩합니다.
        try:
            text = file_bytes.decode(encoding)
        except (UnicodeError, LookupError) as error:
            errors.append(f"{encoding}: {type(error).__name__}")
            continue

        # 2) 텍스트에서 '진짜 표가 시작되는 헤더 줄'을 찾아 읽습니다.
        #    (공공데이터 CSV의 앞쪽 검색조건·메타데이터 줄을 자동으로 건너뜀)
        try:
            data, note = _read_csv_text(text)
        except Exception as error:
            errors.append(f"{encoding}: {type(error).__name__}")
            continue

        if data is not None and data.shape[1] >= 1 and data.shape[0] >= 1:
            label = encoding if not note else f"{encoding} ({note})"
            return data, label

    raise ValueError(
        "CSV 파일을 읽을 수 없습니다. 파일이 손상됐거나 지원하지 않는 형식일 수 있어요. "
        "엑셀에서 열어 'CSV UTF-8(쉼표로 분리)'로 다시 저장한 뒤 올려보세요.\n"
        f"(시도한 인코딩: {', '.join(errors)})"
    )


def _read_csv_text(text):
    """
    CSV 텍스트에서 실제 표가 시작되는 헤더 줄을 추정해 DataFrame으로 읽습니다.

    공공데이터 CSV는 표 위에 '검색조건', '제공기관' 같은 메타데이터 줄이
    여러 개 붙어 있는 경우가 많습니다. 각 줄의 '열(필드) 개수'를 세어
    가장 흔한 열 수(= 표의 너비)를 찾고, 그 너비가 처음 등장하는 줄을
    헤더로 보고 그 위 줄들은 건너뜁니다.

    Returns:
        (DataFrame, note) — note는 머리말을 건너뛴 경우 안내 문자열
    """
    import csv
    from io import StringIO
    from collections import Counter

    rows = list(csv.reader(StringIO(text)))

    # 내용이 있는 줄들의 필드 개수만 모읍니다.
    field_counts = [len(r) for r in rows if any(str(c).strip() for c in r)]
    if not field_counts:
        raise ValueError("내용이 없는 CSV입니다.")

    # 2개 이상 열을 가진 줄들 중 가장 자주 나오는 너비를 표의 열 수로 봅니다.
    width_counter = Counter(c for c in field_counts if c >= 2)
    dominant_width = (
        max(width_counter.items(), key=lambda kv: (kv[1], kv[0]))[0]
        if width_counter else max(field_counts)
    )

    # 그 너비가 처음 나타나는 줄을 헤더로 봅니다(그 위는 머리말).
    header_index = 0
    for i, r in enumerate(rows):
        if len(r) == dominant_width and any(str(c).strip() for c in r):
            header_index = i
            break

    # 헤더 줄부터 다시 읽습니다. thousands=','로 "22,776" 같은 천단위 숫자도 인식.
    data = pd.read_csv(
        StringIO(text),
        skiprows=header_index,
        skip_blank_lines=True,
        thousands=",",
    )

    data = _clean_loaded_columns(data)

    note = f"머리말 {header_index}줄 건너뜀" if header_index > 0 else ""
    return data, note


def _clean_loaded_columns(data):
    """컬럼명 공백을 정리하고, 줄 끝 쉼표로 생긴 빈 'Unnamed' 컬럼을 제거합니다."""
    data = data.rename(columns=lambda c: str(c).strip())

    drop_columns = [
        column for column in data.columns
        if str(column).startswith("Unnamed") and data[column].isna().all()
    ]
    if drop_columns:
        data = data.drop(columns=drop_columns)

    return data


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


def recommend_analysis_flow(data):
    """
    업로드된 데이터의 구조를 보고 다음 분석 흐름을 추천합니다.

    사용자가 "이제 무엇을 해야 하지?"에서 멈추지 않도록
    컬럼 타입, 결측/중복, 날짜 후보, 행 수를 기준으로 추천 페이지와 이유를 만듭니다.
    """

    if data is None or data.empty:
        return (
            "데이터가 비어 있어 추천 흐름을 만들 수 없습니다.",
            DataFrame(columns=["순서", "추천 작업", "이유", "추천 페이지"]),
            []
        )

    df = data.copy()
    row_count, column_count = df.shape
    memory_mb = df.memory_usage(deep=True).sum() / 1024 / 1024

    numeric_columns = df.select_dtypes(include="number").columns.tolist()
    categorical_columns = df.select_dtypes(
        include=["object", "category", "string"]
    ).columns.tolist()
    datetime_columns = df.select_dtypes(
        include=["datetime", "datetimetz"]
    ).columns.tolist()

    date_name_keywords = [
        "날짜", "일자", "년월", "월일", "기준일", "등록일", "수정일",
        "date", "time", "created", "updated",
    ]
    date_name_candidates = [
        column for column in df.columns
        if any(keyword in str(column).lower() for keyword in date_name_keywords)
    ]
    date_candidates = list(dict.fromkeys(datetime_columns + date_name_candidates))

    missing_cells = int(df.isna().sum().sum())
    missing_ratio = missing_cells / (row_count * column_count) if row_count and column_count else 0
    duplicate_rows = int(df.duplicated().sum())

    recommendations = []

    def add(title, reason, page):
        recommendations.append({
            "순서": len(recommendations) + 1,
            "추천 작업": title,
            "이유": reason,
            "추천 페이지": page,
        })

    add(
        "데이터 상태 먼저 확인",
        f"{row_count:,}행, {column_count:,}열 데이터입니다. 결측치·중복·타입을 먼저 확인하면 이후 분석 오류를 줄일 수 있습니다.",
        "데이터 품질 점검",
    )

    if missing_cells > 0 or duplicate_rows > 0:
        add(
            "정제 후 분석",
            f"결측치 {missing_cells:,}개, 중복 행 {duplicate_rows:,}개가 있습니다. 필요한 처리 후 분석하는 것을 권장합니다.",
            "데이터 정제",
        )
    elif column_count >= 1:
        add(
            "필요한 컬럼만 가볍게 정리",
            "큰 문제는 없어 보이지만, 날짜 타입 변경이나 불필요한 컬럼 삭제를 해두면 분석이 더 편해집니다.",
            "데이터 정제",
        )

    if date_candidates and numeric_columns:
        add(
            "시간 흐름 분석",
            f"날짜 후보({', '.join(map(str, date_candidates[:3]))})와 숫자형 변수 {len(numeric_columns)}개가 있어 추세·이동평균 분석이 가능합니다.",
            "시계열 분석",
        )

    if categorical_columns and numeric_columns:
        add(
            "그룹별 차이 비교",
            f"범주형 변수 {len(categorical_columns)}개와 숫자형 변수 {len(numeric_columns)}개가 있어 그룹별 평균·합계 비교가 가능합니다.",
            "그룹별 집계",
        )

    if len(numeric_columns) >= 2:
        add(
            "변수 간 관계 확인",
            f"숫자형 변수가 {len(numeric_columns)}개 있어 상관분석이나 회귀분석으로 관계를 확인할 수 있습니다.",
            "통계 분석",
        )

    if len(numeric_columns) >= 2 and row_count >= 30:
        add(
            "설명/예측 모델 검토",
            "표본 수와 숫자형 변수가 충분해 보입니다. 종속변수와 설명변수를 정해 회귀분석을 시도할 수 있습니다.",
            "회귀분석",
        )

    if len(categorical_columns) >= 2:
        add(
            "범주형 변수 관계 확인",
            f"범주형 변수가 {len(categorical_columns)}개 있어 교차표와 카이제곱 검정으로 관계를 볼 수 있습니다.",
            "통계 분석",
        )

    add(
        "결과 모아 보고서 만들기",
        "분석 과정에서 중요한 표와 그래프를 리포트에 담아 HTML 보고서로 정리할 수 있습니다.",
        "보고서",
    )

    notes = []
    if memory_mb > 150 or row_count > 1_000_000:
        notes.append(
            "데이터가 큰 편입니다. 링크 배포 환경에서는 전체 데이터 분석보다 샘플·집계 중심 분석을 권장합니다."
        )
    if missing_ratio >= 0.2:
        notes.append(
            f"전체 셀의 약 {missing_ratio * 100:.1f}%가 결측치입니다. 분석 전에 결측 처리 기준을 정하는 것이 좋습니다."
        )
    if len(numeric_columns) == 0:
        notes.append(
            "숫자형 컬럼이 없어 통계·회귀·시계열 값 분석이 제한됩니다. 숫자로 보이는 컬럼은 데이터 정제에서 숫자형으로 바꿔보세요."
        )
    if not date_candidates:
        notes.append(
            "날짜 컬럼이 뚜렷하지 않습니다. 시간 흐름을 보고 싶다면 날짜 컬럼을 날짜형으로 변환해야 합니다."
        )

    summary = (
        f"이 데이터는 {row_count:,}행, {column_count:,}열입니다. "
        f"숫자형 {len(numeric_columns)}개, 범주형 {len(categorical_columns)}개, "
        f"날짜 후보 {len(date_candidates)}개를 찾았습니다."
    )

    return summary, DataFrame(recommendations), notes



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


# ============================================================
# 시계열 분석 도우미
# ============================================================
# 날짜 컬럼을 기준으로 데이터를 기간별로 묶고(리샘플링), 흐름과 추세를
# 보기 쉽게 정리합니다. 가장 흔한 실무 데이터가 시계열입니다.
# ============================================================

# 화면에 보여줄 기간 이름 → pandas resample 규칙(rule) 매핑입니다.
# pandas 3.x 권장 alias를 사용합니다(ME=월말, QE=분기말, YE=연말).
RESAMPLE_RULES = {
    "일별": "D",
    "주별": "W",
    "월별": "ME",
    "분기별": "QE",
    "연별": "YE",
}


def detect_datetime_columns(data):
    """이미 datetime 타입인 컬럼 이름 목록을 반환합니다."""
    return data.select_dtypes(include=["datetime", "datetimetz"]).columns.tolist()


def resample_timeseries(data, date_column, value_column, period="월별", agg="평균"):
    """
    날짜 컬럼을 기준으로 값 컬럼을 기간별로 집계(리샘플링)합니다.

    Args:
        data (DataFrame): 원본 데이터
        date_column (str): 날짜로 사용할 컬럼(자동으로 datetime 변환)
        value_column (str): 집계할 숫자형 컬럼
        period (str): "일별" / "주별" / "월별" / "분기별" / "연별"
        agg (str): "평균" / "합계" / "건수"

    Returns:
        DataFrame: [date_column, value_column] 기간별 집계 결과(시간순 정렬)
    """
    rule = RESAMPLE_RULES.get(period, "ME")
    agg_func = {"평균": "mean", "합계": "sum", "건수": "count"}.get(agg, "mean")

    df = data[[date_column, value_column]].copy()
    df[date_column] = pd.to_datetime(df[date_column], errors="coerce")

    # 날짜 변환에 실패한 행은 제외합니다.
    df = df.dropna(subset=[date_column])

    # 건수는 '기간별 행 개수'이므로 값 컬럼의 타입과 무관합니다.
    # 평균·합계일 때만 값 컬럼을 숫자로 바꾸고 빈 값을 제외합니다.
    if agg_func != "count":
        df[value_column] = pd.to_numeric(df[value_column], errors="coerce")
        df = df.dropna(subset=[value_column])

    if df.empty:
        raise ValueError("날짜로 변환 가능한 데이터가 없습니다. 다른 컬럼을 선택해주세요.")

    resampler = df.set_index(date_column).resample(rule)

    if agg_func == "count":
        # size()는 값이 비어 있어도 행 수를 세므로 '건수'에 적합합니다.
        resampled = resampler.size().reset_index(name=value_column)
    else:
        resampled = resampler[value_column].agg(agg_func).reset_index()

    return resampled


def add_moving_average(ts_df, value_column, window=3, ma_column="이동평균"):
    """시계열 집계 결과에 이동평균(rolling mean) 컬럼을 추가합니다.

    이동평균은 짧은 변동(노이즈)을 부드럽게 만들어 추세를 보기 쉽게 합니다.
    """
    result = ts_df.copy()
    result[ma_column] = (
        result[value_column].rolling(window=window, min_periods=1).mean()
    )
    return result


def timeseries_trend_insight(ts_df, date_column, value_column):
    """시계열의 전반적인 추세와 변동성을 해석 문장으로 만듭니다."""
    series = ts_df[[date_column, value_column]].dropna()

    if len(series) < 3:
        return "추세를 판단하기에 데이터 구간이 너무 적습니다."

    # 시간 순서를 0,1,2,... 정수 축으로 바꿔 기울기를 계산합니다.
    x = np.arange(len(series))
    y = series[value_column].to_numpy(dtype=float)

    slope = np.polyfit(x, y, 1)[0]

    first_value = y[0]
    last_value = y[-1]
    start_label = series[date_column].iloc[0]
    end_label = series[date_column].iloc[-1]
    peak_idx = int(np.nanargmax(y))
    low_idx = int(np.nanargmin(y))
    peak_value = y[peak_idx]
    low_value = y[low_idx]
    peak_label = series[date_column].iloc[peak_idx]
    low_label = series[date_column].iloc[low_idx]

    # 변화율(%)은 시작값이 0이 아닐 때만 계산합니다.
    if first_value != 0:
        change_pct = (last_value - first_value) / abs(first_value) * 100
        change_text = f" (시작 대비 약 {change_pct:+.1f}%)"
    else:
        change_text = ""

    if slope > 0:
        trend = "전반적으로 **증가**하는 추세"
    elif slope < 0:
        trend = "전반적으로 **감소**하는 추세"
    else:
        trend = "뚜렷한 추세가 없는 흐름"

    try:
        start_str = pd.Timestamp(start_label).date()
        end_str = pd.Timestamp(end_label).date()
        peak_str = pd.Timestamp(peak_label).date()
        low_str = pd.Timestamp(low_label).date()
    except Exception:
        start_str, end_str = start_label, end_label
        peak_str, low_str = peak_label, low_label

    mean_value = np.nanmean(y)
    std_value = np.nanstd(y)
    volatility_text = ""
    if mean_value and not np.isnan(mean_value):
        cv = std_value / abs(mean_value)
        if cv >= 0.5:
            volatility_text = (
                " 기간별 변동 폭이 큰 편이라 평균 추세만으로 판단하기보다 "
                "특정 급등/급락 구간의 원인을 함께 확인하는 것이 좋습니다."
            )
        elif cv >= 0.2:
            volatility_text = " 중간 수준의 변동이 있어 이동평균과 원자료를 함께 보는 것이 좋습니다."
        else:
            volatility_text = " 기간별 변동 폭은 비교적 안정적인 편입니다."

    return (
        f"`{value_column}`는 {start_str}부터 {end_str}까지 {trend}를 보입니다"
        f"{change_text}. 관측 구간에서 최고값은 {peak_str}의 {peak_value:,.2f}, "
        f"최저값은 {low_str}의 {low_value:,.2f}입니다.{volatility_text} "
        "이동평균선을 함께 보면 단기 변동을 걷어낸 흐름을 더 명확히 볼 수 있어요. "
        "⚠️ 과거 추세가 미래에도 이어진다는 보장은 없으니 예측에는 주의하세요."
    )


def _format_insight_value(value):
    """인사이트 문장에 넣을 숫자를 보기 좋게 포맷합니다."""
    if pd.isna(value):
        return "계산 불가"
    try:
        return f"{float(value):,.2f}"
    except Exception:
        return str(value)


def group_analysis_rationale(group_columns, value_column, agg_label, chart_type):
    """그룹 집계를 왜 수행하는지 설명하는 범용 분석 근거 문장을 만듭니다."""
    groups = ", ".join(f"`{column}`" for column in group_columns)

    if len(group_columns) == 1:
        group_reason = (
            f"{groups}은 데이터를 여러 그룹으로 나누는 기준 변수입니다. "
            "그룹별 차이와 집중도를 확인하기 위해 사용했습니다."
        )
    else:
        group_reason = (
            f"{groups}은 두 기준을 함께 비교하기 위한 변수입니다. "
            "단일 기준으로는 보이지 않는 조합별 차이를 확인하기 위해 사용했습니다."
        )

    if agg_label == "개수":
        value_reason = (
            "`개수`는 각 그룹에 데이터가 얼마나 많이 분포하는지 보여주는 기본 지표입니다. "
            "그룹별 규모와 데이터 집중도를 비교하기 위해 사용했습니다."
        )
    elif agg_label == "합계":
        value_reason = (
            f"`{value_column}`의 합계는 그룹별 전체 규모나 기여도를 비교하기 위한 지표입니다."
        )
    elif agg_label == "평균":
        value_reason = (
            f"`{value_column}`의 평균은 그룹별 일반적인 수준을 비교하기 위한 지표입니다. "
            "다만 그룹별 표본 수가 다르면 평균이 왜곡될 수 있어 개수도 함께 확인하는 것이 좋습니다."
        )
    elif agg_label == "중앙값":
        value_reason = (
            f"`{value_column}`의 중앙값은 극단값의 영향을 줄이고 대표적인 수준을 보기 위한 지표입니다."
        )
    else:
        value_reason = (
            f"`{value_column}`의 {agg_label}은 그룹별 값의 경계와 범위를 확인하기 위한 지표입니다."
        )

    if chart_type == "bar":
        chart_reason = "막대그래프는 범주별 값의 크기 차이를 직관적으로 비교하기에 적합해서 사용했습니다."
    elif chart_type == "heatmap":
        chart_reason = "히트맵은 두 범주 조합에서 값이 집중되는 구간을 색으로 빠르게 찾기 위해 사용했습니다."
    else:
        chart_reason = "선택한 그래프는 집계 결과를 비교하기 쉽게 보여주기 위해 사용했습니다."

    caution = (
        "이 분석은 그룹 간 차이를 탐색하는 단계이므로, 차이가 곧 원인이라는 뜻은 아닙니다. "
        "필요하면 통계 분석 페이지에서 유의성 검정을 함께 확인하는 것이 좋습니다."
    )

    return "\n\n".join([group_reason, value_reason, chart_reason, caution])


def timeseries_analysis_rationale(date_column, value_column, period, agg, ma_window):
    """시계열 분석을 왜 수행하는지 설명하는 범용 분석 근거 문장을 만듭니다."""
    value_reason = (
        f"`{date_column}`은 시간 순서를 나타내는 변수이므로 변화 흐름을 보기 위해 사용했습니다. "
        f"`{value_column}`은 시간에 따라 비교할 수 있는 숫자형 지표라서 분석 대상으로 선택했습니다."
    )

    agg_reason = (
        f"{period} 단위로 `{agg}` 집계를 적용해 너무 세부적인 변동을 줄이고, "
        "기간별 흐름을 비교할 수 있게 했습니다."
    )

    chart_reason = (
        "선그래프는 시간 순서에 따른 증가, 감소, 반복 패턴을 확인하기에 적합해서 사용했습니다. "
        f"{ma_window}개 구간 이동평균은 단기 변동을 부드럽게 만들어 전반적인 추세를 보기 위한 보조선입니다."
    )

    caution = (
        "시계열 추세는 과거 데이터의 흐름을 요약한 것이며, 미래에도 같은 흐름이 이어진다는 보장은 없습니다. "
        "예측이나 원인 해석에는 외부 요인과 추가 검증이 필요합니다."
    )

    return "\n\n".join([value_reason, agg_reason, chart_reason, caution])


def group_aggregation_insight(result, group_column, value_column, agg_label):
    """단일 그룹 집계 결과를 보고서용 해석 문장으로 바꿉니다."""
    if result is None or result.empty:
        return "집계 결과가 비어 있어 해석을 생성할 수 없습니다."

    if group_column not in result.columns or value_column not in result.columns:
        return "집계 결과 컬럼을 확인할 수 없어 해석을 생성할 수 없습니다."

    df = result[[group_column, value_column]].copy()
    df[value_column] = pd.to_numeric(df[value_column], errors="coerce")
    df = df.dropna(subset=[value_column]).sort_values(value_column, ascending=False)

    if df.empty:
        return "집계값이 모두 비어 있어 해석을 생성할 수 없습니다."

    top = df.iloc[0]
    bottom = df.iloc[-1]
    group_count = len(df)
    top_group = str(top[group_column])
    top_value = top[value_column]
    bottom_group = str(bottom[group_column])
    bottom_value = bottom[value_column]

    lines = [
        f"`{top_group}` 그룹이 {value_column} 기준으로 가장 높은 값({_format_insight_value(top_value)})을 보입니다."
    ]

    if group_count >= 2:
        second = df.iloc[1]
        gap = top_value - second[value_column]
        lines.append(
            f"2위 `{second[group_column]}`와의 차이는 {_format_insight_value(gap)}입니다. "
            "이 차이가 실제로 의미 있는지는 표본 수, 기간, 집계 기준이 같은지 함께 확인해야 합니다."
        )

    if group_count >= 3:
        median_value = df[value_column].median()
        if median_value != 0 and not pd.isna(median_value):
            ratio = top_value / median_value
            lines.append(
                f"전체 그룹의 중앙값({_format_insight_value(median_value)})과 비교하면 "
                f"상위 그룹은 약 {ratio:.1f}배 수준입니다. "
                "특정 그룹이 전체 패턴을 끌어올리는지 확인할 수 있는 지점입니다."
            )
        lines.append(
            f"가장 낮은 그룹은 `{bottom_group}`({_format_insight_value(bottom_value)})입니다. "
            "상위/하위 그룹의 차이가 데이터 수집 누락, 표본 수 차이, 실제 행동 차이 중 무엇에서 왔는지 분리해서 보는 것이 좋습니다."
        )

    non_negative = (df[value_column] >= 0).all()
    can_use_share = agg_label in ["개수", "합계"] and non_negative
    total = df[value_column].sum()
    if can_use_share and total > 0:
        top_share = top_value / total * 100
        if top_share >= 50:
            lines.append(
                f"`{top_group}` 하나가 전체의 {top_share:.1f}%를 차지합니다. "
                "결과가 일부 그룹에 집중되어 있으므로 평균보다 점유율과 상위 그룹 비중을 함께 보는 편이 안전합니다."
            )
        else:
            lines.append(
                f"`{top_group}`의 전체 비중은 {top_share:.1f}%입니다. "
                "상위 그룹이 크기는 하지만 한 그룹만으로 전체가 설명되는 구조는 아닙니다."
            )
    elif agg_label in ["평균", "중앙값"]:
        lines.append(
            f"`{agg_label}` 비교는 그룹별 표본 수에 민감합니다. "
            "표본 수가 작은 그룹의 평균/중앙값은 우연한 값에 흔들릴 수 있으니 개수 집계와 함께 확인하는 것이 좋습니다."
        )

    return "\n\n".join(lines)


def pivot_aggregation_insight(pivot, row_column, column_column, value_name):
    """2차원 피벗 집계 결과를 보고서용 해석 문장으로 바꿉니다."""
    if pivot is None or pivot.empty:
        return "피벗 집계 결과가 비어 있어 해석을 생성할 수 없습니다."

    numeric = pivot.apply(pd.to_numeric, errors="coerce")
    stacked = numeric.stack(dropna=True)

    if stacked.empty:
        return "피벗표의 집계값이 모두 비어 있어 해석을 생성할 수 없습니다."

    max_key = stacked.idxmax()
    min_key = stacked.idxmin()
    max_value = stacked.loc[max_key]
    min_value = stacked.loc[min_key]
    filled_ratio = stacked.count() / numeric.size * 100 if numeric.size else 0

    row_max, col_max = max_key
    row_min, col_min = min_key

    lines = [
        f"`{row_column}={row_max}`, `{column_column}={col_max}` 조합이 "
        f"{value_name} 기준으로 가장 높은 값({_format_insight_value(max_value)})을 보입니다.",
        f"가장 낮은 조합은 `{row_column}={row_min}`, `{column_column}={col_min}`"
        f"({_format_insight_value(min_value)})입니다.",
    ]

    if filled_ratio < 70:
        lines.append(
            f"피벗표에서 실제 값이 있는 셀은 전체의 {filled_ratio:.1f}%입니다. "
            "빈 조합이 많은 편이므로 없는 수요/활동인지, 데이터 누락인지 먼저 구분해야 합니다."
        )
    else:
        lines.append(
            f"피벗표의 값 채움 비율은 {filled_ratio:.1f}%로, 대부분의 조합을 비교할 수 있습니다. "
            "색이 진한 구간을 우선 확인하면 집중되는 조합을 빠르게 찾을 수 있습니다."
        )

    return "\n\n".join(lines)
