from pandas import pivot_table

def long2wide(df, hue, values, dropna=True):
    """
    long format 데이터프레임을 group 단위로 컬럼을 펼처 wide format으로 변환하는 함수

    Args:
        - df : 변환할 데이터 프레임
        - hue : 펼칠 기준이 되는 그룹 열 이름(각 값이 새 열이 됨)
        - values : 펼칠 값이 담긴 열 이름
        - dropna : 결측치 행을 결과에서 제외할 지 여부 (기본값 : True)

    Returns
        - wide format으로 변환된 데이터프레임
    """
    wide = pivot_table(data=df,
                       index=df.groupby(hue).cumcount(),
                       columns=hue, values=values, dropna=dropna)
    
    wide.columns.name = None
    wide.index.name = None
    return wide