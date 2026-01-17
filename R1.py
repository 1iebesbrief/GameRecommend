import streamlit as st
from google import genai # 使用 2026 新版 SDK
from fpdf import FPDF
import json

# --- 1. 初始化 Gemini Client (2026 标准语法) ---
# 请确保此处填入的是你新生成的有效 API Key
API_KEY = "AIzaSyAB-tPUNus0WOVJ7SptCV0wovZVgns_VrQ" 
client = genai.Client(api_key=API_KEY)

# --- Page Configuration ---
st.set_page_config(page_title="Indie Game Design Assistant", layout="wide")

# --- Initialize Session State ---
if 'genre_pool' not in st.session_state:
    st.session_state.genre_pool = []
    st.session_state.demo_pool = []
    st.session_state.visible_genres = []
    st.session_state.visible_demos = []
    st.session_state.selected_details = None

# --- Helper Function: PDF Generation ---
def create_pdf(content):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for key, value in content.items():
        display_key = key.replace("_", " ").title()
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, txt=f"{display_key}:", ln=True)
        pdf.set_font("Arial", size=11)
        pdf.multi_cell(0, 8, txt=f"{value}\n")
    return pdf.output(dest='S').encode('latin-1')

# --- Dialog Logic ---
@st.dialog("Game Genre Preview")
def show_preview_modal(genre_item):
    st.write(f"**Recommendation Reason**: {genre_item['reason']}")
    st.write(f"**Estimated Development Period**: {genre_item['est_time']}")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("❌ Not Interested"):
            st.session_state.genre_pool.remove(genre_item)
            update_visible_items()
            st.rerun()
    with col2:
        if st.button("✅ Interested"):
            st.session_state.selected_details = genre_item
            st.rerun()

def update_visible_items():
    st.session_state.visible_genres = st.session_state.genre_pool[:3]
    st.session_state.visible_demos = st.session_state.demo_pool[:2]

# --- Sidebar Inputs ---
st.sidebar.title("🎮 Project Constraints")
outline = st.sidebar.text_area("Story Outline", placeholder="Enter your game concept here...", height=150)
team = st.sidebar.slider("Team Size (People)", 1, 10, 2)
time_limit = st.sidebar.slider("Duration (Months)", 1, 6, 3)
budget = st.sidebar.slider("Budget ($)", 0, 50000, 5000)

if st.sidebar.button("Generate Initial Proposal"):
    prompt = f"""
    As a professional game producer, analyze this project:
    Outline: {outline}
    Team Size: {team} people
    Time Limit: {time_limit} months
    Budget: ${budget}

    Return a JSON with 5 recommended game genres and 5 demo directions.
    JSON structure: 
    {{ 
      "genres": [
        {{ "name": "Genre", "reason": "..", "est_time": "..", 
           "details": {{ "optimized_outline": "..", "protagonist": "..", "storyline": "..", "blurb": "..", "examples": ".." }} 
        }}
      ], 
      "demos": [ {{ "name": "..", "reason": "..", "est_time": ".." }} ] 
    }}
    """
    
    try:
        with st.spinner("AI is analyzing (Using Gemini 1.5 Flash)..."):
            # --- 2. 使用新版生成调用方法 ---
            response = client.models.generate_content(
                model='models/gemini-2.5-flash', 
                contents=prompt,
                config={'response_mime_type': 'application/json'} # 关键：强制JSON格式
            )
            
            # --- 3. 解析响应内容 ---
            data = json.loads(response.text)
            st.session_state.genre_pool = data['genres']
            st.session_state.demo_pool = data['demos']
            update_visible_items()
            st.session_state.selected_details = None
            st.success("Proposal Generated Successfully!")
    except Exception as e:
        st.error(f"Failed to fetch recommendations: {e}")

# --- Main Interface Display ---
st.title("🕹️ Indie Game Strategy Assistant")

if st.session_state.selected_details:
    item = st.session_state.selected_details
    st.header(f"🔍 Deep Analysis: {item['name']}")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("📖 Narrative & Gameplay")
        st.write(f"**Optimized Outline**: {item['details']['optimized_outline']}")
        st.write(f"**Protagonist**: {item['details']['protagonist']}")
        st.write(f"**Core Storyline**: {item['details']['storyline']}")
    with col_b:
        st.subheader("📢 Marketing & References")
        st.write(f"**Store Page Blurb**: {item['details']['blurb']}")
        st.write(f"**Classic Examples**: {item['details']['examples']}")
        
        full_info = {"Genre": item['name'], "Reason": item['reason'], **item['details']}
        pdf_bytes = create_pdf(full_info)
        st.download_button("📥 Download PDF Report", data=pdf_bytes, file_name="game_plan.pdf")
    
    if st.button("⬅️ Back to Recommendations"):
        st.session_state.selected_details = None
        st.rerun()
else:
    if st.session_state.visible_genres:
        st.subheader("💡 Recommended Game Genres")
        cols = st.columns(3)
        for idx, genre in enumerate(st.session_state.visible_genres):
            with cols[idx]:
                st.info(f"**{genre['name']}**")
                if st.button("View Preview", key=f"g_{idx}"):
                    show_preview_modal(genre)

        st.divider()
        st.subheader("🚀 Recommended Demo Directions")
        d_cols = st.columns(2)
        for idx, demo in enumerate(st.session_state.visible_demos):
            with d_cols[idx % 2]:
                st.success(f"**{demo['name']}**")
                st.write(demo['reason'])