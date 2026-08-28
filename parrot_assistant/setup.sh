#!/bin/bash

# Parrot OS / Debian Assistant Setup Script
# Run this script to completely install all required dependencies

echo "========================================================="
echo "   PARROT OS ASSISTANT - HI-TECH DASHBOARD SETUP SCRIPT  "
echo "========================================================="
echo ""

echo "[*] Step 1: Installing System Dependencies via apt-get..."
sudo apt-get update
sudo apt-get install -y portaudio19-dev python3-pyaudio espeak-ng alsa-utils ffmpeg mpv libxcb-cursor0 libpulse-mainloop-glib0 cmake build-essential

if [ $? -ne 0 ]; then
    echo "[!] Error installing system dependencies. Setup aborted."
    exit 1
fi
echo "[+] System dependencies installed successfully."
echo ""

echo "[*] Step 2: Installing Python Dependencies via pip..."
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "[!] Error installing Python requirements."
    echo "[!] Ensure you have the correct Python version and virtual environment activated."
    exit 1
fi
echo "[+] Python dependencies installed successfully."
echo ""

echo "========================================================="
echo " SETUP COMPLETE! "
echo "========================================================="
echo ""
echo "To run the High-Tech Dashboard, execute:"
echo "  python main.py"
echo ""
echo "Make sure to set your Groq API Key if using the online LLM:"
echo "  export GROQ_API_KEY='your_key_here'"
echo ""
