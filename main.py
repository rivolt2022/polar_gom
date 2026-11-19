import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots


# ─────────────────────────────────────────
# 한글 폰트 CSS
# ─────────────────────────────────────────
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
   font-family: 'Noto Sans KR', 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif;
}
</style>
""",
    unsafe_allow_html=True,
)


# ─────────────────────────────────────────
# 열 이름 표준화 함수 (반드시 포함)
# ─────────────────────────────────────────
def std_cols(df):
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    rename = {}
    for c in df.columns:
        k = c.lower().replace(" ", "")
        if k in ("time", "categories", "시간", "날짜", "datetime", "date"):
            rename[c] = "time"
        elif k in ("temperature", "온도"):
            rename[c] = "temperature"
        elif k in ("humidity", "습도"):
            rename[c] = "humidity"
        elif k == "ph":
            rename[c] = "ph"
        elif k == "ec":
            rename[c] = "ec"
        elif "생중량" in k:
            rename[c] = "생중량"
        elif "잎" in k:
            rename[c] = "잎 수"
        elif "지상부" in k and "길이" in k:
            rename[c] = "지상부 길이"
        elif "지하부" in k and "길이" in k:
            rename[c] = "지하부 길이"
        elif "지상부" in k and ("질량" in k or "무게" in k):
            rename[c] = "지상부 질량"
        elif "지하부" in k and ("질량" in k or "무게" in k):
            rename[c] = "지하부 질량"
        elif "개체" in k:
            rename[c] = "개체번호"
    df = df.rename(columns=rename)
    for c in df.columns:
        if c in ("time", "개체번호"):
            continue
        if not pd.api.types.is_numeric_dtype(df[c]):
            num = pd.to_numeric(
                df[c].astype(str)
                .str.replace(",", "")
                .str.extract(r"(-?\d+\.?\d*)")[0],
                errors="coerce",
            )
            if num.notna().mean() >= 0.5:
                df[c] = num
    if "생중량" not in df.columns and {"지상부 질량", "지하부 질량"} <= set(df.columns):
        df["생중량"] = df["지상부 질량"] + df["지하부 질량"]
    if "time" in df.columns:
        t = df["time"].astype(str).str.strip()
        parsed = pd.to_datetime(t, errors="coerce", format="mixed")
        bad = parsed.isna() & t.str.match(r"^\d{8}_\d{1,2}$")
        if bad.any():
            parts = t[bad].str.split("_", expand=True)
            parsed[bad] = (
                pd.to_datetime(parts[0], format="%Y%m%d")
                + pd.to_timedelta(parts[1].astype(int), unit="h")
            )
        df["time"] = parsed
    return df


# ─────────────────────────────────────────
# 캐싱된 데이터 로딩 함수
# ─────────────────────────────────────────
@st.cache_data
def load_env_csv(file):
    try:
        df = pd.read_csv(file, encoding="utf-8-sig")
    except (UnicodeDecodeError, Exception):
        df = pd.read_csv(file, encoding="cp949")
    return std_cols(df)


@st.cache_data
def load_growth_csv(file):
    try:
        df = pd.read_csv(file, encoding="utf-8-sig")
    except (UnicodeDecodeError, Exception):
        df = pd.read_csv(file, encoding="cp949")
    return std_cols(df)


# ─────────────────────────────────────────
# 학교명 추출 (파일명에서)
# ─────────────────────────────────────────
def extract_school_name(filename):
    name = str(filename)
    for ch in ["_", ".", " "]:
        if ch in name:
            name = name.split(ch)[0]
            break
    return name


# ─────────────────────────────────────────
# 페이지 설정
# ─────────────────────────────────────────
st.set_page_config(page_title="극지식물 생육 분석 대시보드", layout="wide")
st.title("🌱 우리 학교 극지식물 개체별 생육 차이 분석")


# ─────────────────────────────────────────
# 사이드바: CSV 업로드
# ─────────────────────────────────────────
st.sidebar.header("📂 데이터 업로드")
env_file = st.sidebar.file_uploader("환경 CSV 업로드", type="csv")
growth_file = st.sidebar.file_uploader("생육 결과 CSV 업로드", type="csv")

school_name = "우리 학교"
if env_file is not None:
    school_name = extract_school_name(env_file.name)
elif growth_file is not None:
    school_name = extract_school_name(growth_file.name)

st.sidebar.info(f"🏫 학교명: {school_name}")

st.sidebar.header("📏 생육 측정 항목 선택")
growth_items = st.sidebar.multiselect(
    "비교할 항목 (기본 모두 선택)",
    ["잎 수", "지상부 길이", "지하부 길이", "생중량"],
    default=["잎 수", "지상부 길이", "지하부 길이", "생중량"],
)

st.sidebar.markdown("---")
st.sidebar.caption(
    "💡 CSV 인코딩이 utf-8-sig로 안 읽히면 cp949로 자동 재시도합니다.\n"
    "열 이름이 달라도 std_cols 함수로 자동 표준화됩니다."
)


# ═════════════════════════════════════════
# 탭 정의
# ═════════════════════════════════════════
tab1, tab2, tab3 = st.tabs(
    ["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"]
)


# ─────────────────────────────────────────
# TAB 1: 실험 개요
# ─────────────────────────────────────────
with tab1:
    try:
        st.header("📖 실험 개요")

        col_bg1, col_bg2 = st.columns([1, 1])
        with col_bg1:
            st.subheader("🔬 연구 배경")
            st.markdown(
                f"""
**{school_name}**에서는 극지식물(저온 환경에서 자라는 식물)의 개체별 생육 차이를 알아보기 위해
환경 데이터(온도·습도·pH·EC)와 생육 결과 데이터(잎 수, 길이, 질량)를 수집했습니다.

같은 조건에서 자랐더라도 개체마다 생장 속도가 다르며,
이러한 차이가 환경 요인(온도, 습도 등)과 어떤 관계가 있는지 분석하는 것이 이 실험의 목적입니다.
"""
            )

        with col_bg2:
            st.subheader("🎯 분석 목적")
            st.markdown(
                """
1. **개체별 생중량 분포** — 평균, 표준편차, 변동 계수(CV)로 개체 간 차이를 수치화
   → *CV(변동 계수) = 표준편차 ÷ 평균. 값이 클수록 개체 간 차이가 크다는 뜻입니다.*

2. **형태 지표와 생중량의 관계** — 잎 수·지상부 길이와 생중량의 상관계수 및 산점도
   → *상관계수(r)는 -1~1 사이 값으로, 1에 가까울수록 강한 양의 관계입니다.*

3. **상위 25% vs 하위 25% 개체 비교** — 잘 자란 개체와 덜 자란 개체의 특징 비교
"""
            )

        env_df = None
        growth_df = None
        if env_file is not None:
            with st.spinner("🌡️ 환경 데이터를 로딩 중입니다..."):
                env_df = load_env_csv(env_file)
        if growth_file is not None:
            with st.spinner("🌱 생육 결과 데이터를 로딩 중입니다..."):
                growth_df = load_growth_csv(growth_file)

        if env_df is None and growth_df is None:
            st.info("📎 왼쪽 사이드바에서 CSV 파일을 업로드해 주세요.")
        else:
            st.subheader("📋 데이터 요약")
            summary_rows = []
            if growth_df is not None:
                n_individuals = (
                    growth_df["개체번호"].nunique()
                    if "개체번호" in growth_df.columns
                    else len(growth_df)
                )
                summary_rows.append({"항목": "총 개체 수", "값": f"{n_individuals}개체"})
                if "time" in growth_df.columns:
                    t_g = growth_df["time"].dropna()
                    if len(t_g) > 0:
                        summary_rows.append(
                            {
                                "항목": "생육 측정 기간",
                                "값": f"{t_g.min().strftime('%Y-%m-%d')} ~ {t_g.max().strftime('%Y-%m-%d')}",
                            }
                        )
                summary_rows.append(
                    {
                        "항목": "생육 측정 항목",
                        "값": ", ".join(
                            [c for c in growth_df.columns if c not in ("개체번호", "time")]
                        ),
                    }
                )
            if env_df is not None:
                summary_rows.append({"항목": "환경 데이터 행 수", "값": f"{len(env_df)}행"})
                if "time" in env_df.columns:
                    t_e = env_df["time"].dropna()
                    if len(t_e) > 0:
                        summary_rows.append(
                            {
                                "항목": "환경 측정 기간",
                                "값": f"{t_e.min().strftime('%Y-%m-%d')} ~ {t_e.max().strftime('%Y-%m-%d')}",
                            }
                        )
                env_cols_list = [c for c in env_df.columns if c != "time"]
                summary_rows.append(
                    {"항목": "환경 측정 항목", "값": ", ".join(env_cols_list)}
                )
            st.dataframe(pd.DataFrame(summary_rows), width="stretch")

            st.subheader("📊 주요 지표")
            card_cols = st.columns(4)

            if growth_df is not None and "개체번호" in growth_df.columns:
                n_total = growth_df["개체번호"].nunique()
                card_cols[0].metric("🌱 총 개체수", f"{n_total}개체")
            elif growth_df is not None:
                card_cols[0].metric("🌱 총 개체수", f"{len(growth_df)}행")

            if env_df is not None and "temperature" in env_df.columns:
                t_avg = env_df["temperature"].dropna()
                if len(t_avg) > 0:
                    card_cols[1].metric("🌡️ 평균 온도", f"{t_avg.mean():.1f}°C")
                else:
                    card_cols[1].metric("🌡️ 평균 온도", "데이터 없음")
            else:
                card_cols[1].metric("🌡️ 평균 온도", "CSV 없음")

            if env_df is not None and "humidity" in env_df.columns:
                h_avg = env_df["humidity"].dropna()
                if len(h_avg) > 0:
                    card_cols[2].metric("💧 평균 습도", f"{h_avg.mean():.1f}%")
                else:
                    card_cols[2].metric("💧 평균 습도", "데이터 없음")
            else:
                card_cols[2].metric("💧 평균 습도", "CSV 없음")

            if growth_df is not None and "생중량" in growth_df.columns:
                sv = growth_df["생중량"].dropna()
                if len(sv) > 0:
                    card_cols[3].metric("⚖️ 평균 생중량", f"{sv.mean():.2f}g")
                else:
                    card_cols[3].metric("⚖️ 평균 생중량", "데이터 없음")
            else:
                card_cols[3].metric("⚖️ 평균 생중량", "CSV 없음")

    except Exception as e:
        st.warning(f"⚠️ 이 부분은 데이터 형식 때문에 표시하지 못했어요: {e}")


# ─────────────────────────────────────────
# TAB 2: 환경 데이터
# ─────────────────────────────────────────
with tab2:
    try:
        if env_df is None:
            st.info(
                "🌡️ 환경 CSV를 사이드바에서 업로드해 주세요. "
                "이 탭은 업로드 전까지 비어 있습니다."
            )
        else:
            st.header("🌡️ 환경 데이터")

            st.subheader("📋 환경 요약 통계")
            env_summary_cols = []
            for col in ["temperature", "humidity", "ph", "ec"]:
                if col in env_df.columns:
                    vals = env_df[col].dropna()
                    if len(vals) >= 1:
                        env_summary_cols.append(
                            {
                                "측정 항목": col,
                                "평균": f"{vals.mean():.2f}",
                                "최소": f"{vals.min():.2f}",
                                "최대": f"{vals.max():.2f}",
                                "데이터 수": f"{len(vals)}",
                            }
                        )
            if env_summary_cols:
                st.dataframe(pd.DataFrame(env_summary_cols), width="stretch")
            else:
                st.info("표시할 환경 수치 열이 없습니다.")

            st.subheader("📈 날짜별 환경 변화 (일별 평균)")

            if "time" in env_df.columns:
                env_df_time = env_df.copy()
                env_df_time["date"] = env_df_time["time"].dt.date

                if "temperature" in env_df.columns:
                    temp_daily = (
                        env_df_time.groupby("date")["temperature"]
                        .mean()
                        .reset_index()
                        .rename(columns={"temperature": "평균 온도"})
                    )
                    temp_daily = temp_daily.dropna(subset=["평균 온도"])
                    if len(temp_daily) >= 2:
                        fig_temp = px.line(
                            temp_daily,
                            x="date",
                            y="평균 온도",
                            markers=True,
                            title="🌡️ 일별 평균 온도 변화",
                            labels={"date": "날짜", "평균 온도": "평균 온도 (°C)"},
                        )
                        fig_temp.update_layout(
                            font=dict(
                                family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"
                            ),
                            xaxis_title="날짜",
                            yaxis_title="평균 온도 (°C)",
                        )
                        st.plotly_chart(fig_temp, width="stretch")
                    else:
                        st.info("온도 데이터가 충분하지 않아 그래프를 표시할 수 없어요.")

                if "humidity" in env_df.columns:
                    hum_daily = (
                        env_df_time.groupby("date")["humidity"]
                        .mean()
                        .reset_index()
                        .rename(columns={"humidity": "평균 습도"})
                    )
                    hum_daily = hum_daily.dropna(subset=["평균 습도"])
                    if len(hum_daily) >= 2:
                        fig_hum = px.line(
                            hum_daily,
                            x="date",
                            y="평균 습도",
                            markers=True,
                            title="💧 일별 평균 습도 변화",
                            labels={"date": "날짜", "평균 습도": "평균 습도 (%)"},
                        )
                        fig_hum.update_layout(
                            font=dict(
                                family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"
                            ),
                            xaxis_title="날짜",
                            yaxis_title="평균 습도 (%)",
                        )
                        st.plotly_chart(fig_hum, width="stretch")
                    else:
                        st.info("습도 데이터가 충분하지 않아 그래프를 표시할 수 없어요.")

                env_phys_cols = []
                if "ph" in env_df.columns:
                    env_phys_cols.append("ph")
                if "ec" in env_df.columns:
                    env_phys_cols.append("ec")

                if env_phys_cols and "date" in env_df_time.columns:
                    phys_daily_list = []
                    for col in env_phys_cols:
                        daily = (
                            env_df_time.groupby("date")[col]
                            .mean()
                            .reset_index()
                            .rename(columns={col: col})
                        )
                        phys_daily_list.append(daily.set_index("date")[col])
                    if phys_daily_list:
                        phys_daily = pd.concat(phys_daily_list, axis=1).reset_index()
                        phys_daily = phys_daily.dropna()
                        if len(phys_daily) >= 2:
                            fig_phys = px.line(
                                phys_daily,
                                x="date",
                                y=env_phys_cols,
                                markers=True,
                                title="🧪 일별 pH · EC 변화",
                                labels={"date": "날짜"},
                            )
                            fig_phys.update_layout(
                                font=dict(
                                    family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"
                                ),
                                xaxis_title="날짜",
                            )
                            st.plotly_chart(fig_phys, width="stretch")
                        else:
                            st.info(
                                "pH·EC 데이터가 충분하지 않아 그래프를 표시할 수 없어요."
                            )

            with st.expander("📄 환경 데이터 원본 테이블 + CSV 다운로드"):
                if env_df is not None:
                    st.dataframe(env_df, width="stretch")
                    csv_bytes = env_df.to_csv(index=False).encode("utf-8-sig")
                    st.download_button(
                        label="⬇️ 환경 데이터 CSV 다운로드",
                        data=csv_bytes,
                        file_name=f"{school_name}_환경데이터.csv",
                        mime="text/csv",
                    )
    except Exception as e:
        st.warning(f"⚠️ 이 부분은 데이터 형식 때문에 표시하지 못했어요: {e}")


# ─────────────────────────────────────────
# TAB 3: 생육 결과
# ─────────────────────────────────────────
with tab3:
    try:
        if growth_df is None:
            st.info(
                "🌱 생육 결과 CSV를 사이드바에서 업로드해 주세요. "
                "이 탭은 업로드 전까지 비어 있습니다."
            )
        else:
            st.header("📊 생육 결과")

            # ── 🥇 핵심 결과 카드 ──
            st.subheader("🥇 핵심 결과")
            kpi_cols = st.columns(3)

            if "생중량" in growth_df.columns:
                sv = growth_df["생중량"].dropna()
                if len(sv) >= 2:
                    kpi_cols[0].metric("📊 평균 생중량", f"{sv.mean():.2f} g")
                    max_idx = sv.idxmax()
                    min_idx = sv.idxmin()
                    max_id = (
                        growth_df.loc[max_idx, "개체번호"]
                        if "개체번호" in growth_df.columns
                        else "N/A"
                    )
                    min_id = (
                        growth_df.loc[min_idx, "개체번호"]
                        if "개체번호" in growth_df.columns
                        else "N/A"
                    )
                    kpi_cols[1].metric(
                        "🏆 최대 생중량", f"{sv.max():.2f} g", delta=f"개체 {max_id}"
                    )
                    kpi_cols[2].metric(
                        "🔻 최소 생중량", f"{sv.min():.2f} g", delta=f"개체 {min_id}"
                    )
                else:
                    kpi_cols[0].metric("📊 평균 생중량", "데이터 부족")
            else:
                kpi_cols[0].metric("📊 평균 생중량", "생중량 열 없음")

            st.divider()

            # ── 개체별 생육 비교: 막대 그래프 ──
            st.subheader("📏 개체별 생육 비교")
            bar_cols = st.columns(2)

            if "생중량" in growth_df.columns and "개체번호" in growth_df.columns:
                sv_sorted = (
                    growth_df[["개체번호", "생중량"]]
                    .dropna()
                    .sort_values("생중량", ascending=False)
                )
                if len(sv_sorted) >= 2:
                    fig_bar_weight = px.bar(
                        sv_sorted,
                        x="개체번호",
                        y="생중량",
                        labels={
                            "개체번호": "개체번호",
                            "생중량": "생중량 (g)",
                        },
                        title="⚖️ 개체별 생중량 비교",
                    )
                    fig_bar_weight.update_layout(
                        font=dict(
                            family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"
                        ),
                        xaxis_title="개체번호",
                        yaxis_title="생중량 (g)",
                    )
                    bar_cols[0].plotly_chart(fig_bar_weight, width="stretch")
                else:
                    bar_cols[0].info("생중량 데이터가 충분하지 않아요.")
            else:
                bar_cols[0].info("생중량 열이 없어 이 그래프를 표시할 수 없어요.")

            if growth_items:
                item_col_map = {
                    "잎 수": "잎 수",
                    "지상부 길이": "지상부 길이",
                    "지하부 길이": "지하부 길이",
                }
                plot_items = [
                    item_col_map[i]
                    for i in growth_items
                    if i in item_col_map and i in growth_df.columns
                ]
                if plot_items and "개체번호" in growth_df.columns:
                    gr = growth_df[["개체번호"] + plot_items].dropna()
                    if len(gr) >= 2:
                        fig_bar_items = px.bar(
                            gr,
                            x="개체번호",
                            y=plot_items,
                            labels={"개체번호": "개체번호"},
                            title="📊 개체별 생육 지표 비교",
                        )
                        fig_bar_items.update_layout(
                            font=dict(
                                family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"
                            ),
                            xaxis_title="개체번호",
                        )
                        bar_cols[1].plotly_chart(fig_bar_items, width="stretch")
                    else:
                        bar_cols[1].info("선택한 항목의 데이터가 충분하지 않아요.")
                else:
                    bar_cols[1].info("선택한 측정 항목열이 데이터에 없어요.")

            st.divider()

            # ── 생중량 분포 (박스플롯) ──
            st.subheader("📦 생중량 분포")
            if "생중량" in growth_df.columns:
                sv_box = growth_df["생중량"].dropna()
                if len(sv_box) >= 2:
                    fig_box = px.box(
                        growth_df[["개체번호", "생중량"]].dropna(),
                        x="개체번호",
                        y="생중량",
                        labels={
                            "개체번호": "개체번호",
                            "생중량": "생중량 (g)",
                        },
                        title="📦 개체별 생중량 분포 (박스플롯)",
                    )
                    fig_box.update_layout(
                        font=dict(
                            family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"
                        ),
                        xaxis_title="개체번호",
                        yaxis_title="생중량 (g)",
                    )
                    st.plotly_chart(fig_box, width="stretch")

                    sv_stats = growth_df["생중량"].dropna()
                    col_s1, col_s2, col_s3 = st.columns(3)
                    col_s1.metric("평균", f"{sv_stats.mean():.2f} g")
                    col_s2.metric("표준편차", f"{sv_stats.std():.2f} g")
                    col_s3.metric("CV (변동 계수)", f"{sv_stats.std()/sv_stats.mean():.3f}")
                    st.caption(
                        "💡 **표준편차**는 값이 평균에서 얼마나 퍼져 있는지 나타내고, "
                        "**CV(변동 계수)**는 표준편차를 평균으로 나눈 값으로 단위가 다른 그룹 간 비교에 유용합니다. "
                        "CV가 0.5보다 크면 개체 간 차이가 큰 편입니다."
                    )
                else:
                    st.info("생중량 데이터가 충분하지 않아 분포를 표시할 수 없어요.")
            else:
                st.info("생중량 열이 없어 분포 그래프를 표시할 수 없어요.")

            st.divider()

            # ── 상관관계 분석 (산점도 2개 + 추세선) ──
            st.subheader("🔗 상관관계 분석")
            st.markdown(
                "💡 **상관계수(r)** 는 -1에서 1 사이의 값으로, 1에 가까울수록 두 지표가 함께 증가하는 강한 양의 관계, "
                "-1에 가까울수록 한 지표가 증가할 때 다른 지표가 감소하는 강한 음의 관계를 의미합니다. 0에 가까우면 관계가 약합니다."
            )

            corr_pairs = [("잎 수", "잎 수"), ("지상부 길이", "지상부 길이")]
            corr_plots = []
            for label, col_name in corr_pairs:
                if col_name in growth_df.columns and "생중량" in growth_df.columns:
                    valid = growth_df[[col_name, "생중량"]].dropna()
                    if len(valid) >= 2:
                        r = valid[col_name].corr(valid["생중량"])
                        slope, intercept = np.polyfit(
                            valid[col_name], valid["생중량"], 1
                        )
                        corr_plots.append((label, col_name, valid, r, slope, intercept))

            if corr_plots:
                n_plots = len(corr_plots)
                titles_list = []
                for label, col_name, valid, r, slope, intercept in corr_plots:
                    titles_list.append(f"{label} vs 생중량 (r = {r:.3f})")

                corr_fig = make_subplots(
                    rows=1,
                    cols=n_plots,
                    subplot_titles=titles_list,
                    horizontal_spacing=0.25,
                )

                for idx, (label, col_name, valid, r, slope, intercept) in enumerate(
                    corr_plots
                ):
                    col_idx = idx + 1
                    corr_fig.add_trace(
                        go.Scatter(
                            x=valid[col_name],
                            y=valid["생중량"],
                            mode="markers",
                            marker=dict(size=8, color="#2E8B57", opacity=0.7),
                            name=f"{label} vs 생중량",
                            showlegend=(idx == 0),
                        ),
                        row=1,
                        col=col_idx,
                    )
                    x_range_full = np.linspace(
                        valid[col_name].min(), valid[col_name].max(), 100
                    )
                    y_fit = slope * x_range_full + intercept
                    corr_fig.add_trace(
                        go.Scatter(
                            x=x_range_full,
                            y=y_fit,
                            mode="lines",
                            line=dict(color="#DC143C", width=2),
                            name=f"추세선 (기울기={slope:.3f})",
                            showlegend=(idx == 0),
                        ),
                        row=1,
                        col=col_idx,
                    )
                    corr_fig.update_xaxes(
                        title_text=label, row=1, col=col_idx
                    )
                    corr_fig.update_yaxes(
                        title_text="생중량 (g)", row=1, col=col_idx
                    )

                corr_fig.update_layout(
                    font=dict(
                        family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"
                    ),
                    height=450,
                    showlegend=True,
                )
                st.plotly_chart(corr_fig, width="stretch")

                st.markdown("### 📐 상관계수 해석")
                for label, col_name, valid, r, slope, intercept in corr_plots:
                    if r > 0.7:
                        direction = "강한 양의 관계"
                    elif r > 0.3:
                        direction = "약한 양의 관계"
                    elif r > -0.3:
                        direction = "거의 관계 없음"
                    else:
                        direction = "강한 음의 관계"
                    st.info(
                        f"**{label} vs 생중량**: r = {r:.3f} → {direction}\n"
                        f"추세선 기울기 = {slope:.3f} "
                        f"(잎 수/길이가 1 증가할 때 생중량은 약 {slope:.3f}g 증가)"
                    )
            else:
                st.info(
                    "잎 수 또는 지상부 길이 열이 없어 상관관계 분석을 할 수 없어요."
                )

            st.divider()

            # ── 상위 25% vs 하위 25% 비교 ──
            st.subheader("🏆 생중량 상위 25% vs 하위 25% 비교")
            if "생중량" in growth_df.columns:
                sv_full = growth_df["생중량"].dropna()
                if len(sv_full) >= 4:
                    q75 = sv_full.quantile(0.75)
                    q25 = sv_full.quantile(0.25)
                    top_df = (
                        growth_df[growth_df["생중량"] >= q75]
                        .dropna(subset=["생중량"])
                    )
                    bot_df = (
                        growth_df[growth_df["생중량"] <= q25]
                        .dropna(subset=["생중량"])
                    )

                    comp_cols = st.columns(2)
                    with comp_cols[0]:
                        st.markdown(f"### 🥇 상위 25% (생중량 ≥ {q75:.2f} g)")
                        st.metric("개체 수", f"{len(top_df)}개체")
                        if len(top_df) > 0:
                            st.metric("평균 생중량", f"{top_df['생중량'].mean():.2f} g")
                            for col in ["잎 수", "지상부 길이", "지하부 길이"]:
                                if col in top_df.columns:
                                    vals = top_df[col].dropna()
                                    if len(vals) > 0:
                                        st.metric(f"평균 {col}", f"{vals.mean():.1f}")
                    with comp_cols[1]:
                        st.markdown(f"### 🔻 하위 25% (생중량 ≤ {q25:.2f} g)")
                        st.metric("개체 수", f"{len(bot_df)}개체")
                        if len(bot_df) > 0:
                            st.metric("평균 생중량", f"{bot_df['생중량'].mean():.2f} g")
                            for col in ["잎 수", "지상부 길이", "지하부 길이"]:
                                if col in bot_df.columns:
                                    vals = bot_df[col].dropna()
                                    if len(vals) > 0:
                                        st.metric(f"평균 {col}", f"{vals.mean():.1f}")

                    if len(top_df) > 0 and len(bot_df) > 0:
                        comp_data_rows = []
                        for col in ["생중량", "잎 수", "지상부 길이", "지하부 길이"]:
                            if col in growth_df.columns:
                                t_vals = top_df[col].dropna()
                                b_vals = bot_df[col].dropna()
                                if len(t_vals) > 0 and len(b_vals) > 0:
                                    comp_data_rows.append(
                                        {
                                            "지표": col,
                                            "상위 25% 평균": round(t_vals.mean(), 2),
                                            "하위 25% 평균": round(b_vals.mean(), 2),
                                        }
                                    )
                        if comp_data_rows:
                            comp_df = pd.DataFrame(comp_data_rows)
                            fig_comp = px.bar(
                                comp_df,
                                x="지표",
                                y=["상위 25% 평균", "하위 25% 평균"],
                                barmode="group",
                                labels={"지표": "지표", "value": "평균값"},
                                title="📊 상위 25% vs 하위 25% 지표 비교",
                            )
                            fig_comp.update_layout(
                                font=dict(
                                    family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"
                                ),
                                xaxis_title="지표",
                                yaxis_title="평균값",
                            )
                            st.plotly_chart(fig_comp, width="stretch")
                else:
                    st.info(
                        "데이터가 충분하지 않아 상위/하위 25% 비교를 할 수 없어요."
                    )
            else:
                st.info(
                    "생중량 열이 없어 상위/하위 25% 비교를 할 수 없어요."
                )

            with st.expander("📄 생육 결과 데이터 원본 테이블 + CSV 다운로드"):
                if growth_df is not None:
                    st.dataframe(growth_df, width="stretch")
                    csv_bytes_g = growth_df.to_csv(index=False).encode("utf-8-sig")
                    st.download_button(
                        label="⬇️ 생육 결과 CSV 다운로드",
                        data=csv_bytes_g,
                        file_name=f"{school_name}_생육결과데이터.csv",
                        mime="text/csv",
                    )

    except Exception as e:
        st.warning(f"⚠️ 이 부분은 데이터 형식 때문에 표시하지 못했어요: {e}")
