import numpy as np
import pandas as pd
from math import sqrt
from pandas import DataFrame, melt, concat
from scipy.stats import t
from scipy.stats import normaltest, bartlett, levene
from scipy.stats import ttest_1samp, wilcoxon, ttest_rel, ttest_ind, mannwhitneyu
from scipy.stats import pearsonr, spearmanr

# pingouin / statsmodels / statannotations 는 import가 무겁고 일부 함수에서만
# 쓰이므로, 각 함수 안에서 필요할 때 지연 import합니다. (앱 시작 속도 개선)

from . import my_plot
from . import my_prep

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
        sample = data[c].dropna().astype("float")

        if len(sample) < 8:
            s = None
            p = None
            normalize = False
        else:
            s, p = normaltest(sample)
            normalize = p >= alpha

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
        samples = [
            data[c].dropna().astype("float")
            for c in columns
        ]

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
        from statannotations.Annotator import Annotator
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
        from statannotations.Annotator import Annotator
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

# ==============================================
# 일원 분산분석 함수 정의
# ==============================================
def anova_oneway(data, y, between, alpha=0.05):
    """
    일원분산분석(One-way ANOVA)

    Args:
        data (DataFrame): 검정 대상 데이터프레임(long 형식)
        y (str) : 종속변수(연속형) 컬럼명
        between (str): 집단을 구분하는 독립변수(명목형) 컬럼명
        alpha (float): 유의수준 (기본값:0.05)

    Returns:
        DataFrame : pingouin의 분산분석 결과표(One-way ANOVA 또는 Welch-ANOVA)에 설명용 컬럼을 덧붙인 결과표
            - test: 사용한 검정 이름
            - effect_size : np2 기준 효과크기 해석 라벨(큼/중간/작음/미미함)
    """

    # 분석에 사용할 두 컬럼만 추출하고 결측 행 제거
    df = data[[y, between]].dropna()

    # 집단별 종속변수 값을 wide 형태(집단=컬럼)로 모아 가정 검정에 전달
    wide = my_prep.long2wide(df, hue=between, values=y)
    assumption = test_assumptions(wide, columns=list(wide.columns), alpha=alpha)

    # 등분산성 충족 여부 추출(정규성은 robust 가정에 따라 분기에 사용하지 않음)
    # 집단이 1개로 줄면 equal_var 행이 없을 수 있으므로 비어 있는 경우를 방어합니다.
    equal_var_result = assumption[assumption['test'] == 'equal_var']['result']
    equal_var = bool(equal_var_result.iloc[0]) if not equal_var_result.empty else False

    # 등분산성 여부에 따라 일반 ANOVA / Welch-ANOVA 선택
    from pingouin import anova, welch_anova
    if equal_var:
        anova_name = 'anova'
        aov = anova(data=df, dv=y, between=between)
    else:
        anova_name = 'welch_anova'
        aov =welch_anova(data=df, dv=y, between=between)

    # 어떤 검정을 사용했는지 식별할 수 있도록 맨 앞에 test 컬럼 추가
    aov.insert(0, 'test', anova_name)

    # ---효과크기 해석 컬럼 추가 ---
    # pingouin이 제공하는 Cohen의 효과크기 기준표로 해석하여 라벨 부여
    # ≥ 0.14 -> 큼, ≥ 0.06 -> 중간 , ≥ 0.01 -> 작음, 그 미만 -> 미미함
    conditions = [
        aov['np2'] >=0.14,
        aov['np2'] >=0.06,
        aov['np2'] >=0.01
    ]
    labels = ["Large", "Medium", "Small"]
    aov['effect_size'] = np.select(conditions, labels, default='Negligible')

    return aov


# ==============================================
# 사후 검정 함수 정의
# ==============================================
def posthoc_oneway(data, y, between, alpha=0.05, plot=True, palette=None, 
                   title=None, xlabel=None, ylabel=None, width=1280, height=640, save_path=None):
    """
    일원분산분석(One-way ANOVA)의 사후검정을 수행하는 함수

    Args:
        data (DataFrame): 검정 대상 데이터프레임(long 형식)
        y (str) : 종속변수(연속형) 컬럼명
        between (str): 집단을 구분하는 독립변수(명목형) 컬럼명
        alpha (float): 유의수준 (기본값:0.05)
        plot (bool): 결과를 시각화할지 여부 (기본값: True)
        palette (str or list): 색상 팔레트
        title (str): 그래프 제목
        xlabel (str): x축 라벨
        ylabel (str): y축 라벨
        width (int): 그래프 가로 크기
        height (int) : 그래프 세로 크기
        save_path (str): 그래프 저장 경로

    Returns:
        DataFrame : 그룹 쌍별 사후 검정 결과표(Tukey HSD 또는 Games-Howell)
    """

    # 분석에 사용할 두 컬럼만 추출하고 결측 행 제거
    df = data[[y, between]].dropna()

    # 집단별 종속변수 값을 wide 형태(집단=컬럼)로 모아 가정 검정에 전달
    wide = my_prep.long2wide(df, hue=between, values=y)
    assumption = test_assumptions(wide, columns=list(wide.columns), alpha=alpha)

    # 등분산성 충족 여부 추출(정규성은 robust 가정에 따라 분기에 사용하지 않음)
    # 집단이 1개로 줄면 equal_var 행이 없을 수 있으므로 비어 있는 경우를 방어합니다.
    equal_var_result = assumption[assumption['test'] == 'equal_var']['result']
    equal_var = bool(equal_var_result.iloc[0]) if not equal_var_result.empty else False

    # 등분산성 여부에 따라 사후 검정 방법 선택
    from pingouin import pairwise_tukey, pairwise_gameshowell
    if equal_var:
        posthoc_name = 'Tukey HSD'
        result = pairwise_tukey(data=df, dv=y, between=between)
        # pingouin 버전/패치에 따라 p값 컬럼명이 다를 수 있어 유연하게 선택
        pcol = "p-tukey" if "p-tukey" in result.columns else "p_tukey"
    else:
        posthoc_name = 'Games-Howell'
        result = pairwise_gameshowell(data=df, dv=y, between=between)
        pcol='pval'

    # 그래프 x축 순서(그룹 순서)
    order = sorted(df[between].unique())

    # 비교 대상 그룹 쌍과 그에 대응하는 p값 추출
    pairs = list(zip(result['A'], result['B']))
    pvalues = list(result[pcol])

    # 어떤 사후 검정을 사용했는지 식별할 수 있도록 맨 앞에 test 컬럼 추가
    result.insert(0,'test', posthoc_name)
    # p값이 유의수준 미만이면 통계적으로 유의(귀무가설 기각)
    result['significant'] = result[pcol] < alpha

    # --- 효과크기 해석 컬럼 추가 ---
    # hedges(Hedges' g)는 두 집단 평균차에 대한 표준화 효과크기로,
    # Cohen의 d 기준표를 따라 절댓값으로 해석한다.
    #   ≥ 0.8 → 큼, ≥ 0.5 → 중간, ≥ 0.2 → 작음, 그 미만 → 미미함
    # 부호는 비교 방향(A-B)을 의미하므로 크기 해석에는 절댓값을 사용한다.
    abs_hedges = result["hedges"].abs()
    conditions = [
        abs_hedges >= 0.8,
        abs_hedges >= 0.5,
        abs_hedges >= 0.2,
    ]
    labels = ["Large", "Medium", "Small"]
    result["effect_size"] = np.select(conditions, labels, default="Negligible")

    # 시각화 옵션이 True인 경우, 시각화 수행
    if plot:
        fig, ax= my_plot.init(title=title, width=width, height=height, xlabel=xlabel, ylabel=ylabel)
        my_plot.boxplot(data=df, x=between, y=y, hue=between, palette=palette, ax=ax)

        # 독립표본 t검정 결과를 시각화에 추가
        from statannotations.Annotator import Annotator
        annotator = Annotator(data=df, x=between, y=y,
                            pairs=pairs, order=order,
                            ax=ax)                      # 그래프 축
        
        # 검정을 새로 수행하지 않고, 앞서 구한 p값을 그대로 주입하여 주석 표시
        annotator.configure(text_format='star', loc='inside')
        annotator.set_pvalues(pvalues)
        annotator.annotate()
        my_plot.show()

    return result


#==============================================
# 이원분산분석
#==============================================
def anova_twoway(data, y, between, alpha=0.05):
    """이원분산분석 (Two-way ANOVA)
    두 개의 명목형 독립변수(주효과)와 그 상호작용효과가 연속형 종속변수에 미치는 영향을 검정한다.
    Args:
    data (DataFrame): 검정 대상 데이터프레임 (long 형식)
    y (str): 종속변수(연속형) 컬럼명
    between (list): 집단을 구분하는 두 개의 독립변수(명목형) 컬럼명 리스트
    alpha (float): 유의수준 (기본값: 0.05)
    Returns:
    DataFrame: 이원분산분석 결과표에 설명용 컬럼을 덧붙인 결과표.- test: 사용한 검정 이름- np2: 편에타제곱(partial eta-squared) 기준 효과크기- effect_size: np2 기준 효과크기 해석 라벨(Large/Medium/Small/Negligible)- significant: p값이 유의수준 미만인지 여부
    """
    # between은 두 개의 명목형 변수를 담은 리스트여야 한다.
    if not isinstance(between, (list, tuple)) or len(between) != 2:
        raise ValueError("between은 두 개의 명목형 변수명을 담은 리스트여야 합니다.")
    
    # 분석에 사용할 컬럼만 추출하고 결측 행 제거
    df = data[[y, between[0], between[1]]].dropna()

    # 두 명목형 변수의 모든 조합(셀)별 값을 wide 형태로 모아 가정 검정에 전달
    cell = df.copy()
    cell["_cell"] = cell[between[0]].astype(str) + ", " + cell[between[1]].astype(str)
    wide = my_prep.long2wide(cell, hue="_cell", values=y)
    assumption = test_assumptions(wide, columns=list(wide.columns), alpha=alpha)

    # 등분산성 충족 여부 추출
    equal_var = bool(assumption[assumption["test"] == "equal_var"]["result"].iloc[0])

    # 등분산성 여부에 따라 분석 방법 분기
    if equal_var:
        # [등분산 충족] 일반 이원분산분석
        test_name = "two-way ANOVA"
        from pingouin import anova
        aov = anova(data=df, dv=y, between=list(between))
        # p값 컬럼명은 pingouin 버전에 따라 다를 수 있어 유연하게 선택
        pcol = "p-unc" if "p-unc" in aov.columns else "p_unc"
    else:
        test_name = "OLS (HC3) Type-II ANOVA"
        from statsmodels.formula.api import ols
        import statsmodels.api as sm
        # Q()로 컬럼명을 감싸 공백/특수문자가 있는 컬럼명도 안전하게 처리
        formula = "Q('{0}') ~ C(Q('{1}')) * C(Q('{2}'))".format(y, between[0], 
        between[1])
        model = ols(formula, data=df).fit(cov_type="HC3")
        aov = sm.stats.anova_lm(model, typ=2, robust="hc3")

        # statsmodels 결과표에는 np2가 없으므로 편에타제곱을 직접 계산한다.
        #   np2 = SS_effect / (SS_effect + SS_residual)
        ss_resid = aov.loc["Residual", "sum_sq"]
        aov["np2"] = aov["sum_sq"] / (aov["sum_sq"] + ss_resid)
        aov.loc["Residual", "np2"] = np.nan

        # 인덱스에 담긴 효과명을 Source 컬럼으로 변환
        aov = aov.reset_index().rename(columns={"index": "Source"})
        # statsmodels가 만든 효과명(C(Q('water')):C(Q('sun')) 등)을
        # pingouin 결과와 동일한 형태(water * sun)로 정리한다.
        aov["Source"] = (aov["Source"].str.replace("C(Q('", "", regex=False)
                                        .str.replace("'))", "", regex=False)
                                        .str.replace(":", " * ", regex=False))
        pcol = "PR(>F)"

    # 어떤 검정을 사용했는지 식별할 수 있도록 맨 앞에 test 컬럼 추가
    aov.insert(0, "test", test_name)

    # --- 효과크기 해석 컬럼 추가 --
    # 편에타제곱(np2)을 Cohen의 기준표로 해석한다.
    #   ≥ 0.14 → 큼, ≥ 0.06 → 중간, ≥ 0.01 → 작음, 그 미만 → 미미함
    conditions = [
        aov["np2"] >= 0.14,
        aov["np2"] >= 0.06,
        aov["np2"] >= 0.01,
        ]
    labels = ["Large", "Medium", "Small"]
    aov["effect_size"] = np.select(conditions, labels, default="Negligible")

    # np2가 없는 행(잔차 등)은 효과크기 해석 대상이 아니므로 표시를 비운다.
    aov.loc[aov["np2"].isna(), "effect_size"] = "-"
    # p값이 유의수준 미만이면 통계적으로 유의(귀무가설 기각)
    aov["significant"] = aov[pcol] < alpha

    return aov



def posthoc_twoway(data, y, between, alpha=0.05):
    """
    이원분산분석(Two-way ANOVA)의 사후검정을 수행하는 함수
        Args:
            data (DataFrame): 검정 대상 데이터프레임 (long 형식)
            y (str): 종속변수(연속형) 컬럼명
            between (list): 집단을 구분하는 두 개의 독립변수(명목형) 컬럼명 리스트
            alpha (float): 유의수준 (기본값: 0.05)
        Returns:
            DataFrame: 조합(셀) 집단 쌍별 사후검정 결과표(Tukey HSD 또는 Games-Howell)
                - test: 사용한 사후검정 이름
                - significant: p값이 유의수준 미만인지 여부
                - effect_size: |Hedges' g| 기준 효과크기 해석 라벨
    """
    # between은 두 개의 명목형 변수를 담은 리스트여야 한다.
    if not isinstance(between, (list, tuple)) or len(between) != 2:
        raise ValueError("between은 두 개의 명목형 변수명을 담은 리스트여야 합니다.")
    
    # 분석에 사용할 컬럼만 추출하고 결측 행 제거
    df = data[[y, between[0], between[1]]].dropna().copy()
    
    # 두 명목형 변수를 결합하여 조합(셀) 단위의 집단 컬럼 생성
    group = "{0} * {1}".format(between[0], between[1])
    df[group] = df[between[0]].astype(str) + ", " + df[between[1]].astype(str)

    # 조합별 종속변수 값을 wide 형태로 모아 등분산성 가정 검정에 전달
    wide = my_prep.long2wide(df, hue=group, values=y)
    assumption = test_assumptions(wide, columns=list(wide.columns), alpha=alpha)

    # 등분산성 충족 여부 추출
    equal_var = bool(assumption[assumption["test"] == "equal_var"]["result"].iloc[0])

    # 등분산성 여부에 따라 사후검정 방법 선택
    from pingouin import pairwise_tukey, pairwise_gameshowell
    if equal_var:
        posthoc_name = "Tukey HSD"
        result = pairwise_tukey(data=df, dv=y, between=group)
        # pingouin 버전/패치에 따라 p값 컬럼명이 다를 수 있어 유연하게 선택
        pcol = "p-tukey" if "p-tukey" in result.columns else "p_tukey"

    else:
        posthoc_name = "Games-Howell"
        result = pairwise_gameshowell(data=df, dv=y, between=group)
        pcol = "pval"

    # 어떤 사후검정을 사용했는지 식별할 수 있도록 맨 앞에 test 컬럼 추가
    result.insert(0, "test", posthoc_name)
    # p값이 유의수준 미만이면 통계적으로 유의(귀무가설 기각)
    result["significant"] = result[pcol] < alpha

    # --- 효과크기 해석 컬럼 추가 --
    # hedges(Hedges' g)는 두 집단 평균차에 대한 표준화 효과크기로,
    # Cohen의 d 기준표를 따라 절댓값으로 해석한다.
    #   ≥ 0.8 → 큼, ≥ 0.5 → 중간, ≥ 0.2 → 작음, 그 미만 → 미미함
    abs_hedges = result["hedges"].abs()
    conditions = [
        abs_hedges >= 0.8,
        abs_hedges >= 0.5,
        abs_hedges >= 0.2,
        ]
    labels = ["Large", "Medium", "Small"]
    result["effect_size"] = np.select(conditions, labels, default="Negligible")

    return result

#==============================================
# 상관분석 함수 정의
#==============================================
def correlation(data, x, y, alpha=0.05, plot=True, palette=None, 
                title=None, xlabel=None, ylabel=None, width=1280, height=640, save_path=None):
    """
    두 연속형 변수의 상관분석을 일괄 수행하는 함수

     Args:
        data (DataFrame): 분석 대상 데이터프레임
        x (str): 첫 번째 연속형 변수 컬럼명
        y (str): 두 번째 연속형 변수 컬럼명
        alpha (float): 유의수준 (기본값: 0.05)
        plot (bool): 산점도(회귀선 포함)를 시각화할지 여부 (기본값: True)
        palette (str or list): 색상 팔레트 (기본값: None)
        title (str): 그래프 제목 (기본값: None)
        xlabel (str): x축 라벨 (기본값: None)
        ylabel (str): y축 라벨 (기본값: None)
        width (int): 그래프 너비 (기본값: 1280)
        height (int): 그래프 높이 (기본값: 640)
        save_path (str): 그래프 저장 경로 (기본값: None)

    Returns:
        DataFrame: (x, y)를 인덱스로 하는 단일 행 결과표
    """

    # -- 1) 같은 행끼리 비교해야 하므로 두 컬럼을 함께 결측 행 제거 --
    pair = data[[x,y]].dropna()
    vx, vy = pair[x], pair[y]
    
    # -- 2) 정규성 검정 (test_assumptitons 재사용) --
    report = test_assumptions(pair, columns=[x, y], alpha=alpha)
    norm_x = bool(report.loc[x, 'result'])
    norm_y = bool(report.loc[y, 'result'])

    # -- 3) 선형성 검정 (Ramsey RESET Test) --
    # H0: 모형이 올바르게 설정됨(선형). p >=alpha이면 선형성 충족
    import statsmodels.api as sm
    from statsmodels.stats.diagnostic import linear_reset
    try:
        X = sm.add_constant(vx)
        model = sm.OLS(vy, X).fit()
        linearity = bool(linear_reset(model, power=2, use_f=True).pvalue >= alpha)
    except Exception:
        # 표본이 적거나 완전 공선성 등으로 선형성 검정이 불가하면 '판단 보류'로 둡니다.
        linearity = True

    # -- 4) 이상치(영향점) 및 왜도 점검 --
    # IQR(사분위수) 울타리를 벗어난 행을 제외한 데이터를 별도로 만들어, 피어슨 r이 크게 바뀌면(>=0.1) '영향점'으로 판단한다.
    # 단순히 이상치가 존재하는 것과 상관계수를 왜곡하는 것은 다르다.
    trimmed = pair.copy()
    for col in (x,y):
        # 울타리는 항상 원본(pair) 기준으로 계산
        q1 = pair[col].quantile(0.25)
        q3 = pair[col].quantile(0.75)
        iqr = q3 - q1
        trimmed = trimmed[(trimmed[col] >= q1 - 1.5 * iqr) & (trimmed[col] <= q3 + 1.5 * iqr)]

    r_full = pearsonr(vx, vy)[0]
    # 이상치 제거 후 표본이 2개 미만이면 영향점 판단을 생략합니다.
    if len(trimmed) >= 2:
        r_trim = pearsonr(trimmed[x], trimmed[y])[0]
        influential = bool(abs(r_full - r_trim) >= 0.1)
    else:
        influential = False
    high_skew = bool(abs(vx.skew()) > 1 or abs(vy.skew()) >1)

    # -- 5) 가정에 따른 상관계수 선택 --
    # 모든 가정을 충족하면 피어슨, 하나라도 위반하면 스피어만을 사용한다.
    use_pearson = linearity and norm_x and norm_y and \
                (not influential) and (not high_skew)

    if use_pearson:
        method = "Pearson"
        coef, p = pearsonr(vx, vy)
    else:
        method = "Spearman"
        coef, p = spearmanr(vx, vy)

    # --- 6) 상관 강도 해석 라벨 ---
    # |r| > 0.7 → 강함, 0.3 < |r| <= 0.7 → 중간,
    # 0 < |r| <= 0.3 → 약함, 그 외 → 없음
    a = abs(coef)
    if a > 0.7:    strength = "Strong"
    elif a > 0.3:  strength = "Moderate"
    elif a > 0:    strength = "Weak"
    else:          strength = "None"
    
    # --- 7) 가정 점검 결과와 선택된 상관계수를 단일 행 결과표로 정리 ---
    row = {
        "x": x,
        "y": y,
        "method": method,
        "coef": round(float(coef), 4),
        "p-value": round(float(p), 4),
        "strength": strength,
        "significant": bool(p < alpha),
        "normality_x": norm_x,
        "normality_y": norm_y,
        "linearity": linearity,
        "influential_outlier": influential,
        "high_skew": high_skew,
    }
    result_df = DataFrame([row]).set_index(["x", "y"])
    
   # --- 8) 시각화 ---
    # 시각화 옵션이 True인 경우, 산점도와 회귀선을 시각화
    if plot:
        my_plot.lmplot(data=pair, x=x, y=y, palette=palette,
                    title=title, xlabel=xlabel, ylabel=ylabel,
                    width=width, height=height, save_path=save_path)

    # --- 9) 결과 반환 ---
    return result_df


# ==========================================================
# Streamlit 앱용 통계 검정 보조 함수
# ==========================================================

def interpret_p_value(p_value, alpha=0.05):
    """
    p-value를 기준으로 귀무가설 기각 여부를 판단합니다.
    """

    if p_value < alpha:
        return "귀무가설 기각"
    else:
        return "귀무가설 채택"


def normality_test_for_app(data, columns=None, alpha=0.05):
    """
    선택한 숫자형 변수들에 대해 정규성 검정을 수행합니다.

    사용 검정:
    - scipy.stats.normaltest

    귀무가설 H0:
    - 해당 변수는 정규분포를 따른다.

    대립가설 H1:
    - 해당 변수는 정규분포를 따르지 않는다.
    """

    if columns is None:
        columns = data.select_dtypes(include="number").columns.tolist()

    if isinstance(columns, str):
        columns = [columns]

    result_rows = []

    for column in columns:
        sample = data[column].dropna()

        if len(sample) < 8:
            result_rows.append({
                "변수": column,
                "검정": "normaltest",
                "귀무가설(H0)": "정규분포를 따른다",
                "대립가설(H1)": "정규분포를 따르지 않는다",
                "표본수": len(sample),
                "통계량": None,
                "p-value": None,
                "판정": "검정 불가",
                "해석": "normaltest는 표본 수가 너무 적으면 적절하지 않습니다."
            })
            continue

        statistic, p_value = normaltest(sample)

        decision = interpret_p_value(p_value, alpha)

        result_rows.append({
            "변수": column,
            "검정": "normaltest",
            "귀무가설(H0)": "정규분포를 따른다",
            "대립가설(H1)": "정규분포를 따르지 않는다",
            "표본수": len(sample),
            "통계량": round(float(statistic), 4),
            "p-value": round(float(p_value), 4),
            "판정": decision,
            "해석": "정규성 만족" if p_value >= alpha else "정규성 불만족"
        })

    return DataFrame(result_rows)


def equal_variance_test_for_app(data, columns, alpha=0.05, center="median"):
    """
    두 개 이상의 숫자형 변수에 대해 등분산성 검정을 수행합니다.

    먼저 각 변수의 정규성을 확인합니다.

    검정 선택 로직:
    - 모든 변수가 정규성 만족 → Bartlett 검정
    - 하나라도 정규성 불만족 → Levene 검정

    귀무가설 H0:
    - 각 변수의 분산은 같다.

    대립가설 H1:
    - 적어도 하나의 변수는 분산이 다르다.
    """

    if isinstance(columns, str):
        columns = [columns]

    if len(columns) < 2:
        return DataFrame([{
            "검정": "등분산성 검정",
            "귀무가설(H0)": "각 변수의 분산은 같다",
            "대립가설(H1)": "적어도 하나의 변수는 분산이 다르다",
            "통계량": None,
            "p-value": None,
            "판정": "검정 불가",
            "해석": "등분산성 검정은 변수가 2개 이상일 때만 수행합니다."
        }])

    normality_result = normality_test_for_app(
        data,
        columns=columns,
        alpha=alpha
    )

    normality_available = normality_result["p-value"].notna().all()

    all_normal = (
        normality_available
        and (normality_result["판정"] == "귀무가설 채택").all()
    )

    samples = [
        data[column].dropna().astype(float)
        for column in columns
    ]

    if all_normal:
        test_name = "Bartlett"
        statistic, p_value = bartlett(*samples)
    else:
        test_name = "Levene"
        statistic, p_value = levene(*samples, center=center)

    decision = interpret_p_value(p_value, alpha)

    result = DataFrame([{
        "검정": test_name,
        "귀무가설(H0)": "각 변수의 분산은 같다",
        "대립가설(H1)": "적어도 하나의 변수는 분산이 다르다",
        "통계량": round(float(statistic), 4),
        "p-value": round(float(p_value), 4),
        "판정": decision,
        "해석": "등분산성 만족" if p_value >= alpha else "등분산성 불만족"
    }])

    return result


def assumption_test_for_app(data, columns=None, alpha=0.05):
    """
    통계 분석 전에 필요한 가정 검정을 한 번에 수행합니다.

    수행 로직:
    1. 각 변수별 정규성 검정 수행
    2. 변수가 2개 이상이면 등분산성 검정 수행
    3. 변수가 1개이면 정규성 결과만 반환

    반환:
    - normality_result: 정규성 검정 결과
    - variance_result: 등분산성 검정 결과 또는 None
    """

    if columns is None:
        columns = data.select_dtypes(include="number").columns.tolist()

    if isinstance(columns, str):
        columns = [columns]

    normality_result = normality_test_for_app(
        data,
        columns=columns,
        alpha=alpha
    )

    if len(columns) >= 2:
        variance_result = equal_variance_test_for_app(
            data,
            columns=columns,
            alpha=alpha
        )
    else:
        variance_result = None

    return normality_result, variance_result


def crosstab_chi2_for_app(data, row_column, col_column, alpha=0.05):
    """두 범주형 변수의 교차표와 카이제곱 독립성 검정을 수행합니다.

    귀무가설 H0: 두 변수는 서로 독립이다(관계 없다).
    대립가설 H1: 두 변수는 독립이 아니다(관계 있다).

    Returns:
        observed (DataFrame): 관측빈도 교차표
        result (DataFrame): 검정 결과 요약표
        interpretation (str): 해석 문장
    """
    # scipy.stats는 이미 로드돼 있어 비용이 거의 없습니다.
    from scipy.stats import chi2_contingency

    # 두 컬럼을 함께 결측 제거한 뒤 관측빈도 교차표 생성
    pair = data[[row_column, col_column]].dropna()
    observed = pd.crosstab(pair[row_column], pair[col_column])

    # 카이제곱 검정은 행/열 모두 범주가 2개 이상이어야 합니다.
    if observed.shape[0] < 2 or observed.shape[1] < 2:
        result = DataFrame([{
            "검정": "카이제곱 독립성 검정",
            "통계량(χ²)": None,
            "자유도": None,
            "p-value": None,
            "판정": "검정 불가",
        }])
        return observed, result, "두 변수 모두 범주가 2개 이상이어야 카이제곱 검정을 할 수 있습니다."

    chi2, p, dof, expected = chi2_contingency(observed)

    # 기대빈도 5 미만 셀 비율(카이제곱 가정 점검용)
    expected_lt5_ratio = float((expected < 5).mean())

    # Cramér's V (효과크기) = sqrt(χ² / (n * (min(행,열) - 1)))
    n = int(observed.values.sum())
    min_dim = min(observed.shape) - 1
    cramers_v = sqrt(chi2 / (n * min_dim)) if (n > 0 and min_dim > 0) else 0.0

    if cramers_v >= 0.5:
        strength = "강함"
    elif cramers_v >= 0.3:
        strength = "중간"
    elif cramers_v >= 0.1:
        strength = "약함"
    else:
        strength = "매우 약함"

    significant = p < alpha

    result = DataFrame([{
        "검정": "카이제곱 독립성 검정",
        "통계량(χ²)": round(float(chi2), 4),
        "자유도": int(dof),
        "p-value": round(float(p), 4),
        "Cramér's V": round(float(cramers_v), 4),
        "관계 강도": strength,
        "판정": "귀무가설 기각(관계 있음)" if significant else "귀무가설 채택(독립)",
    }])

    if significant:
        interpretation = (
            f"카이제곱 검정 결과 p-value는 {p:.3f}로 유의수준 {alpha}보다 작습니다. "
            f"따라서 `{row_column}`와(과) `{col_column}`는 서로 독립이라고 보기 어렵습니다. "
            f"즉, 두 변수 사이에 통계적으로 유의한 관계가 있습니다. "
            f"관계의 강도(Cramér's V)는 {cramers_v:.3f}로 '{strength}' 수준입니다."
        )
    else:
        interpretation = (
            f"카이제곱 검정 결과 p-value는 {p:.3f}로 유의수준 {alpha}보다 크거나 같습니다. "
            f"따라서 `{row_column}`와(과) `{col_column}`가 서로 관계가 있다고 보기 어렵습니다(독립으로 판단)."
        )

    if expected_lt5_ratio > 0.2:
        interpretation += (
            f"\n\n⚠️ 기대빈도가 5 미만인 셀이 {expected_lt5_ratio * 100:.0f}%입니다. "
            "이 경우 카이제곱 결과의 신뢰도가 떨어질 수 있어, 범주를 합치거나 표본을 늘리는 것을 고려하세요."
        )

    return observed, result, interpretation


def format_p_value(p_value):
    if p_value < 0.0001:
        return "< 0.0001"
    return round(float(p_value), 4)

#================
def group_mean_test_for_app(data, group_column, value_column, alpha=0.05):
    """
    범주형 집단 컬럼과 숫자형 값 컬럼을 이용해 그룹 간 평균 차이를 검정합니다.

    입력 데이터 형태:
    - long 형태
    - 예: 구분 | 값

    로직:
    1. 집단 수가 2개이면 독립표본 검정 수행
    2. 집단 수가 3개 이상이면 ANOVA 수행
    """

    df = data[[group_column, value_column]].dropna().copy()

    groups = df[group_column].dropna().unique().tolist()

    if len(groups) < 2:
        return {
            "test_type": "검정 불가",
            "message": "집단이 2개 이상이어야 평균 차이 검정을 수행할 수 있습니다.",
            "group_count": DataFrame(),
            "assumption_result": DataFrame(),
            "test_result": DataFrame(),
            "posthoc_result": None
        }

    group_count = (
        df[group_column]
        .value_counts()
        .reset_index()
    )

    group_count.columns = [group_column, "표본 수"]

    # ------------------------------------------------------
    # 집단이 2개인 경우: 독립표본 검정
    # ------------------------------------------------------
    if len(groups) == 2:
        group1 = groups[0]
        group2 = groups[1]

        wide_data = DataFrame({
            str(group1): df.loc[df[group_column] == group1, value_column].reset_index(drop=True),
            str(group2): df.loc[df[group_column] == group2, value_column].reset_index(drop=True)
        })

        assumption_result = test_assumptions(
            wide_data,
            columns=[str(group1), str(group2)],
            alpha=alpha
        )

        test_result = test_independent(
            wide_data,
            group1=str(group1),
            group2=str(group2),
            alpha=alpha,
            plot=False
        )

        return {
            "test_type": "두 집단 평균 차이 검정",
            "message": "집단이 2개이므로 독립표본 검정을 수행했습니다.",
            "group_count": group_count,
            "assumption_result": assumption_result.reset_index(),
            "test_result": test_result.reset_index(),
            "posthoc_result": None
        }

    # ------------------------------------------------------
    # 집단이 3개 이상인 경우: ANOVA
    # ------------------------------------------------------
    else:
        assumption_wide = my_prep.long2wide(
            df,
            hue=group_column,
            values=value_column
        )

        assumption_result = test_assumptions(
            assumption_wide,
            columns=list(assumption_wide.columns),
            alpha=alpha
        )

        test_result = anova_oneway(
            df,
            y=value_column,
            between=group_column,
            alpha=alpha
        )

        # pingouin 결과에서 p-value 컬럼 찾기
        if "p-unc" in test_result.columns:
            p_value = test_result["p-unc"].iloc[0]
        elif "pval" in test_result.columns:
            p_value = test_result["pval"].iloc[0]
        else:
            p_value = None

        if p_value is not None and p_value < alpha:
            posthoc_result = posthoc_oneway(
                df,
                y=value_column,
                between=group_column,
                alpha=alpha,
                plot=False
            )
        else:
            posthoc_result = None

        return {
            "test_type": "세 집단 이상 평균 차이 검정",
            "message": "집단이 3개 이상이므로 ANOVA 계열 검정을 수행했습니다.",
            "group_count": group_count,
            "assumption_result": assumption_result.reset_index(),
            "test_result": test_result,
            "posthoc_result": posthoc_result
        }
    
def format_p_value_for_app(p_value):
    if p_value is None:
        return None

    try:
        p_value = float(p_value)
    except Exception:
        return p_value

    return f"{p_value:.3f}"

def format_stat_result_for_app(result):
    """
    통계 결과표를 Streamlit 화면에 보기 좋게 정리합니다.
    """

    if result is None:
        return None

    formatted = result.copy()

    p_value_columns = [
        column for column in formatted.columns
        if "p" in str(column).lower()
    ]

    for column in p_value_columns:
        formatted[column] = formatted[column].apply(format_p_value_for_app)

    bool_columns = formatted.select_dtypes(include="bool").columns

    for column in bool_columns:
        formatted[column] = formatted[column].map({
            True: "만족",
            False: "불만족"
        })

    numeric_columns = formatted.select_dtypes(include="number").columns

    for column in numeric_columns:
        formatted[column] = formatted[column].round(4)

    return formatted

def make_test_interpretation(test_name, p_value, alpha=0.05):
    """
    통계 검정 결과를 사용자가 이해하기 쉬운 문장으로 바꿔주는 함수입니다.
    """

    try:
        p_value = float(p_value)
    except Exception:
        return "p-value를 숫자로 변환할 수 없어 결과를 해석할 수 없습니다."

    if p_value < alpha:
        return (
            f"{test_name} 결과, p-value는 {p_value:.3f}로 "
            f"유의수준 {alpha}보다 작습니다. "
            "따라서 귀무가설(H0)을 기각합니다. "
            "즉, 통계적으로 유의한 차이가 있다고 해석할 수 있습니다."
        )

    else:
        return (
            f"{test_name} 결과, p-value는 {p_value:.3f}로 "
            f"유의수준 {alpha}보다 크거나 같습니다. "
            "따라서 귀무가설(H0)을 기각할 수 없습니다. "
            "즉, 통계적으로 유의한 차이가 있다고 보기 어렵습니다."
        )
    
def make_posthoc_insight(posthoc_result, alpha=0.05):
    """
    사후검정 결과표를 해석해서 핵심 인사이트 문장을 만들어주는 함수입니다.

    이 함수는 사후검정 결과에서 다음 내용을 자동으로 찾습니다.

    1. 전체 비교 조합 수
    2. 통계적으로 유의한 비교 조합 수
    3. 평균 차이가 가장 큰 집단쌍
    4. p-value가 가장 작은 집단쌍

    Parameters
    ----------
    posthoc_result : DataFrame
        사후검정 결과표
    alpha : float
        유의수준

    Returns
    -------
    str
        사후검정 해석 문장
    """

    if posthoc_result is None or posthoc_result.empty:
        return "사후검정 결과가 없어 인사이트를 생성할 수 없습니다."

    result = posthoc_result.copy()

    # ------------------------------------------------------------
    # 1. 집단쌍 컬럼 찾기
    # ------------------------------------------------------------
    # 사후검정 결과는 보통 A, B 컬럼에 비교 집단명이 들어갑니다.
    # 예: A = D10, B = F11
    # ------------------------------------------------------------
    group_a_column = None
    group_b_column = None

    if "A" in result.columns and "B" in result.columns:
        group_a_column = "A"
        group_b_column = "B"

    elif "group1" in result.columns and "group2" in result.columns:
        group_a_column = "group1"
        group_b_column = "group2"

    else:
        return "사후검정 결과에서 비교 집단 컬럼을 찾지 못했습니다."

    # ------------------------------------------------------------
    # 2. p-value 컬럼 찾기
    # ------------------------------------------------------------
    # 사후검정 함수에 따라 p-value 컬럼명이 다를 수 있습니다.
    # 예: p-tukey, pval, p-corr, p-unc
    # ------------------------------------------------------------
    p_value_column = None

    possible_p_columns = [
        "p-tukey",
        "pval",
        "p-corr",
        "p-unc",
        "p_unc",
        "p-value",
        "p"
    ]

    for column in possible_p_columns:
        if column in result.columns:
            p_value_column = column
            break

    if p_value_column is None:
        return "사후검정 결과에서 p-value 컬럼을 찾지 못했습니다."

    result[p_value_column] = pd.to_numeric(
        result[p_value_column],
        errors="coerce"
    )

    # ------------------------------------------------------------
    # 3. 평균 차이 컬럼 찾기
    # ------------------------------------------------------------
    # 사후검정 결과에는 보통 diff 컬럼이 있습니다.
    # diff가 양수/음수인지에 따라 어느 집단 평균이 큰지 판단할 수 있습니다.
    # ------------------------------------------------------------
    diff_column = None

    possible_diff_columns = [
        "diff",
        "mean_diff",
        "mean difference"
    ]

    for column in possible_diff_columns:
        if column in result.columns:
            diff_column = column
            break

    # ------------------------------------------------------------
    # 4. 전체 비교 수와 유의한 비교 수 계산
    # ------------------------------------------------------------
    total_count = len(result)

    significant_result = result[
        result[p_value_column] < alpha
    ].copy()

    significant_count = len(significant_result)

    if significant_count == 0:
        return (
            f"사후검정 결과, 총 {total_count}개의 비교 조합 중 "
            "통계적으로 유의한 차이가 확인된 조합은 없습니다."
        )

    insight_text = (
        f"사후검정 결과, 총 {total_count}개의 비교 조합 중 "
        f"{significant_count}개 조합에서 통계적으로 유의한 차이가 확인되었습니다."
    )

    # ------------------------------------------------------------
    # 5. 평균 차이가 가장 큰 집단쌍 찾기
    # ------------------------------------------------------------
    if diff_column is not None:
        significant_result[diff_column] = pd.to_numeric(
            significant_result[diff_column],
            errors="coerce"
        )

        max_diff_row = significant_result.loc[
            significant_result[diff_column].abs().idxmax()
        ]

        group_a = max_diff_row[group_a_column]
        group_b = max_diff_row[group_b_column]
        diff_value = max_diff_row[diff_column]

        if diff_value > 0:
            direction_text = f"`{group_a}` 집단의 평균이 `{group_b}` 집단보다 높습니다."
        elif diff_value < 0:
            direction_text = f"`{group_b}` 집단의 평균이 `{group_a}` 집단보다 높습니다."
        else:
            direction_text = "두 집단의 평균 차이는 거의 없습니다."

        insight_text += (
            f"\n\n가장 큰 평균 차이는 `{group_a}` 집단과 `{group_b}` 집단 사이에서 나타났습니다. "
            f"{direction_text}"
        )

    # ------------------------------------------------------------
    # 6. p-value가 가장 작은 집단쌍 찾기
    # ------------------------------------------------------------
    min_p_row = significant_result.loc[
        significant_result[p_value_column].idxmin()
    ]

    min_p_group_a = min_p_row[group_a_column]
    min_p_group_b = min_p_row[group_b_column]
    min_p_value = min_p_row[p_value_column]

    insight_text += (
        f"\n\n가장 작은 p-value를 보인 비교는 "
        f"`{min_p_group_a}` 집단과 `{min_p_group_b}` 집단입니다. "
        f"p-value는 {min_p_value:.3f}입니다."
    )

    return insight_text