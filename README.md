
##🎬 AI-Powered Study Shorts Generator

This is a Flask web app that turns input questions into fun to follow Youtube Shorts-styled videos. It uses OpenRouter (GPT) to generate answers, 
ElevenLabs for lifelike voice synthesis, and FFmpeg to overlay animated subtitles on looping background videos like Subway Surfers or Minecraft, which are popular background gameplay videos online.  
The result is a fully dynamic video with auto-generated speech and styled, animated subtitles — all built with:

Flask (Python web framework)

OpenRouter GPT (text generation)

 ElevenLabs API (text-to-speech)

FFmpeg (video/audio/subtitle processing)

.ASS subtitle animation (scaling/fade effects)

Bootstrap (frontend styling)

To run this app locally, make sure you have FFmpeg installed and its bin folder added to your system’s PATH environment variable. You’ll also need a free ElevenLabs account to obtain an API key for text-to-speech functionality.

##  Getting Started

1. Clone the repo
2. Create a `.env` file with your API keys
3. Install requirements:
   pip install -r requirements.txt
4. Run with `.python app.py`
