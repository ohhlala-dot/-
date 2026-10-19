import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ==================================================
# 1. 페이지 설정 및 디자인
# ==================================================
st.set_page_config(
    page_title="동네별 인구 피라미드",
    page_icon="🏘️",
    layout="wide",
)

DATA_URL = (
    "https://raw.githubusercontent.com/first2022-cyber/"
    "contents/main/population_ts_yearly_gender.zip"
)

# 나이 라벨을 0세부터 100세 이상까지 순서대로 만듭니다.
AGE_LABELS = [f"{age}세" for age in range(101)]
AGE_LABELS[-1] = "100세 이상"

MALE_COLOR = "#D88972"
FEMALE_COLOR = "#E9B65D"
BACKGROUND_COLOR = "#FFF9F2"
TEXT_COLOR = "#49382E"


# ==================================================
# 2. 데이터 불러오기
# ==================================================
@st.cache_data(show_spinner="인구 데이터를 불러오는 중입니다...")
def load_data():
    # pandas가 URL의 ZIP 압축을 자동으로 풀어 CSV를 읽습니다.
    df = pd.read_csv(DATA_URL, compression="zip")
    df.columns = df.columns.astype(str).str.strip()

    # 최신 연도 데이터만 사용합니다.
    df["연도"] = pd.to_numeric(df["연도"], errors="coerce")
    df = df.dropna(subset=["연도"])
    latest_year = int(df["연도"].max())
    df = df[df["연도"] == latest_year].copy()

    # 지역명 앞뒤의 공백을 정리합니다.
    for col in ["시도", "시군구", "동"]:
        df[col] = df[col].astype("string").str.strip()

    # 남녀 인구 열을 숫자로 바꾸고, 비어 있는 값은 0으로 처리합니다.
    population_columns = [
        col for col in df.columns
        if col.startswith(("남_", "여_"))
    ]
    for col in population_columns:
        df[col] = pd.to_numeric(
            df[col].astype(str).str.replace(",", "", regex=False),
            errors="coerce",
        ).fillna(0)

    return df, latest_year


# ==================================================
# 3. 화면 스타일
# ==================================================
st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: {BACKGROUND_COLOR};
        color: {TEXT_COLOR};
    }}
    h1, h2, h3 {{
        color: {TEXT_COLOR};
    }}
    div[data-testid="stMetric"] {{
        background-color: #FFFFFF;
        border: 1px solid #F0DDCA;
        border-radius: 14px;
        padding: 16px;
    }}
    div[data-testid="stSelectbox"] label {{
        color: {TEXT_COLOR};
        font-weight: 600;
    }}
    .aging-warning {{
        display: inline-block;
        background: #FFF0D8;
        color: #8B4A20;
        border: 1px solid #E9B65D;
        border-radius: 10px;
        padding: 8px 12px;
        margin: 0 0 12px 0;
        font-weight: 700;
    }}
    .neighborhood-summary {{
        background: #FFFFFF;
        border-left: 5px solid #D88972;
        border-radius: 10px;
        padding: 14px 18px;
        margin-top: 10px;
        color: {TEXT_COLOR};
        line-height: 1.6;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🏘️ 동네별 인구 피라미드")
st.markdown(
    "우리 동네의 연령별 인구 구성을 살펴보세요. "
    "남성은 왼쪽, 여성은 오른쪽에 표시됩니다."
)
st.divider()


# ==================================================
# 4. 데이터 로딩 및 기본 열 확인
# ==================================================
try:
    df, latest_year = load_data()
except Exception as e:
    st.error(
        "인구 데이터를 불러오지 못했습니다. "
        "인터넷 연결과 데이터 주소를 확인해 주세요."
    )
    st.exception(e)
    st.stop()

required_columns = ["연도", "시도", "시군구", "동"]
missing_columns = [col for col in required_columns if col not in df.columns]
if missing_columns:
    st.error(f"데이터에 필요한 열이 없습니다: {missing_columns}")
    st.stop()

st.caption(f"📅 분석 기준 연도: {latest_year}년 · 데이터에서 확인된 가장 최신 연도")


# ==================================================
# 5. 시도 → 시군구 → 동 선택
# ==================================================
st.subheader("📍 지역 선택")

sido_options = sorted(df["시도"].dropna().unique().tolist())
if not sido_options:
    st.warning("선택할 수 있는 시도 데이터가 없습니다.")
    st.stop()

col1, col2, col3 = st.columns(3)

with col1:
    selected_sido = st.selectbox("① 시도", options=sido_options, key="selected_sido")

sigungu_data = df[df["시도"] == selected_sido]
sigungu_options = sorted(sigungu_data["시군구"].dropna().unique().tolist())
if not sigungu_options:
    st.warning("선택한 시도에 시군구 데이터가 없습니다.")
    st.stop()

with col2:
    selected_sigungu = st.selectbox(
        "② 시군구", options=sigungu_options, key="selected_sigungu"
    )

dong_data = sigungu_data[sigungu_data["시군구"] == selected_sigungu]
dong_options = sorted(dong_data["동"].dropna().unique().tolist())
if not dong_options:
    st.warning("선택한 시군구에 동 데이터가 없습니다.")
    st.stop()

with col3:
    selected_dong = st.selectbox("③ 동", options=dong_options, key="selected_dong")


# ==================================================
# 6. 선택한 동네의 연령별 인구 계산
# ==================================================
selected_data = df[
    (df["시도"] == selected_sido)
    & (df["시군구"] == selected_sigungu)
    & (df["동"] == selected_dong)
]

if selected_data.empty:
    st.warning("선택한 지역의 인구 데이터가 없습니다.")
    st.stop()

male_columns = [f"남_{age}세" for age in range(100)] + ["남_100세 이상"]
female_columns = [f"여_{age}세" for age in range(100)] + ["여_100세 이상"]

missing_population_columns = [
    col for col in male_columns + female_columns if col not in df.columns
]
if missing_population_columns:
    st.error(
        "일부 연령별 인구 열을 찾을 수 없습니다. "
        "실제 CSV의 열 이름을 확인해 주세요."
    )
    st.write("누락된 열 예시:", missing_population_columns[:10])
    st.stop()

# 같은 동네가 여러 행이면 연령별 인구를 합산합니다.
population = selected_data[male_columns + female_columns].sum()

male_population = np.rint(
    np.array([population[col] for col in male_columns], dtype=float)
).astype(int)
female_population = np.rint(
    np.array([population[col] for col in female_columns], dtype=float)
).astype(int)

# 남성은 왼쪽에 보이도록 음수로 바꿉니다.
male_negative = -male_population

total_male = int(male_population.sum())
total_female = int(female_population.sum())
total_population = total_male + total_female

# 65세 이상은 65세부터 100세 이상까지의 인구를 합산합니다.
elderly_population = int(
    male_population[65:].sum() + female_population[65:].sum()
)
aging_rate = (
    elderly_population / total_population * 100
    if total_population > 0
    else 0.0
)

# 평균연령은 연령별 인구를 가중치로 계산합니다.
# '100세 이상'은 계산을 위해 대표값 100세로 간주합니다.
ages = np.arange(101)
all_age_population = male_population + female_population
average_age = (
    float(np.average(ages, weights=all_age_population))
    if total_population > 0
    else 0.0
)


# ==================================================
# 7. 지표 카드 3개
# ==================================================
st.divider()
st.subheader(f"📊 {selected_sido} {selected_sigungu} {selected_dong} 인구 현황")

# 고령화율이 20%를 초과하면 카드 영역 위에 주의 표시를 띄웁니다.
if aging_rate > 20:
    st.markdown(
        '<div class="aging-warning">⚠️ 고령화율 20% 초과: 고령화 사회 지표 확인</div>',
        unsafe_allow_html=True,
    )

metric1, metric2, metric3 = st.columns(3)

with metric1:
    st.metric("👥 총인구", f"{total_population:,}명")

with metric2:
    st.metric("🎂 평균연령", f"{average_age:.1f}세")

with metric3:
    st.metric("🌳 고령화율 (65세 이상)", f"{aging_rate:.1f}%")


# ==================================================
# 8. 인구 피라미드 가로 막대그래프
# ==================================================
fig = go.Figure()

fig.add_trace(
    go.Bar(
        y=AGE_LABELS,
        x=male_negative,
        name="남성",
        orientation="h",
        marker_color=MALE_COLOR,
        customdata=male_population,
        hovertemplate="나이: %{y}<br>남성 인구: %{customdata:,}명<extra></extra>",
    )
)

fig.add_trace(
    go.Bar(
        y=AGE_LABELS,
        x=female_population,
        name="여성",
        orientation="h",
        marker_color=FEMALE_COLOR,
        hovertemplate="나이: %{y}<br>여성 인구: %{x:,}명<extra></extra>",
    )
)

max_population = max(
    int(male_population.max()),
    int(female_population.max()),
    1,
)
axis_limit = max_population * 1.12
axis_end = int(np.ceil(axis_limit))
tick_step = max(1, int(np.ceil(axis_end / 5)))
tick_values = list(range(-axis_end, axis_end + 1, tick_step))
tick_values = sorted(set(tick_values + [-axis_end, 0, axis_end]))

fig.update_layout(
    title={"text": "연령별 남녀 인구 분포", "x": 0.5, "xanchor": "center"},
    barmode="overlay",
    bargap=0.08,
    height=1900,
    paper_bgcolor=BACKGROUND_COLOR,
    plot_bgcolor="#FFFFFF",
    font={"family": "Arial, sans-serif", "size": 12, "color": TEXT_COLOR},
    legend={
        "orientation": "h",
        "yanchor": "bottom",
        "y": 1.02,
        "xanchor": "center",
        "x": 0.5,
    },
    margin={"l": 95, "r": 45, "t": 100, "b": 70},
    xaxis={
        "title": "인구 수 (명)",
        "range": [-axis_limit, axis_limit],
        "tickmode": "array",
        "tickvals": tick_values,
        "ticktext": [f"{abs(v):,}" for v in tick_values],
        "zeroline": True,
        "zerolinewidth": 2,
        "zerolinecolor": "#9B8172",
        "gridcolor": "#F1E7DE",
    },
    yaxis={
        "title": "나이",
        # 순서를 직접 지정합니다. 축 반전 옵션은 사용하지 않습니다.
        # AGE_LABELS의 첫 항목인 0세가 아래, 마지막인 100세 이상이 위에 표시됩니다.
        "categoryorder": "array",
        "categoryarray": AGE_LABELS,
        "tickmode": "array",
        "tickvals": AGE_LABELS,
        "ticktext": AGE_LABELS,
        "showgrid": False,
        "automargin": True,
    },
)

st.plotly_chart(fig, use_container_width=True)

st.caption(
    "※ 남성은 왼쪽, 여성은 오른쪽에 표시됩니다. "
    "가로축의 눈금은 양쪽 모두 인구 수의 절댓값입니다."
)


# ==================================================
# 9. 동네 인구 구성 자동 설명
# ==================================================
# 0~14세를 아이 인구로, 65세 이상을 어르신 인구로 계산합니다.
children_population = int(
    male_population[:15].sum() + female_population[:15].sum()
)
children_rate = (
    children_population / total_population * 100
    if total_population > 0
    else 0.0
)
elderly_rate = aging_rate

if total_population == 0:
    neighborhood_description = (
        "인구 데이터가 없어 아이와 어르신의 비중을 비교하기 어렵습니다."
    )
elif children_rate >= elderly_rate + 5:
    neighborhood_description = (
        f"이 동네는 아이가 많은 편입니다. "
        f"0~14세 비율은 {children_rate:.1f}%, "
        f"65세 이상 비율은 {elderly_rate:.1f}%입니다."
    )
elif elderly_rate >= children_rate + 5:
    neighborhood_description = (
        f"이 동네는 어르신이 많은 편입니다. "
        f"65세 이상 비율은 {elderly_rate:.1f}%, "
        f"0~14세 비율은 {children_rate:.1f}%입니다."
    )
else:
    neighborhood_description = (
        f"이 동네는 아이와 어르신의 비중이 비교적 비슷합니다. "
        f"0~14세 비율은 {children_rate:.1f}%, "
        f"65세 이상 비율은 {elderly_rate:.1f}%입니다."
    )

st.markdown(
    f'<div class="neighborhood-summary"><strong>🔎 한눈에 보는 동네 특징</strong><br>'
    f'{neighborhood_description}</div>',
    unsafe_allow_html=True,
)


# ==================================================
# 10. 연령별 인구 표
# ==================================================
with st.expander("📋 연령별 인구 데이터 표 보기"):
    result_table = pd.DataFrame(
        {
            "나이": AGE_LABELS,
            "남성 인구": male_population,
            "여성 인구": female_population,
            "전체 인구": male_population + female_population,
        }
    )
    st.dataframe(result_table, hide_index=True, use_container_width=True)

st.markdown(
    """
    <div style="
        text-align:center;
        color:#8A7567;
        padding:20px 0 5px 0;
        font-size:13px;
    ">
        동네별 인구 피라미드 · 최신 연도 기준
    </div>
    """,
    unsafe_allow_html=True,
)
