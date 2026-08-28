import os

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "your_groq_api_key_here")

# STT Configuration
STT_ENGINE = "faster-whisper" # or "vosk"
STT_MODEL_SIZE = "tiny.en"
AUDIO_RATE = 16000
CHUNK_SIZE = 1024

# TTS Configuration
TTS_ENGINE = "pyttsx3" # or "edge-tts"
TTS_RATE = 150
TTS_VOLUME = 1.0

# LLM Configuration
OLLAMA_ENDPOINT = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen:5b"

# Memory Configuration
MEMORY_DB_PATH = "memory.db"

# Scraper Configuration
SEARCH_ENGINE = "duckduckgo"

# System Tools Configuration
WORKSPACE_DIR = os.path.expanduser("~/parrot_assistant_workspace")

# Wake Word
WAKE_WORD = "hey assistant"
STOP_WORD = "stop"

# Router Configuration
PING_HOST = "8.8.8.8"
PING_PORT = 53
PING_TIMEOUT = 2
