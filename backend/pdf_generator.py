from fpdf import FPDF
from PIL import Image
import io
import base64

def create_improved_pdf(data, img_b64=None):
    """
    Generate a professional PDF with cover page and better formatting.
    Handles all layout and styling logic separately from business logic.
    """
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # --- Cover Page ---
    pdf.add_page()
    pdf.set_fill_color(15, 23, 42) # Dark Slate Blue (Theme Color)
    pdf.rect(0, 0, 210, 297, 'F') # A4 Size Background
    
    # Cover Text
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", 'B', 32)
    pdf.set_y(80)
    pdf.cell(0, 15, "GAME DESIGN", ln=True, align='C')
    pdf.cell(0, 15, "SPECIFICATION", ln=True, align='C')
    
    # Project Title
    pdf.set_font("Helvetica", '', 20)
    pdf.ln(20)
    # Handle potential encoding issues with standard fonts
    title = data.get('name', 'Untitled Project').encode('latin-1', 'replace').decode('latin-1')
    pdf.cell(0, 10, title, ln=True, align='C')
    
    # Cover Image placement
    if img_b64:
        try:
            img_data = base64.b64decode(img_b64)
            img_io = io.BytesIO(img_data)
            img = Image.open(img_io)
            # Center image: (210 - 120) / 2 = 45
            pdf.image(img, x=45, y=160, w=120) 
        except Exception:
            pass # Fail silently for image errors on PDF
            
    # --- Content Pages ---
    pdf.add_page()
    pdf.set_text_color(0, 0, 0)
    
    # Helper for Section Titles
    def chapter_title(label):
        pdf.set_font("Helvetica", 'B', 14)
        pdf.set_fill_color(200, 220, 255) # Light Blue Highlight
        pdf.cell(0, 10, f"  {label}", ln=True, fill=True, border='L')
        pdf.ln(4)

    # Helper for Body Text
    def body_text(txt):
        pdf.set_font("Helvetica", '', 11)
        # Encode/Decode to handle basic latin characters cleanly in FPDF
        safe_txt = str(txt).encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 6, safe_txt)
        pdf.ln(3)

    # 1. Executive Summary
    chapter_title("1. Executive Summary")
    body_text(f"Genre/Type: {data.get('name')}")
    body_text(f"Concept: {data.get('details', {}).get('optimized_outline', '')}")
    pdf.ln(5)

    # 2. Narrative Design
    chapter_title("2. Narrative Design")
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(0, 6, "Protagonist:", ln=True)
    body_text(data.get('details', {}).get('protagonist', 'N/A'))
    
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(0, 6, "Story Arc:", ln=True)
    body_text(data.get('details', {}).get('storyline', 'N/A'))
    pdf.ln(5)

    # 3. Gameplay & Mechanics
    chapter_title("3. Core Gameplay")
    body_text(f"Marketing Hook: {data.get('details', {}).get('release_blurb', '')}")
    pdf.ln(2)
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(0, 6, "Core Loop:", ln=True)
    body_text(data.get('details', {}).get('core_loop', ''))
    pdf.ln(5)

    # 4. Production Roadmap
    chapter_title("4. Development Roadmap")
    cycle = str(data.get('cycle', '')).encode('latin-1', 'replace').decode('latin-1')
    body_text(f"Initial Phase Est: {cycle}")
    
    pred = data.get('details', {}).get('full_game_prediction', {})
    if pred:
        pdf.ln(2)
        pdf.set_font("Helvetica", 'B', 11)
        pdf.cell(0, 6, "Full Game Projection:", ln=True)
        body_text(f"Timeline: {pred.get('cycle', 'N/A')}")
        body_text(f"Estimated Budget: {pred.get('budget', 'N/A')}")

    # 5. References
    chapter_title("5. Market References")
    refs = data.get('classic_references', [])
    for ref in refs:
         body_text(f"- {ref.get('title')} ({ref.get('url')})")

    return pdf.output(dest='S').encode('latin-1')
