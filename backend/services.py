import os
import json
import requests
import time
import base64
from google import genai
from .pdf_generator import create_improved_pdf

class GameAIClient:
    """
    Handles interactions with AI models (Gemini, Hugging Face) 
    and orchestrates data flow.
    """
    def __init__(self, api_key=None, hf_token=None):
        self.api_key = api_key if api_key else os.environ.get("GOOGLE_API_KEY", "")
        self.client = genai.Client(api_key=self.api_key)
        self.hf_token = hf_token
        self.hf_music_url = "https://huggingface.co/facebook/musicgen-small"
        self.hf_image_url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"

    def generate_proposal(self, story, team_size, duration, budget):
        """
        Interacts with Gemini to generate game design proposals.
        Returns detailed JSON with both Achievable concepts and Demo ideas.
        """
        prompt = f"""
        Act as a Senior Executive Game Producer and Architect. Analyze these constraints:
        Story Idea: {story}
        Team: {team_size} people | Duration: {duration} months | Initial Budget: ${budget}

        Task:
        1. "Achievable Genres": Identify 3 genres that can result in a HIGH-QUALITY FULL GAME within these STRICT constraints. 
           - Focus: Commercial viability and immediate development.
           - Detail: The 'optimized_outline' and 'reason' must be at least 4 high-density sentences.

        2. "Demo Prototypes": Identify 2 vertical slice/prototype ideas to prove the core mechanic in {duration} months.
           - Focus: Technical feasibility and "fun factor" verification.
           - Logic: These are small-scale tests. If expanded to a full game later, the budget MUST BE REASONABLE.

        STRICT BUDGET & CONTENT RULES:
        - For ANY 'full_game_prediction', the budget MUST be at least 5 to 10 times the initial budget (e.g., if initial is $10k, full game must be $100k+).
        - NEVER suggest a full game budget lower than the initial input.
        - Descriptions must be professional, technical, and exhaustive.

        Return ONLY raw JSON (NO MARKDOWN) with this structure:
        {{
            "achievable_genres": [
                {{
                    "name": "Genre Name",
                    "reason": "Extensive competitive analysis and fit explanation (4+ sentences)...",
                    "cycle": "{duration} months (Full Release)",
                    "visual_prompt": "Cinematic English prompt for AAA concept art",
                    "classic_references": [{{"title": "Game Name", "url": "URL"}}],
                    "details": {{
                        "optimized_outline": "Exhaustive narrative structure and world-building (5+ sentences)...",
                        "protagonist": "Detailed character profile",
                        "storyline": "Comprehensive plot summary",
                        "release_blurb": "Punchy marketing hook",
                        "core_loop": "Deep dive into gameplay mechanics and player progression..."
                    }}
                }}
            ],
            "demo_ideas": [
                {{
                    "name": "Demo Name",
                    "reason": "Technical necessity and prototype goals (4+ sentences)...",
                    "cycle": "1-2 months (Vertical Slice)",
                    "visual_prompt": "English prompt focusing on core mechanic visualization",
                    "classic_references": [{{"title": "Game Name", "url": "URL"}}],
                    "details": {{
                        "optimized_outline": "Focus on the specific scope of the demo (4+ sentences)...",
                        "protagonist": "Character role in the demo",
                        "storyline": "The specific slice of story being tested",
                        "release_blurb": "Prototype goal statement",
                        "core_loop": "The single core mechanic being verified",
                        "full_game_prediction": {{ 
                            "cycle": "Projected full development time (e.g., 24 months)", 
                            "budget": "Projected commercial budget (MUST be > 5x ${budget})" 
                        }}
                    }}
                }}
            ]
        }}
        """
        
        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-flash-preview-09-2025',
                contents=prompt,
                config={'response_mime_type': 'application/json'}
            )
            return json.loads(response.text)
        except Exception as e:
            print(f"Error generating proposal: {e}")
            return None

    def generate_image(self, prompt):
        """Generates an image via Hugging Face API."""
        if not self.hf_token: return None
        headers = {"Authorization": f"Bearer {self.hf_token}"}
        payload = {"inputs": f"Concept art, video game style, masterpiece, {prompt}"}
        
        try:
            response = requests.post(self.hf_image_url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                return base64.b64encode(response.content).decode('utf-8')
            elif response.status_code == 503: # Cold start retry
                time.sleep(5)
                response = requests.post(self.hf_image_url, headers=headers, json=payload, timeout=30)
                if response.status_code == 200:
                    return base64.b64encode(response.content).decode('utf-8')
            return None
        except Exception: return None

    def generate_audio(self, prompt):
        """Generates audio via Hugging Face API."""
        if not self.hf_token: return None
        headers = {"Authorization": f"Bearer {self.hf_token}"}
        payload = {"inputs": f"{prompt}, video game background music, high quality, instrumental"}
        
        try:
            response = requests.post(self.hf_music_url, headers=headers, json=payload, timeout=60)
            if response.status_code == 200:
                return base64.b64encode(response.content).decode('utf-8')
            return None
        except Exception: return None

    def export_pdf(self, data, img_b64=None):
        """Wrapper to call the separated PDF generator"""
        return create_improved_pdf(data, img_b64)
    


    def get_genre_wiki_info(self, genre_name):
        prompt = f"""
        Act as a gaming encyclopedia. For the game genre "{genre_name}":
        1. Write a strict 2-sentence "Wikipedia-style" definition.
        2. List 10 related sub-genres or mechanism tags (e.g., "Open World", "PVP").
        
        Return JSON: {{ "summary": "...", "tags": ["tag1", "tag2"...] }}
        """
        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-flash-preview-09-2025', 
                contents=prompt,
                config={'response_mime_type': 'application/json'}
            )
            return json.loads(response.text)
        except:
            return {"summary": "Info unavailable.", "tags": []}

    def evaluate_specific_genre(self, genre, story, team, duration, budget):
        """
        Verify the feasibility of specific types.
        Logic:
        1. If budget/time is sufficient -> Generate full game proposal.
        2. If budget is insufficient but sufficient for a demo -> Generate demo proposal.
        3. If completely mismatched (e.g., FPS with only £100 budget) -> Return reason for non-feasibility.
        """
        prompt = f"""
        Act as a Senior Executive Producer. 
        User wants to make a "{genre}" game.
        Constraints: Story: {story} | Team: {team} | Months: {duration} | Budget: ${budget}

        Analyze feasibility STRICTLY:
        1. **Feasible for Full Game**: If budget > $10,000 AND duration > 6 months (adjust threshold based on genre complexity).
        2. **Feasible for Demo**: If budget is low but enough for a prototype.
        3. **Not Feasible**: If constraints are ridiculous for this genre (e.g. MMORPG with $500).

        Return JSON:
        {{
            "status": "feasible_game" OR "feasible_demo" OR "impossible",
            "reason": "Explanation...",
            # If feasible (game or demo), provide details similar to previous format:
            "data": {{
                "name": "{genre} Project",
                "reason": "Why it works...",
                "cycle": "Est time",
                "visual_prompt": "Art prompt...",
                "classic_references": [{{"title": "Ref Game", "url": "#"}}],
                "details": {{
                    "optimized_outline": "...",
                    "protagonist": "...",
                    "storyline": "...",
                    "release_blurb": "...",
                    "core_loop": "...",
                    "full_game_prediction": {{ "cycle": "...", "budget": "..." }}
                }}
            }}
        }}
        """
        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-flash-preview-09-2025', 
                contents=prompt,
                config={'response_mime_type': 'application/json'}
            )
            return json.loads(response.text)
        except Exception as e:
            print(e)
            return None
