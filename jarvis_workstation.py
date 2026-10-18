import os
import sys
import json
import time
import subprocess
import threading
import select
import psutil
import datetime
import re
import wave
import io
import glob
import signal
import shutil
import numpy as np
import pyaudio
from faster_whisper import WhisperModel

# ================= Configuration =================
PIPER_BIN = "bin/piper/piper"
VOICE_ONNX = "voices/en_US-lessac-medium.onnx"
OLLAMA_MODEL = "qwen2.5:1.5b"

HOME_DIR = "/home/dggos"

SAMPLE_RATE = 16000
CHUNK_SIZE = 1024

VOICE_TRIGGER = 0.54
SILENCE_FLOOR = 0.42
SILENCE_TIMEOUT = 0.55

ALLOWED_PREFIXES = [
    "hi jarvis", "hey jarvis", "hello jarvis", "ok jarvis", "okay jarvis",
    "hi", "hey", "jarvis", "hello", "listen", "jervis", "javi", "travis", "jarees"
]

WORD_TO_NUM = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "fifteen": 15, "twenty": 20, "thirty": 30, "forty": 40,
    "forty five": 45, "fifty": 50, "sixty": 60, "half an": 30, "an": 1, "a": 1
}

def launch_in_terminal(command_str):
    for term in ["konsole", "x-terminal-emulator", "mate-terminal", "xfce4-terminal", "xterm"]:
        if shutil.which(term):
            if term == "konsole":
                subprocess.Popen(["konsole", "-e", "bash", "-c", command_str], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.Popen([term, "-e", f"bash -c \"{command_str}\""], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
    subprocess.Popen(["bash", "-c", command_str], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# ================= 1. Master Menu Controller =================
class MasterMenuController:
    def __init__(self):
        self.awaiting_choice = False
        self.menu_options = {
            "1": "Chatbot",
            "2": "Alarm",
            "3": "Jupyter",
            "4": "Player",
            "5": "Shell",
            "6": "YT Music Downloader",
            "7": "CBT Exam Portal",
            "0": "Exit"
        }

    def start(self):
        self.awaiting_choice = True
        return "Master menu is active. Choose one, sir, or do you want me to read all options?"

    def read_menu(self):
        items = [f"{k}: {v}" for k, v in self.menu_options.items()]
        return "The options are: " + ", ".join(items) + ". Which one would you like?"

    def handle_choice(self, user_text):
        t = user_text.lower().strip()
        if any(w in t for w in ["read", "say it all", "options", "tell me all"]):
            return self.read_menu()

        selected = None
        for word, num in WORD_TO_NUM.items():
            if re.search(rf"\b{word}\b", t) and num in range(8):
                selected = str(num)
                break

        if not selected:
            digit_match = re.search(r"\b([0-7])\b", t)
            if digit_match:
                selected = digit_match.group(1)

        if not selected:
            if "chatbot" in t: selected = "1"
            elif "alarm" in t: selected = "2"
            elif "jupyter" in t: selected = "3"
            elif "player" in t or "music" in t: selected = "4"
            elif "shell" in t: selected = "5"
            elif "yt" in t or "downloader" in t: selected = "6"
            elif "cbt" in t or "exam" in t or "study" in t: selected = "7"
            elif "exit" in t or "cancel" in t or "zero" in t: selected = "0"

        if not selected:
            return "I could not find that option. Please tell me a number from 0 to 7."

        self.awaiting_choice = False
        if selected == "0":
            return "Exiting master menu."

        service_name = self.menu_options.get(selected, selected)
        target_dir = HOME_DIR

        cmd_map = {
            "1": f"cd '{target_dir}/bash_scripts' && bash chatbot.sh; exec bash",
            "2": f"cd '{target_dir}/bash_scripts' && bash alarm.sh; exec bash",
            "3": f"cd '{target_dir}/bash_scripts' && bash jupyter.sh; exec bash",
            "4": f"cd '{target_dir}/python-codes/player' && python3 play.py; exec bash",
            "5": f"cd '{target_dir}/python-codes/shell' && python3 main.py; exec bash",
            "6": f"cd '{target_dir}/python-codes/yt-music-downloader' && python3 song_downloader.py; exec bash",
            "7": f"cd '{target_dir}/python-codes/study' && bash run.sh; exec bash",
        }

        launch_in_terminal(cmd_map.get(selected, f"cd '{target_dir}' && echo '{selected}' | bash master.sh; exec bash"))
        return f"Opening {service_name} in a new terminal."

master_ctl = MasterMenuController()

# ================= 2. Tools & Actions =================
def run_bash_command(command_str):
    clean_cmd = re.sub(r"^(run cmd|run command|execute command|cmd)\s+", "", command_str, flags=re.IGNORECASE).strip()
    if not clean_cmd:
        return "No command provided."
    try:
        proc = subprocess.run(clean_cmd, shell=True, capture_output=True, text=True, timeout=8)
        output = proc.stdout.strip() if proc.stdout else proc.stderr.strip()
        if not output:
            return f"Command finished with exit code {proc.returncode}."
        preview = " ".join([l.strip() for l in output.splitlines()[:2]])
        return f"Result: {preview[:150]}"
    except Exception as e:
        return f"Command error: {e}"

def file_manager_operations(text):
    t = text.lower()
    if any(k in t for k in ["read file", "read the file", "open file", "cat file"]):
        match = re.search(r"(?:read file|read the file|open file|cat file)\s+([a-zA-Z0-9_\-\.\/]+)", t)
        if match:
            fname = match.group(1).strip()
            paths = [fname, os.path.join(HOME_DIR, fname), os.path.expanduser(f"~/{fname}")]
            target = next((p for p in paths if os.path.isfile(p)), None)
            if not target:
                found = glob.glob(f"{HOME_DIR}/**/{fname}", recursive=True)
                if found: target = found[0]
            if target and os.path.isfile(target):
                try:
                    with open(target, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read(250).strip()
                    first_line = content.splitlines()[0] if content else "File is empty"
                    return f"Reading {os.path.basename(target)}: {first_line[:120]}"
                except Exception as e:
                    return f"Error reading file: {e}"
            return f"File {fname} not found."

    if any(k in t for k in ["list files", "show files", "list my files", "list files in home"]):
        target_dir = HOME_DIR if "home" in t else os.getcwd()
        try:
            entries = os.listdir(target_dir)[:8]
            return f"Files in {os.path.basename(target_dir)}: {', '.join(entries)}."
        except Exception as e:
            return f"Unable to list files: {e}"
    return None

def execute_system(text):
    t = text.lower()
    if master_ctl.awaiting_choice:
        return master_ctl.handle_choice(text)
    if any(k in t for k in ["run master file", "master file", "master script", "open master"]):
        return master_ctl.start()

    if ".sh" in t or "run script" in t:
        match = re.search(r"([a-zA-Z0-9_\-\.\/]+\.sh)", t)
        if match:
            script_path = match.group(1)
            launch_in_terminal(f"bash {script_path}; exec bash")
            return f"Running script {script_path} in terminal."

    if t.startswith("run cmd") or t.startswith("run command") or t.startswith("cmd "):
        return run_bash_command(text)

    f_resp = file_manager_operations(text)
    if f_resp: return f_resp

    if any(k in t for k in ["ches", "check status", "system status", "health check", "system info", "battery"]):
        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory().percent
        bat = psutil.sensors_battery()
        bat_str = f"{bat.percent}%" if bat else "AC power"
        return f"Battery is at {bat_str}. CPU load is {cpu}%, RAM load is {ram}%."

    if "volume" in t:
        if "up" in t or "increase" in t:
            subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "10%+"], check=False)
            return "Volume increased."
        if "down" in t or "decrease" in t:
            subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "10%-"], check=False)
            return "Volume decreased."
        if "hundred" in t or "max" in t:
            subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "1.0"], check=False)
            return "Volume set to maximum."
        if "fifty" in t or "half" in t:
            subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "0.5"], check=False)
            return "Volume set to fifty percent."

    if "brightness" in t or "screen" in t:
        if "up" in t or "increase" in t:
            subprocess.run(["brightnessctl", "set", "+15%"], check=False)
            return "Brightness raised."
        if "down" in t or "decrease" in t:
            subprocess.run(["brightnessctl", "set", "15%-"], check=False)
            return "Brightness lowered."

    if "wake" in t and "lock" in t:
        if "off" in t or "disable" in t:
            subprocess.run(["xset", "s", "on"], check=False)
            return "Screen wake-lock disabled."
        else:
            subprocess.run(["xset", "s", "off"], check=False)
            return "Screen wake-lock enabled."

    if "time" in t: return f"It is {datetime.datetime.now().strftime('%I:%M %p')}."
    if "date" in t or "day" in t: return f"Today is {datetime.datetime.now().strftime('%A, %B %d, %Y')}."
    return None

# ================= 3. Audio Player with Barge-In =================
class AudioPlayer:
    def __init__(self):
        self.tts_proc = None
        self.piper_proc = None
        self.is_speaking = False
        self.interrupt_flag = threading.Event()

    def stop_playback(self):
        self.interrupt_flag.set()
        if self.tts_proc and self.tts_proc.poll() is None:
            try:
                self.tts_proc.kill()
            except Exception:
                pass
        if self.piper_proc and self.piper_proc.poll() is None:
            try:
                self.piper_proc.kill()
            except Exception:
                pass
        self.tts_proc = None
        self.piper_proc = None
        self.is_speaking = False

    def speak(self, text, stream=None):
        if not text:
            return
        self.is_speaking = True
        self.interrupt_flag.clear()
        cleaned = re.sub(r"[*_#`]", "", text)
        print(f"\033[38;5;75m[Jarvis]: {cleaned}\033[0m")
        try:
            self.piper_proc = subprocess.Popen(
                [PIPER_BIN, "--model", VOICE_ONNX, "--length_scale", "0.78", "--output_raw"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
            )
            self.tts_proc = subprocess.Popen(
                ["aplay", "-r", "22050", "-f", "S16_LE", "-t", "raw", "-q", "-"],
                stdin=self.piper_proc.stdout, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            self.piper_proc.stdin.write(cleaned.encode("utf-8"))
            self.piper_proc.stdin.close()

            while self.tts_proc and self.tts_proc.poll() is None:
                if self.interrupt_flag.is_set():
                    self.stop_playback()
                    break
                time.sleep(0.02)
        except Exception as e:
            print(f"[Audio Error] {e}")
        finally:
            self.tts_proc = None
            self.piper_proc = None
            time.sleep(0.35)
            if stream:
                try:
                    avail = stream.get_read_available()
                    while avail > 0:
                        stream.read(avail, exception_on_overflow=False)
                        avail = stream.get_read_available()
                except Exception:
                    pass
            self.is_speaking = False

audio_out = AudioPlayer()

def keyboard_interrupt_listener():
    """Background listener: Press Enter or type in the terminal to instantly interrupt."""
    while True:
        try:
            rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
            if rlist:
                line = sys.stdin.readline()
                if audio_out.is_speaking:
                    audio_out.stop_playback()
                    print("\n\033[38;5;208m[Playback Interrupted via Keyboard]\033[0m")
        except Exception:
            time.sleep(0.1)

def play_chime(freq=820, duration=0.07):
    def _chime():
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paFloat32, channels=1, rate=22050, output=True)
        t = np.linspace(0, duration, int(22050 * duration), False)
        tone = 0.3 * np.sin(2 * np.pi * freq * t)
        stream.write(tone.astype(np.float32).tobytes())
        stream.stop_stream()
        stream.close()
        p.terminate()
    threading.Thread(target=_chime, daemon=True).start()

# ================= 4. Core Voice Assistant =================
class JarvisWorkstation:
    def __init__(self):
        print("[Init] Loading faster-whisper neural model (tiny.en int8)...")
        self.stt = WhisperModel("tiny.en", device="cpu", compute_type="int8", cpu_threads=4)
        self.audio = pyaudio.PyAudio()
        threading.Thread(target=keyboard_interrupt_listener, daemon=True).start()

    def stream_ollama(self, prompt):
        sys_prompt = {
            "role": "system",
            "content": "You are Jarvis, a highly advanced, capable, and intelligent Linux workstation assistant. "
                       "You are direct, exceptionally smart, and professional. Provide the best possible solution or answer directly. "
                       "Keep responses concise and easy to understand when spoken (1-3 sentences maximum). "
                       "Do not use markdown formatting, asterisks, or bullet points."
        }

        payload = {
            "model": OLLAMA_MODEL,
            "messages": [sys_prompt, {"role": "user", "content": prompt}],
            "options": {"num_ctx": 2048, "temperature": 0.5},
            "stream": True
        }

        try:
            proc = subprocess.Popen(
                ["curl", "-s", "-X", "POST", "http://localhost:11434/api/chat",
                 "-H", "Content-Type: application/json", "-d", json.dumps(payload)],
                stdout=subprocess.PIPE, text=True
            )
            buffer = ""
            for line in proc.stdout:
                if audio_out.interrupt_flag.is_set():
                    proc.terminate()
                    break
                if not line.strip(): continue
                try:
                    token = json.loads(line).get("message", {}).get("content", "")
                    buffer += token
                    if re.search(r"[.!?]\s+|[\n]", buffer):
                        parts = re.split(r"([.!?]\s+|[\n])", buffer)
                        sentence = parts[0] + parts[1].strip()
                        buffer = "".join(parts[2:])
                        if sentence.strip():
                            yield sentence.strip()
                except Exception:
                    continue
            if buffer.strip() and not audio_out.interrupt_flag.is_set():
                yield buffer.strip()
        except Exception as e:
            print(f"[Ollama Error] {e}")

    def listen_utterance(self, stream):
        frames = []
        silence_start = None
        has_spoken = False

        while True:
            data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
            if audio_out.is_speaking:
                continue

            pcm = np.frombuffer(data, dtype=np.int16)
            energy = float(np.max(np.abs(pcm))) / 32768.0

            if energy > VOICE_TRIGGER:
                if not has_spoken:
                    bars = "=" * int(energy * 25)
                    print(f"\r\033[38;5;220m[Voice Detected]: {energy:0.2f} |{bars:<25}|\033[0m", end="", flush=True)
                frames.append(data)
                has_spoken = True
                silence_start = None
            elif has_spoken:
                frames.append(data)
                if energy < SILENCE_FLOOR:
                    if silence_start is None:
                        silence_start = time.time()
                    elif time.time() - silence_start > SILENCE_TIMEOUT:
                        print("\r" + " " * 60 + "\r", end="", flush=True)
                        break
                else:
                    silence_start = None
            else:
                frames.append(data)
                if len(frames) > int(16000 / CHUNK_SIZE * 0.25):
                    frames.pop(0)

        audio_bytes = b"".join(frames)
        return np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0

    def extract_prefix_query(self, raw_text):
        cleaned = re.sub(r"[^\w\s]", "", raw_text.lower()).strip()
        for prefix in sorted(ALLOWED_PREFIXES, key=len, reverse=True):
            pattern = rf"^{prefix}\b"
            if re.search(pattern, cleaned):
                remainder = re.sub(pattern, "", cleaned).strip()
                return remainder if remainder else "hello"
        return None

    def run(self):
        stream = self.audio.open(
            format=pyaudio.paInt16, channels=1, rate=SAMPLE_RATE,
            input=True, frames_per_buffer=CHUNK_SIZE
        )

        print("\n\033[38;5;48m>>> ADVANCED JARVIS WORKSTATION ONLINE (PREFIX-GATED) <<<")
        print(">>> Prefix Required: Start with 'Hi', 'Hey', or 'Jarvis' <<<")
        print(">>> Interruption Active: Press [Enter] anytime to cut speech <<<\033[0m\n")

        while True:
            audio_data = self.listen_utterance(stream)
            if len(audio_data) < 6000:
                continue

            segments, _ = self.stt.transcribe(
                audio_data,
                beam_size=1,
                best_of=1,
                temperature=0.0,
                condition_on_previous_text=False
            )
            raw_text = " ".join([seg.text for seg in segments]).strip().lower()
            if not raw_text:
                continue

            print(f"[Heard]: \"{raw_text}\"")

            query = self.extract_prefix_query(raw_text)

            if master_ctl.awaiting_choice:
                clean_stripped = re.sub(r"[^\w\s]", "", raw_text).strip()
                if any(k in clean_stripped for k in ["0", "1", "2", "3", "4", "5", "6", "7", "one", "two", "three", "four", "five", "six", "seven", "zero", "read", "options", "chatbot", "jupyter", "player", "shell"]):
                    query = clean_stripped

            if query is None:
                continue

            play_chime()
            self.process_query(query, stream)

    def process_query(self, text, stream):
        print(f"\n\033[38;5;35m[User]: {text}\033[0m")

        quick_resp = execute_system(text)
        if quick_resp:
            audio_out.speak(quick_resp, stream)
            return

        for sentence in self.stream_ollama(text):
            if audio_out.interrupt_flag.is_set():
                break
            audio_out.speak(sentence, stream)

if __name__ == "__main__":
    try:
        JarvisWorkstation().run()
    except KeyboardInterrupt:
        audio_out.stop_playback()
        print("\nExiting Jarvis cleanly.")
