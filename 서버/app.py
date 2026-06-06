import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import os

# 페이지 기본 설정 (와이드 모드)
st.set_page_config(page_title="영주시 그린리모델링 AI 진단", layout="wide")

st.title("🏢 영주시 그린리모델링 맞춤형 AI 진단 솔루션")
st.markdown("---")

# 💡 현재 폴더 기준 (로컬 실행 및 깃허브 배포 공용)
base_path = "./" 

# 1. 데이터 불러오기 및 법정동 통합 전처리
try:
    df = pd.read_csv(os.path.join(base_path, '영주시_동별_리모델링_순위.csv'), encoding='cp949')
except:
    try:
        df = pd.read_csv(os.path.join(base_path, '영주시_동별_리모델링_순위.csv'), encoding='utf-8')
    except:
        # 파일이 없을 때를 대비한 예외용 백업 데이터
        df = pd.DataFrame({
            '분석구역': ['가흥1동', '가흥2동', '영주1동', '영주2동', '풍기읍', '하망동'],
            '최종_그린리모델링_시급도점수': [85.5, 72.3, 78.0, 65.2, 78.4, 91.2],
            '빈집_개수': [8, 4, 5, 2, 12, 15],
            '노인복지시설_개수': [4, 2, 3, 1, 6, 5]
        })

df['분석구역'] = df['분석구역'].str.strip()

# 💡 지도와 완벽 매칭을 위해 스트림릿 사이트에서도 가흥/영주/휴천을 하나로 묶어 표현
def merge_to_legal_dong(name):
    if '가흥' in name: return '가흥동'
    if '영주' in name: return '영주동'
    if '휴천' in name: return '휴천동'
    return name

df['통합동명'] = df['분석구역'].apply(merge_to_legal_dong)

# 그룹화하여 평균 및 합산
df_grouped = df.groupby('통합동명').agg({
    '최종_그린리모델링_시급도점수': 'mean',
    '빈집_개수': 'sum',
    '노인복지시설_개수': 'sum'
}).reset_index()

# 2. 사이드바 인터페이스 (통합된 법정동 이름으로 표출)
st.sidebar.header("🔍 분석 구역 선택")
dong_list = df_grouped['통합동명'].unique().tolist()
selected_dong = st.sidebar.selectbox("영주시 읍면동을 선택하세요:", dong_list)

# 선택된 동네 데이터 매칭
row = df_grouped[df_grouped['통합동명'] == selected_dong].iloc[0]
score = row['최종_그린리모델링_시급도점수']
vacant = row['빈집_개_수'] if '빈집_개_수' in row else row['빈집_개수']
senior = row['노인복지시설_개_수'] if '노인복지시설_개_수' in row else row['노인복지시설_개수']

# 3. 메인 화면 레이아웃 분할 (좌측: AI 맞춤 진단서 / 우측: 완벽한 지도)
col1, col2 = st.columns([4, 6])

with col1:
    st.subheader(f"📢 [{selected_dong}] AI 맞춤형 진단 결과")
    
    st.metric(label="🔥 통합 그린리모델링 시급도 점수", value=f"{score:.1f} / 100점")
    
    sub_col1, sub_col2 = st.columns(2)
    sub_col1.metric(label="📦 지역 내 총 빈집 현황", value=f"{int(vacant)}개")
    sub_col2.metric(label="👵 노인복지시설 총 개수", value=f"{int(senior)}개")
    
    st.markdown("### 💡 AI 핵심 제안 사업")
    if score >= 75 and vacant >= 5:
        st.error("**[최우선 정비 구역 제안]**\n\n해당 통합 구역은 노후 가옥 및 빈집 비율이 높습니다. 고효율 단열재와 창호를 도입하여 취약계층을 위한 공공 임대 주택이나 마을 복지 쉼터로 전환하는 그린인프라 사업을 강력히 제안합니다.")
    elif senior >= 4:
        st.warning("**[에너지 복지 집중 강화]**\n\n어르신들의 복지시설 이용률이 높은 지역입니다. 여름철 폭염과 겨울철 한파에 대비해 시설 전체에 고효율 열차단 옥상 쿨루프 시공 및 신재생 태양광 패널 설치 사업을 제안합니다.")
    else:
        st.success("**[소규모 민간 주택 이자 지원]**\n\n전반적인 정비 상태가 양호한 지역입니다. 대규모 공공 개발보다는 민간 노후 주택을 대상으로 정부의 '그린리모델링 공사비 이자 지원 사업'을 집중 홍보하고 지원금을 매칭하는 방식을 제안합니다.")

with col2:
    st.subheader("🗺️ 영주시 공간 시각화 분석 지도")
    
    # 코랩에서 완벽하게 대성공해서 구워진 HTML 지도 연동
    html_path = os.path.join(base_path, '영주시_새_읍면동_최종지도.html')
    
    if os.path.exists(html_path):
        with open(html_path, 'r', encoding='utf-8') as f:
            html_data = f.read()
        components.html(html_data, height=580, scrolling=True)
    else:
        st.info("💡 폴더 내에 '영주시_새_읍면동_최종지도.html' 파일이 배치되면 지도가 자동으로 렌더링됩니다.")