# Realtime Voice Translator

A fast, offline, local real-time voice translator with a professional UI built with CustomTkinter.
It supports live translation from English/Tagalog to Hindi/English, includes a conversation history, Text-to-Speech (TTS), and an offline heuristic for speaker diarization.

## Prerequisites

### 1. System Dependencies (Debian/Ubuntu)
You must install system-level audio development headers and TTS tools before installing the Python packages:
```bash
sudo apt-get update
sudo apt-get install -y portaudio19-dev python3-pyaudio espeak-ng alsa-utils
```

*Note on Windows:* You don't usually need system headers, but `pyaudio` and `pyttsx3` use SAPI5 on Windows natively.

### 2. Python Dependencies
Install the required packages using the provided `requirements.txt`:
```bash
pip install -r requirements.txt
```

## Running the Application

Execute the translator script:
```bash
python translator.py
```

The first time you run the application, it will download the required offline Whisper models and Argos Translate language packages in the background.

## Features
- **Offline & Free:** Uses `faster-whisper` and `argostranslate` to ensure zero API costs and full local processing.
- **Speaker Diarization (No-API):** Uses an offline conversational pause-based heuristic to track the number of speakers and switch turns automatically.
- **TTS Feedback:** Reads out the translated text using `pyttsx3`.
