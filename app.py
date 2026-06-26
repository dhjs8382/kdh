import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import os
import time
# 💡 Gemini API 및 멀티모달 분석을 위한 라이브러리 추가
from google import genai
from PIL import Image

# 0. 페이지 레이아웃 및 디자인 설정 (확정된 타이틀 적용)
st.set_page_config(page_title="영주시 노후 주택 진단 및 주거환경 개선 가이드", layout="wide")

st.title("🏛️ 영주시 노후 주택 진단 및 주거환경 개선 가이드")
st.caption("AI와 GIS 공공데이터를 융합한 실시간 주택 진단 및 의사결정 지원 플랫폼")
st.markdown("---")

base_path = "./"

# 💡 안전한 API 키 로드 (Streamlit Secrets 기능 사용)
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=GEMINI_API_KEY)
except Exception:
    st.error("🔒 Streamlit Secrets에 'GEMINI_API_KEY'가 설정되지 않았거나 올바르지 않습니다.")
    GEMINI_API_KEY = None
    client = None

# 1. 🗄️ 실제 CSV 데이터 로드 및 법정동 통합
@st.cache_data
def load_actual_data():
    csv_path = os.path.join(base_path, '영주시_동별_리모델링_순위.csv')
    try:
        data = pd.read_csv(csv_path, encoding='cp949')
    except:
        data = pd.read_csv(csv_path, encoding='utf-8')

    data['분석구역'] = data['분석구역'].str.strip()

    def to_legal_dong(name):
        if '가흥' in name: return '가흥동'
        if '영주' in name: return '영주동'
        if '휴천' in name: return '휴천동'
        return name

    data['통합동명'] = data['분석구역'].apply(to_legal_dong)

    # 6가지 실제 데이터 컬럼만 사용
    grouped = data.groupby('통합동명').agg({
        '최종_그린리모델링_시급도점수': 'mean',
        '시급도_원점수': 'mean',
        '빈집_개수': 'sum',
        '노인복지시설_개수': 'sum',
        '녹지시설_개_수' if '녹지시설_개_수' in data.columns else '녹지시설_개수': 'sum',
        '총_공동주택_세대수': 'sum'
    }).reset_index()
    
    # 💡 데이터 전처리 및 로직 전파 과정에서 발생한 '대동', '영동' 최종 강제 제거
    grouped = grouped[~grouped['통합동명'].isin(['대동', '영동'])].reset_index(drop=True)

    return grouped

df_actual = load_actual_data()

# 2. 사이드바 - 지리 구역 설정
st.sidebar.header("📍 1단계: 진단 지역 설정")
dong_list = df_actual['통합동명'].unique().tolist()
selected_dong = st.sidebar.selectbox("건축물이 위치한 영주시 읍면동을 고르세요:", dong_list)
row = df_actual[df_actual['통합동명'] == selected_dong].iloc[0]

# 3. 메인 화면 - 사진 업로드 세션
st.subheader("📷 2단계: 건축물 현장 외관 사진 업로드 및 AI 분석")
st.write("현장에서 직접 촬영하거나 수집한 노후 건축물의 외벽 전경 사진을 올려주세요. Gemini 멀티모달 AI가 이미지의 노후 상태를 정밀 진단합니다.")

uploaded_file = st.file_uploader("여기를 클릭하거나 사진 파일을 드래그하여 업로드하세요 (JPG, PNG)", type=["jpg", "png", "jpeg"])

st.markdown("---")

if uploaded_file is None:
    st.info("💡 위 화면에 진단할 건축물 사진을 업로드해 주세요.")
else:
    st.success("🎉 이미지 업로드 완료! Gemini 비전 AI 및 GIS 공공데이터 융합 분석을 시작합니다.")

    col1, col2 = st.columns([5, 5])

    # [왼쪽 영역] Gemini 멀티모달 AI 시각 분석 결과 출력
    with col1:
        st.subheader("👁️ Gemini AI 실시간 외관 정성 평가")
        img = Image.open(uploaded_file)
        st.image(img, caption="현장 수집 건축물 외관", use_column_width=True)

        if client is None:
            st.warning("⚠️ API 클라이언트가 초기화되지 않아 수치 시뮬레이션으로 대체합니다. Secrets를 확인해 주세요.")
            vision_score = 75.0
            ai_report = "API 키가 설정되지 않아 실시간 AI 리포트를 출력할 수 없습니다."
        else:
            with st.spinner("🔄 Gemini AI가 주택 사진을 정밀 분석 중입니다..."):
                try:
                    # 💡 [프롬프트 설계] Gemini에게 사진 분석과 더불어 공공데이터(GIS) 컨텍스트를 함께 제공
                    dong_info_text = f"""
                    [선택 구역 GIS 데이터]
                    - 행정 구역: 경상북도 영주시 {selected_dong}
                    - 관내 빈집 개수: {int(row['빈집_개수'])}개
                    - 노인복지시설 수: {int(row['노인복지시설_개수'])}개소
                    - 녹지시설 현황: {int(row['녹지시설_개수'])}개소
                    - 총 공동주택 규모: {int(row['총_공동주택_세대수']):,} 세대
                    """

                    prompt = f"""
                    당신은 건축공학 및 도시재생 전문가AI 입니다. 첨부된 노후 주택 사진과 해당 건물이 위치한 지역의 GIS 공공데이터 정보를 종합 분석하여 [주거환경 개선 맞춤형 가이드 리포트]를 7줄~13줄 사이로 작성해 주세요.
                    
                    ---
                    {dong_info_text}
                    ---
                    
                    [작성 필수 항목]
                    1. **건축물 외관 노후도 분석**: 사진을 바탕으로 외벽 균열, 도장 벗겨짐, 창호 노후도 상태를 공학적으로 예리하게 평가해 주세요.
                    2. **종합 노후도 점수**: 외관 상태를 종합하여 0~100점 사이의 점수를 산정하고 그 이유를 알려주세요.
                    3. **지역 데이터 연계 융합 진단**: 제공된 동네의 GIS 데이터(빈집, 노인시설, 녹지)와 이 주택의 상태를 연결하여, 이 건물이 지역 재생 관점에서 어떤 포지션인지 분석해 주세요.
                    4. **맞춤형 주거환경 개선 가이드**: 진단 결과를 바탕으로 이 건물에 가장 시급하고 효과적인 '친환경 단열/차열 건축 공법(쿨루프, 외단열 등)'과 '공간 활용 방안'을 구체적으로 조언해 주세요.
                    
                    """

                    # Gemini 2.5 Flash 호출
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=[img, prompt]
                    )
                    ai_report = response.text
                    
                except Exception as e:
                    st.error(f"❌ Gemini API 호출 중 오류가 발생했습니다: {e}")
                    ai_report = "오류가 발생하여 리포트를 생성하지 못했습니다."

        # 메인 영역에 생성된 AI 리포트 표출
        st.markdown("### 🤖 Gemini AI 분석 리포트")
        st.markdown(ai_report)

    # [오른쪽 영역] 정량 GIS 데이터 표출 (기존 대시보드 유지)
    with col2:
        st.subheader(f"📊 [{selected_dong}] GIS 공공데이터 현황")

        st.metric(label="🔥 최종 주거환경 개선 시급도 점수", value=f"{row['최종_그린리모델링_시급도점수']:.1f} / 100점")

        m_c1, m_c2 = st.columns(2)
        m_c1.metric(label="📉 지역 시급도 원점수", value=f"{row['시급도_원점수']:.1f}점")
        m_c2.metric(label="🏢 총 공동주택 세대수", value=f"{int(row['총_공동주택_세대수']):,} 세대")

        m_c3, m_c4, m_c5 = st.columns(3)
        m_c3.metric(label="📦 빈집 수", value=f"{int(row['빈집_개수'])}개")
        m_c4.metric(label="👵 노인시설", value=f"{int(row['노인복지시설_개수'])}개")
        m_c5.metric(label="🌳 녹지시설", value=f"{int(row['녹지시설_개수'])}개")

        st.markdown("#### 🧮 데이터 융합 프로세스 안내")
        st.info(f"""
        * **정성 데이터:** Gemini Vision AI 실시간 주택 크랙 및 노후도 시각 분석
        * **정량 데이터:** 영주시 GIS 공공 통계 데이터셋 (선택: {selected_dong})
        * **종합 결론:** 위 두 핵심 엔진의 분석 결과가 상단과 좌측 'AI 분석 리포트'에 통합 반영되어 도출됩니다.
        """)

    st.markdown("---")

    # 5. 하단 영역 - 지도 레이아웃 배치
    st.subheader("🗺️ 영주시 읍면동별 거시 지표 분석")
    st.caption("영주시 전체의 주거환경 취약도 및 개선 시급도 분포 현황")

    html_path = os.path.join(base_path, '영주시_새_읍면동_최종지도.html')
    if os.path.exists(html_path):
        with open(html_path, 'r', encoding='utf-8') as f:
            html_data = f.read()
        components.html(html_data, height=550, scrolling=True)
    else:
        st.warning("⚠️ '영주시_새_읍면동_최종지도.html' 파일이 배치되어야 지도가 표시됩니다.")