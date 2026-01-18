import streamlit as st
import base64
import os
from dotenv import load_dotenv
from backend import GameAIClient

load_dotenv()
# --- 1. Init & Styles ---
st.set_page_config(page_title="Indie Game Studio Pro", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0f172a; color: #f8fafc; }
    .card {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 20px;
        height: 200px;
        overflow-y: auto;
        transition: all 0.3s;
    }
    .card:hover { border-color: #38bdf8; transform: translateY(-3px); }
    .card h3 { color: #38bdf8; font-size: 1.2rem; }
    .highlight-box {
        background: #1e293b; border-left: 4px solid #38bdf8; padding: 15px; margin: 10px 0;
    }
    .success-box {
        background: #064e3b; border-left: 4px solid #34d399; padding: 15px; margin: 10px 0;
    }
    /* Modal/Popup simulation style */
    .modal-container {
        border: 1px solid #475569;
        border-radius: 10px;
        padding: 20px;
        background-color: #1e293b;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. State & Backend Setup ---
if 'game_client' not in st.session_state:
    # 错误写法：api_key = "" 
    # 正确写法：从环境变量读取
    api_key = os.getenv("GOOGLE_API_KEY") 
    hf_token = os.getenv("HF_TOKEN")
    
    # 确保 key 不为空再初始化，否则给出提示
    if not api_key:
        st.error("未找到 GOOGLE_API_KEY，请检查 .env 文件！")
    
    st.session_state.game_client = GameAIClient(api_key, hf_token)

# State initialization
base_keys = ['proposals', 'view', 'selected_item', 'selected_cat']
for k in base_keys:
    if k not in st.session_state:
        st.session_state[k] = None

# 修复 TypeError 的核心：确保 generated_media 始终是字典 {}
if 'generated_media' not in st.session_state or st.session_state.generated_media is None:
    st.session_state.generated_media = {}
# For the filtering/recommendation logic
if 'visible_items' not in st.session_state: st.session_state.visible_items = {}
if 'hidden_items' not in st.session_state: st.session_state.hidden_items = {}

# --- 3. View Logic (Router) ---

def go_home(): st.session_state.view = 'home'
def go_detail(): st.session_state.view = 'detail'

def handle_card_click(item, category):
    st.session_state.selected_item = item
    st.session_state.selected_cat = category
    st.session_state.view = 'modal' # Show popup/modal view

def handle_not_interested():
    """Logic to swap the rejected item with a new one from the hidden list"""
    cat = st.session_state.selected_cat
    current = st.session_state.selected_item
    
    # Remove current from visible list
    st.session_state.visible_items[cat] = [
        x for x in st.session_state.visible_items[cat] if x['name'] != current['name']
    ]
    
    # Add a new one from hidden list if available
    if st.session_state.hidden_items.get(cat):
        new_item = st.session_state.hidden_items[cat].pop(0)
        st.session_state.visible_items[cat].append(new_item)
    
    # Return to home grid
    go_home()

# --- 4. Render Components ---

def render_sidebar():
    with st.sidebar:
        st.title("🛠️ Project Lab")
        
        st.markdown("### 📝 Constraints")
        story = st.text_area("Story Idea", "A cyberpunk detective solving crimes in dreams...", height=100)
        col1, col2 = st.columns(2)
        team = col1.number_input("Team Size", 1, 50, 3)
        duration = col2.number_input("Months", 1, 36, 6)
        budget = st.slider("Budget ($)", 1000, 100000, 10000)
        
        if st.button("🚀 Analyze & Generate", type="primary", use_container_width=True):
            with st.spinner("AI Architect is analyzing constraints..."):
                # Call the Service
                data = st.session_state.game_client.generate_proposal(story, team, duration, budget)
                
                if data:
                    st.session_state.proposals = data
                    # Initialize Lists: Show top 3 Genres, Top 2 Demos. Keep rest in "Hidden"
                    all_genres = data.get('achievable_genres', [])
                    all_demos = data.get('demo_ideas', [])
                    
                    st.session_state.visible_items['achievable'] = all_genres[:3]
                    st.session_state.hidden_items['achievable'] = all_genres[3:]
                    
                    st.session_state.visible_items['demos'] = all_demos[:2]
                    st.session_state.hidden_items['demos'] = all_demos[2:]
                    
                    go_home()
                    st.rerun()

def render_home():
    st.markdown("# 🎮 Game Design Dashboard")
    
    if not st.session_state.proposals:
        st.info("👈 Please configure your project in the sidebar to begin.")
        return

    # --- Section 1: Achievable Genres ---
    st.subheader("✅ Achievable Game Genres")
    cols = st.columns(3)
    items = st.session_state.visible_items.get('achievable', [])
    
    if not items: 
        st.warning("No genres found fitting these constraints. Try increasing budget or duration.")
    
    for i, item in enumerate(items):
        with cols[i % 3]:
            st.markdown(f"""
            <div class="card">
                <h3>{item['name']}</h3>
                <p style="color:#cbd5e1; font-size:0.9em;">{item['reason'][:120]}...</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"Analyze {item['name']}", key=f"gen_{i}"):
                handle_card_click(item, 'achievable')
                st.rerun()

    # --- Section 2: Demo Recommendations ---
    st.divider()
    st.subheader("🧪 Recommended Prototypes (Demos)")
    d_cols = st.columns(2)
    d_items = st.session_state.visible_items.get('demos', [])
    
    if not d_items: st.info("No specific demo ideas generated.")

    for i, item in enumerate(d_items):
        with d_cols[i % 2]:
            st.markdown(f"""
            <div class="card" style="border-color: #818cf8;">
                <h3>{item['name']} (Demo)</h3>
                <p style="color:#cbd5e1; font-size:0.9em;">{item['reason'][:120]}...</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"Analyze Demo {i+1}", key=f"dem_{i}"):
                handle_card_click(item, 'demos')
                st.rerun()

def render_modal():
    """
    Simulates a popup window for quick evaluation.
    User decides to 'Interested' (Proceed) or 'Not Interested' (Swap).
    """
    item = st.session_state.selected_item
    
    # Use empty containers to center visually or just use layout
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        with st.container():
            st.markdown(f"""
            <div class="modal-container">
                <h2>🧐 Evaluate Strategy: {item['name']}</h2>
                <p><b>Feasibility Analysis:</b> {item['reason']}</p>
                <p>⏱️ <b>Est. Cycle:</b> {item.get('cycle', 'N/A')}</p>
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            if c1.button("❌ Not Interested (Hide)", use_container_width=True):
                handle_not_interested()
                st.rerun()
            if c2.button("✨ Interested (Deep Dive)", type="primary", use_container_width=True):
                go_detail()
                st.rerun()
    st.markdown("---")

def render_detail():
    item = st.session_state.selected_item
    details = item.get('details', {})
    
    if st.button("⬅️ Back to Dashboard"):
        go_home()
        st.rerun()
        
    st.title(f"🚀 Design Blueprint: {item['name']}")
    
    # 1. Media Section (Image & Audio)
    media_key = f"{item['name']}_img"
    audio_key = f"{item['name']}_audio"
    
    col_media, col_text = st.columns([1, 1.5])
    
    with col_media:
        # Image Generation
        if media_key not in st.session_state.generated_media:
            with st.spinner("Visualizing concept..."):
                img = st.session_state.game_client.generate_image(item.get('visual_prompt', item['name']))
                st.session_state.generated_media[media_key] = img
        
        img_data = st.session_state.generated_media.get(media_key)
        if img_data:
            st.image(base64.b64decode(img_data), use_container_width=True, caption="AI Concept Art")
        else:
            st.warning("Image model warming up or token missing.")

        # Audio Generation
        st.write("### Audio Atmosphere")
        if st.button("🎵 Generate Soundscape"):
            with st.spinner("Composing soundtrack..."):
                aud = st.session_state.game_client.generate_audio(item.get('name'))
                st.session_state.generated_media[audio_key] = aud
                st.rerun()
                
        aud_data = st.session_state.generated_media.get(audio_key)
        if aud_data:
            st.audio(base64.b64decode(aud_data), format="audio/wav")

    with col_text:
        # Game Details
        st.markdown(f"<div class='highlight-box'><b>📢 One-Liner:</b><br>{details.get('release_blurb', 'N/A')}</div>", unsafe_allow_html=True)
        
        st.subheader("Narrative & Gameplay")
        st.write(f"**Protagonist:** {details.get('protagonist', 'N/A')}")
        st.write(f"**Story Arc:** {details.get('storyline', 'N/A')}")
        st.write(f"**Core Loop:** {details.get('core_loop', 'N/A')}")
        
        # Long-Term Prediction (Requirement 2)
        pred = details.get('full_game_prediction', {})
        if pred:
            st.markdown(f"""
            <div class='success-box'>
                <h4>🔮 Long-term Projection (Full Game)</h4>
                <p>If you proceed to a full release after this phase:</p>
                <ul>
                    <li><b>Projected Dev Cycle:</b> {pred.get('cycle', 'N/A')}</li>
                    <li><b>Projected Budget:</b> {pred.get('budget', 'N/A')}</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

    # 2. Classic References (Requirement 2 & 3)
    st.divider()
    st.subheader("🔗 Classic References")
    refs = item.get('classic_references', [])
    if refs:
        cols_ref = st.columns(3)
        for idx, link in enumerate(refs):
            with cols_ref[idx % 3]:
                st.markdown(f"**[{link.get('title', 'Game Link')}]({link.get('url', '#')})**")
    else:
        st.caption("No specific references found.")
    
    st.divider()
    col_pdf, _ = st.columns([1, 2])
    with col_pdf:
        if st.button("📥 Export Professional GDD (PDF)", type="primary", use_container_width=True):
            with st.spinner("Compiling PDF Report..."):
                # 获取当前生成的图片（如果有）
                img_data = st.session_state.generated_media.get(media_key)
                
                # 调用后端 service 的导出功能
                pdf_bytes = st.session_state.game_client.export_pdf(
                    item, 
                    img_data
                )
                
                # 触发下载
                st.download_button(
                    label="Click to Download PDF",
                    data=pdf_bytes,
                    file_name=f"{item['name'].replace(' ', '_')}_GDD.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

# --- 5. Main Execution ---
render_sidebar()

if st.session_state.view == 'modal':
    render_modal()
elif st.session_state.view == 'detail':
    render_detail()
else:
    render_home()