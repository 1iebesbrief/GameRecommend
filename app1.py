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
    api_key = os.getenv("GOOGLE_API_KEY") 
    hf_token = os.getenv("HF_TOKEN")
    
    if not api_key:
        st.error("GOOGLE_API_KEY Not Found")
    
    st.session_state.game_client = GameAIClient(api_key, hf_token)

# State initialization
base_keys = ['proposals', 'view', 'selected_item', 'selected_cat']
for k in base_keys:
    if k not in st.session_state:
        st.session_state[k] = None

if 'generated_media' not in st.session_state or st.session_state.generated_media is None:
    st.session_state.generated_media = {}
# For the filtering/recommendation logic
if 'visible_items' not in st.session_state: st.session_state.visible_items = {}
if 'hidden_items' not in st.session_state: st.session_state.hidden_items = {}
if 'wiki_genre' not in st.session_state: st.session_state.wiki_genre = None
if 'wiki_data' not in st.session_state: st.session_state.wiki_data = None

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

import threading
import time

import threading
import time
import streamlit as st

def render_sidebar():
    with st.sidebar:
        st.title("🛠️ Project Lab")
        
        if 'is_analyzing' not in st.session_state:
            st.session_state.is_analyzing = False
        if 'game_client' not in st.session_state:
            st.error("Game client not initialized. Please check your .env or backend setup.")
            return

        st.markdown("### 📝 Constraints")
        story = st.text_area("Story Idea", "A cyberpunk detective solving crimes in dreams...", height=100)
        col1, col2 = st.columns(2)
        team = col1.number_input("Team Size", 1, 20, 3)
        duration = col2.number_input("Months", 1, 24, 6)
        budget = st.slider("Budget ($)", 0, 10000, 1000)
        
        if not st.session_state.is_analyzing:
            if st.button("🚀 Analyze & Generate", type="primary", use_container_width=True):
                st.session_state.is_analyzing = True
                st.rerun()
        else:
            if st.button("🛑 Stop & Cancel Analysis", type="secondary", use_container_width=True):
                st.session_state.is_analyzing = False
                st.rerun()

            status_placeholder = st.empty()
            res_container = []
            
            client_instance = st.session_state.game_client

            def run_ai_task(client):
                try:
                    res = client.generate_proposal(story, team, duration, budget)
                    res_container.append(res)
                except Exception as e:
                    res_container.append(e)

            ai_thread = threading.Thread(target=run_ai_task, args=(client_instance,))
            ai_thread.start()

            loading_messages = [
                "🏗️ Architecting the game world...",
                "📊 Analyzing feasibility and budget...",
                "📚 Pulling classic references..."
            ]
            
            msg_idx = 0
            while ai_thread.is_alive():
                with status_placeholder.container():
                    st.markdown(f"""
                    <div style="padding:15px; background:rgba(56, 189, 248, 0.1); border-radius:10px; border-left:4px solid #38bdf8;">
                        <p style="margin:0; color:#38bdf8; font-weight:bold;">AI Architect is at work...</p>
                        <p style="margin:0; font-size:0.9em; color:#cbd5e1;">{loading_messages[msg_idx % 3]}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                time.sleep(3)
                msg_idx += 1
                
                if not st.session_state.is_analyzing:
                    break

            status_placeholder.empty()
            if res_container and st.session_state.is_analyzing:
                data = res_container[0]
                st.session_state.is_analyzing = False 
                
                if isinstance(data, Exception):
                    st.error(f"Analysis failed: {str(data)}")
                elif data:
                    st.session_state.proposals = data
                    all_genres = data.get('achievable_genres', [])
                    all_demos = data.get('demo_ideas', [])
                    st.session_state.visible_items['achievable'] = all_genres[:3]
                    st.session_state.hidden_items['achievable'] = all_genres[3:]
                    st.session_state.visible_items['demos'] = all_demos[:2]
                    st.session_state.hidden_items['demos'] = all_demos[2:]
                    
                    go_home()
                    st.rerun()

def render_home():
    
    # 1. System Intro
    st.markdown("""
    <div style="text-align: center; padding: 40px 20px;">
        <h1 style="background: -webkit-linear-gradient(45deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 3.5rem;">
            Indie Game Studio Pro
        </h1>
        <p style="font-size: 1.2rem; color: #cbd5e1; max-width: 800px; margin: 0 auto;">
            Your AI-powered co-founder for game development. <br>
            Explore genres below OR use the sidebar to generate a custom proposal.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # 2. Interactive Genre Cloud
    st.markdown("### 🔥 Trending Genres Explorer")
    popular_genres = [
        "Roguelike", "Metroidvania", "Cyberpunk RPG", "Visual Novel", 
        "Hypercasual", "Turn-based Strategy", "Survival Horror", "Platformer",
        "Deckbuilder", "Idle Clicker", "Tower Defense", "Puzzle", "FPS", "MOBA"
    ]
    
    cloud_cols = st.columns(4)
    for i, genre in enumerate(popular_genres):
        with cloud_cols[i % 4]:
            if st.button(f"🏷️ {genre}", key=f"cloud_{i}", use_container_width=True):
                st.session_state.wiki_genre = genre
                with st.spinner(f"Fetching {genre} encyclopedia data..."):
                    info = st.session_state.game_client.get_genre_wiki_info(genre)
                    st.session_state.wiki_data = info
                st.session_state.view = 'wiki'
                st.rerun()
    
    st.markdown("---")

    
    if st.session_state.proposals:
        st.subheader("📋 Your Generated Proposals")

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
    User decides to 'Interested' (Proceed), 'Not Interested' (Swap), 
    or 'Back to Dashboard' (Decide Later).
    """
    item = st.session_state.selected_item
    
    # Centered Layout
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 3, 1])
    
    with col2:
        with st.container():
            # Evaluation Card UI
            st.markdown(f"""
            <div class="modal-container">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h2 style="margin:0;">🧐 Evaluate Strategy: {item['name']}</h2>
                </div>
                <hr style="border-color: rgba(255,255,255,0.1);">
                <p><b>Feasibility Analysis:</b> {item['reason']}</p>
                <p>⏱️ <b>Est. Development Cycle:</b> {item.get('cycle', 'N/A')}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # First Row: Primary Decision Buttons
            c1, c2 = st.columns(2)
            if c1.button("❌ Not Interested (Hide & Swap)", use_container_width=True):
                handle_not_interested()
                st.rerun()
            if c2.button("✨ Interested (Deep Dive)", type="primary", use_container_width=True):
                go_detail()
                st.rerun()
            
            # Second Row: Neutral Navigation Button
            st.write("") # Add a little spacing
            if st.button("⬅️ Back to Dashboard (Decide Later)", use_container_width=True):
                go_home()
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
        img_data = st.session_state.generated_media.get(media_key)
    
        if img_data and len(img_data) > 500: 
            st.image(base64.b64decode(img_data), use_container_width=True)
        else:
            if st.button("🎨 Recreate image"): 
                pass

        st.write("### 🎵 Game Background Music Preview")
        aud_data = st.session_state.generated_media.get(audio_key)
        if aud_data and len(aud_data) > 500:
            st.audio(base64.b64decode(aud_data), format="audio/wav")
        else:
            st.caption("The audio is currently queued or generation has failed. Please click the button below to retry.")
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
                img_data = st.session_state.generated_media.get(media_key)
                
                pdf_bytes = st.session_state.game_client.export_pdf(
                    item, 
                    img_data
                )
                
                st.download_button(
                    label="Click to Download PDF",
                    data=pdf_bytes,
                    file_name=f"{item['name'].replace(' ', '_')}_GDD.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

def render_genre_wiki():
    genre = st.session_state.wiki_genre
    info = st.session_state.wiki_data or {"summary": "Loading...", "tags": []}

    # --- Navigation ---
    if st.button("⬅️ Back to Home"):
        go_home()
        st.rerun()

    # --- 1. Wikipedia Style Header ---
    st.title(f"📚 {genre}")
    st.markdown(f"""
    <div style="background: #1e293b; padding: 20px; border-left: 5px solid #818cf8; border-radius: 5px;">
        <p style="font-size: 1.1rem; font-style: italic;">"{info.get('summary')}"</p>
    </div>
    """, unsafe_allow_html=True)

    # --- 2. Related Tags Cloud ---
    st.markdown("#### 🔗 Related Mechanics & Tags")
    tags_html = " ".join([f"<span style='background:#334155;padding:5px 10px;border-radius:15px;margin:5px;display:inline-block;font-size:0.9em;'>#{tag}</span>" for tag in info.get('tags', [])])
    st.markdown(tags_html, unsafe_allow_html=True)

    st.divider()

    # --- 3. Feasibility Check Form ---
    st.subheader(f"🛠️ Build a {genre} Project")
    st.info(f"Fill in your constraints below to see if a **{genre}** game is feasible for you.")

    with st.form("wiki_feasibility_form"):
        col1, col2 = st.columns(2)
        story_input = st.text_area("Core Story Idea", "A hero saves the world...", height=80)
        team_input = col1.number_input("Team Size", 1, 50, 3)
        duration_input = col2.number_input("Months", 1, 36, 6)
        budget_input = st.slider("Budget ($)", 1000, 100000, 10000)
        
        submitted = st.form_submit_button(f"🚀 Analyze Feasibility: {genre}")

    if submitted:
        with st.spinner(f"Simulating {genre} production pipeline..."):
            result = st.session_state.game_client.evaluate_specific_genre(
                genre, story_input, team_input, duration_input, budget_input
            )
            
            if result:
                status = result.get('status')
                reason = result.get('reason')
                
                # Generate game or demo
                if status in ['feasible_game', 'feasible_demo']:
                    if status == 'feasible_game':
                        st.success(f"✅ Greenlit! A full {genre} game is feasible.")
                    else:
                        st.warning(f"⚠️ Budget/Time Tight. Recommending a **Vertical Slice (Demo)** instead.")
                        st.markdown(f"**Reason:** {reason}")

                    item_data = result.get('data')
                    item_data['name'] = item_data.get('name', f"{genre} Project") 
                    
                    st.session_state.selected_item = item_data
                    st.session_state.selected_cat = 'wiki_generated' 
                    if 'generated_media' not in st.session_state: st.session_state.generated_media = {}
                    
                    go_detail() 
                    st.rerun()

                # Give reasons when it is impossible to recommend game genres
                else:
                    st.error(f"❌ Not Feasible: {genre}")
                    st.markdown(f"""
                    <div style="padding:15px; background:rgba(239, 68, 68, 0.1); border:1px solid #ef4444; border-radius:8px;">
                        <b>AI Analysis:</b> {reason}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown("### 💡 Alternative Options")
                    st.write("Your constraints don't fit this specific genre. Would you like us to recommend genres that *do* fit?")
                    
                    if st.button("🔄 Auto-Recommend Suitable Genres"):
                        with st.spinner("Pivoting strategy... Finding suitable genres..."):
                             data = st.session_state.game_client.generate_proposal(
                                 story_input, team_input, duration_input, budget_input
                             )
                             if data:
                                st.session_state.proposals = data
                                # Update lists
                                all_genres = data.get('achievable_genres', [])
                                all_demos = data.get('demo_ideas', [])
                                st.session_state.visible_items['achievable'] = all_genres[:3]
                                st.session_state.visible_items['demos'] = all_demos[:2]
                                
                                go_home() 
                                st.rerun()

# --- 5. Main Execution ---
render_sidebar()

if st.session_state.view == 'modal':
    render_modal()
elif st.session_state.view == 'detail':
    render_detail()
elif st.session_state.view == 'wiki':
    render_genre_wiki()
else:
    render_home()

