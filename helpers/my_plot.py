import numpy as np
from pandas import pivot_table
import plotly.express as px


# ------------------------------------------------------------
# 무거운 라이브러리 지연 로딩 (앱 시작 속도 개선)
# 아래쪽 matplotlib/seaborn 함수들은 수업/정적 그래프용이고,
# Streamlit 앱은 Plotly 기반 make_* 함수만 사용합니다.
# 그래서 matplotlib/seaborn은 실제로 그 함수가 호출되는 순간에만 import합니다.
# ------------------------------------------------------------
class _LazyModule:
    """속성에 처음 접근할 때 모듈을 import하는 지연 로더."""

    def __init__(self, module_name, on_load=None):
        self._module_name = module_name
        self._module = None
        self._on_load = on_load

    def __getattr__(self, attr):
        if self._module is None:
            import importlib
            self._module = importlib.import_module(self._module_name)
            if self._on_load is not None:
                self._on_load()
        return getattr(self._module, attr)


def _apply_korean_font():
    """matplotlib/seaborn이 처음 로드되는 순간 한글 폰트 설정을 적용합니다."""
    from . import setup_korean_font
    setup_korean_font()


plt = _LazyModule("matplotlib.pyplot", on_load=_apply_korean_font)
sb = _LazyModule("seaborn", on_load=_apply_korean_font)

#----------------------------------------------------------

def init(width=1280, height=640, rows=1, cols=1, grid=True, title=None, xlabel=None, ylabel=None, twinx=False):
    """
    그래프의 크기와 dpi를 설정하여 fig와 ax 객체를 반환하는 함수

    Parameters:
        - width: 그래프의 가로 크기(픽셀 단위)
        - height : 그래프의 세로 크기(픽셀 단위)
        - rows : 그래프의 행 수
        - cols : 그래프의 열 수
        - title : 그래프의 제목(기본값 : None)
        - Xlabel : x축 레이블(기본값 : None)
        - Ylabel : y축 레이블(기본값 : None)
        - grid : 그래프에 그리드를 표시할지 여부(기본값 : True)

    Return:
        - fig : 생성된 Figure 객체
        - ax : 생성된 Axes 객체 또는 Axes 배열
    """

    my_figsize = ((width /100)*cols, (height /100)*rows)
    fig,ax = plt.subplots(rows, cols, figsize=my_figsize, dpi=200)
    

    if rows > 1 or cols > 1:
        ax = ax.flatten()  # 2차원 배열을 1차원으로 평탄화하여 반복처리
        fig.suptitle(title, fontsize=32, fontweight=500)
        for a in ax:
            a.grid(grid, alpha=0.5)
    
    else:
        ax.grid(True, alpha=0.5)

        if title:
            ax.set_title(title, fontsize=24, fontweight=500, pad=15)

        if xlabel:
            ax.set_xlabel(xlabel, fontsize=16, fontweight=400, labelpad=5)

        if ylabel:
            ax.set_ylabel(ylabel, fontsize=16, fontweight=400, labelpad=5)

    if twinx:
        ax_right = ax.twinx()
        ax = (ax, ax_right)

    return fig, ax


#----------------------------------------------------------

def show(save_path=None):
    """
    그래프를 화면에 표시하는 함수

    Parameters:
        - gird: 그리드를 표시할지 여부(기본값:True)
        - save_path: 그래프를 저장할 파일 경로, None이면 저장하지 않음
    """

    if save_path:
        plt.savefig(save_path)

    plt.tight_layout()  
    plt.show()          
    plt.close()       

#----------------------------------------------------------

def lineplot(data=None, x=None, y=None, hue=None,
             title=None, xlabel=None, ylabel=None, color=None,
             linewidth=2.0, linestyle="-", palette=None,
             marker=None, markersize=None, markeredgewidth=None,
             markeredgecolor=None, markerfacecolor=None,
             width=1280, height=640, save_path=None, ax=None):
    """
    선 그래프를 그린다
    Args:
        data: 시각화할 데이터.
        x: x축 컬럼명 혹은 x축 값 시퀀스.
        y: y축 컬럼명 혹은 y축 값 시퀀스.
        hue: 범주 구분 컬럼명.
        title: 그래프 제목.
        xlabel: x축 레이블.
        ylabel: y축 레이블.
        linewidth: 선 굵기.
        palette: 색상 팔레트 이름.
        marker: 마커 모양.
        markersize: 마커 크기.
        markeredgewidth: 마커 테두리 두께.
        markeredgecolor: 마커 테두리 색상.
        markerfacecolor: 마커 배경 색상.
        width: 캔버스 가로 픽셀.
        height: 캔버스 세로 픽셀.
        save_path: 이미지 저장 경로.
    """
    # 그래프 초기화
    fig = None
    if ax is None:
        fig, ax = init(width=width, height=height, title=title, xlabel=xlabel, ylabel=ylabel)

    # 선 그래프 그리기  
    sb.lineplot(data=data, x=x, y=y, linewidth=linewidth, hue=hue, color=color, linestyle=linestyle,
                palette=palette, marker=marker, markersize=markersize, markeredgewidth=markeredgewidth, markerfacecolor=markerfacecolor, markeredgecolor=markeredgecolor, ax=ax)
    
    # 그래프 표시
    if fig is not None:
        show(save_path=save_path)


#----------------------------------------------------------
def kdeplot(data=None, x=None, hue=None, meanline=False, clevel=0,
            title=None, xlabel=None, ylabel=None,
            fill=False, linewidth=2.0, palette=None,
            width=1280, height=640, save_path=None, ax=None):
    """
    단변량 커널 밀도 그래프를 그린다. 범주에 따른 구분은 지원하지 않는다.

    Args:
        data: 시각화할 데이터.
        x: x축 컬럼명 혹은 x축 값 시퀀스.
        meanline: 평균선 표시 여부.
        title: 그래프 제목.
        xlabel: x축 레이블.
        ylabel: y축 레이블.
        fill: 면적 채우기 여부.
        linewidth: 선 굵기.
        palette: 색상 팔레트 이름
        width: 캔버스 가로 픽셀.
        height: 캔버스 세로 픽셀.
        save_path: 이미지 저장 경로.
    """

    # my_stats는 이 함수에서만 쓰므로 지연 import (앱 시작 시 통계 라이브러리 로딩 방지)
    from . import my_stats

    # 그래프 초기화
    fig = None
    if ax is None:
        fig, ax = init(width=width, height=height, title=title, 
                    xlabel=xlabel, ylabel=ylabel)
    
    # 단변량 커널 밀도 그래프 그리기
    sb.kdeplot(data=data, x=x, fill=fill, linewidth=linewidth, hue=hue, 
               palette=palette, ax=ax)
    
    # 신뢰구간 표시(신뢰수준이 0이 아닌 경우에만)
    if clevel:
        ymin, ymax = ax.get_ylim() # 그래프의 y축 범위 조회

        if hue is None:
            #그래프에 적용된 팔레트의 첫번째 색상을 따른다(팔레트가 없으면 기본 파란색)
            color = sb.color_palette(palette)[0] if palette else '#0066ff'
            # 전체 데이터에 대한 신뢰구간 표시
            _draw_ci(ax, my_stats.ci(data, column=x, clevel=clevel), color, ymax)

        else:
            # hue 범주별로 신뢰구간 표시(kdeplot이 그린 라인의 색상과 일치시킴)
            categories = list(data[hue].unique())
            # 팔레트에서 범주의 수에 맞는 색상값 추출
            colors = sb.color_palette(palette, n_colors=len(categories))

            # 각 범주에 대해 신뢰구간 표시
            for i, cat in enumerate(categories):
                cdata=data.loc[data[hue] == cat, x]
                _draw_ci(ax, my_stats.ci(cdata, clevel=clevel), colors[i], ymax)

        ax.set_ylim(ymin, ymax) # y축 범위 유지
    
    # 평균선 표시
     # 평균선 표시
    if meanline:
        y_max = ax.get_ylim()[1]

        if hue is None:
            mv = data[x].mean()
            ax.axvline(x=mv, color='red', linestyle='--', linewidth=linewidth * 0.5)
            ax.text(x=mv + 0.05, y=y_max * 0.95, s=f'Mean: {mv:.2f}', color='red', fontsize=14, fontweight=500, ha='center')
        else:
            # hue 범주별 평균선 표시 (kdeplot이 그린 라인의 색상과 일치시킴)
            categories = list(data[hue].unique())

            # 팔레트에서 범주의 수에 맞는 색상값 추출
            colors = sb.color_palette(palette, n_colors=len(categories))

            # 각 범주에 대해 평균선 표시
            for i, cat in enumerate(categories):
                mv = data.loc[data[hue] == cat, x].mean()
                ax.axvline(x=mv, color=colors[i], linestyle='--', linewidth=linewidth * 0.5)
                ax.text(x=mv + 0.05, y=y_max * (0.95 - i * 0.07), s=f'{cat} Mean: {mv:.2f}', color=colors[i], fontsize=14, fontweight=500, ha='center')
        
    # 그래프 표시
    if fig is not None:
        show(save_path=save_path)


#----------------------------------------------------------
def histplot(data=None, x=None, bins='auto', hue=None,
             title=None, xlabel=None, ylabel=None,
             linewidth=1, palette=None, kde=False,
             width=1280, height=640, save_path=None, ax=None):
    
    """
    히스토그램을 그린다.

    Args:
        data: 시각화할 데이터
        x: 히스토그램 대상 컬럼명
        bins: 구간 수 또는 경계
        hue: 범주 컬럼명
        title: 그래프 제목
        xlabel: x축 레이블
        ylabel: y축 레이블
        linewidth: 선 굵기
        palette: 색상 팔레트 이름
        kde: 커널 밀도 그래프 겹쳐 그릴지 여부
        width: 캔버스 가로 픽셀
        height: 캔버스 세로 픽셀
        save_path 이미지 저장 경로
    """
    # 그래프 초기화
    fig = None
    if ax is None:
        fig, ax = init(width=width, height=height, title=title, xlabel=xlabel, ylabel=ylabel)

    # 구간 산정
    if isinstance(bins, int):
        hist, bins = np.histogram(data[x], bins=bins)
        bins = np.round(bins, 1)
        ax.set_xticks(bins, bins)
    elif isinstance(bins, (list, np.ndarray)):
        ax.set_xticks(bins, bins)

    # 히스토그램 그리기
    sb.histplot(data=data, x=x, hue=hue, linewidth=linewidth,
                palette=palette, kde=kde, bins=bins, ax=ax)
    
    # 그래프 표시
    if fig is not None:
        show(save_path=save_path)

#----------------------------------------------------------
def boxplot(data=None, x=None, y=None, hue=None, orient=None,   palette=None, order=None, 
             title=None, xlabel=None, ylabel=None,
             width=1280, height=640, save_path=None, ax=None):
    """
    상자 그림(boxplot)을 그린다.

    Args:
        data: 시각화할 데이터
        x: x축 범주 컬럼명
        y: y축 범주 컬럼명
        hue: 범주 구분 컬럼명
        orient: 상자그림 방향 (None, 'v' 또는 'h')
        palette: 색상 팔레트 이름
        order : 상자그림 순서를 의미하는 연속형 자료형
        title: 그래프 제목
        xlabel: x축 레이블
        ylabel: y축 레이블
        width: 캔버스 가로 픽셀
        height: 캔버스 세로 픽셀
        save_path: 이미지 저장 경로
    """
    # 그래프 초기화
    fig = None
    if ax is None:
        fig, ax = init(width=width, height=height, title=title, xlabel=xlabel, ylabel=ylabel)

    # 상자그림 그리기
    sb.boxplot(data=data, x=x, y=y, hue=hue, orient=orient,
                palette=palette, order=order, ax=ax)
    
    # 그래프 표시
    if fig is not None:
        show(save_path=save_path)

#----------------------------------------------------------
def violinplot(data=None, x=None, y=None, hue=None, orient=None, 
               palette=None, title=None, xlabel=None, ylabel=None,
               width=1280, height=640, save_path=None, ax=None):
    """
    바이올린 플롯(violinplot)을 그린다.

    Args:
        data: 시각화할 데이터
        x: x축 범주 컬럼명
        y: y축 범주 컬럼명
        hue: 범주 구분 컬럼명
        orient: 상자그림 방향 (None, 'v' 또는 'h')
        palette: 색상 팔레트 이름
        title: 그래프 제목
        xlabel: x축 레이블
        ylabel: y축 레이블
        width: 캔버스 가로 픽셀
        height: 캔버스 세로 픽셀
        save_path: 이미지 저장 경로
    """
    # 그래프 초기화
    fig = None
    if ax is None:
        fig, ax = init(width=width, height=height, title=title, xlabel=xlabel, ylabel=ylabel)

    # 히스토그램 그리기
    sb.violinplot(data=data, x=x, y=y, hue=hue, orient=orient,
                  palette=palette, ax=ax)
    
    # 그래프 표시
    if fig is not None:
        show(save_path=save_path)


#----------------------------------------------------------
def heatmap(data=None, annot=True, fmt="0.2f", linewidth=0.5, 
            palette=None, title=None, xlabel=None, ylabel=None,
            width=1280, height=640, save_path=None, ax=None):
    """
    히트맵(heatmap)을 그린다.

    Args:
        data: 시각화할 데이터 (2차원 배열 또는 Dataframe)
        annot: 셀에 값 표시 여부 
        fmt: 셀에 표시할 값의 형식
        linewidth: 셀 간격 선 두께
        palette: 색상 팔레트 이름
        title: 그래프 제목
        xlabel: x축 레이블
        ylabel: y축 레이블
        width: 캔버스 가로 픽셀
        height: 캔버스 세로 픽셀
        save_path: 이미지 저장 경로
    """

    # 그래프 초기화
    fig = None
    if ax is None:
        fig, ax = init(width=width, height=height, title=title, xlabel=xlabel, ylabel=ylabel)

    # 그리드 제거
    ax.grid(False)

    # 히스토그램 그리기
    sb.heatmap(data=data, annot=annot, fmt=fmt, linewidths=linewidth, cmap=palette, ax=ax)
    
    # 그래프 표시
    if fig is not None:
        show(save_path=save_path)

#----------------------------------------------------------
def barplot(data=None, x=None, y=None, hue=None, estimator=np.mean, 
            palette=None, title=None, xlabel=None, ylabel=None,
            width=1280, height=640, save_path=None, ax=None):
    """
    막대그래프를 그린다.

    Args:
        data: 시각화할 데이터 (2차원 배열 또는 Dataframe)
        x: x축 범주 컬럼명
        y: y축 범주 컬럼명
        hue: 범주 구분 컬럼명
        estimator: 막대 높이 계산 함수(기본값: np.mean)
        palette: 색상 팔레트 이름
        title: 그래프 제목
        xlabel: x축 레이블
        ylabel: y축 레이블
        width: 캔버스 가로 픽셀
        height: 캔버스 세로 픽셀
        save_path: 이미지 저장 경로
    """
    # 그래프 초기화
    fig = None
    if ax is None:
        fig, ax=init(width=width, height=height, title=title, xlabel=xlabel, ylabel=ylabel)

    # 히스토그램 그리기
    sb.barplot(data=data, x=x, y=y, hue=hue, estimator=estimator, palette=palette, ax=ax)
    
    # 그래프 표시
    if fig is not None:
        show(save_path=save_path)

#----------------------------------------------------------
def countplot(data=None, x=None, y=None, hue=None, 
              palette=None, title=None, xlabel=None, ylabel=None,
              width=1280, height=640, save_path=None, ax=None):
    """
    막대그래프를 그린다.

    Args:
        data: 시각화할 데이터 (2차원 배열 또는 Dataframe)
        x: x축 범주 컬럼명
        y: y축 범주 컬럼명
        hue: 범주 구분 컬럼명
        palette: 색상 팔레트 이름
        title: 그래프 제목
        xlabel: x축 레이블
        ylabel: y축 레이블
        width: 캔버스 가로 픽셀
        height: 캔버스 세로 픽셀
        save_path: 이미지 저장 경로
    """
    # 그래프 초기화    
    fig = None
    if ax is None:
        fig, ax=init(width=width, height=height, title=title, xlabel=xlabel, ylabel=ylabel)

    # 히스토그램 그리기
    sb.countplot(data=data, x=x, y=y, hue=hue, palette=palette, ax=ax)
    
    # 그래프 표시
    if fig is not None:
        show(save_path=save_path)


#----------------------------------------------------------
def pieplot(x, labels, autopct="%0.1f%%", startangle=90, counterclock=False,
            explode=None, donutchart=False,
            wedge_width=0.7, wedge_color="#ffffff", wedge_linewidth=3,
            palette=None, title=None, xlabel=None, ylabel=None,
            width=1280, height=640, save_path=None, ax=None):
    """
    파이 그래프 혹은 도넛 그래프를 그린다.

    Args:
        x : x축 범주 컬럼명
        labels : 파이 조각에 대한 라벨
        autopct : 퍼센트 표시 형식
        startangle: 시작 각도 
        counterclock: 시계 반대 방향으로 그릴지 여부
        explode: 조각 간격
        donutchart: 도넛 차트 여부
        wedge_width: 도넛 차트일 때 조각 너비 비율
        wedge_color: 도넛 차트일 때 조각 사이 경계선 색상
        wedge_linewidth : 도넛 차트일 때 조각 사이 경계선 굵기
        palette: 색상 팔레트 이름
        title: 그래프 제목
        xlabel: x축 레이블
        ylabel: y축 레이블
        width: 캔버스 가로 픽셀
        height: 캔버스 세로 픽셀
        save_path: 이미지 저장 경로
    """

    # 그래프 초기화
    fig=None
    if ax is None:
        fig, ax= init(width=width, height=height, title=title, xlabel=xlabel, ylabel=ylabel)

    # 색상값을 팔레트로부터 추출
    color_list = None
    if palette:
        color_list = sb.color_palette(palette, n_colors=len(labels))
    
    # 도넛 그래프 그리기 옵션 생성
    wedgeprops = None
    if donutchart:
        wedgeprops={'width': wedge_width, 'edgecolor':wedge_color,
                    'linewidth':wedge_linewidth}
    
    # 파이 그래프 그리기
    ax.pie(x, labels=labels, autopct=autopct, startangle=startangle,
           counterclock=counterclock, explode=explode,
           colors=color_list, wedgeprops=wedgeprops)
    
    # 그래프 표시
    if fig is not None:
        show(save_path=save_path) 


#----------------------------------------------------------
def stackplot(data, x, y, hue, aggfunc=np.sum, orient='v', ratio=False,
              text=True, text_color="#ffffff", text_fontsize=12,
              text_format=None,
              palette=None, title=None, xlabel=None, ylabel=None,
              width=1280, height=640, save_path=None, ax=None):
    """
    누적 막대그래프를 그린다

    Args:
        data: 시각화할 데이터.
        x: x축 범주 컬럼명.
        y: y축 값 컬럼명.
        hue: 범주 구분 컬럼명.
        aggfunc: 누적할 값 계산 함수 (기본값: np.sum).
        orient: 막대 방향 ('v' 또는 'h').
        ratio: 누적값을 비율로 표시할지 여부.
        text: 누적값 텍스트 표시 여부
        palette: 색상 팔레트 이름
        title: 그래프 제목
        xlabel: x축 레이블
        ylabel: y축 레이블
        width: 캔버스 가로 픽셀
        height: 캔버스 세로 픽셀
        save_path: 이미지 저장 경로
    """

    # 그래프 초기화
    fig = None
    if ax is None:
            fig, ax = init(width=width, height=height, title=title, xlabel=xlabel, ylabel=ylabel)

    # 데이터 피벗팅 (fill_value=0 --> 결측치를 0으로 채움)후 인덱스를 문자열 카테고리로 변환
    df = pivot_table(data=data, index=x, values=y, columns=hue, aggfunc=aggfunc, fill_value=0)
    df.index = df.index.astype("str").astype("category")

    # 누적값을 비율로 변환하는 경우    
    if ratio:
        if text_format is None:              # 텍스트 포맷이 없다면 강제 지정
            text_format = "{:.1f}%"

        df['sum'] = df.sum(axis=1)           # 각 행의 합 계산하여 'sum' 열에 저장

        for col in df.columns:              # 각 열에 대해 누적값을 비율로 변환
            df[col] = df[col] / df['sum'] * 100

        df.drop(columns='sum', inplace=True) # 'sum' 열 제거

        if orient == 'v':                    # 그래프 방향에 따라 축 범위 설정
            ax.set_ylim(0, 100)
        else:
            ax.set_xlim(0, 100)
    else:
        if text_format is None:              # 텍스트 포맷이 없다면 강제 지정
            text_format = "{:.1f}"

    # 색상값 생성하기
    color_list = None
    if palette is not None:
        color_list = sb.color_palette(palette, n_colors=len(df.columns))

    # 피벗테이블의 각 열에 대해 누적 막대그래프 그리기
    for i, col in enumerate(df.columns):
        color = None

        if color_list is not None:
            color = color_list[i]

        if orient == 'v':                    # 세로 그래프인 경우
            ax.bar(df.index, df[col], bottom=df.iloc[:, :i].sum(axis=1), color=color,
                   label=col)
        else:                                # 가로 그래프인 경우
            ax.barh(df.index, df[col], left=df.iloc[:, :i].sum(axis=1), color=color,
                    label=col)

        # 누적값 텍스트 표시
        if text:
            for j, val in enumerate(df[col]):
                if val == 0:  # 누적값이 0인 경우 텍스트 표시하지 않음
                    continue

                if orient == 'v':
                    ax.text(x=j, y=df.iloc[j, :i].sum() + val / 2,
                            s=text_format.format(val), ha='center', va='center',
                            color=text_color, fontsize=text_fontsize)
                else:
                    ax.text(x=df.iloc[j, :i].sum() + val / 2, y=j,
                            s=text_format.format(val), ha='center', va='center',
                            color=text_color, fontsize=text_fontsize)

    # 범례 표시
    ax.legend(bbox_to_anchor=(1, 1))

    # 그래프 표시
    if fig is not None:
        show(save_path=save_path)

#----------------------------------------------------------
def scatterplot(data, x, y, hue=None, marker='o', color=None, size=100,
                edgecolor='#ffffff', linewidth=1.5, alpha=1,
                palette=None, 
                outline=None,
                title=None, xlabel=None, ylabel=None,
                width=1280, height=640, save_path=None, ax=None):
    """
    산점도를 그린다

    Args:
        data: 시각화할 데이터.
        x: x축 범주 컬럼명.
        y: y축 값 컬럼명.
        hue: 범주 구분 컬럼명.
        marker: 마커모양 (기본값: o)
        color : 마커색상 (hue가 None일때 적용)
        size: 마커 크기(기본값 100)
        edgecolor: 마커 테두리 색상(기본값 : #ffffff) 
        linewidth 마커 테두리 두께 (기본값: 1.5) 
        alpha: 마커 투명도(0~1, 기본값: 1)
        palette: 색상 팔레트 이름
        title: 그래프 제목
        xlabel: x축 레이블
        ylabel: y축 레이블
        width: 캔버스 가로 픽셀
        height: 캔버스 세로 픽셀
        save_path: 이미지 저장 경로
    """

    # 그래프 초기화
    fig = None
    if ax is None:
        fig, ax = init(width=width, height=height, title=title, xlabel=xlabel, ylabel=ylabel)

    # 군집을 분류할 분류값이 없다면 palette 옵션이 무의미하므로 None으로 설정
    if hue == None:
        if color is None and palette is not None:
            color = sb.color_palette(palette)[0]

        palette=None
    else:
        color=None

    # 산점도 그리기
    sb.scatterplot(data=data, x=x, y=y,
                   hue=hue,               # 군집을 구분할 분류값이 있는 컬럼명
                   color=color,           # 마커 색상
                   palette=palette,       # 색상 팔레트 설정
                   marker=marker,         # 마커 모양
                   s=size,                # 마커 크기
                   edgecolor=edgecolor,   # 마커 테두리 색상
                   linewidth=linewidth,   # 마커 테두리 두께
                   alpha=alpha,           # 마커 투명도
                   ax=ax)           
    
    # 외곽선 그리기
    if outline and hue is not None:
        # 외곽선 그리기
        plot_hull(data=data, x=x, y=y, hue=hue, palette=palette, ax=ax)
    
    # 그래프 표시
    if fig is not None:
        show(save_path=save_path)

#----------------------------------------------------------
def plot_hull(data, x, y, hue, palette, ax):
    """
    ConvexHull을 이용하여 각 군집의 외곽선을 그리는 함수

    Args:
        data: 시각화할 데이터.
        x: x축 범주 컬럼명.
        y: y축 값 컬럼명.
        palette: 색상 팔레트 이름
        ax: ConvexHull로 외곽선을 그릴 Axes 객체
    """

    from scipy.spatial import ConvexHull

    # 데이터의 군집 종류 얻기
    classes = list(data[hue].unique())

    # 각 클래스에 대하여 반복 수행
    for i,v in enumerate(classes):
        # 현재 클래스에 해당하는 데이터 포인트 추출
        df_c = data.loc[data[hue] == v, [x,y]]

        # convexhull은 3개 이상의 점이 필요하므로 데이터 포인터가 3개 미만인 경우 중단해야 함
        if len(df_c) < 3:
            continue

        hull = ConvexHull(df_c)
        points = np.append(hull.vertices, hull.vertices[0])

        # 현재 클래스에 적용될 색상값 생성
        color = sb.color_palette(palette)[i]

        # points를 index로 하는 데이터 포인트를 선과 면으로 표시
        ax.plot(df_c.iloc[points,0], df_c.iloc[points,1], linewidth=1, linestyle=':', color=color)
        ax.fill(df_c.iloc[points,0], df_c.iloc[points,1], alpha=0.1, color=color)

#----------------------------------------------------------
def lmplot(data, x, y, hue=None, palette=None, col=None, row=None, markers="o",
           scatter_edgecolor='#ffffff', scatter_linewidths=1, scatter_size=50,
           scatter_alpha=0.8, linestyle="-", linecolor=None, linewidth=2,
           title=None, xlabel=None, ylabel=None,
           width=1280, height=640, save_path=None):
    """
    seaborn lmplot으로 산점도 그래프와 회귀선을 시각화 한다.

    Args:
        data (DataFrame): 시각화할 데이터.
        x (str): 독립변수 컬럼
        y (str): 종속변수 컬럼
        hue (str|None): 범주 컬럼
        palette (str|None): 팔레트 이름
        cole (str|None): 열 패싯 컬럼
        row (str|None): 행 패싯 컬럼
        markers (str|list[str]): 산점도 점 모양
        scatter_edgecolor (str|None): 산점도 점 외곽선 색상
        scatter_linewidths (float): 산점도 점 외곽선 굵기
        scatter_size (int): 산점도 점 크기
        scatter_alpha (float) : 산점도 점 투명도
        linestyle (str) : 회귀선 스타일
        linecolor (str|None) : 회귀선 색상
        linewidth (float): 회귀선 굵기
        title: 그래프 제목
        xlabel: x축 레이블
        ylabel: y축 레이블
        width: 캔버스 가로 픽셀
        height: 캔버스 세로 픽셀
        save_path: 이미지 저장 경로
    
    Returns:
        None
    """
    #1) 그래프 초기화
    w=width/100 # 그래프 가로 크기
    h=height/100 # 그래프 세로 크기
    my_dpi = 200

    # hue가 지정되지 않았는데 palette와 linecolor가 지정된 경우, 무의미하므로 None으로 설정
    if not hue and palette:
        palette = None
        linecolor = None
    
    # 2) lmplot 그리기
    g = sb.lmplot(data=data, x=x, y=y, height=h, aspect=w/h, hue=hue, col=col, row=row,
                  legend=False, markers=markers, palette=palette,
                  scatter_kws={
                      "edgecolor":scatter_edgecolor,
                      "linewidths":scatter_linewidths,
                      "s":scatter_size,
                      "alpha": scatter_alpha},
                line_kws={
                    "linestyle":linestyle,
                    "color":linecolor,
                    "linewidth":linewidth
                })
    
    # 3) 그래프 설정
    g.fig.set_dpi(my_dpi)  # 그래프 해상도 설정
    g.fig.set_tight_layout(True) # 여백제거

    if title:
        g.fig.suptitle(title, fontsize=24, fontweight=500, y=1)

    for x in g.axes.flatten():
        x.grid(True, alpha=0.5)
        x.set_axisbelow(True)

        if xlabel: x.set_xlabel(xlabel, fontsize=16, fontweight=400, labelpad=5)
        if ylabel: x.set_ylabel(ylabel, fontsize=16, fontweight=400, labelpad=5)

        if hue is not None:
            x.legend(bbox_to_anchor=(1,1), loc='upper left')



    show(save_path=save_path)


#----------------------------------------------------------
def pairplot(data, x=None, y=None, hue=None, palette=None, diag_kind='kde', reg=False,
             markers="o", scatter_size=20, scatter_alpha=0.8, linestyle="-", linecolor=None, linewidth=1.5,
             title=None, width=1280, height=640, save_path=None):
    
    """
    산점도 행렬 시각화

    Args:
        data (DataFrame): 시각화할 데이터.
        x (str|list[str]|None): 대상 컬럼명 혹은 컬럼명 리스트
        y (str|list[str]|None): 대상 컬럼명 혹은 컬럼명 리스트
        hue (str|None): 범주 컬럼
        palette (str|None): 팔레트 이름
        diag_kind (str): 대각선에 표시할 그래프 종류, 'hist' or 'kde'
        reg (bool) : 회귀선 표시 여부
        markers (str|list[str]): 산점도 점 모양
        scatter_size (int): 산점도 점 크기
        scatter_alpha (float) : 산점도 점 투명도
        linestyle (str) : 회귀선 스타일
        linecolor (str|None) : 회귀선 색상
        linewidth (float): 회귀선 굵기
        title: 그래프 제목
        width: 캔버스 가로 픽셀
        height: 캔버스 세로 픽셀
        save_path: 이미지 저장 경로
    """

    # 1) # 1) 그래프 초기화
    figsize = (width / 100, height/100)

    # hue가 지정되지 않았는데 palette와 linecolor가 지정된 경우, 무의미하므로 None으로 설정
    if not hue and palette:
        palette = None

    # 회귀선의 표시 여부에 따라서 plot_kws 분기
    if reg:
        plot_kws= {
            'scatter_kws':{'s':scatter_size, 'alpha':scatter_alpha},
            'line_kws':{'color':linecolor, 'linewidth':linewidth, 'linestyle':linestyle}}
        
    else:
        plot_kws = {"s": scatter_size, "alpha": scatter_alpha}

    # 2) pair plot 그리기
    g = sb.pairplot(data=data, hue=hue, markers=markers, palette=palette,
                    kind='reg' if reg else 'scatter',
                    diag_kind=diag_kind, plot_kws=plot_kws)
    g.fig.set_dpi(200)
    g.fig.set_figwidth(figsize[0])
    g.fig.set_figheight(figsize[1])

    if title:
        g.fig.suptitle(title, fontsize=24, fontweight='bold')

# 3) 개별 그래프 설정 및 화면 출력
    for ax in g.axes.flatten():
        ax.set_axisbelow(True)
        ax.grid(True, alpha=0.5)

    show(save_path)


#----------------------------------------------------------
def _draw_ci(ax, interval, color, ymax):
    """
    kdeplot에서 단일 신뢰구간(하한~상한)을 지정한 색상으로 그리는 보조 함수

    Args:
        ax: 그래프를 그릴 Axes 객체
        interval: (신뢰구간 하한, 신뢰구간 상한) 튜플
        color: 신뢰구간 선/텍스트/영역에 적용할 색상
        ymax: 영역 채우기와 텍스트 위치 계산에 사용할 y축 상한
    """

    cmin, cmax = interval

    # 신뢰구간 범위에 대한 세로 직선 그리기(cmin~cmax)
    ax.axvline(cmin, linestyle=':', color=color, linewidth=0.5)
    ax.axvline(cmax, linestyle=':', color=color, linewidth=0.5)

    # 신뢰구간 범위에 대한 텍스트 추가
    ax.text(cmin, ymax*0.9, f'{cmin:.2f}', color=color, fontsize=11, ha='right')
    ax.text(cmax, ymax*0.9, f'{cmax:.2f}', color=color, fontsize=11, ha='left')

    # 신뢰구간 범위에 대한 영역 채우기(cmin~cmax)
    ax.fill_between([cmin, cmax], 0, ymax, alpha=0.1, color=color)


#=========================================
import plotly.express as px
import plotly.graph_objects as go
import plotly.figure_factory as ff
import pandas as pd


# =========================================
# Streamlit 앱용 Plotly 시각화 함수
# =========================================
# 위쪽의 matplotlib / seaborn 함수들은 수업용 또는 정적 그래프용입니다.
# 아래 함수들은 Streamlit 앱에서 바로 사용할 수 있도록 Plotly 기반으로 작성했습니다.
#
# 색상 처리 기준:
# - palette_name: Plotly 기본 팔레트 이름
# - color_column: 범례 또는 색상 구분에 사용할 컬럼
# - color_map: 특정 범주값에 직접 지정한 색상 딕셔너리
# - single_color: 범례가 없는 그래프에서 사용할 단일 색상
# =========================================

import plotly.express as px
import plotly.figure_factory as ff
import pandas as pd


def get_color_palette(palette_name="Set2"):
    """
    선택한 팔레트 이름에 맞는 Plotly 색상 목록을 반환합니다.

    예:
    - Set2
    - Pastel
    - Bold
    - Dark2
    - Plotly
    """

    palette_map = {
        "Set2": px.colors.qualitative.Set2,
        "Pastel": px.colors.qualitative.Pastel,
        "Bold": px.colors.qualitative.Bold,
        "Dark2": px.colors.qualitative.Dark2,
        "Plotly": px.colors.qualitative.Plotly,
        "D3": px.colors.qualitative.D3,
        "G10": px.colors.qualitative.G10,
        "Safe": px.colors.qualitative.Safe,
    }

    return palette_map.get(palette_name, px.colors.qualitative.Set2)


def make_histogram(
    data,
    column,
    color_column=None,
    palette_name="Set2",
    color_map=None,
    single_color=None,
):
    """
    숫자형 컬럼의 분포를 히스토그램으로 보여줍니다.
    color_column이 있으면 범주별 색상으로 나누어 표시합니다.
    """

    if color_column is None:
        fig = px.histogram(
            data,
            x=column,
            title=f"{column} 분포",
            color_discrete_sequence=[single_color] if single_color else get_color_palette(palette_name),
        )

        if single_color:
            fig.update_traces(marker_color=single_color)

    else:
        fig = px.histogram(
            data,
            x=column,
            color=color_column,
            title=f"{column} 분포",
            color_discrete_sequence=get_color_palette(palette_name),
            color_discrete_map=color_map or {},
        )

    return fig


def make_kde_plot(
    data,
    column,
    single_color=None,
):
    """
    숫자형 컬럼의 KDE 플롯을 만듭니다.
    KDE 플롯은 단일 분포선이므로 단일 색상만 적용합니다.
    """

    values = data[column].dropna()

    fig = ff.create_distplot(
        [values],
        [column],
        show_hist=False,
        show_rug=False,
        colors=[single_color] if single_color else None,
    )

    fig.update_layout(
        title=f"{column} KDE 플롯",
        xaxis_title=column,
        yaxis_title="density",
    )

    return fig


def make_bar_count(
    data,
    column,
    palette_name="Set2",
    color_map=None,
    single_color=None,
    use_category_colors=True,
):
    """
    범주형 컬럼의 값 개수를 막대그래프로 보여줍니다.
    use_category_colors가 True이면 범주별 색상을 적용합니다.
    """

    chart_data = (
        data[column]
        .fillna("결측치")
        .astype(str)
        .value_counts()
        .reset_index()
    )

    chart_data.columns = [column, "개수"]

    if use_category_colors:
        fig = px.bar(
            chart_data,
            x=column,
            y="개수",
            color=column,
            title=f"{column}별 개수",
            color_discrete_sequence=get_color_palette(palette_name),
            color_discrete_map=color_map or {},
        )

    else:
        fig = px.bar(
            chart_data,
            x=column,
            y="개수",
            title=f"{column}별 개수",
            color_discrete_sequence=[single_color] if single_color else get_color_palette(palette_name),
        )

        if single_color:
            fig.update_traces(marker_color=single_color)

    return fig


def make_bar_aggregation(
    data,
    x_column,
    y_column,
    aggregation_method,
    palette_name="Set2",
    color_map=None,
    single_color=None,
    use_category_colors=True,
):
    """
    범주형 컬럼별로 숫자형 컬럼을 집계해 막대그래프로 보여줍니다.

    aggregation_method:
    - 합계
    - 평균
    - 최댓값
    - 최솟값
    """

    agg_map = {
        "합계": "sum",
        "평균": "mean",
        "최댓값": "max",
        "최솟값": "min",
    }

    chart_data = (
        data
        .groupby(x_column, dropna=False, as_index=False)[y_column]
        .agg(agg_map[aggregation_method])
        .sort_values(y_column, ascending=False)
    )

    chart_data[x_column] = chart_data[x_column].astype(str)

    if use_category_colors:
        fig = px.bar(
            chart_data,
            x=x_column,
            y=y_column,
            color=x_column,
            title=f"{x_column}별 {y_column} {aggregation_method}",
            color_discrete_sequence=get_color_palette(palette_name),
            color_discrete_map=color_map or {},
        )

    else:
        fig = px.bar(
            chart_data,
            x=x_column,
            y=y_column,
            title=f"{x_column}별 {y_column} {aggregation_method}",
            color_discrete_sequence=[single_color] if single_color else get_color_palette(palette_name),
        )

        if single_color:
            fig.update_traces(marker_color=single_color)

    return fig


def make_count_plot(
    data,
    x_column,
    color_column=None,
    palette_name="Set2",
    color_map=None,
):
    """
    범주형 컬럼의 개수를 카운트 플롯 형태로 보여줍니다.
    color_column이 있으면 색상 기준 컬럼으로 그룹을 나눕니다.
    """

    if color_column is None:
        color_column = x_column

    fig = px.histogram(
        data,
        x=x_column,
        color=color_column,
        barmode="group",
        title=f"{x_column} 카운트 플롯",
        color_discrete_sequence=get_color_palette(palette_name),
        color_discrete_map=color_map or {},
    )

    return fig


def make_scatter(
    data,
    x_column,
    y_column,
    color_column=None,
    palette_name="Set2",
    color_map=None,
    single_color=None,
):
    """
    숫자형 컬럼 2개의 관계를 산점도로 보여줍니다.
    color_column이 있으면 범주별 색상을 적용합니다.
    """

    if color_column is None:
        fig = px.scatter(
            data,
            x=x_column,
            y=y_column,
            title=f"{x_column}와 {y_column}의 관계",
            color_discrete_sequence=[single_color] if single_color else get_color_palette(palette_name),
        )

        if single_color:
            fig.update_traces(marker_color=single_color)

    else:
        fig = px.scatter(
            data,
            x=x_column,
            y=y_column,
            color=color_column,
            title=f"{x_column}와 {y_column}의 관계",
            color_discrete_sequence=get_color_palette(palette_name),
            color_discrete_map=color_map or {},
        )

    return fig


def make_lm_plot(
    data,
    x_column,
    y_column,
    color_column=None,
    palette_name="Set2",
    color_map=None,
    single_color=None,
):
    """
    산점도에 OLS 회귀선을 함께 표시합니다.
    Plotly의 trendline="ols"는 statsmodels 패키지가 필요합니다.
    """

    if color_column is None:
        fig = px.scatter(
            data,
            x=x_column,
            y=y_column,
            trendline="ols",
            title=f"{x_column}와 {y_column}의 관계와 회귀선",
            color_discrete_sequence=[single_color] if single_color else get_color_palette(palette_name),
        )

        if single_color:
            fig.update_traces(marker_color=single_color)

    else:
        fig = px.scatter(
            data,
            x=x_column,
            y=y_column,
            color=color_column,
            trendline="ols",
            title=f"{x_column}와 {y_column}의 관계와 회귀선",
            color_discrete_sequence=get_color_palette(palette_name),
            color_discrete_map=color_map or {},
        )

    return fig


def make_line(
    data,
    x_column,
    y_column,
    color_column=None,
    palette_name="Set2",
    color_map=None,
    single_color=None,
):
    """
    X축 순서에 따른 숫자형 값의 변화를 선그래프로 보여줍니다.
    color_column이 있으면 그룹별 선 색상을 적용합니다.
    """

    if color_column is None:
        fig = px.line(
            data,
            x=x_column,
            y=y_column,
            title=f"{x_column}별 {y_column} 변화",
            color_discrete_sequence=[single_color] if single_color else get_color_palette(palette_name),
        )

        if single_color:
            fig.update_traces(line_color=single_color)

    else:
        fig = px.line(
            data,
            x=x_column,
            y=y_column,
            color=color_column,
            title=f"{x_column}별 {y_column} 변화",
            color_discrete_sequence=get_color_palette(palette_name),
            color_discrete_map=color_map or {},
        )

    return fig


def make_box(
    data,
    y_column,
    x_column=None,
    palette_name="Set2",
    color_map=None,
    single_color=None,
):
    """
    숫자형 데이터의 분포와 이상치를 박스플롯으로 보여줍니다.
    x_column이 있으면 그룹별 박스플롯을 만듭니다.
    """

    if x_column is None:
        fig = px.box(
            data,
            y=y_column,
            points="outliers",
            title=f"{y_column} 박스플롯",
            color_discrete_sequence=[single_color] if single_color else get_color_palette(palette_name),
        )

        if single_color:
            fig.update_traces(marker_color=single_color)

    else:
        fig = px.box(
            data,
            x=x_column,
            y=y_column,
            color=x_column,
            points="outliers",
            title=f"{x_column}별 {y_column} 박스플롯",
            color_discrete_sequence=get_color_palette(palette_name),
            color_discrete_map=color_map or {},
        )

    return fig


def make_violin(
    data,
    y_column,
    x_column=None,
    color_column=None,
    palette_name="Set2",
    color_map=None,
    single_color=None,
):
    """
    숫자형 데이터의 분포 형태를 바이올린 플롯으로 보여줍니다.
    """

    if color_column is None:
        fig = px.violin(
            data,
            x=x_column,
            y=y_column,
            box=True,
            points="outliers",
            title=f"{y_column} 바이올린 플롯",
            color_discrete_sequence=[single_color] if single_color else get_color_palette(palette_name),
        )

        if single_color:
            fig.update_traces(marker_color=single_color)

    else:
        fig = px.violin(
            data,
            x=x_column,
            y=y_column,
            color=color_column,
            box=True,
            points="outliers",
            title=f"{y_column} 바이올린 플롯",
            color_discrete_sequence=get_color_palette(palette_name),
            color_discrete_map=color_map or {},
        )

    return fig


def make_correlation_heatmap(
    data,
    columns,
    color_scale="RdBu_r",
):
    """
    숫자형 컬럼 간 상관관계를 히트맵으로 보여줍니다.
    color_scale은 연속형 색상 팔레트입니다.
    """

    corr_data = data[columns].corr()

    fig = px.imshow(
        corr_data,
        text_auto=".2f",
        title="상관관계 히트맵",
        color_continuous_scale=color_scale,
        zmin=-1,
        zmax=1,
        aspect="auto",
    )

    return fig


def make_pair_plot(
    data,
    columns,
    color_column=None,
    palette_name="Set2",
    color_map=None,
    single_color=None,
):
    """
    여러 숫자형 컬럼의 관계를 산점도 행렬로 보여줍니다.
    """

    if color_column is None:
        fig = px.scatter_matrix(
            data,
            dimensions=columns,
            title="Pair Plot",
            color_discrete_sequence=[single_color] if single_color else get_color_palette(palette_name),
        )

        if single_color:
            fig.update_traces(marker_color=single_color)

    else:
        fig = px.scatter_matrix(
            data,
            dimensions=columns,
            color=color_column,
            title="Pair Plot",
            color_discrete_sequence=get_color_palette(palette_name),
            color_discrete_map=color_map or {},
        )

    fig.update_traces(diagonal_visible=False)

    return fig


def make_pie_chart(
    data,
    column,
    hole=0,
    palette_name="Set2",
    color_map=None,
):
    """
    범주형 컬럼의 비율을 파이 차트 또는 도넛 차트로 보여줍니다.
    hole=0이면 파이 차트, hole=0.4처럼 값이 있으면 도넛 차트입니다.
    """

    chart_data = (
        data[column]
        .fillna("결측치")
        .astype(str)
        .value_counts()
        .reset_index()
    )

    chart_data.columns = [column, "개수"]

    fig = px.pie(
        chart_data,
        names=column,
        values="개수",
        hole=hole,
        title=f"{column} 비율",
        color=column,
        color_discrete_sequence=get_color_palette(palette_name),
        color_discrete_map=color_map or {},
    )

    return fig


def make_stacked_bar(
    data,
    x_column,
    y_column,
    color_column,
    aggregation_method,
    palette_name="Set2",
    color_map=None,
):
    """
    누적 막대그래프를 만듭니다.
    x_column은 X축 범주, color_column은 누적으로 쌓을 범주입니다.
    """

    agg_map = {
        "합계": "sum",
        "평균": "mean",
        "개수": "count",
    }

    chart_data = (
        data
        .groupby([x_column, color_column], dropna=False, as_index=False)[y_column]
        .agg(agg_map[aggregation_method])
    )

    chart_data[x_column] = chart_data[x_column].astype(str)
    chart_data[color_column] = chart_data[color_column].astype(str)

    fig = px.bar(
        chart_data,
        x=x_column,
        y=y_column,
        color=color_column,
        title=f"{x_column}별 {y_column} {aggregation_method} 누적 막대그래프",
        color_discrete_sequence=get_color_palette(palette_name),
        color_discrete_map=color_map or {},
    )

    return fig

#===============
#지도
#===============
def make_map(data, lat_column, lon_column, color_column=None, size_column=None, hover_column=None, palette_name="Set2"):
    """
    위도/경도 컬럼을 이용해 지도 위에 점을 표시하는 함수입니다.
    """

    color_palette = get_color_palette(palette_name)

    fig = px.scatter_map(
        data,
        lat=lat_column,
        lon=lon_column,
        color=color_column,
        size=size_column,
        hover_name=hover_column,
        color_discrete_sequence=color_palette,
        zoom=11,
        height=700,
        title="지도 시각화"
    )

    if size_column is None:
        fig.update_traces(
            marker=dict(
                size=10,
                opacity=0.85
            )
        )
    else:
        fig.update_traces(
            marker=dict(
                opacity=0.75
            )
        )

    fig.update_layout(
        margin=dict(l=0, r=0, t=40, b=0)
    )

    return fig

def make_scatter_with_trendline(data, x, y, color=None):
    """
    산점도에 선형 추세선을 함께 표시하는 함수입니다.

    Parameters
    ----------
    data : DataFrame
        시각화할 데이터
    x : str
        x축 숫자형 컬럼
    y : str
        y축 숫자형 컬럼
    color : str or None
        색상으로 구분할 컬럼

    Returns
    -------
    fig
        Plotly Figure
    """

    chart_data = data[[x, y]].dropna()

    if color is not None:
        chart_data = data[[x, y, color]].dropna()

    fig = px.scatter(
        chart_data,
        x=x,
        y=y,
        color=color,
        trendline="ols",
        opacity=0.65,
        title=f"{x}와 {y}의 관계"
    )

    fig.update_traces(
        marker=dict(size=7)
    )

    return fig


def make_residual_plot(resid_df, pred_column="예측값", resid_column="잔차"):
    """
    회귀분석 잔차 진단 플롯: 예측값(x) 대비 잔차(y) 산점도.

    좋은 모델이라면 점들이 0 기준선 주변에 특정 패턴 없이 고르게 퍼져 있어야 합니다.
    깔때기 모양(퍼짐이 점점 커짐)·곡선 패턴이 보이면 모델 가정이 깨졌다는 신호입니다.
    """

    fig = px.scatter(
        resid_df,
        x=pred_column,
        y=resid_column,
        opacity=0.65,
        title="잔차 진단 (예측값 대비 잔차)",
    )

    fig.update_traces(marker=dict(size=7))

    # 잔차 0 기준선
    fig.add_hline(y=0, line_dash="dash", line_color="#e45756")

    return fig


def make_timeseries_line(ts_df, date_column, value_columns, title="시계열 추이"):
    """
    시계열 집계 결과를 선그래프로 그립니다.

    value_columns에 [원래값, 이동평균]처럼 여러 컬럼을 넘기면
    한 그래프에 함께 표시합니다.
    """

    if isinstance(value_columns, str):
        value_columns = [value_columns]

    fig = px.line(
        ts_df,
        x=date_column,
        y=value_columns,
        markers=True,
        title=title,
    )

    # Streamlit 화면에서는 테마가 자동으로 색을 입혀주지만,
    # HTML 보고서로 내보낼 때는 기본 스타일이 달라져 선이 모두 검정으로 보일 수 있습니다.
    # 그래서 시계열 그래프는 선 색상을 명시적으로 고정합니다.
    line_colors = [
        "#0068c9",
        "#83c9ff",
        "#ff7f0e",
        "#2ca02c",
        "#d62728",
        "#9467bd",
    ]
    for index, trace in enumerate(fig.data):
        color = line_colors[index % len(line_colors)]
        trace.update(
            line=dict(color=color, width=2.5),
            marker=dict(color=color, size=6),
        )

    fig.update_layout(
        legend_title_text="",
        xaxis_title=date_column,
        yaxis_title="값",
    )

    return fig
