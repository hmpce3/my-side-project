# 자동 데이터 분석 대시보드

CSV, Excel, JSON 데이터를 업로드하면 데이터 품질 점검, 정제, 시각화, 그룹별 집계, 통계 분석, 보고서 생성을 한 번에 진행할 수 있는 Streamlit 기반 데이터 분석 웹앱입니다.

복잡한 코드를 직접 작성하지 않아도 데이터를 빠르게 살펴보고, 분석 주제를 찾고, 결과를 HTML 보고서로 정리할 수 있도록 만드는 것이 목표입니다.

## 배포 링크

https://my-side-project-9qsbh9hfdsf7a7dgpdzrks.streamlit.app/

## 주요 기능

- CSV, Excel, JSON 파일 업로드
- 여러 파일 결합 및 파일별 오류 처리
- 결측치, 중복 행, 데이터 타입, 고유값 점검
- 숫자형/범주형 데이터 요약
- 주요 상관관계 자동 인사이트
- 데이터 정제 및 타입 변환
- 숫자형 구간화(binning)와 정규화/스케일링(Min-Max, Z-점수)
- 자동 시각화
- 직접 시각화
- 그룹별 집계 및 피벗 테이블
- 통계 분석
  - 단일표본 T-TEST
  - 대응표본 T-TEST
  - 독립표본 T-TEST
  - 일원분산분석 ANOVA
  - 상관분석
  - 교차분석(카이제곱 검정)
  - 비모수 검정(Mann-Whitney U, Wilcoxon, Kruskal-Wallis)
- 회귀분석(단순·다중 선형회귀, R²·회귀계수·잔차 진단)
- 시계열 분석(기간별 리샘플링, 이동평균, 추세 해석)
- 분석 결과를 HTML 보고서로 내보내기

## 사용 흐름

1. 데이터 업로드 / 결합
2. 데이터 품질 점검
3. 데이터 정제 (구간화·스케일링 포함)
4. 자동 시각화 또는 직접 시각화
5. 그룹별 집계
6. 통계 분석 (모수 / 비모수)
7. 회귀분석
8. 시계열 분석
9. 보고서 생성

## 기술 스택

- Python
- Streamlit
- Pandas
- NumPy
- Plotly
- SciPy
- Pingouin
- Statsmodels
- Matplotlib
- Seaborn

## 로컬 실행 방법

```bash
pip install -r requirements.txt
streamlit run app.py
```

Windows에서는 `실행.bat` 파일을 실행해 로컬 환경에서 앱을 열 수 있습니다.

## 프로젝트 목적

이 프로젝트는 데이터 분석을 처음 접하는 사용자도 파일을 업로드한 뒤 기본적인 탐색, 정제, 시각화, 통계 분석, 보고서 생성을 한 화면 흐름 안에서 진행할 수 있도록 돕기 위해 만들었습니다.

특히 분석 과정에서 사용자가 다음 질문에 답할 수 있도록 설계했습니다.

- 데이터에 결측치나 중복값이 얼마나 있는가?
- 어떤 변수들이 서로 강하게 관련되어 있는가?
- 그룹별로 어떤 차이가 있는가?
- 통계적으로 유의한 차이나 관계가 있는가?
- 분석 결과를 어떻게 보고서로 정리할 수 있는가?

---

# Automated Data Analysis Dashboard

This is a Streamlit-based data analysis web app that allows users to upload CSV, Excel, or JSON files and perform data quality checks, data cleaning, visualization, group aggregation, statistical analysis, and HTML report generation in one workflow.

The goal of this project is to help users explore data, discover analysis topics, and summarize results without having to write complex code manually.

## Live App

https://my-side-project-9qsbh9hfdsf7a7dgpdzrks.streamlit.app/

## Key Features

- Upload CSV, Excel, and JSON files
- Combine multiple files and isolate file-level errors
- Check missing values, duplicate rows, data types, and unique values
- Summarize numerical and categorical data
- Generate automatic correlation insights
- Clean data and convert data types
- Bin numeric columns and normalize/scale them (Min-Max, Z-score)
- Create automatic visualizations
- Create custom visualizations
- Perform group aggregation and pivot-style analysis
- Run statistical analyses
  - One-sample t-test
  - Paired t-test
  - Independent t-test
  - One-way ANOVA
  - Correlation analysis
  - Crosstab analysis with chi-square test
  - Non-parametric tests (Mann-Whitney U, Wilcoxon, Kruskal-Wallis)
- Regression analysis (simple/multiple linear regression with R², coefficients, residual diagnostics)
- Time series analysis (period resampling, moving average, trend insight)
- Export analysis results as an HTML report

## Workflow

1. Upload and combine data
2. Check data quality
3. Clean data (including binning and scaling)
4. Create automatic or custom visualizations
5. Aggregate data by group
6. Run statistical analysis (parametric / non-parametric)
7. Run regression analysis
8. Run time series analysis
9. Generate a report

## Tech Stack

- Python
- Streamlit
- Pandas
- NumPy
- Plotly
- SciPy
- Pingouin
- Statsmodels
- Matplotlib
- Seaborn

## Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

On Windows, you can also run the app by opening `실행.bat`.

## Project Goal

This project was built to make basic data analysis more accessible. Users can upload a dataset and move through exploration, cleaning, visualization, statistical testing, and report generation in a single app.

The app is designed to help answer questions such as:

- How many missing or duplicate values are in the data?
- Which variables are strongly related?
- How do values differ across groups?
- Are there statistically significant differences or relationships?
- How can the analysis results be organized into a report?
