import os
import json
import requests
import time
import base64
import io
from backend.pdf_generator import create_manual_pdf, convert_html_to_pdf, get_fallback_html
from huggingface_hub import InferenceClient
from backend.text_to_music import generate_local_music

_GENAI_BACKEND = None
_GENAI_IMPORT_ERROR = None
try:
    from google import genai as genai_sdk
    _GENAI_BACKEND = "google-genai"
except Exception as exc:
    try:
        import google.generativeai as genai_sdk
        _GENAI_BACKEND = "google-generativeai"
    except Exception as exc2:
        _GENAI_IMPORT_ERROR = exc2


class _GenAIClientCompat:
    def __init__(self, api_key):
        if not _GENAI_BACKEND:
            raise ImportError(
                f"Google GenAI SDK not available: {_GENAI_IMPORT_ERROR}. "
                "Install google-genai or google-generativeai."
            )
        self._backend = _GENAI_BACKEND
        if self._backend == "google-genai":
            self._client = genai_sdk.Client(api_key=api_key)
        else:
            genai_sdk.configure(api_key=api_key)
            self._client = None

    @property
    def models(self):
        if self._backend == "google-genai":
            return self._client.models
        return self

    def generate_content(self, model, contents, config=None):
        if self._backend == "google-genai":
            return self._client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
        model_obj = genai_sdk.GenerativeModel(model)
        return model_obj.generate_content(contents)

class GameAIClient:
    """
    Handles interactions with AI models (Gemini, Hugging Face) 
    and orchestrates data flow.
    """
    def __init__(self, api_key=None, hf_token=None):
        self.api_key = api_key if api_key else os.environ.get("GOOGLE_API_KEY", "")
        self.client = _GenAIClientCompat(api_key=self.api_key)
        self.hf_token = os.environ.get("HF_TOKEN", "")
        self.hf_music_url = "https://huggingface.co/facebook/musicgen-small"
        self.hf_image_url = "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0"
        self.hf_coder_url = "https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct"

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

        client = InferenceClient(
        provider="nscale",
        api_key=self.hf_token,
        )

        image = client.text_to_image(
        prompt,
        model="stabilityai/stable-diffusion-xl-base-1.0",
        )

        image.save("test_output3.png")
            # Convert the image into a Base64 string
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
        return img_str

    def generate_audio(self, prompt):
        """Generates audio via the local MusicGen pipeline."""
        model_name = os.environ.get("LOCAL_MUSIC_MODEL", "small")
        device = os.environ.get("LOCAL_MUSIC_DEVICE") or None
        try:
            duration = int(os.environ.get("LOCAL_MUSIC_DURATION", 8))
        except (TypeError, ValueError):
            duration = 8

        audio_bytes, error = generate_local_music(
            prompt,
            duration=duration,
            model_name=model_name,
            device=device,
        )
        if audio_bytes:
            return base64.b64encode(audio_bytes).decode("utf-8")
        if error:
            print(f"Local music generation failed: {error}")
        return None

    def generate_music_profile(self, data):
        details = data.get("details", {}) if isinstance(data, dict) else {}
        payload = {
            "name": data.get("name", "") if isinstance(data, dict) else "",
            "release_blurb": details.get("release_blurb", ""),
            "core_loop": details.get("core_loop", ""),
            "storyline": details.get("storyline", ""),
            "protagonist": details.get("protagonist", ""),
        }

        profile = None
        if self.api_key:
            prompt = (
                "You are a game music director. Given the game data JSON, "
                "produce a compact music brief in JSON with keys: "
                "mood (2-3 words), tempo_bpm (int 60-180), energy (0-1 float), "
                "instruments (list 3-6), style_tags (list 3-6), notes (1 short sentence). "
                "Return only JSON.\n"
                f"Game data: {json.dumps(payload, ensure_ascii=True)}"
            )
            try:
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash-preview-09-2025",
                    contents=prompt,
                    config={"response_mime_type": "application/json"},
                )
                profile = json.loads(response.text)
            except Exception as exc:
                print(f"Music profile generation failed: {exc}")

        if not isinstance(profile, dict):
            profile = self._fallback_music_profile(data)
        return profile

    def compose_music_prompt(self, data, profile=None):
        if profile is None:
            profile = self.generate_music_profile(data)

        details = data.get("details", {}) if isinstance(data, dict) else {}
        parts = [
            f"{data.get('name', 'Game')} game soundtrack" if isinstance(data, dict) else "Game soundtrack",
            details.get("release_blurb", ""),
            details.get("core_loop", ""),
        ]

        if profile:
            mood = profile.get("mood")
            if mood:
                parts.append(f"Mood: {mood}")
            tempo = profile.get("tempo_bpm")
            if tempo:
                parts.append(f"Tempo {tempo} BPM")
            instruments = profile.get("instruments")
            if instruments:
                if isinstance(instruments, (list, tuple)):
                    instruments = ", ".join(str(item) for item in instruments if item)
                parts.append(f"Instruments: {instruments}")
            style_tags = profile.get("style_tags")
            if style_tags:
                if isinstance(style_tags, (list, tuple)):
                    style_tags = ", ".join(str(item) for item in style_tags if item)
                parts.append(f"Style: {style_tags}")
            notes = profile.get("notes")
            if notes:
                parts.append(str(notes))

        parts.append("loopable, clean mix, game background music")
        return ", ".join([part for part in parts if part])

    def _fallback_music_profile(self, data):
        details = data.get("details", {}) if isinstance(data, dict) else {}
        text = " ".join(
            str(value)
            for value in [
                data.get("name", "") if isinstance(data, dict) else "",
                details.get("release_blurb", ""),
                details.get("core_loop", ""),
                details.get("storyline", ""),
            ]
        ).lower()

        if any(key in text for key in ("horror", "survival", "nightmare", "eerie")):
            return {
                "mood": "tense, eerie",
                "tempo_bpm": 80,
                "energy": 0.35,
                "instruments": ["low strings", "ambient drones", "sub bass"],
                "style_tags": ["dark", "atmospheric", "minimal"],
                "notes": "Sparse pulses and distant textures.",
            }
        if any(key in text for key in ("cyberpunk", "sci-fi", "sci fi", "futuristic", "neon")):
            return {
                "mood": "edgy, futuristic",
                "tempo_bpm": 120,
                "energy": 0.7,
                "instruments": ["synth bass", "analog pads", "electronic drums"],
                "style_tags": ["neon", "noir", "electronic"],
                "notes": "Driving groove with shimmering synth layers.",
            }
        if any(key in text for key in ("fantasy", "magic", "myth", "kingdom", "dragon")):
            return {
                "mood": "epic, hopeful",
                "tempo_bpm": 100,
                "energy": 0.6,
                "instruments": ["strings", "choir", "orchestral percussion"],
                "style_tags": ["cinematic", "orchestral", "heroic"],
                "notes": "Warm harmonies and sweeping melodies.",
            }
        if any(key in text for key in ("strategy", "tactics", "turn-based", "management", "simulation")):
            return {
                "mood": "focused, measured",
                "tempo_bpm": 90,
                "energy": 0.45,
                "instruments": ["piano", "soft synths", "light percussion"],
                "style_tags": ["minimal", "ambient", "steady"],
                "notes": "Subtle layers with a steady pulse.",
            }

        return {
            "mood": "cinematic, neutral",
            "tempo_bpm": 100,
            "energy": 0.5,
            "instruments": ["synth pads", "drums", "bass"],
            "style_tags": ["ambient", "cinematic", "modern"],
            "notes": "Balanced, unobtrusive background loop.",
        }

    def generate_gdd_enrichment(self, data):
        if not self.api_key or not isinstance(data, dict):
            return None

        details = data.get("details", {}) if isinstance(data, dict) else {}
        payload = {
            "title": data.get("name", ""),
            "release_blurb": details.get("release_blurb", ""),
            "core_loop": details.get("core_loop", ""),
            "storyline": details.get("storyline", ""),
            "protagonist": details.get("protagonist", ""),
            "optimized_outline": details.get("optimized_outline", ""),
            "reason": data.get("reason", ""),
            "cycle": data.get("cycle", ""),
            "classic_references": data.get("classic_references", []),
        }

        prompt = (
            "You are a senior game producer. Expand the provided game data into a professional "
            "GDD supplement for a PDF export. Keep it concise but complete. "
            "Return ONLY JSON with this schema:\n"
            "{\n"
            '  "executive_summary": "2-3 sentences",\n'
            '  "pillars": ["3-5 short bullets"],\n'
            '  "target_audience": "1-2 sentences",\n'
            '  "player_experience": "2-3 sentences",\n'
            '  "key_features": ["5-8 bullets"],\n'
            '  "progression": "1-2 sentences",\n'
            '  "content_scope": "1-2 sentences",\n'
            '  "art_direction": "1-2 sentences",\n'
            '  "audio_direction": "1-2 sentences",\n'
            '  "ui_ux": "1-2 sentences",\n'
            '  "accessibility": "1-2 sentences",\n'
            '  "tech_scope": "1-2 sentences",\n'
            '  "production_plan": [\n'
            '     {"phase": "Pre-production", "duration": "X weeks", "deliverables": "..."},\n'
            '     {"phase": "Production", "duration": "X weeks", "deliverables": "..."}\n'
            "  ],\n"
            '  "risks": ["3-5 bullets"],\n'
            '  "success_metrics": ["3-5 bullets"],\n'
            '  "monetization": "1-2 sentences",\n'
            '  "live_ops": "1-2 sentences",\n'
            '  "marketing_hooks": ["3-5 bullets"]\n'
            "}\n"
            f"Game data: {json.dumps(payload, ensure_ascii=True)}"
        )

        primary_model = os.environ.get("GDD_MODEL", "gemini-2.5-pro-preview-09-2025")
        config = {
            "response_mime_type": "application/json",
            "temperature": 0.6,
            "max_output_tokens": 1200,
        }

        try:
            response = self.client.models.generate_content(
                model=primary_model,
                contents=prompt,
                config=config,
            )
            return json.loads(response.text)
        except Exception as exc:
            print(f"GDD enrichment failed on {primary_model}: {exc}")

        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash-preview-09-2025",
                contents=prompt,
                config=config,
            )
            return json.loads(response.text)
        except Exception as exc:
            print(f"GDD enrichment fallback failed: {exc}")
            return None

    def generate_html_design(self, data, img_b64=None, enrichment=None):
        """
        Responsible solely for generating HTML code strings
        """
        if not self.hf_token: 
            return get_fallback_html(data)

        genre = data.get('name', 'Game')
        details = data.get('details', {})
        
        extra_notes = ""
        if isinstance(enrichment, dict):
            summary = enrichment.get("executive_summary")
            pillars = enrichment.get("pillars")
            features = enrichment.get("key_features")
            if summary:
                extra_notes += f"\n- Executive Summary: {summary}"
            if pillars:
                extra_notes += f"\n- Design Pillars: {pillars}"
            if features:
                extra_notes += f"\n- Key Features: {features}"

        prompt_content = f"""
        You are an expert Frontend Developer. 
        Task: Create a highly stylized, single-file HTML5 Design Document.
        
        Game Info:
        - Title: {genre}
        - Theme: {genre} style (e.g. Cyberpunk=neon, Fantasy=parchment).
        - Description: {details.get('release_blurb', 'N/A')}
        - Core Loop: {details.get('core_loop', 'N/A')}
        {extra_notes}
        
        Requirements:
        1. Use internal CSS (<style>) for aggressive styling.
        2. RETURN ONLY VALID HTML CODE. Start with <!DOCTYPE html>.
        """

        payload = {
            "inputs": prompt_content,
            "parameters": {"max_new_tokens": 2048, "temperature": 0.7, "return_full_text": False}
        }
        
        headers = {"Authorization": f"Bearer {self.hf_token}"}

        try:
            response = requests.post(self.hf_coder_url, headers=headers, json=payload, timeout=60)
            result = response.json()
            
            if isinstance(result, list) and len(result) > 0:
                html_code = result[0].get('generated_text', '')
                html_code = html_code.replace("```html", "").replace("```", "").strip()
                
                if img_b64:
                    img_tag = f'<div style="text-align:center; margin:20px 0;"><img src="data:image/png;base64,{img_b64}" style="max-width:80%; border-radius:10px;"></div>'
                    if "<body>" in html_code:
                        html_code = html_code.replace("<body>", f"<body>{img_tag}")
                    else:
                        html_code = f"{img_tag}{html_code}"
                
                return html_code
            else:
                return get_fallback_html(data)
                
        except Exception as e:
            print(f"Coder API Error: {e}")
            return get_fallback_html(data)

    def export_pdf(self, data, img_b64=None, use_ai_design=False):

        enrichment = self.generate_gdd_enrichment(data)
        if use_ai_design:
            html_content = self.generate_html_design(data, img_b64, enrichment=enrichment)
            pdf_bytes = convert_html_to_pdf(html_content)
            if pdf_bytes:
                return pdf_bytes
        return create_manual_pdf(data, img_b64, enrichment=enrichment)


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
