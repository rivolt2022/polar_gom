[Role]
너는 Streamlit 전문가야.
CSV 업로드 시 인코딩(utf-8-sig/cp949) 오류와
학교마다 다른 열 이름 때문에 생기는 오류(KeyError),
한글 폰트 깨짐을 완벽히 방지하며,
Streamlit Cloud에서도 에러 없이 실행되는 코드를 작성한다.
고등학생이 이해할 수 있도록 통계 용어(평균·표준편차·상관 등)에는 짧은 설명을 붙인다.
 
 
[Task]
우리 학교 극지식물 개체별 생육 차이 분석 대시보드 제작
📁 파일 구조:
polar-plant-dashboard/
├── main.py
└── requirements.txt
 
📎 함께 첨부한 우리 학교 CSV 2개(환경·생육)의 실제 열 이름을 먼저 확인하고, 그 파일을 그대로 올려도 오류 없이 동작하도록 작성
 
📊 데이터 정보:
환경 데이터 (CSV 1개): OO고_환경데이터.csv
* 학교마다 열 이름이 다름 ⚠️
   - 형식 A: time, temperature, humidity, ph, ec, water_temp, co2
   - 형식 B: categories, 온도, 습도, EC, PH
* 시간 열 값도 학교마다 다름: '2026-07-15 06:00:00' 또는 '20260715_0'(날짜_시각)
* ph·ec·co2가 없는 학교도 있고, '비고' 같은 글자 열이 있는 학교도 있음
* 센서가 측정하지 못한 빈 기간이 있을 수 있음
생육 결과 데이터 (CSV 1개): OO고_생육결과데이터.csv
* 개체 수: 학교마다 다름 (약 20~90개)
* 열 이름에 단위·띄어쓰기가 붙어 있음 ⚠️: 개체번호, 잎 수(장), 지상부 길이(mm), 지하부길이(mm), 생중량(g), 지상부질량(g), 지하부질량(g)
* 생중량(g) 열이 없는 학교도 있음 → 지상부 질량 + 지하부 질량으로 계산
* 개체번호는 숫자(1, 2, …) 또는 글자(A1, A2, …)
* ✅ 우리 학교 개체끼리 비교 (개체번호는 분석 항목에서 제외)
핵심 분석:
1. 개체별 생중량 분포와 차이 (평균·표준편차·CV)
2. 잎 수·지상부 길이와 생중량의 관계 (상관계수·산점도)
3. 생중량 상위 25% vs 하위 25% 개체 비교
 
[Format]
앱 구조:
* 제목: 🌱 우리 학교 극지식물 개체별 생육 차이 분석
* 레이아웃: wide mode
* 사이드바: CSV 업로드 2개 (환경 데이터·생육 결과 데이터) + 생육 측정 항목 선택
3개 탭:
Tab 1 "📖 실험 개요"
* 연구 배경 및 목적
* 데이터 요약 표 (개체 수, 측정 기간, 측정 항목)
* 주요 지표 카드 4개: 총 개체수, 평균 온도, 평균 습도, 평균 생중량
Tab 2 "🌡️ 환경 데이터"
* 환경 요약 (평균·최소·최대 표)
* 날짜별 시계열 (일별 평균 꺾은선)
   * 온도 변화
   * 습도 변화
   * pH·EC 변화 (열이 있을 때만)
* expander: 환경 데이터 원본 테이블 + CSV 다운로드
Tab 3 "📊 생육 결과"
* 🥇 핵심 결과 카드: 평균 생중량과 최대·최소 개체
* 개체별 생육 비교 (막대 그래프)
   * 평균 생중량 (⭐ 가장 중요)
   * 평균 잎 수
   * 평균 지상부 길이
   * 평균 지하부 길이
* 생중량 분포 (박스플롯 또는 바이올린 플롯)
* 상관관계 분석 (산점도 2개 + 추세선)
   * 잎 수 vs 생중량
   * 지상부 길이 vs 생중량
* expander: 생육 데이터 원본 + CSV 다운로드
 
 
[Constraints]
✅ 필수 1: CSV 업로드 (매우 중요!)
* st.sidebar.file_uploader 2개 (환경 CSV · 생육 CSV)
* utf-8-sig로 읽고 실패하면 cp949로 다시 읽기
* 업로드 전에는 st.info()로 안내하고, 파일이 없는 탭은 if/else로 나머지 내용을 건너뛰기 (탭 안에서 st.stop() 사용 금지 → 다른 탭까지 멈춤)
* 한 파일만 올려도 해당 탭은 동작
* 학교명은 업로드한 파일명 앞부분에서 읽기 (학교명 하드코딩 금지)
예시 코드:
env_file = st.sidebar.file_uploader("환경 CSV", type="csv")
growth_file = st.sidebar.file_uploader("생육 CSV", type="csv")
 
✅ 필수 2: 열 이름 표준화 (KeyError 방지, 가장 중요!)
* 아래 std_cols 함수를 그대로 넣고, CSV를 읽은 직후 두 데이터 모두에 반드시 적용
* 그 다음부터는 표준 이름만 사용: time, temperature, humidity, ph, ec / 개체번호, 잎 수, 지상부 길이, 지하부 길이, 생중량, 지상부 질량, 지하부 질량
* 열을 꺼내 쓰기 전에 항상 `if "temperature" in df.columns:`처럼 있는지 확인하고, 없으면 그 그래프·카드만 st.info()로 건너뛰기
예시 코드:
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
            num = pd.to_numeric(df[c].astype(str).str.replace(",", "").str.extract(r"(-?\d+\.?\d*)")[0], errors="coerce")
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
            parsed[bad] = pd.to_datetime(parts[0], format="%Y%m%d") + pd.to_timedelta(parts[1].astype(int), unit="h")
        df["time"] = parsed
    return df
 
✅ 필수 3: 어떤 학교 CSV가 와도 에러 화면이 나오지 않게 (안전장치)
* with tab1:, with tab2:, with tab3: 안의 내용 전체를 각각 try: ~ except Exception as e: 로 감싸고, except에서는 st.warning(f"⚠️ 이 부분은 데이터 형식 때문에 표시하지 못했어요: {e}")만 출력
* 평균·최대·최소·idxmax·상관계수 계산 전에 dropna()로 빈 값을 빼고, 남은 값이 없거나 2개 미만이면 st.info()로 건너뛰기
* 숫자 계산과 그래프에는 std_cols를 거친 숫자 열만 사용 (글자 열은 계산에 넣지 않기)
* 열 이름이 하나도 맞지 않는 엉뚱한 파일이 올라와도 앱이 멈추지 않고 안내 문구만 보여주기
 
3. Plotly 서브플롯 (NameError 방지)
반드시 import 포함
from plotly.subplots import make_subplots
 
4. 추세선 (ModuleNotFoundError 방지)
* px.scatter의 trendline 인자는 statsmodels가 필요해서 오류 발생 → 사용 금지
* 추세선은 np.polyfit(x, y, 1)로 기울기·절편을 구해 go.Scatter(mode="lines")로 직접 추가
* 상관계수·추세선 계산 전에 dropna()로 빈 값 제거, 값이 2개 미만이면 건너뛰기
 
5. CSV 다운로드 (한글 깨짐 방지)
* df.to_csv(index=False).encode('utf-8-sig')로 만들어 st.download_button에 전달
 
6. 한글 폰트 (깨짐 방지)
Streamlit CSS
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
   font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)
Plotly
fig.update_layout(
   font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
)
 
7. 성능 & 안정성
* 모든 데이터 로딩 함수에 @st.cache_data
* 로딩 중 st.spinner()
* 데이터 없을 경우 st.error()로 명확히 안내
* 그래프·표는 st.plotly_chart(fig, width="stretch"), st.dataframe(df, width="stretch")로 표시
* ⚠️ fig.update_layout()에는 width를 넣지 않기 (width="stretch"는 st.plotly_chart에만 사용, 그래프 안에 넣으면 ValueError)
 
❌ 금지 사항:
* "여기에 코드 추가" 같은 플레이스홀더
* 학교명·파일명·열 이름 하드코딩 (std_cols로 표준화한 이름만 사용)
* df["temperature"]처럼 열이 있는지 확인하지 않고 바로 꺼내 쓰기
* to_excel()·openpyxl 사용 (CSV만 사용)
* import 누락된 상태의 make_subplots
* 탭 안에서 st.stop() 사용 (다른 탭까지 빈 화면이 됨)
* 개체번호를 분석 항목(그래프·상관·예측)에 넣기
* px.scatter의 trendline 인자 사용
* use_container_width 사용 (대신 width="stretch")
* try/except 없이 탭 내용을 바로 실행하기
* fig.update_layout(width="stretch") 처럼 그래프 설정에 글자 width 넣기
* px.bar·px.box·px.histogram에 markers 인자 넣기 (px.line에만 사용 가능)
* 리스트를 여러 개 + 로 이어 붙여 표 만들기 (괄호 짝이 틀려 SyntaxError) → rows.append()로 한 줄씩 추가
* 개체번호로 merge·isin 하기 (학교마다 숫자/글자가 달라 오류) → 한 DataFrame 안에서 정렬·필터로 계산
 
 
✅ 기타:
- @st.cache_data로 데이터 로딩 최적화
- 에러 발생 시 st.error()로 명확히 안내
- 로딩 중 st.spinner() 표시
- 개체별 생중량 비교 시 상위·하위 개체 강조
- 그래프에 쓰는 열이 없으면 그 그래프만 st.info()로 건너뛰기
 
 
[Output]
 
 
1. main.py
- 완성된 전체 코드
- 복사-붙여넣기 후 즉시 실행 가능
- 모든 그래프, 버튼, 다운로드 실제 작동
- 답변은 main.py 전체 코드(```python 코드 블록 1개)와 requirements.txt(``` 코드 블록 1개)만 출력하고, 설명은 3줄 이내
- 출력 전에 괄호 짝과 들여쓰기를 한 번 더 확인 (SyntaxError 없이)
- 추가 질문 없이 바로 코드 작성 (CSV가 첨부되지 않았으면 위 데이터 정보 기준으로 작성)
 
