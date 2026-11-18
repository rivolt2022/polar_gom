import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats
import io

# ─────────────────────────────────────────────
# 페이지 기본 설정
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="극지식물 생육 분석 대시보드",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# 한글 폰트 CSS
# ─────────────────────────────────────────────
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""",
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────
# CSV 읽기 헬퍼 (인코딩 이중 시도)
# ─────────────────────────────────────────────
@st.cache_data
def load_csv(file, label: str):
    """업로드된 CSV 파일을 utf-8-sig → cp949 순서로 시도하여 읽는다."""
    if file is None:
        return None
    try:
        df = pd.read_csv(file, encoding="utf-8-sig")
        return df
    except (UnicodeDecodeError, UnicodeError):
        file.seek(0)
        try:
            df = pd.read_csv(file, encoding="cp949")
            return df
        except (UnicodeDecodeError, UnicodeError):
            return None

def extract_school_name(filename: str) -> str:
    """파일명에서 학교명 부분을 추정한다. 예: '인천여고_환경데이터.csv' → '인천여고'"""
    base = filename.replace(".csv", "")
    if "_" in base:
        return base.split("_")[0]
    return base

# ─────────────────────────────────────────────
# 사이드바: 파일 업로드
# ─────────────────────────────────────────────
st.sidebar.title("📂 데이터 업로드")
env_file = st.sidebar.file_uploader("환경 데이터 CSV", type="csv")
growth_file = st.sidebar.file_uploader("생육 결과 데이터 CSV", type="csv")

st.sidebar.markdown("---")
st.sidebar.info(
    "💡 CSV 파일을 업로드하세요.\n"
    "• 환경 데이터는 time, temperature, humidity, ph, ec, water_temp, co2 등의 열을 포함할 수 있습니다.\n"
    "• 생육 결과 데이터는 개체번호, 잎 수, 지상부 길이, 지하부 길이, 생중량 등의 열을 포함할 수 있습니다.\n"
    "• 한 파일만 업로드해도 해당 탭은 동작합니다."
)

# ─────────────────────────────────────────────
# 데이터 로딩 (캐시 + 스피너)
# ─────────────────────────────────────────────
with st.spinner("데이터를 불러오는 중..."):
    env_df = load_csv(env_file, "환경") if env_file is not None else None
    growth_df = load_csv(growth_file, "생육") if growth_file is not None else None

# 학교명 추출
school_name = None
if env_file is not None:
    school_name = extract_school_name(env_file.name)
elif growth_file is not None:
    school_name = extract_school_name(growth_file.name)

# ─────────────────────────────────────────────
# 데이터 요약 정보 계산
# ─────────────────────────────────────────────
env_summary = None
if env_df is not None:
    numeric_cols = env_df.select_dtypes(include=[np.number]).columns.tolist()
    env_summary = {
        "컬럼": numeric_cols,
        "평균": env_df[numeric_cols].mean().round(2).to_dict(),
        "최소": env_df[numeric_cols].min().round(2).to_dict(),
        "최대": env_df[numeric_cols].max().round(2).to_dict(),
        "측정 기간": f"{env_df['time'].min()} ~ {env_df['time'].max()}" if "time" in env_df.columns else "N/A",
    }

growth_summary = None
growth_num_cols = []
if growth_df is not None:
    growth_num_cols = growth_df.select_dtypes(include=[np.number]).columns.tolist()
    exclude_cols = [c for c in growth_num_cols if "개체번호" in c or "번호" in c]
    analysis_cols = [c for c in growth_num_cols if c not in exclude_cols]
    growth_summary = {
        "총 개체수": len(growth_df),
        "평균 생중량(g)": growth_df["생중량"].mean() if "생중량" in growth_df.columns else None,
        "평균 잎 수": growth_df["잎 수"].mean() if "잎 수" in growth_df.columns else None,
        "평균 지상부 길이(mm)": growth_df["지상부 길이"].mean() if "지상부 길이" in growth_df.columns else None,
        "평균 지하부 길이(mm)": growth_df["지하부 길이"].mean() if "지하부 길이" in growth_df.columns else None,
        "측정 항목": analysis_cols,
    }

# ─────────────────────────────────────────────
# 탭 구성
# ─────────────────────────────────────────────
tab_overview, tab_env, tab_growth = st.tabs(
    ["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"]
)

# ═════════════════════════════════════════════
#  Tab 1: 실험 개요
# ═════════════════════════════════════════════
with tab_overview:
    st.title("🌱 우리 학교 극지식물 개체별 생육 차이 분석")

    if school_name:
        st.markdown(f"### 🏫 분석 대상: **{school_name}**")

    st.subheader("🔬 연구 배경 및 목적")
    st.markdown(
        """
극지식물은 극한의 환경 조건에서 생존하는 식물로, 환경 요인(온도, 습도, pH, EC 등)이
개체의 생육에 어떤 영향을 미치는지 이해하는 것이 중요합니다.

이 대시보드는 우리 학교에서 측정한 **환경 데이터**와 각 개체의 **생육 결과 데이터**를 종합하여,
개체별 생육 차이를 통계적으로 분석하는 도구입니다.

**주요 분석 항목:**
- 개체별 생중량 분포와 차이 (평균, 표준편차, 변동계수 CV)
- 잎 수·지상부 길이와 생중량의 관계 (상관계수, 산점도)
- 생중량 상위 25% vs 하위 25% 개체 비교
"""
    )

    st.subheader("📋 데이터 요약")
    col1, col2 = st.columns(2)
    with col1:
        if env_df is not None:
            st.markdown("#### 환경 데이터")
            env_info = {
                "총 행 수": len(env_df),
                "측정 기간": env_summary["측정 기간"] if env_summary else "N/A",
                "측정 항목 수": len(env_summary["컬럼"]) if env_summary else 0,
                "측정 항목": ", ".join(env_summary["컬럼"]) if env_summary else "N/A",
            }
            st.table(pd.DataFrame([env_info]).T.rename({0: "값"}, axis=1))
        else:
            st.info("환경 데이터가 업로드되지 않았습니다.")

    with col2:
        if growth_df is not None:
            st.markdown("#### 생육 결과 데이터")
            growth_info = {
                "총 개체 수": growth_summary["총 개체수"],
                "측정 항목 수": len(growth_summary["측정 항목"]) if growth_summary else 0,
                "측정 항목": ", ".join(growth_summary["측정 항목"]) if growth_summary else "N/A",
            }
            st.table(pd.DataFrame([growth_info]).T.rename({0: "값"}, axis=1))
        else:
            st.info("생육 결과 데이터가 업로드되지 않았습니다.")

    st.subheader("📊 주요 지표")
    card_cols = st.columns(4)
    if growth_df is not None and env_df is not None:
        mean_bw_val = growth_summary["평균 생중량(g)"]
        card_data = [
            ("총 개체수", f"{growth_summary['총 개체수']} 개체", "👾"),
            ("평균 온도", f"{env_df['temperature'].mean():.2f} °C", "🌡️"),
            ("평균 습도", f"{env_df['humidity'].mean():.2f} %", "💧"),
            ("평균 생중량", f"{mean_bw_val:.2f} g" if mean_bw_val is not None else "N/A", "⚖️"),
        ]
        for i, (label, value, icon) in enumerate(card_data):
            with card_cols[i]:
                st.markdown(f"**{icon} {label}**")
                st.markdown(f"# {value}")
    elif growth_df is not None:
        card_data = [
            ("총 개체수", f"{growth_summary['총 개체수']} 개체", "👾"),
            ("평균 생중량", f"{growth_summary['평균 생중량(g)']:.2f} g" if growth_summary['평균 생중량(g)'] is not None else "N/A", "⚖️"),
            ("평균 잎 수", f"{growth_summary['평균 잎 수']:.2f} 장" if growth_summary['평균 잎 수'] is not None else "N/A", "🍃"),
            ("평균 지상부 길이", f"{growth_summary['평균 지상부 길이(mm)']:.2f} mm" if growth_summary['평균 지상부 길이(mm)'] is not None else "N/A", "📏"),
        ]
        for i, (label, value, icon) in enumerate(card_data):
            with card_cols[i]:
                st.markdown(f"**{icon} {label}**")
                st.markdown(f"# {value}")
    elif env_df is not None:
        card_data = [
            ("총 행 수", f"{len(env_df)} 행", "📄"),
            ("평균 온도", f"{env_df['temperature'].mean():.2f} °C", "🌡️"),
            ("평균 습도", f"{env_df['humidity'].mean():.2f} %", "💧"),
            ("측정 기간", env_summary["측정 기간"] if env_summary else "N/A", "📅"),
        ]
        for i, (label, value, icon) in enumerate(card_data):
            with card_cols[i]:
                st.markdown(f"**{icon} {label}**")
                st.markdown(f"# {value}")
    else:
        st.info("데이터를 업로드하면 주요 지표가 표시됩니다.")

    with st.expander("📖 통계 용어 간단 설명"):
        st.markdown("""
**평균 (Mean):** 모든 값의 합을 개수로 나눈 값. 대표적인 중심 경향성 지표입니다.

**표준편차 (Standard Deviation):** 값들이 평균에서 얼마나 퍼져 있는지를 나타냅니다. 클수록 개체 간 차이가 크다는 뜻입니다.

**변동계수 (CV, Coefficient of Variation):** (표준편차 ÷ 평균) × 100 으로 계산하며, 단위가 다른 그룹끼리 변동을 비교할 때 사용합니다.

**상관계수 (Correlation Coefficient):** 두 변수가 얼마나 함께 움직이는지 나타내는 값. -1 ~ +1 사이이며, +1에 가까울수록 양의 관계(한쪽이 커지면 다른 쪽도 커짐), -1에 가까울수록 음의 관계입니다.

**상위 25% / 하위 25% (Quartile):** 데이터를 크기 순으로 정렬했을 때 위쪽 1/4, 아래쪽 1/4에 해당하는 그룹입니다. 75퍼센타일 이상과 25퍼센타일 이하로 구분합니다.
""")

# ═════════════════════════════════════════════
#  Tab 2: 환경 데이터
# ═════════════════════════════════════════════
with tab_env:
    st.title("🌡️ 환경 데이터 분석")

    if env_df is None:
        st.error("환경 데이터가 업로드되지 않았습니다. 사이드바에서 CSV 파일을 업로드해주세요.")
    else:
        if env_summary:
            st.subheader("📋 환경 데이터 요약")
            env_table_data = []
            for col in env_summary["컬럼"]:
                env_table_data.append({
                    "측정 항목": col,
                    "평균": env_summary["평균"].get(col, "N/A"),
                    "최소": env_summary["최소"].get(col, "N/A"),
                    "최대": env_summary["최대"].get(col, "N/A"),
                })
            st.table(pd.DataFrame(env_table_data))

        st.subheader("📈 날짜별 환경 변화 (일별 평균)")

        if "time" in env_df.columns:
            try:
                env_df["time_parsed"] = pd.to_datetime(env_df["time"], errors="coerce")
                env_df["day"] = env_df["time_parsed"].dt.date

                daily_mean = env_df.groupby("day")[env_summary["컬럼"]].mean().reset_index()
                daily_mean["day_str"] = daily_mean["day"].astype(str)

                if "temperature" in env_summary["컬럼"]:
                    st.markdown("#### 온도 변화")
                    fig_temp = px.line(
                        daily_mean,
                        x="day_str",
                        y="temperature",
                        markers=True,
                        title="일별 평균 온도 변화",
                        labels={"day_str": "날짜", "temperature": "온도 (°C)"},
                    )
                    fig_temp.update_layout(
                        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"),
                        xaxis_tickangle=45,
                        height=320,
                        margin=dict(t=40, b=40, l=40, r=20),
                    )
                    st.plotly_chart(fig_temp, use_container_width=False, width="stretch")

                if "humidity" in env_summary["컬럼"]:
                    st.markdown("#### 습도 변화")
                    fig_hum = px.line(
                        daily_mean,
                        x="day_str",
                        y="humidity",
                        markers=True,
                        title="일별 평균 습도 변화",
                        labels={"day_str": "날짜", "humidity": "습도 (%)"},
                    )
                    fig_hum.update_layout(
                        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"),
                        xaxis_tickangle=45,
                        height=320,
                        margin=dict(t=40, b=40, l=40, r=20),
                    )
                    st.plotly_chart(fig_hum, use_container_width=False, width="stretch")

                sub_cols = st.columns(2)
                has_ph = "ph" in env_summary["컬럼"]
                has_ec = "ec" in env_summary["컬럼"]
                if has_ph or has_ec:
                    with sub_cols[0]:
                        if has_ph:
                            st.markdown("#### pH 변화")
                            fig_ph = px.line(
                                daily_mean,
                                x="day_str",
                                y="ph",
                                markers=True,
                                title="일별 평균 pH 변화",
                                labels={"day_str": "날짜", "ph": "pH"},
                            )
                            fig_ph.update_layout(
                                font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"),
                                xaxis_tickangle=45,
                                height=280,
                                margin=dict(t=40, b=40, l=40, r=20),
                            )
                            st.plotly_chart(fig_ph, use_container_width=False, width="stretch")
                        else:
                            st.info("pH 데이터가 없습니다.")
                    with sub_cols[1]:
                        if has_ec:
                            st.markdown("#### EC 변화")
                            fig_ec = px.line(
                                daily_mean,
                                x="day_str",
                                y="ec",
                                markers=True,
                                title="일별 평균 EC 변화",
                                labels={"day_str": "날짜", "ec": "EC (dS/m)"},
                            )
                            fig_ec.update_layout(
                                font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"),
                                xaxis_tickangle=45,
                                height=280,
                                margin=dict(t=40, b=40, l=40, r=20),
                            )
                            st.plotly_chart(fig_ec, use_container_width=False, width="stretch")
                        else:
                            st.info("EC 데이터가 없습니다.")
            except Exception as e:
                st.error(f"날짜별 시계열 작성 중 오류가 발생했습니다: {e}")

        with st.expander("📄 환경 데이터 원본 테이블"):
            st.dataframe(env_df, use_container_width=True)
            csv_env = env_df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="⬇️ 환경 데이터 CSV 다운로드",
                data=csv_env,
                file_name=f"{school_name}_환경데이터_원본.csv" if school_name else "환경데이터_원본.csv",
                mime="text/csv",
            )

# ═════════════════════════════════════════════
#  Tab 3: 생육 결과
# ═════════════════════════════════════════════
with tab_growth:
    st.title("📊 생육 결과 분석")

    if growth_df is None:
        st.error("생육 결과 데이터가 업로드되지 않았습니다. 사이드바에서 CSV 파일을 업로드해주세요.")
    else:
        if "생중량" in growth_df.columns:
            mean_bw = growth_df["생중량"].mean()
            max_idx = growth_df["생중량"].idxmax()
            min_idx = growth_df["생중량"].idxmin()

            id_col = None
            for c in growth_df.columns:
                if "개체번호" in c or "번호" in c:
                    id_col = c
                    break

            max_id = growth_df.loc[max_idx, id_col] if id_col else f"개체 {max_idx+1}"
            min_id = growth_df.loc[min_idx, id_col] if id_col else f"개체 {min_idx+1}"
            max_val = growth_df.loc[max_idx, "생중량"]
            min_val = growth_df.loc[min_idx, "생중량"]
            std_bw = growth_df["생중량"].std()
            cv_bw = (std_bw / mean_bw * 100) if mean_bw != 0 else 0

            st.subheader("🥇 핵심 결과")
            kcol1, kcol2, kcol3, kcol4 = st.columns(4)
            with kcol1:
                st.markdown("**⭐ 평균 생중량**")
                st.markdown(f"# {mean_bw:.2f} g")
                st.caption(f"표준편차: {std_bw:.2f} g | CV: {cv_bw:.1f}%")
            with kcol2:
                st.markdown("**🔝 최대 생중량**")
                st.markdown(f"# {max_val:.2f} g")
                st.caption(f"개체: {max_id}")
            with kcol3:
                st.markdown("**🔻 최소 생중량**")
                st.markdown(f"# {min_val:.2f} g")
                st.caption(f"개체: {min_id}")
            with kcol4:
                st.markdown("**📊 총 개체수**")
                st.markdown(f"# {len(growth_df)} 개체")
                st.caption("극지식물 생육 개체")

        st.subheader("📈 개체별 생육 비교")
        if "생중량" in growth_df.columns:
            bw_sorted = growth_df.sort_values("생중량", ascending=False).reset_index(drop=True)
            q75 = growth_df["생중량"].quantile(0.75)
            q25 = growth_df["생중량"].quantile(0.25)

            colors = []
            for v in bw_sorted["생중량"]:
                if v >= q75:
                    colors.append("#2ecc71")
                elif v <= q25:
                    colors.append("#e74c3c")
                else:
                    colors.append("#3498db")

            fig_bar = go.Figure()
            fig_bar.add_trace(
                go.Bar(
                    x=list(range(1, len(bw_sorted) + 1)),
                    y=bw_sorted["생중량"],
                    marker_color=colors,
                    hovertext=[f"개체 {i+1}" for i in range(len(bw_sorted))],
                )
            )
            fig_bar.update_layout(
                title="개체별 생중량 비교 (🟢상위25% 🔵중간 🔴하위25%)",
                xaxis_title="개체 번호",
                yaxis_title="생중량 (g)",
                font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"),
                height=400,
                margin=dict(t=50, b=40, l=40, r=20),
            )
            st.plotly_chart(fig_bar, use_container_width=False, width="stretch")

        st.subheader("📊 평균 생육 지표")
        mcol1, mcol2, mcol3, mcol4 = st.columns(4)
        with mcol1:
            st.markdown("**⭐ 평균 생중량**")
            if "생중량" in growth_df.columns:
                st.markdown(f"# {growth_df['생중량'].mean():.2f} g")
            else:
                st.info("데이터 없음")
        with mcol2:
            if "잎 수" in growth_df.columns:
                st.markdown("**🍃 평균 잎 수**")
                st.markdown(f"# {growth_df['잎 수'].mean():.2f} 장")
            else:
                st.info("잎 수 데이터 없음")
        with mcol3:
            if "지상부 길이" in growth_df.columns:
                st.markdown("**📏 평균 지상부 길이**")
                st.markdown(f"# {growth_df['지상부 길이'].mean():.2f} mm")
            else:
                st.info("지상부 길이 데이터 없음")
        with mcol4:
            if "지하부 길이" in growth_df.columns:
                st.markdown("**🌱 평균 지하부 길이**")
                st.markdown(f"# {growth_df['지하부 길이'].mean():.2f} mm")
            else:
                st.info("지하부 길이 데이터 없음")

        st.subheader("📦 생중량 분포")
        if "생중량" in growth_df.columns:
            fig_box = px.box(
                growth_df,
                y="생중량",
                points="outliers",
                title="개체별 생중량 분포 (박스플롯)",
                labels={"생중량": "생중량 (g)"},
            )
            fig_box.update_layout(
                font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"),
                yaxis_title="생중량 (g)",
                height=320,
                margin=dict(t=40, b=40, l=40, r=20),
            )
            fig_box.add_hline(
                y=growth_df["생중량"].mean(),
                line_dash="dash",
                line_color="red",
                annotation_text="평균",
                annotation_position="top right",
            )
            st.plotly_chart(fig_box, use_container_width=False, width="stretch")

        st.subheader("🔗 상관관계 분석")
        corr_col1, corr_col2 = st.columns(2)

        with corr_col1:
            if "잎 수" in growth_df.columns and "생중량" in growth_df.columns:
                st.markdown("#### 🍃 잎 수 vs 생중량")
                fig_scatter1 = px.scatter(
                    growth_df,
                    x="잎 수",
                    y="생중량",
                    trendline="ols",
                    title="잎 수와 생중량의 관계",
                    labels={"잎 수": "잎 수 (장)", "생중량": "생중량 (g)"},
                )
                fig_scatter1.update_layout(
                    font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"),
                    height=340,
                    margin=dict(t=40, b=40, l=40, r=20),
                )
                st.plotly_chart(fig_scatter1, use_container_width=False, width="stretch")

                r1, p1 = stats.pearsonr(growth_df["잎 수"], growth_df["생중량"])
                label1 = ("(강한 양의 상관)" if r1 > 0.7 else
                          "(중간 양의 상관)" if r1 > 0.4 else
                          "(약한 양의 상관)" if r1 > 0 else
                          "(약한 음의 상관)" if r1 > -0.4 else
                          "(중간 음의 상관)" if r1 > -0.7 else
                          "(강한 음의 상관)")
                st.markdown(f"**상관계수 (r): {r1:.3f}**  {label1}")
                st.caption(
                    "상관계수는 -1에서 +1 사이 값입니다. +1에 가까우면 잎 수가 많을수록 생중량도 커지는 경향, "
                    "-1에 가까우면 반대 경향을 보입니다. 0에 가까우면 두 변수 사이에 뚜렷한 선형 관계가 없다고 봅니다."
                )
            else:
                st.info("잎 수 또는 생중량 데이터가 없습니다.")

        with corr_col2:
            if "지상부 길이" in growth_df.columns and "생중량" in growth_df.columns:
                st.markdown("#### 📏 지상부 길이 vs 생중량")
                fig_scatter2 = px.scatter(
                    growth_df,
                    x="지상부 길이",
                    y="생중량",
                    trendline="ols",
                    title="지상부 길이와 생중량의 관계",
                    labels={"지상부 길이": "지상부 길이 (mm)", "생중량": "생중량 (g)"},
                )
                fig_scatter2.update_layout(
                    font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"),
                    height=340,
                    margin=dict(t=40, b=40, l=40, r=20),
                )
                st.plotly_chart(fig_scatter2, use_container_width=False, width="stretch")

                r2, p2 = stats.pearsonr(growth_df["지상부 길이"], growth_df["생중량"])
                label2 = ("(강한 양의 상관)" if r2 > 0.7 else
                          "(중간 양의 상관)" if r2 > 0.4 else
                          "(약한 양의 상관)" if r2 > 0 else
                          "(약한 음의 상관)" if r2 > -0.4 else
                          "(중간 음의 상관)" if r2 > -0.7 else
                          "(강한 음의 상관)")
                st.markdown(f"**상관계수 (r): {r2:.3f}**  {label2}")
                st.caption(
                    "지상부 길이가 긴 개체일수록 생중량도 큰 경향이 있는지 확인할 수 있습니다. "
                    "상관계수의 해석은 위 잎 수 분석과 동일합니다."
                )
            else:
                st.info("지상부 길이 또는 생중량 데이터가 없습니다.")

        with st.expander("📄 생육 데이터 원본 테이블"):
            st.dataframe(growth_df, use_container_width=True)
            csv_growth = growth_df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="⬇️ 생육 데이터 CSV 다운로드",
                data=csv_growth,
                file_name=f"{school_name}_생육결과데이터_원본.csv" if school_name else "생육결과데이터_원본.csv",
                mime="text/csv",
            )
