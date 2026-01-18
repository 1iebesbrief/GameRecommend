import streamlit as st
import json
import base64
import requests
import time
import io
from fpdf import FPDF
from google import genai
from PIL import Image

# --- 1. Configuration & Initialization ---
API_KEY = "AIzaSyCOkQiX2q-4RJyvivdQmPyK5X7BejXKlPo" # Environment automatically injects this
client = genai.Client(api_key=API_KEY)
APP_ID = "indie-game-studio-v2"

st.set_page_config(page_title="Indie Game Design Studio Pro", layout="wide", initial_sidebar_state="expanded")

# --- 2. Custom CSS Styles (Gamified UI) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&family=JetBrains+Mono&display=swap');
    
    .stApp {
        background-color: #0f172a;
        color: #f8fafc;
        font-family: 'Inter', sans-serif;
    }
    
    .genre-card {
        border-radius: 16px;
        padding: 20px;
        background: rgba(30, 41, 59, 0.7);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        margin-bottom: 20px;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        height: 100%;
        position: relative;
        overflow: hidden;
    }
    
    .genre-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 25px rgba(0,0,0,0.5);
        border-color: #38bdf8;
    }
    
    .genre-bg {
        position: absolute;
        top: 0; left: 0; width: 100%; height: 100%;
        z-index: -1;
        opacity: 0.3;
        background-size: cover;
        background-position: center;
    }
    
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s;
    }
    
    .main-header {
        background: linear-gradient(90deg, #38bdf8, #818cf8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 3rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. Utility Functions ---

def generate_image(prompt):
    """Generate concept art using Imagen 4.0"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-4.0-generate-001:predict?key={API_KEY}"
    payload = {
        "instances": [{"prompt": f"High quality video game concept art, cinematic lighting, {prompt}"}],
        "parameters": {"sampleCount": 1}
    }
    try:
        res = requests.post(url, json=payload)
        res.raise_for_status()
        b64_data = res.json()["predictions"][0]["bytesBase64Encoded"]
        return b64_data
    except Exception as e:
        st.error(f"Image Gen Error: {e}")
        return None

def generate_audio_preview(text):
    """Simulate game atmosphere audio description using Gemini TTS"""
    payload = {
        "contents": [{ "parts": [{ "text": f"Acting as a professional game sound designer, describe the music style and auditory experience of the following game in a deep, atmospheric voice: {text}" }] }],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": { "voiceConfig": { "prebuiltVoiceConfig": { "voiceName": "Charon" } } }
        },
        "model": "gemini-2.5-flash-preview-tts"
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key={API_KEY}"
    try:
        res = requests.post(url, json=payload)
        res.raise_for_status()
        audio_b64 = res.json()["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
        return audio_b64
    except Exception as e:
        return None

def create_pro_pdf(data, img_b64=None):
    """Generate professional game design PDF"""
    pdf = FPDF()
    pdf.add_page()
    
    # Title
    pdf.set_font("Helvetica", 'B', 24)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 20, "Game Concept Specification", ln=True, align='C')
    
    # Illustration
    if img_b64:
        img_data = base64.b64decode(img_b64)
        img_io = io.BytesIO(img_data)
        img = Image.open(img_io)
        img_path = "temp_concept.png"
        img.save(img_path)
        pdf.image(img_path, x=10, y=35, w=190)
        pdf.ln(110)
    
    # Content Area
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, f"Genre: {data['name']}", ln=True)
    pdf.ln(5)
    
    pdf.set_font("Helvetica", '', 12)
    for key, value in data['details'].items():
        if key == "classic_links": continue
        pdf.set_font("Helvetica", 'B', 12)
        pdf.cell(0, 8, f"{key.replace('_', ' ').title()}:", ln=True)
        pdf.set_font("Helvetica", '', 11)
        pdf.multi_cell(0, 6, str(value))
        pdf.ln(3)
        
    return pdf.output(dest='S')

# --- 4. Core Logic ---

if 'project' not in st.session_state:
    st.session_state.project = None
if 'selected_idx' not in st.session_state:
    st.session_state.selected_idx = None
if 'images' not in st.session_state:
    st.session_state.images = {}
if 'audios' not in st.session_state:
    st.session_state.audios = {}

with st.sidebar:
    st.markdown("### 🛠️ Project Lab")
    outline = st.text_area("Story Outline", "In a neon-drenched cyberpunk city, a protagonist who can manipulate time works as a hacker...", height=150)
    col1, col2 = st.columns(2)
    with col1:
        team_size = st.number_input("Team Size", 1, 50, 3)
    with col2:
        duration = st.number_input("Duration (Months)", 1, 24, 6)
    budget = st.slider("Budget ($)", 1000, 100000, 10000)
    
    if st.button("🚀 Start AI Proposal", use_container_width=True):
        with st.spinner("Gemini is conceiving the game architecture..."):
            prompt = f"""
            Analyze the following game concept and provide the 3 best matching genre proposals.
            Story: {outline} | Team: {team_size} people | Duration: {duration} months | Budget: ${budget}
            
            Return in JSON format with fields:
            genres: [
              {{
                "name": "Genre Name",
                "reason": "Recommendation Reason",
                "img_prompt": "A detailed English prompt for generating concept art for this genre",
                "details": {{
                   "optimized_outline": "Optimized script outline",
                   "core_loop": "Description of the core gameplay loop",
                   "classic_links": [ {{"title": "Game Title", "url": "Link"}} ],
                   "prediction": {{ "full_cycle": "Full development cycle prediction", "budget_breakdown": "Budget breakdown suggestion" }}
                }}
              }}
            ]
            """
            response = client.models.generate_content(
                model='gemini-2.5-flash-preview-09-2025',
                contents=prompt,
                config={'response_mime_type': 'application/json'}
            )
            st.session_state.project = json.loads(response.text)
            st.session_state.images = {} # Reset images
            st.session_state.audios = {} # Reset audio
            st.session_state.selected_idx = None

# --- 5. Main Interface Rendering ---

st.markdown('<h1 class="main-header">Indie Game Studio Pro</h1>', unsafe_allow_html=True)

if not st.session_state.project:
    st.info("👈 Please enter your creative outline in the sidebar to let AI start the journey.")
else:
    if st.session_state.selected_idx is None:
        st.subheader("💡 Recommended Proposals")
        cols = st.columns(3)
        for i, genre in enumerate(st.session_state.project['genres']):
            with cols[i]:
                # Asynchronously generate/load images
                if i not in st.session_state.images:
                    with st.spinner("Generating concept art..."):
                        st.session_state.images[i] = generate_image(genre['img_prompt'])
                
                img_data = st.session_state.images[i]
                bg_style = f"background-image: url(data:image/png;base64,{img_data});" if img_data else ""
                
                st.markdown(f"""
                <div class="genre-card">
                    <div class="genre-bg" style="{bg_style}"></div>
                    <h3>{genre['name']}</h3>
                    <p style="font-size: 0.9rem; color: #cbd5e1;">{genre['reason']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"Explore {genre['name']}", key=f"btn_{i}", use_container_width=True):
                    st.session_state.selected_idx = i
                    st.rerun()
    else:
        # Detail Page
        idx = st.session_state.selected_idx
        genre = st.session_state.project['genres'][idx]
        img_data = st.session_state.images[idx]
        
        if st.button("⬅️ Back to Recommendations"):
            st.session_state.selected_idx = None
            st.rerun()
            
        col_main, col_side = st.columns([2, 1])
        
        with col_main:
            st.title(f"🎮 {genre['name']}")
            if img_data:
                st.image(f"data:image/png;base64,{img_data}", use_container_width=True, caption="AI Generated Game Concept Art")
            
            st.subheader("📖 Deep Narrative & Gameplay")
            st.write(f"**Optimized Outline**: {genre['details']['optimized_outline']}")
            st.write(f"**Core Loop**: {genre['details']['core_loop']}")
            
            st.subheader("📈 Prediction & Budget")
            st.info(f"📅 **Full Cycle Prediction**: {genre['details']['prediction']['full_cycle']}")
            st.success(f"💰 **Budget Breakdown**: {genre['details']['prediction']['budget_breakdown']}")

        with col_side:
            st.subheader("🎵 Atmospheric Audio Preview")
            if idx not in st.session_state.audios:
                with st.spinner("AI Audio Designer working..."):
                    audio_text = f"The atmosphere of this {genre['name']} game is: {genre['details']['optimized_outline']}"
                    st.session_state.audios[idx] = generate_audio_preview(audio_text)
            
            if st.session_state.audios[idx]:
                st.audio(base64.b64decode(st.session_state.audios[idx]), format="audio/wav")
                st.caption("AI simulation of the game's audio style and mood")
            
            st.divider()
            st.subheader("🔗 Classic References")
            for link in genre['details']['classic_links']:
                st.markdown(f"- [{link['title']}]({link['url']})")
                
            st.divider()
            pdf_data = create_pro_pdf(genre, img_data)
            st.download_button(
                label="📥 Download PDF Report",
                data=pdf_data,
                file_name=f"{genre['name']}_Design_Plan.pdf",
                mime="application/pdf",
                use_container_width=True
            )

st.sidebar.markdown("---")
st.sidebar.caption("Powered by Gemini 2.5 & Imagen 4.0")
