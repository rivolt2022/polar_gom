import io
import os
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st


# ─────────────────────────────────────────────
# 한글 폰트 (Streamlit CSS)
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
   font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# CSV 읽기 (인코딩 2단계 시도)
# ─────────────────────────────────────────────
@st.cache_data
def read_csv(file):
    data = file.getvalue()
    for enc in ("utf-8-sig", "cp949"):
        try:
            return pd.read_csv(io.BytesIO(data), encoding=enc)
        except Exception:
            pass
    return pd.DataFrame()


# ─────────────────────────────────────────────
# 열 이름 표준화
# ─────────────────────────────────────────────
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
            s = df[c].astype(str).str.replace(",", "")
            num = pd.to_numeric(
                s.str.extract(r"(-?\d+\.?\d*)")[0], errors="coerce"
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


# ─────────────────────────────────────────────
# 학교명 추출 (파일명에서)
# ─────────────────────────────────────────────
def extract_school_name(filename):
    base = os.path.splitext(os.path.basename(filename))[0]
    base = base.replace("_", " ").replace(".csv", "")
    chars = []
    for ch in base:
        if ch.isalnum() or ch in (" ", "-", "·"):
            chars.append(ch)
        else:
            break
    name = "".join(chars).strip()
    return name if name else "우리 학교"


# ─────────────────────────────────────────────
# 숫자 열만 골라내기
# ─────────────────────────────────────────────
def numeric_cols(df, exclude=("time", "개체번호")):
    excl = set(exclude)
    return [c for c in df.columns if c not in excl and pd.api.types.is_numeric_dtype(df[c])]


# ─────────────────────────────────────────────
# Streamlit 페이지 설정
# ─────────────────────────────────────────────
st.set_page_config(page_title="극지식물 생육 분석", layout="wide")
st.title("🌱 우리 학교 극지식물 개체별 생육 차이 분석")


# ─────────────────────────────────────────────
# 사이드바: 파일 업로드 + 측정 항목 선택
# ─────────────────────────────────────────────
st.sidebar.header("📁 데이터 업로드")
env_file     = st.sidebar.file_uploader("환경 CSV", type="csv")
growth_file  = st.sidebar.file_uploader("생육 결과 CSV", type="csv")

env_df    = read_csv(env_file)    if env_file    else pd.DataFrame()
growth_df = read_csv(growth_file) if growth_file else pd.DataFrame()

env_df    = std_cols(env_df)    if not env_df.empty    else env_df
growth_df = std_cols(growth_df) if not growth_df.empty else growth_df

env_school    = extract_school_name(env_file.name)    if env_file    else None
growth_school = extract_school_name(growth_file.name) if growth_file else None
school_name   = (env_school or growth_school or "우리 학교")

st.sidebar.info(f"🏫 학교명: **{school_name}**")
st.sidebar.divider()

growth_measure = st.sidebar.selectbox(
    "📊 생육 측정 항목 선택",
    ["생중량", "잎 수", "지상부 길이", "지하부 길이", "지상부 질량", "지하부 질량"],
    index=0,
    help="사이드바에서 선택한 항목이 탭3의 막대 그래프 정렬 기준이 됩니다.",
)
st.sidebar.divider()
st.sidebar.markdown("ℹ️ **Tip**\n- 파일이 없으면 해당 탭은 건너뛰고 다른 탭은 정상 동작합니다.\n- 한 파일만 올려도 그 탭은 작동합니다.")


# ─────────────────────────────────────────────
# 탭 구성
# ─────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])


# ═════════════════════════════════════════════
# TAB 1 — 실험 개요
# ═════════════════════════════════════════════
with tab1:
    try:
        st.header("🔬 연구 배경 및 목적")
        st.markdown("""
**극지식물(Extremophile plant)**은 온도·습도·토양 염분 등 열악한 환경에서도
생존하고 자라는 식물입니다. 이 대시보드에서는 우리 학교 학생들이 재배한
극지식물 **개체별 생육 차이**를 통계적으로 분석합니다.

### 분석 목적
1. **개체별 생중량 분포** — 평균·표준편차·변동계수(CV)로 개체 간 차이를 수치화
   - *평균*: 모든 개체 값을 더해 개수로 나눈 대표값
   - *표준편차*: 평균 주변에서 값들이 얼마나 넓게 퍼져 있는지 나타내는 지표
   - *변동계수(CV)*: 표준편차를 평균으로 나눈 값(%) — 평균 크기가 다를 때도 비교 가능
2. **잎 수·지상부 길이와 생중량의 관계** — 상관계수(r)와 산점도로 연관성 확인
   - *상관계수(r)*: −1 ~ +1 사이 값. +1에 가까울수록 함께 증가, 0에 가까울수록 관계 없음
3. **생중량 상위 25% vs 하위 25% 개체 비교** — 잘 자란 개체와 덜 자란 개체의 특징 차이

> 📐 **통계 용어 참고**
> - **평균(mean)**: 자료의 대표값. 모든 값을 더해 개수로 나눔
> - **표준편차(SD)**: 값들이 평균에서 얼마나 떨어져 있는지 나타내는 산포도 지표
> - **상관계수(correlation coefficient, r)**: 두 변수가 함께 움직이는 정도. −1 ~ +1
> - **변동계수(CV)**: (표준편차 ÷ 평균) × 100 — 단위가 다른 자료도 비교 가능
        """)

        st.divider()

        # ── 데이터 요약 표 ──────────────────────
        st.subheader("📋 데이터 요약")

        summary_rows = []

        # 환경 데이터 요약
        if not env_df.empty:
            env_cols = numeric_cols(env_df)
            time_col = "time" if "time" in env_df.columns else None
            n_env = len(env_df)
            if time_col and pd.api.types.is_datetime64_any_dtype(env_df[time_col]):
                tmin = env_df[time_col].min()
                tmax = env_df[time_col].max()
                period = f"{tmin.strftime('%Y-%m-%d')} ~ {tmax.strftime('%Y-%m-%d')}"
            else:
                period = f"{n_env}개 측정 시점"
            env_rows = []
            for c in env_cols:
                ser = env_df[c].dropna()
                if len(ser) > 0:
                    env_rows.append(
                        {"측정 항목": c, "평균": round(ser.mean(), 2),
                         "최소": round(ser.min(), 2), "최대": round(ser.max(), 2),
                         "측정 수": len(ser)}
                    )
            if env_rows:
                st.subheader(f"🌡️ 환경 데이터 — {school_name or '업로드된 파일'}")
                st.dataframe(pd.DataFrame(env_rows), width="stretch", use_container_width=False)
                summary_rows.append({"구분": "환경", "총 측정 수": n_env,
                                     "측정 기간": period, "측정 항목 수": len(env_rows)})
            else:
                st.info("⚠️ 환경 데이터에서 숫자 열을 찾지 못했어요.")
        else:
            st.info("🌡️ 환경 데이터를 업로드하면 여기에 요약이 표시됩니다.")

        # 생육 데이터 요약
        if not growth_df.empty:
            gr_cols = numeric_cols(growth_df)
            n_gr = len(growth_df)
            gr_rows = []
            for c in gr_cols:
                ser = growth_df[c].dropna()
                if len(ser) > 0:
                    gr_rows.append(
                        {"측정 항목": c, "평균": round(ser.mean(), 2),
                         "최소": round(ser.min(), 2), "최대": round(ser.max(), 2),
                         "측정 개체 수": len(ser)}
                    )
            st.subheader(f"📊 생육 결과 데이터 — {school_name or '업로드된 파일'}")
            st.dataframe(pd.DataFrame(gr_rows), width="stretch", use_container_width=False)
            summary_rows.append({"구분": "생육 결과", "총 개체 수": n_gr,
                                 "측정 기간": "실험 기간 (일 단위 시 환경 데이터 참조)",
                                 "측정 항목 수": len(gr_rows)})
        else:
            st.info("📊 생육 결과 데이터를 업로드하면 여기에 요약이 표시됩니다.")

        if summary_rows:
            st.dataframe(pd.DataFrame(summary_rows), width="stretch", use_container_width=False)

        st.divider()

        # ── 주요 지표 카드 ──────────────────────
        col1, col2, col3, col4 = st.columns(4)

        # 총 개체수
        if not growth_df.empty and "개체번호" in growth_df.columns:
            total = len(growth_df)
            col1.metric("총 개체 수", f"{total}개")
        else:
            col1.metric("총 개체 수", "—")

        # 평균 온도
        if not env_df.empty and "temperature" in env_df.columns:
            t_mean = env_df["temperature"].dropna().mean()
            if pd.notna(t_mean):
                col2.metric("평균 온도", f"{t_mean:.1f}℃")
            else:
                col2.metric("평균 온도", "—")
        else:
            col2.metric("평균 온도", "데이터 없음")

        # 평균 습도
        if not env_df.empty and "humidity" in env_df.columns:
            h_mean = env_df["humidity"].dropna().mean()
            if pd.notna(h_mean):
                col3.metric("평균 습도", f"{h_mean:.1f}%")
            else:
                col3.metric("평균 습도", "—")
        else:
            col3.metric("평균 습도", "데이터 없음")

        # 평균 생중량
        if not growth_df.empty and "생중량" in growth_df.columns:
            gw_mean = growth_df["생중량"].dropna().mean()
            if pd.notna(gw_mean):
                col4.metric("평균 생중량", f"{gw_mean:.2f}g")
            else:
                col4.metric("평균 생중량", "—")
        else:
            col4.metric("평균 생중량", "데이터 없음")

        st.divider()
        st.markdown(
            "_참고: 평균·표준편차 없이 개별 개체만 비교하면 우연한 차이를 과대평가할 수 있습니다. "
            "CV가 20% 미만이면 개체 간 차이가 비교적 작고, 50% 이상이면 생육 편차가 큰 편입니다._"
        )
    except Exception as e:
        st.warning(f"⚠️ 이 부분은 데이터 형식 때문에 표시하지 못했어요: {e}")


# ═════════════════════════════════════════════
# TAB 2 — 환경 데이터
# ═════════════════════════════════════════════
with tab2:
    try:
        if env_df.empty:
            st.info("🌡️ 환경 CSV를 사이드바에서 업로드하면 이 탭의 내용이 표시됩니다.")
            st.stop()

        env_cols = numeric_cols(env_df)

        if not env_cols:
            st.info("⚠️ 환경 데이터에서 숫자 열을 찾지 못했어요.")
            st.stop()

        time_ok = "time" in env_df.columns and pd.api.types.is_datetime64_any_dtype(env_df["time"])

        # ── 환경 요약 표 ─────────────────────────
        st.subheader("📋 환경 요약 (평균 · 최소 · 최대)")
        if time_ok:
            rows = []
            for c in env_cols:
                ser = env_df[c].dropna()
                if len(ser) > 0:
                    rows.append(
                        {"항목": c, "평균": round(ser.mean(), 3),
                         "최소": round(ser.min(), 3), "최대": round(ser.max(), 3),
                         "측정 수": len(ser)}
                    )
            st.dataframe(pd.DataFrame(rows), width="stretch", use_container_width=False)
        else:
            st.info("⚠️ 시간 열의 날짜가 인식할 수 없는 형식이라 환경 요약을 표시하지 못했어요.")

        st.divider()

        # ── 일별 시계열 꺾은선 ──────────────────
        if time_ok:
            st.subheader("📅 날짜별 평균 시계열")
            env_dt = env_df.copy()
            env_dt["date"] = env_dt["time"].dt.floor("D")
            daily = env_dt.groupby("date")[env_cols].mean()

            if "temperature" in env_cols:
                fig_t = go.Figure()
                fig_t.add_trace(go.Scatter(
                    x=daily.index, y=daily["temperature"],
                    mode="lines", name="온도",
                    line=dict(color="#e74c3c", width=2),
                    marker=dict(size=5),
                ))
                fig_t.update_layout(
                    title="🌡️ 일별 평균 온도 변화",
                    xaxis_title="날짜", yaxis_title="온도 (℃)",
                    font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"),
                    hovermode="x unified",
                    height=350,
                )
                st.plotly_chart(fig_t, width="stretch")
            else:
                st.info("⚠️ 온도 열이 없어 온도 시계열을 그리지 못했습니다.")

            if "humidity" in env_cols:
                fig_h = go.Figure()
                fig_h.add_trace(go.Scatter(
                    x=daily.index, y=daily["humidity"],
                    mode="lines", name="습도",
                    line=dict(color="#3498db", width=2),
                    marker=dict(size=5),
                ))
                fig_h.update_layout(
                    title="💧 일별 평균 습도 변화",
                    xaxis_title="날짜", yaxis_title="습도 (%)",
                    font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"),
                    hovermode="x unified",
                    height=350,
                )
                st.plotly_chart(fig_h, width="stretch")
            else:
                st.info("⚠️ 습도 열이 없어 습도 시계열을 그리지 못했습니다.")

            have_ph = "ph" in env_cols
            have_ec = "ec" in env_cols
            if have_ph or have_ec:
                sub = []
                if have_ph:
                    sub.append("ph")
                if have_ec:
                    sub.append("ec")
                daily_sub = daily[sub]

                fig_ph = make_subplots(
                    rows=2, cols=1,
                    subplot_titles=(
                        "🧪 일별 평균 pH 변화" if have_ph else None,
                        "🧫 일별 평균 EC 변화" if have_ec else None,
                    ),
                    vertical_spacing=0.15,
                )
                r = 1
                if have_ph:
                    fig_ph.add_trace(go.Scatter(
                        x=daily_sub.index, y=daily_sub["ph"],
                        mode="lines", name="pH",
                        line=dict(color="#27ae60", width=2),
                        marker=dict(size=4),
                    ), row=r, col=1)
                    r += 1
                if have_ec:
                    fig_ph.add_trace(go.Scatter(
                        x=daily_sub.index, y=daily_sub["ec"],
                        mode="lines", name="EC",
                        line=dict(color="#8e44ad", width=2),
                        marker=dict(size=4),
                    ), row=r, col=1)

                fig_ph.update_layout(
                    height=450,
                    font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"),
                    hovermode="x unified",
                    showlegend=False,
                )
                if have_ph:
                    fig_ph.update_yaxes(title_text="pH", row=1, col=1)
                if have_ec:
                    fig_ph.update_yaxes(title_text="EC (dS/m 또는 mS/cm)", row=2, col=1)
                fig_ph.update_xaxes(title_text="날짜", row=2, col=1)
                st.plotly_chart(fig_ph, width="stretch")
            else:
                st.info("⚠️ pH·EC 열이 없어 이 그래프를 건너뛰었습니다.")

        else:
            st.info("⚠️ 시간 열이 없거나 날짜 형식으로 변환할 수 없어 시계열 그래프를 그리지 못했습니다.")

        st.divider()

        # ── 원본 테이블 + CSV 다운로드 ──────────
        with st.expander("📄 환경 데이터 원본 테이블 + CSV 다운로드"):
            st.dataframe(env_df, width="stretch", use_container_width=False)
            csv_bytes = env_df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "⬇️ 환경 데이터 CSV 다운로드",
                data=csv_bytes,
                file_name="환경데이터_원본.csv",
                mime="text/csv",
            )
    except Exception as e:
        st.warning(f"⚠️ 이 부분은 데이터 형식 때문에 표시하지 못했어요: {e}")


# ═════════════════════════════════════════════
# TAB 3 — 생육 결과
# ═════════════════════════════════════════════
with tab3:
    try:
        if growth_df.empty:
            st.info("📊 생육 결과 CSV를 사이드바에서 업로드하면 이 탭의 내용이 표시됩니다.")
            st.stop()

        gr_cols = numeric_cols(growth_df)

        if not gr_cols:
            st.info("⚠️ 생육 데이터에서 숫자 열을 찾지 못했어요.")
            st.stop()

        has_jw = "생중량" in growth_df.columns
        has_ip = "잎 수"      in growth_df.columns
        has_js = "지상부 길이" in growth_df.columns
        has_js_len = "지하부 길이" in growth_df.columns

        # ─────────────────────────────────────
        # 🥇 핵심 결과 카드
        # ─────────────────────────────────────
        st.subheader("🥇 핵심 결과")
        if has_jw:
            gw = growth_df["생중량"].dropna()
            if len(gw) >= 2:
                gw_mean = gw.mean()
                gw_max  = gw.max()
                gw_min  = gw.min()
                gw_max_id = growth_df.loc[gw.idxmax(), "개체번호"] if "개체번호" in growth_df.columns else "—"
                gw_min_id = growth_df.loc[gw.idxmin(), "개체번호"] if "개체번호" in growth_df.columns else "—"

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("📊 평균 생중량", f"{gw_mean:.2f}g")
                c2.metric("🔺 최대 생중량", f"{gw_max:.2f}g", delta=f"개체 {gw_max_id}")
                c3.metric("🔻 최소 생중량", f"{gw_min:.2f}g", delta=f"개체 {gw_min_id}")
                cv_val = (gw.std() / gw_mean * 100) if gw_mean > 0 else 0
                c4.metric("📈 변동계수(CV)", f"{cv_val:.1f}%",
                          help="CV = (표준편차 ÷ 평균) × 100. 평균 대비 산포 정도.")
            else:
                st.info("⚠️ 생중량 데이터가 2개 미만이라 핵심 결과를 계산하지 못했습니다.")
        else:
            st.info("⚠️ 생중량(또는 지상부 질량+지하부 질량) 열이 없어 핵심 결과를 계산하지 못했습니다.")

        st.divider()

        # ─────────────────────────────────────
        # 개체별 생육 비교 — 막대 그래프
        # ─────────────────────────────────────
        st.subheader("📊 개체별 생육 비교 (막대 그래프)")

        plot_map = {
            "생중량":        ("생중량",        "생중량 (g)"),
            "잎 수":         ("잎 수",         "잎 수 (장)"),
            "지상부 길이":   ("지상부 길이",   "지상부 길이 (mm)"),
            "지하부 길이":   ("지하부 길이",   "지하부 길이 (mm)"),
            "지상부 질량":   ("지상부 질량",   "지상부 질량 (g)"),
            "지하부 질량":   ("지하부 질량",   "지하부 질량 (g)"),
        }

        plot_col, plot_label = plot_map.get(growth_measure, ("생중량", "생중량 (g)"))

        if plot_col in growth_df.columns:
            vals = growth_df[plot_col].dropna()
            ids  = growth_df.loc[vals.index, "개체번호"] if "개체번호" in growth_df.columns else None

            if ids is not None and len(ids) > 0:
                fig_bar = go.Figure()
                fig_bar.add_trace(go.Bar(
                    x=ids.values, y=vals.values,
                    marker_color="#2ecc71",
                    marker_line_color="#1a7a3a",
                    marker_line_width=0.8,
                    opacity=0.85,
                    name=plot_col,
                ))
                fig_bar.update_layout(
                    title=f"🌿 개체별 {plot_label}",
                    xaxis_title="개체", yaxis_title=plot_label,
                    font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"),
                    height=450,
                    showlegend=False,
                )
                st.plotly_chart(fig_bar, width="stretch")
            else:
                fig_bar = go.Figure()
                fig_bar.add_trace(go.Bar(
                    y=vals.values,
                    marker_color="#2ecc71",
                    opacity=0.85,
                    name=plot_col,
                ))
                fig_bar.update_layout(
                    title=f"🌿 개체별 {plot_label}",
                    yaxis_title=plot_label,
                    font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"),
                    height=450,
                    showlegend=False,
                )
                st.plotly_chart(fig_bar, width="stretch")
        else:
            st.info(f"⚠️ '{plot_col}' 열이 없어 막대 그래프를 그리지 못했습니다.")

        st.divider()

        # ─────────────────────────────────────
        # 생중량 분포 (박스플롯 / 바이올린 플롯)
        # ─────────────────────────────────────
        st.subheader("📦 생중량 분포 (박스플롯)")
        toggle_dist = st.radio(
            "그래프 유형",
            ["박스플롯", "바이올린 플롯"],
            horizontal=True,
            index=0,
            help="박스플롯: 중앙값·사분위수·이상치 표시 / 바이올린 플롯: 분포 밀도까지 표시",
        )

        if has_jw:
            gw = growth_df["생중량"].dropna()
            if len(gw) >= 3:
                fig_box = go.Figure()
                if toggle_dist == "박스플롯":
                    fig_box.add_trace(go.Box(
                        y=gw.values, name="생중량",
                        boxpoints="outliers",
                        marker_color="#3498db",
                        line_color="#2980b9",
                        fillcolor="rgba(52,152,219,0.25)",
                    ))
                else:
                    fig_box.add_trace(go.Violin(
                        y=gw.values, name="생중량",
                        box_visible=True,
                        meanline_visible=True,
                        points="outliers",
                        line_color="#2980b9",
                        fillcolor="rgba(52,152,219,0.3)",
                    ))
                fig_box.update_layout(
                    title=f"📦 생중량 분포 — n={len(gw)}개체",
                    yaxis_title="생중량 (g)",
                    font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"),
                    height=380,
                    showlegend=False,
                )
                st.plotly_chart(fig_box, width="stretch")
            else:
                st.info("⚠️ 생중량 데이터가 3개 미만이라 분포 그래프를 그리지 못했습니다.")
        else:
            st.info("⚠️ 생중량 열이 없어 분포 그래프를 그리지 못했습니다.")

        st.divider()

        # ─────────────────────────────────────
        # 상관관계 분석 (산점도 + 추세선)
        # ─────────────────────────────────────
        st.subheader("🔗 상관관계 분석 (산점도 + 추세선)")

        scat_pairs = [
            ("잎 수", "생중량",        "잎 수 (장)",      "생중량 (g)",   "#e74c3c"),
            ("지상부 길이", "생중량", "지상부 길이 (mm)", "생중량 (g)",   "#3498db"),
        ]

        for x_col, y_col, x_label, y_label, color in scat_pairs:
            if x_col in growth_df.columns and y_col in growth_df.columns:
                df_xy = growth_df[[x_col, y_col]].dropna()
                if len(df_xy) >= 3:
                    x = df_xy[x_col].values
                    y = df_xy[y_col].values
                    r_val = np.corrcoef(x, y)[0, 1]

                    fig_sc = go.Figure()
                    fig_sc.add_trace(go.Scatter(
                        x=x, y=y,
                        mode="markers",
                        marker=dict(
                            color=color, size=9,
                            line=dict(width=1, color="white"),
                            opacity=0.8,
                        ),
                        name=f"{x_label} vs {y_label}",
                    ))
                    coef = np.polyfit(x, y, 1)
                    x_line = np.array([x.min(), x.max()])
                    y_line = coef[0] * x_line + coef[1]
                    fig_sc.add_trace(go.Scatter(
                        x=x_line, y=y_line,
                        mode="lines",
                        line=dict(color="rgba(0,0,0,0.55)", width=2, dash="dash"),
                        name=f"추세선 (r={r_val:.2f})",
                    ))
                    fig_sc.update_layout(
                        title=f"📈 {x_label} vs {y_label}  (상관계수 r = {r_val:.2f})",
                        xaxis_title=x_label,
                        yaxis_title=y_label,
                        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"),
                        height=380,
                        hovermode="x unified",
                    )
                    st.plotly_chart(fig_sc, width="stretch")
                else:
                    st.info(f"⚠️ {x_label}과 {y_label} 데이터가 3개 미만이라 상관관계를 계산하지 못했습니다.")
            else:
                st.info(f"⚠️ '{x_col}' 또는 '{y_col}' 열이 없어 이 산점도를 건너뛰었습니다.")

        st.divider()

        # ─────────────────────────────────────
        # 상위 25% vs 하위 25% 비교
        # ─────────────────────────────────────
        if has_jw:
            gw = growth_df["생중량"].dropna()
            if len(gw) >= 4:
                q75, q25 = gw.quantile(0.75), gw.quantile(0.25)
                top_idx  = gw[gw >= q75].index
                bot_idx  = gw[gw <= q25].index

                c_top, c_bot = st.columns(2)
                with c_top:
                    st.markdown(f"#### 🔺 상위 25% (생중량 ≥ {q75:.2f}g)")
                    if len(top_idx) > 0:
                        top_df = growth_df.loc[top_idx, numeric_cols(growth_df)]
                        st.dataframe(
                            top_df.round(2),
                            width="stretch", use_container_width=False,
                        )
                with c_bot:
                    st.markdown(f"#### 🔻 하위 25% (생중량 ≤ {q25:.2f}g)")
                    if len(bot_idx) > 0:
                        bot_df = growth_df.loc[bot_idx, numeric_cols(growth_df)]
                        st.dataframe(
                            bot_df.round(2),
                            width="stretch", use_container_width=False,
                        )

                if len(top_idx) > 0 and len(bot_idx) > 0:
                    st.divider()
                    st.subheader("📌 상위 25% vs 하위 25% 평균 비교")
                    comp_rows = []
                    for c in numeric_cols(growth_df):
                        v_top = growth_df.loc[top_idx, c].dropna().mean()
                        v_bot = growth_df.loc[bot_idx, c].dropna().mean()
                        diff  = v_top - v_bot
                        comp_rows.append({
                            "항목": c,
                            "상위 25% 평균": round(v_top, 2),
                            "하위 25% 평균": round(v_bot, 2),
                            "차이 (상위−하위)": round(diff, 2),
                        })
                    st.dataframe(pd.DataFrame(comp_rows), width="stretch", use_container_width=False)

        # ─────────────────────────────────────
        # 원본 테이블 + CSV 다운로드
        # ─────────────────────────────────────
        st.divider()
        with st.expander("📄 생육 데이터 원본 테이블 + CSV 다운로드"):
            st.dataframe(growth_df, width="stretch", use_container_width=False)
            csv_bytes = growth_df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "⬇️ 생육 결과 CSV 다운로드",
                data=csv_bytes,
                file_name="생육결과_원본.csv",
                mime="text/csv",
            )
    except Exception as e:
        st.warning(f"⚠️ 이 부분은 데이터 형식 때문에 표시하지 못했어요: {e}")


# ─────────────────────────────────────────────
# 하단 푸터
# ─────────────────────────────────────────────
st.divider()
st.caption(
    "🌱 극지식물 생육 분석 대시보드  |  "
    "통계 계산: numpy · pandas  |  "
    "그래프: plotly  |  "
    "제작: Streamlit"
)
