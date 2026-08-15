import customtkinter as ctk
import threading
import queue
import time
import speech_recognition as sr
import numpy as np
from faster_whisper import WhisperModel
import argostranslate.package
import argostranslate.translate
import pyttsx3

# Monkey patch ArgosTranslate to avoid Stanza errors on unsupported Tagalog
import argostranslate.sbd
if hasattr(argostranslate.sbd, 'StanzaSentencizer') and hasattr(argostranslate.sbd.StanzaSentencizer, 'LANGUAGE_CODE_MAPPING'):
    argostranslate.sbd.StanzaSentencizer.LANGUAGE_CODE_MAPPING['tl'] = 'en'


ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class TranslatorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Realtime Voice Translator")
        self.geometry("800x600")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Header
        self.header_label = ctk.CTkLabel(self, text="Realtime Voice Translator", font=("Arial", 24, "bold"))
        self.header_label.grid(row=0, column=0, pady=20, padx=20, sticky="ew")

        # Controls
        self.controls_frame = ctk.CTkFrame(self)
        self.controls_frame.grid(row=1, column=0, pady=10, padx=20, sticky="ew")
        self.controls_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.source_label = ctk.CTkLabel(self.controls_frame, text="Source Language:")
        self.source_label.grid(row=0, column=0, padx=10, pady=10)
        self.source_var = ctk.StringVar(value="Auto-Detect")
        self.source_menu = ctk.CTkOptionMenu(self.controls_frame, variable=self.source_var, values=["Auto-Detect", "en", "tl"])
        self.source_menu.grid(row=0, column=1, padx=10, pady=10)

        self.target_label = ctk.CTkLabel(self.controls_frame, text="Target Language:")
        self.target_label.grid(row=0, column=2, padx=10, pady=10)
        self.target_var = ctk.StringVar(value="hi")
        self.target_menu = ctk.CTkOptionMenu(self.controls_frame, variable=self.target_var, values=["hi", "en"])
        self.target_menu.grid(row=0, column=3, padx=10, pady=10)

        self.start_btn = ctk.CTkButton(self.controls_frame, text="Start Listening", command=self.start_listening, fg_color="green", hover_color="darkgreen")
        self.start_btn.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        self.stop_btn = ctk.CTkButton(self.controls_frame, text="Stop Listening", command=self.stop_listening, fg_color="red", hover_color="darkred", state="disabled")
        self.stop_btn.grid(row=1, column=2, columnspan=2, padx=10, pady=10, sticky="ew")

        # Diarization state
        self.speaker_count = 1
        self.current_speaker_id = 1
        self.last_speech_time = time.time()

        self.speaker_label = ctk.CTkLabel(self.controls_frame, text=f"Detected Speakers: {self.speaker_count}")

        self.speaker_label.grid(row=2, column=0, columnspan=4, pady=5)

        # Intensity Bar
        self.intensity_bar = ctk.CTkProgressBar(self.controls_frame)
        self.intensity_bar.grid(row=3, column=0, columnspan=4, padx=10, pady=5, sticky="ew")
        self.intensity_bar.set(0)


        # Conversation History
        self.history_text = ctk.CTkTextbox(self, font=("Arial", 16))
        self.history_text.grid(row=2, column=0, pady=20, padx=20, sticky="nsew")
        self.history_text.insert("0.0", "--- Conversation History ---\n\n")
        self.history_text.configure(state="disabled")

        self.is_listening = False
        self.ui_queue = queue.Queue()

        # TTS queue
        self.tts_queue = queue.Queue()

        # Audio & Transcription variables
        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True
        try:
            self.microphone = sr.Microphone()
        except Exception as e:
            self.update_history("System", f"No microphone found: {e}\n")
            self.microphone = None

        # Load models in background
        self.whisper_model = None
        threading.Thread(target=self.load_models, daemon=True).start()

        # Start TTS worker thread
        threading.Thread(target=self.tts_worker, daemon=True).start()

        self.check_queue()

    def tts_worker(self):
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)
        while True:
            text = self.tts_queue.get()
            if text is None:
                break
            engine.say(text)
            engine.runAndWait()

    def load_models(self):
        self.update_history("System", "Downloading/Updating Argos packages. This may take a minute...\n")
        try:
            argostranslate.package.update_package_index()
            available_packages = argostranslate.package.get_available_packages()

            # Install needed packages
            needed = [('en','hi'), ('en','tl'), ('tl','en'), ('hi','en')]
            installed_packages = argostranslate.package.get_installed_packages()
            installed_codes = [(pkg.from_code, pkg.to_code) for pkg in installed_packages]

            for pkg in available_packages:
                pair = (pkg.from_code, pkg.to_code)
                if pair in needed and pair not in installed_codes:
                    self.update_history("System", f"Installing {pair[0]} -> {pair[1]} package...\n")
                    pkg.install()

            self.update_history("System", "Loading Whisper STT model...\n")
            self.whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")
            self.update_history("System", "Models loaded successfully. Ready to start.\n")
        except Exception as e:
            self.update_history("System", f"Error loading models: {str(e)}\n")

    def update_speaker_label(self):
        count = self.speaker_count
        self.after(0, lambda: self.speaker_label.configure(text=f"Detected Speakers: {count}"))

    def start_listening(self):
        if self.whisper_model is None:
            self.update_history("System", "Please wait, model is still loading...\n")
            return

        if self.microphone is None:
            self.update_history("System", "Microphone not available.\n")
            return

        self.is_listening = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.update_history("System", "Started listening...\n")
        self.last_speech_time = time.time()

        # Start recording thread
        threading.Thread(target=self.record_and_transcribe, daemon=True).start()

    def stop_listening(self):
        self.is_listening = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.update_history("System", "Stopped listening.\n")

    def record_and_transcribe(self):
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)
            while self.is_listening:
                try:
                    # Capture short bursts of audio continuously keeping stream open
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=5)

                    # Turn taking heuristic: If there was a pause > 2 seconds, toggle speaker
                    current_time = time.time()
                    pause_duration = current_time - self.last_speech_time
                    if pause_duration > 2.0:
                        # Switch speaker if there's a conversational pause
                        self.current_speaker_id = 2 if self.current_speaker_id == 1 else 1
                        # Ensure max count reflects new speakers discovered
                        self.speaker_count = max(self.speaker_count, self.current_speaker_id)
                        self.update_speaker_label()

                    # Convert rate to 16000 for whisper
                    raw_data = audio.get_raw_data(convert_rate=16000, convert_width=2)
                    audio_data = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32) / 32768.0

                    # Calculate intensity (RMS)
                    rms = np.sqrt(np.mean(audio_data**2))
                    # Normalize rms for progress bar (typically 0.0 to 0.1 for voice, scale it up)
                    intensity_val = min(1.0, rms * 10)
                    self.after(0, lambda v=intensity_val: self.intensity_bar.set(v))

                    segments, info = self.whisper_model.transcribe(audio_data, beam_size=5)
                    text = "".join([segment.text for segment in segments]).strip()

                    if text:
                        self.last_speech_time = time.time() # Update last speech time
                        src_lang = self.source_var.get()
                        tgt_lang = self.target_var.get()

                        if src_lang == "Auto-Detect":
                            src_lang = info.language

                        speaker_name = f"Speaker {self.current_speaker_id}"

                        self.update_history(f"{speaker_name} ({src_lang})", f"{text}\n")

                        # Offload translation
                        threading.Thread(target=self.translate_and_speak, args=(text, src_lang, tgt_lang), daemon=True).start()

                except sr.WaitTimeoutError:
                    pass
                except Exception as e:
                    self.update_history("System", f"Error in audio capture: {str(e)}\n")
                    break

    def translate_and_speak(self, text, src, tgt):
        try:
            if src == tgt:
                translated_text = text
            else:
                translated_text = argostranslate.translate.translate(text, src, tgt)

            self.update_history(f"Translation ({tgt})", f"{translated_text}\n")

            # Put to TTS queue to execute in correct thread
            self.tts_queue.put(translated_text)

        except Exception as e:
            self.update_history("System", f"Error translating: {str(e)}\n")

    def update_history(self, speaker, text):
        self.ui_queue.put(f"[{speaker}]: {text}\n")

    def check_queue(self):
        while not self.ui_queue.empty():
            msg = self.ui_queue.get()
            self.history_text.configure(state="normal")
            self.history_text.insert("end", msg)
            self.history_text.see("end")
            self.history_text.configure(state="disabled")
        self.after(100, self.check_queue)

if __name__ == "__main__":
    app = TranslatorApp()
    app.mainloop()
