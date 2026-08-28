import sys
import os
import queue
import numpy as np
import pyaudio
import speech_recognition as sr
from PySide6.QtCore import QThread, Signal
from faster_whisper import WhisperModel

# Ensure parent directory is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import AUDIO_RATE, STT_MODEL_SIZE

class STTEngineThread(QThread):
    """
    STT Engine background thread using Faster-Whisper.
    Emits raw transcribed text and current audio intensity (RMS) for the UI.
    """
    intensity_signal = Signal(float)
    text_signal = Signal(str)

    # Add a signal for logging internal errors to the UI
    log_signal = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = True
        self.recognizer = sr.Recognizer()
        self.microphone_initialized = False

        try:
            # Audio source using PyAudio directly for stream analysis,
            # or via SpeechRecognition for easy buffering
            self.microphone = sr.Microphone(sample_rate=AUDIO_RATE)

            # Initialize Whisper Model
            self.model = WhisperModel(STT_MODEL_SIZE, device="cpu", compute_type="int8")

            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source)
            self.microphone_initialized = True
        except Exception as e:
            # We catch it here but we can't emit yet because signals aren't connected during init.
            # We will handle it in the run loop.
            self.init_error = str(e)

    def run(self):
        if not self.microphone_initialized:
            self.log_signal.emit(f"STT INIT ERROR: {self.init_error}. Please check PyAudio/Microphone.")
            return

        self.log_signal.emit("STT Engine initialized and listening.")
        while self.running:
            try:
                # Listen for speech. We use a short timeout to keep the loop responsive
                # and allow thread to be stopped gracefully.
                with self.microphone as source:
                    audio_data = self.recognizer.listen(source, timeout=1, phrase_time_limit=5)

                # We have speech, calculate intensity for UI before transcription
                raw_data = audio_data.get_raw_data(convert_rate=AUDIO_RATE, convert_width=2)
                # Convert 16-bit PCM to float32
                audio_np = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32) / 32768.0

                # Calculate RMS intensity
                rms = np.sqrt(np.mean(np.square(audio_np)))
                self.intensity_signal.emit(float(rms))

                # Transcribe using Faster-Whisper
                segments, info = self.model.transcribe(audio_np, beam_size=5)
                text = " ".join([segment.text for segment in segments])

                if text.strip():
                    self.text_signal.emit(text.strip())

            except sr.WaitTimeoutError:
                # Normal behavior when nobody is speaking
                self.intensity_signal.emit(0.0)
                continue
            except Exception as e:
                print(f"[STT Error] {e}")

    def stop(self):
        self.running = False
        self.wait()
