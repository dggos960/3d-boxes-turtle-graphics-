# DIY AI Desktop Robot Assistant Guide (Tiny WALL-E Style)

This guide provides a comprehensive overview of how to build your own desktop AI robot assistant capable of seeing, talking, listening, and moving, similar to a tiny WALL-E.

## 1. Hardware Requirements

Since you already have an ESP32, an ESP32-CAM, and a single-color display, you have a great starting point. Here is the full list of what you'll need:

### Core Computing & Vision
- **ESP32 Microcontroller:** The brain for controlling motors, audio output, and the display.
- **ESP32-CAM:** For vision (streaming video to your PC/server).
- **FTDI Programmer (FT232RL):** Needed to program the ESP32-CAM, as it usually lacks a built-in USB-to-serial converter.
- **Desktop Computer / Raspberry Pi:** The "heavy lifter" brain. Microcontrollers aren't powerful enough to run LLMs (AI), advanced STT (Speech-to-Text), and TTS (Text-to-Speech) locally. A PC or Raspberry Pi will process audio/video and send commands to the ESP32.

### Output (Audio & Display)
- **Single-Color Display (e.g., 0.96" I2C OLED SSD1306):** For displaying the robot's eyes or status information. (You already have this).
- **Speaker:** A small 8-ohm speaker.
- **Audio Amplifier (e.g., MAX98357A I2S or PAM8403):** To amplify the sound from the ESP32 to the speaker.

### Input (Audio)
- **Microphone (e.g., INMP441 I2S Omnidirectional Microphone):** For the robot to listen to your voice. Alternatively, you can simply use a USB microphone connected directly to your PC for an easier setup.

### Movement
- **Servo Motors (e.g., SG90 or MG90S):** You will need 2 to 4 servos depending on the complexity of movement (e.g., pan/tilt for the head, arm movement).
- **DC Motors with Wheels (Optional):** If you want it to drive around on your desk, you'll need two small N20 geared DC motors and a motor driver (e.g., L298N or TB6612FNG).

### Power & Chassis
- **Power Supply:** A 5V power supply or a LiPo battery (18650) with a charging module (TP4056) and a boost converter (to ensure a steady 5V for the ESP32 and servos).
- **Chassis/Body:** You can 3D print a WALL-E style body, build it out of cardboard, or use a pre-made robot chassis.
- **Jumper Wires & Breadboard/PCB:** For connecting everything together.

---

## 2. Software Stack

The project will be split into two main parts: the Robot (ESP32) and the Brain (PC/Server).

### On the Robot (ESP32 & ESP32-CAM)
- **Arduino IDE or PlatformIO:** Used to write and flash the C++ firmware.
- **ESP32 Firmware:**
  - Connects to WiFi.
  - Receives movement commands via WebSockets, MQTT, or HTTP.
  - Controls the servos using the `ESP32Servo` library.
  - Updates the OLED display (using `Adafruit_SSD1306` or `U8g2`).
  - Streams audio to the I2S amplifier and reads audio from the I2S microphone (if not using PC audio).
- **ESP32-CAM Firmware:**
  - Connects to WiFi.
  - Runs a web server to stream MJPEG video to the PC.

### On the Brain (Desktop PC or Raspberry Pi)
- **Language:** Python 3.
- **Vision:** `OpenCV` to capture the video stream from the ESP32-CAM and detect faces or objects.
- **Speech-to-Text (STT) "Listening":** `SpeechRecognition` library or `faster-whisper` for local offline transcription.
- **AI / LLM "Thinking":** `llama.cpp` / `Ollama` (for local models like Llama 3 or Mistral) or API-based like OpenAI's `gpt-4o`.
- **Text-to-Speech (TTS) "Talking":** `pyttsx3` (offline) or `elevenlabs` / `gTTS` (cloud).
- **Communication:** `requests` or `websockets` to send movement/display commands back to the ESP32.

---

## 3. Step-by-Step Implementation Guide

### Step 1: ESP32-CAM Setup (Vision)
1. Connect the ESP32-CAM to your computer using the FTDI programmer.
2. Open the Arduino IDE, install ESP32 boards, and go to **File > Examples > ESP32 > Camera > CameraWebServer**.
3. Enter your WiFi credentials in the code and select your camera model (usually `CAMERA_MODEL_AI_THINKER`).
4. Flash the code, open the Serial Monitor to get the IP address, and verify you can see the video stream in your browser.

### Step 2: ESP32 Main Board Setup (Movement & Display)
1. Connect your OLED display (I2C: SDA to GPIO 21, SCL to GPIO 22).
2. Connect your Servos to PWM-capable GPIO pins (e.g., GPIO 12, 13).
3. Write Arduino code to connect to WiFi and host a simple Web Server or WebSocket server.
4. Add code to parse incoming commands (e.g., `/move?pan=90&tilt=45`) and update the servos.
5. Create animations for the OLED eyes (e.g., blinking, happy, sad) and trigger them via commands.

### Step 3: Desktop Server Setup (The AI Brain)
1. Set up a Python virtual environment on your PC.
2. Install the necessary libraries: `pip install opencv-python speechrecognition pyttsx3 requests openai`.
3. Write a Python script that continuously captures frames from the ESP32-CAM URL using `cv2.VideoCapture("http://<ESP32-CAM-IP>:81/stream")`.
4. Implement face tracking: When OpenCV detects a face, calculate its position relative to the center of the frame and send HTTP requests to the ESP32 to move the servos, keeping the face centered.

### Step 4: Adding Voice & AI
1. Create a wake-word mechanism or use a "push-to-talk" key on your keyboard.
2. When triggered, record audio from your PC microphone.
3. Convert the audio to text using STT.
4. Send the text to your LLM of choice along with a system prompt: *"You are a helpful, quirky robot assistant named WALL-E. Keep your answers short."*
5. Receive the text response, convert it to audio using TTS, and play it through your PC speakers (or send it to the ESP32 I2S DAC).
6. (Optional) While the AI is "speaking", send continuous commands to the ESP32 to change the OLED eyes to a "talking" animation.

### Step 5: Assembly and Refinement
1. Mount all hardware inside your robot chassis.
2. Ensure power distribution is stable (servos can draw a lot of current and cause the ESP32 to reset if not powered properly, consider powering servos directly from the 5V source, not the ESP32 5V pin).
3. Fine-tune the servo movements, face tracking PID loop, and AI prompts.

---

## Summary of Data Flow
1. **Camera** -> WiFi -> **PC (OpenCV)** -> Face detected -> **PC calculates angle** -> WiFi -> **ESP32** -> Moves servos.
2. **User speaks** -> **PC Mic** -> STT (Text) -> **AI (LLM)** -> Generates Text -> TTS (Audio) -> **Speaker**.
3. **AI** -> Determines emotional state -> WiFi -> **ESP32** -> Updates OLED Display (Eyes).

Taking it one subsystem at a time (Camera first, then Servos, then Python AI) is the best way to successfully build your robot!
