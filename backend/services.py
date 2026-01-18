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
        Act as a veteran Executive Game Producer. Analyze constraints:
        Story Idea: {story}
        Team: {team_size} | Duration: {duration} months | Budget: ${budget}

        Task:
        1. "Achievable Genres": Identify 5 genres fitting STRICTLY within constraints.
        2. "Demo Prototypes": Identify 5 vertical slice/demo ideas that can be built quickly to prove the concept.

        For each item, provide:
        - "classic_references": List of real classic games (Title + URL) for inspiration.
        - "full_game_prediction": A forecast if this demo/prototype is expanded into a full commercial game.

        Return ONLY raw JSON (NO MARKDOWN) with this structure:
        {{
            "achievable_genres": [
                {{
                    "name": "Genre Name",
                    "reason": "Why it fits",
                    "cycle": "Est. Dev Time",
                    "visual_prompt": "English prompt for concept art",
                    "classic_references": [{{"title": "Game Name", "url": "URL"}}],
                    "details": {{
                        "optimized_outline": "Refined concept",
                        "protagonist": "Character desc",
                        "storyline": "Plot summary",
                        "release_blurb": "One-sentence hook",
                        "core_loop": "Gameplay loop",
                        "full_game_prediction": {{ "cycle": "Full Game Time", "budget": "Full Game Budget" }}
                    }}
                }}
            ],
            "demo_ideas": [
                {{
                    "name": "Demo Name",
                    "reason": "Why this demo works",
                    "cycle": "Demo Dev Time",
                    "visual_prompt": "English prompt for concept art",
                    "classic_references": [{{"title": "Game Name", "url": "URL"}}],
                    "details": {{
                        "optimized_outline": "Demo scope focus",
                        "protagonist": "Character desc",
                        "storyline": "Demo plot slice",
                        "release_blurb": "Demo hook",
                        "core_loop": "Demo mechanics",
                        "full_game_prediction": {{ "cycle": "Expansion Time", "budget": "Expansion Budget" }}
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