# -----------------------------------
# 서브모듈은 지연 로딩 (앱 첫 열기 속도 개선)
# -----------------------------------
# 예전에는 여기서 my_plot/my_data/my_stats/my_prep를 모두 import했습니다.
# 그러면 helper 하나만 써도(예: 데이터 페이지의 my_data) plotly·scipy까지
# 전부 로딩되어 페이지 첫 열기가 느렸습니다.
# 이제는 각 페이지가 `from helpers import my_xxx`로 필요한 모듈만 불러오고,
# 모듈 간 교차 의존성(예: my_stats -> my_plot)은 각 모듈이 알아서 import합니다.


# -----------------------------------
# 한글 폰트 설정 (matplotlib 전용 · 지연 실행)
# -----------------------------------
# Streamlit 앱은 Plotly만 사용하므로 matplotlib import와 폰트 등록이 필요 없습니다.
# 그런데 이 둘은 무겁기 때문에(앱 시작이 느려짐) 패키지 import 시점에 실행하지 않고,
# 실제로 matplotlib/seaborn 그래프를 그릴 때(my_plot의 지연 프록시) 최초 1회만
# 실행되도록 함수로 분리했습니다. 노트북에서 matplotlib 차트를 쓰면 한글이 정상 표시됩니다.
_korean_font_ready = False


def setup_korean_font():
    """matplotlib 그래프용 한글 폰트를 최초 1회만 등록/설정합니다."""
    global _korean_font_ready
    if _korean_font_ready:
        return

    import os
    from matplotlib import font_manager as fm
    from matplotlib import pyplot as plt

    # __file__ 기준 경로라 실행 위치(cwd)와 무관하게 폰트를 찾습니다.
    fpath = os.path.join(os.path.dirname(__file__), "fonts")
    if os.path.isdir(fpath):
        for f in os.listdir(fpath):
            font_path = os.path.join(fpath, f)
            fm.fontManager.addfont(font_path)
            fprop = fm.FontProperties(fname=font_path)
            plt.rcParams['font.family'] = fprop.get_name()

    my_dpi = 200                                # 이미지 선명도(100~300)
    plt.rcParams['font.size'] = 12              # 기본 폰트 크기
    plt.rcParams['axes.unicode_minus'] = False  # 그래프에 마이너스 깨짐 방지
    plt.rcParams['figure.dpi'] = my_dpi         # 그래프의 dpi 설정
    plt.rcParams['savefig.dpi'] = my_dpi        # 저장되는 그래프의 dpi 설정
    plt.rcParams['lines.linewidth'] = 2         # 그래프의 선 굵기 설정
    plt.rcParams['axes.axisbelow'] = True       # 그래프의 축과 격자선을 선보다 뒤에 배치

    _korean_font_ready = True
