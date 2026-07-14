import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import os
import time
from google import genai
from PIL import Image

# 0. 페이지 레이아웃 및 디자인
st.set_page_config(page_title="영주시 노후 주택 진단 플랫폼", layout="wide")

st.title("🏛️ 영주시 노후 주택 진단 및 주거환경 개선 가이드")
st.caption("AI와 GIS 공공데이터를 융합한 실시간 주택 진단 및 의사결정 지원 플랫폼")
st.markdown("---")

base_path = "./"

# API 키 로드
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=GEMINI_API_KEY)
except Exception:
    st.error("🔒 Streamlit Secrets에 'GEMINI_API_KEY'가 설정되지 않았거나 올바르지 않습니다.")
    GEMINI_API_KEY = None
    client = None

# 1. 실제 CSV 데이터 로드 및 법정동 통합
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

    grouped = data.groupby('통합동명').agg({
        '최종_그린리모델링_시급도점수': 'mean',
        '시급도_원점수': 'mean',
        '빈집_개수': 'sum',
        '노인복지시설_개수': 'sum',
        '녹지시설_개_수' if '녹지시설_개_수' in data.columns else '녹지시설_개수': 'sum',
        '총_공동주택_세대수': 'sum'
    }).reset_index()
    
    grouped = grouped[~grouped['통합동명'].isin(['대동', '영동'])].reset_index(drop=True)

    # [추가] 지역 시급도 원점수를 전체 지역 데이터를 기준으로 0~100점 사이로 변환 (Min-Max Scaling)
    min_val = grouped['시급도_원점수'].min()
    max_val = grouped['시급도_원점수'].max()
    
    # 만약 모든 원점수가 같다면 분모가 0이 되는 것을 방지하기 위한 예외 처리
    if max_val != min_val:
        grouped['시급도_변환점수'] = ((grouped['시급도_원점수'] - min_val) / (max_val - min_val)) * 100
    else:
        grouped['시급도_변환점수'] = 50.0  # 모두 같으면 중간값인 50점 부여

    return grouped

df_actual = load_actual_data()

# 2. 사이드바 구역 설정
st.sidebar.header("📍 빠른 지역 설정")
dong_list = df_actual['통합동명'].unique().tolist()
selected_dong = st.sidebar.selectbox("건축물이 위치한 영주시 읍면동을 고르세요:", dong_list)
row = df_actual[df_actual['통합동명'] == selected_dong].iloc[0]

# 3. 메인 화면 사진 업로드
st.subheader("📷 건축물 현장 외관 사진 업로드 및 AI 분석")
uploaded_file = st.file_uploader("여기를 클릭하거나 사진 파일을 드래그하여 업로드하세요 (JPG, PNG)", type=["jpg", "png", "jpeg"])

st.markdown("---")

if uploaded_file is None:
    st.info("💡 위 화면에 진단할 건축물 사진을 업로드해 주세요.")
else:
    st.success("🎉 이미지 업로드 완료")

    col1, col2 = st.columns([5, 5])

    # [오른쪽 영역] 정량 데이터 창고 준비
    # 변환된 지역 시급도 점수 가져오기
    regional_score = row['시급도_변환점수']

    # [왼쪽 영역] AI 시각 분석 결과 출력
    with col1:
        st.subheader("🤖 AI 외관 정성 평가")
        img = Image.open(uploaded_file)
        st.image(img, caption="현장 수집 건축물 외관", use_column_width=True)

        if client is None:
            vision_score = 75.0
            ai_report = "API 키가 설정되지 않아 실시간 AI 리포트를 출력할 수 없습니다."
        else:
            with st.spinner("🔄 AI가 주택 사진을 정밀 분석 중입니다..."):
                try:
                    dong_info_text = f"""
                    [선택 구역 GIS 데이터]
                    - 행정 구역: 경상북도 영주시 {selected_dong}
                    - 변환된 지역 시급도 점수(정량): {regional_score:.1f} / 100점
                    - 관내 빈집 개수: {int(row['빈집_개수'])}개
                    - 노인복지시설 수: {int(row['노인복지시설_개수'])}개소
                    - 녹지시설 현황: {int(row['녹지시설_개수'])}개소
                    """

                    prompt = f"""
                    당신은 건축공학 및 도시재생 전문가AI 입니다. 첨부된 노후 주택 사진과 해당 건물이 위치한 지역의 GIS 공공데이터 정보를 종합 분석하여 [주거환경 개선 맞춤형 가이드 리포트]를 7줄~15줄 사이로 작성해 주세요.
                    
                    ---
                    {dong_info_text}
                    ---
                    
                    [작성 필수 항목]
                    1. **건축물 외관 노후도 분석**: 사진을 바탕으로 외벽 균열, 도장 벗겨짐, 창호 노후도 상태를 공학적으로 예리하게 평가해 주세요.
                    2. **종합 외관 노후도 점수 (정성 점수)**: 오직 '사진 속 상태'만을 기준으로 삼아 **반드시 0점~100점 사이의 정수 점수**를 명시하는데 안좋아 보일수록 100점에 가깝게 상태가 괜찮아 보일수록 0점에 가깝게 명시해주시고 그 명확한 산정 기준을 설명해 주세요. (예: 외관 노후도 점수: XX점)
                    3. **지역 데이터 연계 융합 진단**: 제공된 동네의 GIS 데이터와 이 주택의 상태를 연결하여 분석해 주세요.
                    4. **맞춤형 주거환경 개선 가이드**: 이 건물과 지역 특성에 맞는 맞춤형 단열/차열 건축 공법(쿨루프, 외단열 등)을 조언해 주시고
                    콘크리트 탈락 및 철근 노출 보수 현상이 나타날경우 "CROS 방청 및 단면 복구 시스템을 적용하여 노출된 철근의 부동태 피막을 재생하고 알칼리성을 회복시킨 뒤 고강도 모르타르로 단면을 복구할수있습니다"라는 솔루션을 넣어 조언해주시고
                    외벽 누수 현상이 나타날경우 "외벽 타일 누수는 줄눈 천공 후 스테인리스 핀 고정과 고점도 에폭시 수지 주입으로 구조적 결함을 해결하고, 노화된 실리콘을 제거한 자리에 고탄성 폴리우레탄 실란트를 채워 균열을 메우며, 외벽 건조 후 침투성 발수제를 2회 이상 전면 도포하여 미세 기공을 통한 빗물 흡수를 차단함으로써 해결할 수 있습니다."라는 솔루션을 넣어 조언해 주세요.
                    
                    **[중요 - 시스템 파싱 규칙]**
                    텍스트의 맨 마지막 줄에 다른 문장 없이 오직 아래 형식으로만 종합 점수를 한 줄 추가해 주세요. (코드가 이 값을 읽어갑니다)
                    SCORE: 계산한정수점수
                    """

                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=[img, prompt]
                    )
                    ai_report = response.text
                    
                    # AI 점수 정밀 추출 알고리즘 블록
                    vision_score = 70.0  # 기본 방어값
                    try:
                        import re
                        match = re.search(r'SCORE:\s*(\d+)', ai_report)
                        if match:
                            vision_score = float(match.group(1))
                        else:
                            for line in ai_report.split('\n'):
                                if '종합 외관 노후도 점수' in line or '외관 노후도 점수' in line:
                                    nums = re.findall(r'\d+', line)
                                    if nums:
                                        temp_score = float(nums[0])
                                        if 0 <= temp_score <= 100:
                                            vision_score = temp_score
                                            break
                    except Exception:
                        vision_score = 70.0

                except Exception as e:
                    st.error(f"⚠️ API 호출 중 오류가 발생했습니다: {e}")
                    vision_score = 70.0
                    ai_report = "오류가 발생하여 리포트를 생성하지 못했습니다."

        st.markdown("### 📋 AI 분석 리포트")
        st.markdown(ai_report)

    # 💡 가중치 결합 계산 로직 적용 (발표 수식과 대시보드 동기화 보장)
    final_combined_score = (vision_score * 0.8) + (regional_score * 0.2)

    # [오른쪽 영역] 정량 GIS 데이터 및 최종 결합 점수 표출
    with col2:
        st.subheader(f"📊 [{selected_dong}] GIS 공공데이터 및 통합 진단")

        # 연산된 최신화된 최종 시급도 점수 마크
        st.metric(label="🔥 최종 주거환경 개선 우선도 점수 (AI 80% + 지역 20%)", value=f"{final_combined_score:.1f} / 100점")

        m_c1, m_c2 = st.columns(2)
        m_c1.metric(label="📉 100점 환산 지역 우선도 점수", value=f"{regional_score:.1f}점")
        m_c2.metric(label="🏢 총 공동주택 세대수", value=f"{int(row['총_공동주택_세대수']):,} 세대")

        m_c3, m_c4, m_c5 = st.columns(3)
        m_c3.metric(label="📦 빈집 수", value=f"{int(row['빈집_개수'])}개")
        m_c4.metric(label="👵 노인시설", value=f"{int(row['노인복지시설_개수'])}개")
        m_c5.metric(label="🌳 녹지시설", value=f"{int(row['녹지시설_개수'])}개")

        st.markdown("#### 🧮 최종 점수 산출 기준")
        st.info(f"""
        * **정성 지표 (80%):** Gemini Vision AI가 사진을 판독하여 채점한 주택 외관 노후 점수 (**{vision_score:.1f}점**)
        * **정량 지표 (20%):** 영주시 전체 읍면동 통계를 기반으로 100점 만점으로 환산한 지역 취약도 점수 (**{regional_score:.1f}점**)
        * **최종 연산 산식:** `({vision_score:.1f} × 0.8) + ({regional_score:.1f} × 0.2) = {final_combined_score:.1f}점`
        """)

    st.markdown("---")

    # 5. 하단 영역 지도 레이아웃 배치
    st.subheader("🗺️ 영주시 읍면동별 거시 지표")
    st.caption("영주시 전체의 주거환경 취약도 및 개선 시급도 분포 현황")

    html_path = os.path.join(base_path, '영주시_새_읍면동_최종지도.html')
    if os.path.exists(html_path):
        with open(html_path, 'r', encoding='utf-8') as f:
            html_data = f.read()
        components.html(html_data, height=550, scrolling=True)
    else:
        st.warning("⚠️ '영주시_새_읍면동_최종지도.html' 파일이 배치되어야 지도가 표시됩니다.")
