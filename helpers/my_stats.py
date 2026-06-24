from math import sqrt
from pandas import DataFrame, melt, concat
from scipy.stats import t
from scipy.stats import normaltest, bartlett, levene
from scipy.stats import ttest_1samp, wilcoxon, ttest_rel, ttest_ind, mannwhitneyu

from statannotations.Annotator import Annotator

from . import my_plot

def ci(data, column=None, clevel=0.95):
    """
    주어진 데이터에 대한 모평균의 신뢰구간을 계산하는 함수

    Args:
        data (Series | list | ndarray | DataFrame): 연속형 데이터 또는 데이터프레임
        column (str): data가 데이터프레임인 경우 대상 컬럼명 (기본값: None)
        clevel (float): 신뢰수준 (기본값: 0.95)

    Returns:
        tuple: (신뢰구간 하한, 신뢰구간 상한)
    """
    # 데이터프레임 + 컬럼명 형태로 전달된 경우 해당 컬럼만 추출
    if column is not None:
        data = data[column]

    n=len(data)      # 표본크기
    dof = n-1        # 자유도
    sample_mean = data.mean() # 표본 평균
    sample_std = data.std() # 표본 표준편차
    sample_std_error = sample_std / sqrt(n) # 표준 오차

    # 신뢰구간을 계산하여 리턴한다.
    return t.interval(clevel, dof, loc=sample_mean, scale=sample_std_error)


#----------------------------------------------------------
def test_assumptions(data, columns=None, alpha=0.05, center='median'):
    """
    가설검정의 가정(정규성, 등분산성)을 일괄적으로 검정하여 결과표를 반환하는 함수

    각 변수에 대해 정규성 검정(normaltest)을 수행하고, 변수가 두 개 이상인 경우 등분산성 검정을 수행한다. 이 때 모든 변수가 정규성을 충족하면 Bartlett 검정을, 하나라도 충족하지 못하면 Levene 검정을 선택적으로 사용한다.

    Args:
        data(dataframe) : 검정 대상이 되는 데이터 프레임
        columns(list): 검정에 사용할 컬럼명 목록(기본값: None > 수치형 컬럼 전체)
        alpha(float): 유의수준(기본값: 0.05)
        center(str): Levene 검정 시 사용할 중심 경향값 (기본값: median)

    Returns:
        Dataframe: field를 인덱스로 하는 검정 결과표
                    (test, statistic, p-value, result 컬럼 포함)
    """
    # 검정에 사용할 컬럼 결정(지정하지 않으면 수치형 컬럼 전체 사용)
    if columns is None:
        columns = data.select_dtypes(include='number').columns.tolist()

    # 하나의 컬럼명이 문자열로 전달된 경우 리스트로 감싸준다
    if type(columns) == str:
        columns = [columns]

    report = []   # 결과를 누적할 리스트
    normal_dist=True # 모든 변수가 정규성을 충족하는지 여부

    # 각 변수에 대한 정규성 검정
    for c in columns:
        s, p = normaltest(data[c])
        normalize = p >=alpha

        report.append({
                'field':c,
                'test': 'normaltest',
                'statistic':s,
                'p-value':p,
                'result':normalize
        })
        normal_dist = normal_dist and normalize
        

    # 변수가 두 개 이상인 경우 등분산성 검정
    if len(columns) >1:
        # 각 컬럼을 실수형으로 변환하여 리스트로 추출(Bartlett은 실수형 필요)
        samples = [data[c].astype('float') for c in columns]

        if normal_dist: # 모든 변수가 정규성을 충족 -> Bartlett 검정
            name = "Bartlett"
            s, p = bartlett(*samples)
        else:
            name = "Levene"
            s, p = levene(*samples, center=center)

        report.append({
            'field':name,
            'test': 'equal_var',
            'statistic':s,
            'p-value':p,
            'result':p>=alpha
            })

    # 결과표 리턴
    return DataFrame(report).set_index("field")


#----------------------------------------------------------
def test_1sample(data, column, popmean=0, alpha=0.05):
    """
    한집단의 평균이 기준값(popmean)과 같은지 검정하는 함수

    정규성 충족 시 일표본 t검정, 미충족 시 Wilcoxon 부호 순위 검정을 수행하며, 
    양측/좌측단측/우측단측 세 가지 대립가설을 일괄 검정한다.

    Args:
        data (DataFrame): 검정 대상 데이터프레임
        column (str): 검정할 연속형 컬럼명
        popmean (float):비교 기준이 되는 모평균 μ₀ (기본값:0)
        alpha (float): 유의수준 (기본값: 0.05)

    Returns:
        DataFrame: 대립가설(alternative)별 검정/통계량/p-value/유의성 결과표
                    (two-sided / less / greater 3행 )
    """
    # 대상 컬럼을 결측 제거하여 추출
    sample = data[column].dropna()

    # test_assumptions로 정규성 검정 (단일 컬럼이라 등분산성은 수행되지 않음)
    report = test_assumptions(data, columns=column, alpha=alpha)

    # 정규성 충족 여부 추출
    is_normal = bool(report.loc[column, "result"])

    # 정규성 충족 여부에 따라 적용할 검정 이름 결정
    test_name = "One-sample t-test" if is_normal else "Wilcoxon signed-rank test"

    # 대립가설 방향별 해석 문구 (유의할 때 표시)
    verdicts = {"two-sided":'차이 있음', 'less':'μ₀보다 작음', 'greater':'μ₀보다 큼'}

    rows = []
    # 양측/좌측단측/우측단측을 일괄 검정
    for alt in ("two-sided", "less", "greater"):
        if is_normal: # 정규성 충족 > 일표본 t검정
            stat, p = ttest_1samp(sample, popmean, alternative=alt)
        else:
            stat, p = wilcoxon(sample, popmean, alternative=alt)

        # p < alpha이면 통계적으로 유의(귀무가설 기각)
        significant = p < alpha

        rows.append({
            "test": test_name,
            "alternative": alt,
            "statistic": round(float(stat), 4),
            "p-value": round(float(p), 4),
            "significant":significant,
            "result":verdicts[alt] if significant else "차이없음"
        })

    # 세 방향 결과를 표로 정리하여 반환
    return DataFrame(rows).set_index(["test", "alternative"])

#----------------------------------------------------------
def test_paired(data, before, after, alpha=0.05,
                plot=True, palette=None, title=None, xlabel=None, ylabel=None,
                width=1280, height=640, save_path=None):
    """
    짝지어진 두 측정값(전/후)의 차이가 있는지 검정하는 함수 (wide 형식)

    차이값 d= after - before 의 정규성 충족 시 대응표본 t검정,
    미충족 시 Wilcoxon 부호순위 검정을 수행하며,
    양측, 좌측단측, 우측단측 세 가지 대립가설을 일괄 검정한다.

    Args:
        data (DataFrame): 검정 대상 데이터프레임
        before (str): 사전 측정값 컬럼명
        after (str): 사후 측정값 컬럼명
        alpha (float): 유의수준(기본값: 0.05)
        plot (bool): 결과를 시각화할지 여부 (기본값: True)
        palette (str or list, optional): 색상 팔레트
        title (str, optional): 그래프 제목
        xlabel (str, optional): x축 라벨
        ylabel (str, optional): y축 라벨
        width (int, optional): 그래프 가로 크기
        height (int, optional) : 그래프 세로 크기
        save_path (str, optioanl): 그래프 저장 경로

    Returns:
        DataFrame: 대립가설(alternative)별 검정, 통계량, p-value, 유의성 결과표
    """

    # 같은 행끼리 짝지어야 하므로 두 컬럼을 함께 결측 행 제거
    paired = data[[before, after]].dropna()

    # 차이값 d = after - before를 계산
    d= (paired[after] - paired[before]).rename('diff')

    # test_assumptions로 차이값의 정규성만 검정(단일 컬럼)
    report = test_assumptions(DataFrame({'diff':d}), columns=['diff'], alpha=alpha)

    # 차이값의 정규성 충족 여부
    is_normal = bool(report.loc['diff', 'result'])

    # 정규성 충족 여부에 따라 적용할 검정 이름 결정
    test_name = 'Paired t-test' if is_normal else 'Wilcoxon signed-rank test'

    # 대립가설 방향별 해석 문구(유의할 때 표시)
    verdicts = {
        'two-sided': '차이 있음',
        'less':f'{after} <{before}',
        'greater':f'{after}>{before}'
    }

    rows = []
    # 양측, 좌측단측, 우측단측을 일괄 검정(항상 afrer, before 순)
    for alt in ('two-sided', 'less', 'greater'):
        if is_normal: # 정규성 충족 > 대응표본 t 검정
            stat, p = ttest_rel(paired[after], paired[before], alternative=alt)
        else:
            stat, p = wilcoxon(paired[after], paired[before], alternative=alt)

        significant=p<alpha # p<alpha 이면 통계적으로 유의(귀무가설 기각)

        rows.append({
            "test": test_name,
            "alternative":alt,
            "statistic": round(float(stat), 4),
            'p-value': round(float(p),4),
            "significant":significant,
            'result': verdicts[alt] if significant else "차이 없음"
        })

    # 세 방향 결과를 표로 정리하여 반환 --> 함수 맨 마지막에 return문 필요
    result_df = DataFrame(rows).set_index(["test", "alternative"])

    # 시각화 옵션이 True인 경우, 시각화 수행
    if plot:
        melt_df = melt(paired, value_vars=[before, after], var_name='group', value_name='value')

        fig, ax= my_plot.init()
        my_plot.boxplot(data=melt_df, x='group', y='value', hue='group', palette=palette, ax=ax)

        # 독립표본 t검정 결과를 시각화에 추가
        annotator = Annotator(data=melt_df,              #데이터프레임
                            x='group',                  # x축 변수
                            y='value',                 # y축 변수
                            pairs=[(before,after)], #비교할 그룹 쌍
                            ax=ax)                      # 그래프 축
        
        annotator.configure(test='t-test_paired' if is_normal else 'Wilcoxon')
        annotator.apply_and_annotate()
        my_plot.show()

    return result_df

#----------------------------------------------------------
def test_independent(data, group1, group2, alpha=0.05, plot=True, palette=None, title=None, xlabel=None, 
                     ylabel=None, width=1280, height=640, save_path=None):
    """
    독립된 두 집단의 평균이 같은지 검정하는 함수

    두 집단 모두 정규성 충족 시 등분산성에 따라 Student/Welch t 검정,
    하나라도 미 충족 시 Mann-Whitney U 검정을 수행하며,
    양측/좌측단측/우측단측 세 가지 대립가설을 일괄 검정한다.

    Args:
        data (DataFrame): 검정 대상 데이터프레임
        group1 (str): 첫 번째 집단의 측정값 컬럼명
        group2 (str): 두 번째 집단의 측정값 컬럼명
        alpha (float): 유의수준 (기본값:0.05)
        plot (bool): 결과를 시각화할지 여부 (기본값:True)
        palette (str or list): 색상 팔레트 (기본값: None) 
        title (str): 그래프 제목 (기본값: None) 
        xlabel (str): x축 라벨 (기본값: None)
        ylabel (str): y축 라벨 (기본값: None) 
        width (int): 그래프 너비 (기본값: 1280) 
        height (int): 그래프 높이 (기본값: 640) 
        save_path (str) : 그래프 저장 경로 (기본값: None)

    Returns:
        DataFrame: 대립가설(alternative)별 검정, 통계량, p-value, 유의성 결과표
    """
    # 두 집단의 컬럼명을 수준(level)으로 사용
    lv = [group1, group2]

    # 각 집단 컬럼을 분리하고 결측 제거(독립 표본이므로 컬럼별로 따로 제거)
    a = data[group1].dropna()
    b = data[group2].dropna()

    # 두 집단을 컬럼으로 묶어 정규성+등분산성을 동시에 검정(길이가 달라도 무방)
    paired = concat([a.reset_index(drop=True), b.reset_index(drop=True)], axis=1)
    paired.columns = [str(lv[0]), str(lv[1])]
    report =test_assumptions(paired, columns=list(paired.columns), alpha=alpha)

    # 두 집단 모두 정규성을 충족하는지 확인
    group1_normal = bool(report.loc[str(lv[0]), "result"])
    group2_normal = bool(report.loc[str(lv[1]), "result"])
    both_normal = group1_normal and group2_normal

    # 등분산성 충족 여부 추출
    equal_var = bool(report[report["test"] == "equal_var"]["result"].iloc[0])

    # 가정 검정 결과에 따라 적용할 검정 이름 결정
    if not both_normal:
        test_name = "Mann-Whitney U test"  # 정규성 미충족 -> 비모수 검정
    elif equal_var:
        test_name = "Student t-test"       # 정규성 충족 + 등분산
    else:
        test_name = "Welch t-test"         # 정규성 충족 + 이분산
    
    # 대립가설 방향별 가설을 부등식으로 표현(H0: 귀무가설, H1:대립가설, A=lv[0] / B=lv[1])
    hypothese = {
        "two-sided" : {"H0":f"{lv[0]} = {lv[1]}", "H1":f"{lv[0]} ≠ {lv[1]}"},
        "less" :      {"H0":f"{lv[0]} ≥ {lv[1]}", "H1":f"{lv[0]} < {lv[1]}"},
        "greater" :   {"H0":f"{lv[0]} ≤ {lv[1]}", "H1":f"{lv[0]} > {lv[1]}"},
    }

    rows = []
    # 양측/좌측단측/우측단측을 일괄 검정
    for alt in ("two-sided", "less", "greater"):
        # 적용 검정에 맞춰 대립가설 방향을 전달하여 검정 수행
        if test_name == "Mann-Whitney U test":
            stat, p = mannwhitneyu(a, b, alternative=alt)
        elif test_name == "Student t-test":
            stat, p = ttest_ind(a, b, equal_var=True, alternative=alt)
        else:
            stat, p = ttest_ind(a, b, equal_var=False, alternative=alt)

        # p < alpha 이면 통계적으로 유의(귀무가설 기각)
        significant = p < alpha

        rows.append({
            "test": test_name,
            "alternative":alt,
            "statistic":round(float(stat),4),
            "p-value":round(float(p),4),
            "significant":significant,
            # 유의하면 대립가설(H1) 채택, 아니면 귀무가설(H0)유지
            "result": hypothese[alt]["H1"] if significant else hypothese[alt]["H0"]
        })

    # 세 방향 결과를 표로 정리하여 반환
    result_df = DataFrame(rows).set_index(["test", "alternative"])

    # 시각화 옵션이 True인 경우, 시각화 수행
    if plot:
        # wide 형식을 long 형식으로 변환하여 그룹별 박스플롯 작성
        melt_df = melt(data, value_vars=[group1, group2], var_name="group", value_name="value")

        fig, ax = my_plot.init(title=title, width=width, height=height, xlabel=xlabel, ylabel=ylabel)
        my_plot.boxplot(data=melt_df, x="group", y='value', hue='group', palette=palette, ax=ax)

        # 독립표본 검정 결과를 시각화에 추가
        annotator = Annotator(data= melt_df, x="group", y="value", # 데이터프레임, x축, y축
                              pairs=[(lv[0], lv[1])],              # 비교할 그룹 쌍
                              ax=ax)                               # 그래프 축
        
        if test_name == "Mann-Whitney U test":
            annot_test = "Mann-Whitney"
        elif test_name == "Student t-test":
            annot_test = "t-test_ind"
        else:
            annot_test = "t-test_welch"
        
        annotator.configure(test=annot_test)
        annotator.apply_and_annotate()
        my_plot.show()
    
    return result_df