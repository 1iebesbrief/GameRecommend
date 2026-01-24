🎮 Indie Game Studio Pro: An AI-Powered Creative Support ToolCourse: 4036GENAIY - Generative AI Research Project (Semester 1, 2025-26) 3Type: Creative Support Tool (CST) / Co-Creative System 

Project Overview
Indie Game Studio Pro is a multi-modal Creative Support Tool designed to assist independent game developers during the Ideation and Pre-production stages of game development5.
Game development requires a diverse set of skills: narrative design, visual arts, music composition, and technical project management. 
Independent developers often face "writer's block" or lack specific skills in one of these areas. 
This system acts as an "AI Co-founder," leveraging multiple Generative AI models to provide Skill Augmentation 6and Exploration Support7.

🎯 Core Aims 
Support Type: Ideation (Brainstorming) & Refinement.
Target Audience: Indie game developers, hobbyists, and solo creators.
Creative Value: Reducing the friction between a "raw idea" and a "structured proposal" by automating asset prototyping and documentation.

🚀 Key Features
1. 🧠 Intelligent Feasibility Analysis (Logic Layer) Uses Google Gemini 2.5 to analyze abstract user constraints (Story Idea, Team Size, Budget, Duration).
   It acts as an executive producer, determining if a project is commercially viable or better suited as a "Vertical Slice" (Demo).
2. 🎨 & 🎵 Multi-Modal Asset Generation Integrates Hugging Face Inference APIs to prototype assets instantly:
   Visuals: Generates cover art and concept visualizations using Stable Diffusion XL 1.0.Audio: Composes looping background music and soundtracks using Facebook MusicGen Small.
3. 📄 Automated GDD Generation (HTML/PDF)Solving the tedious task of documentation.
   The system uses Google Gemini 2.5 Flash to generate stylized HTML5 code based on the game's theme (e.g., Cyberpunk styling for a Sci-Fi game), which is then converted into a professional PDF Game Design Document (GDD).
4. 📚 Genre EncyclopediaA knowledge retrieval module that helps users explore game mechanics and genre definitions, powered by LLM knowledge bases.


🛠️ Technical Architecture & Implementation 
Logic & Text Engine: Powered by Google Gemini 2.5 Flash (via Google GenAI) — Responsible for core game logic analysis, feasibility reasoning, and generating narrative text content.
Visual Art Generation: Powered by Stable Diffusion XL 1.0 (via Hugging Face Hub) — tasked with generating high-quality game cover art and visual concepts.
Audio Synthesis: Powered by Facebook MusicGen Small (via Hugging Face Hub) — Used to compose original background music (BGM) and loops.
Code & Layout: Powered by Google Gemini 2.5 Flash (via Google GenAI)  — Specialized in generating the HTML/CSS code required for rendering professional PDF reports.


Project Structure
GameRecommend/
├── app1.py                 # Main Streamlit application entry point
├── backend/
│   ├── __init__.py
│   ├── services.py         # AI Client logic (Gemini & HF integration)
|   ├── text_to_music.py    # AI Music Demo Generation logic (HF integration)
│   └── pdf_generator.py    # PDF conversion logic (xhtml2pdf/fpdf)
├── requirements.txt        # Python dependencies
├── .env                    # API Keys
└── README.md               # Documentation


⚙️ Installation & Usage 
Prerequisites:
Python 3.10+
Google AI Studio API Key
Hugging Face Access Token

Setup Steps:
Clone the repository:Bashgit clone https://github.com/1iebesbrief/GameRecommend.git
cd GameRecommend
Install dependencies:Bashpip install -r requirements.txt
Configure Environment:Create a .env file in the root directory and add your keys:Code snippetGOOGLE_API_KEY=your_google_api_key_here
HF_TOKEN=hf_your_huggingface_token_here
Run the Application:Bashstreamlit run app1.py


⚖️ Ethical Considerations 
Bias in Generation: The image generation model (SDXL) may reflect biases present in its training data (LAION-5B). 
Users should be aware that generated characters might lean towards stereotypes unless specifically prompted.
Feasibility Hallucination: While Gemini is powerful, the "Budget Assessment" is a simulation and should not be used as financial advice.
Data Privacy: This tool processes user game ideas via external APIs (Google & Hugging Face). No user data is permanently stored on our local servers, but data is transmitted to these providers.

🔮 Future Work 
Prompt Refinement: Implementing "Chain of Thought" prompting to improve the consistency of the GDD PDF layouts.
Local Inference: Adding support for local LLMs (e.g., Llama 3) for users concerned about data privacy.
Interactive Editing: Allowing users to manually edit the generated HTML design before exporting to PDF.
