import sys
import os
import pyttsx3
import queue
import numpy as np
from PySide6.QtCore import QThread, Signal

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import TTS_RATE, TTS_VOLUME

class TTSEngineThread(QThread):
    """
    TTS Engine background thread using pyttsx3.
    Thread-safe and supports an instant kill-switch (barge-in).
    """
    intensity_signal = Signal(float)
    finished_signal = Signal()

    log_signal = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.queue = queue.Queue()
        self.running = True
        self._is_speaking = False
        self.engine_initialized = False

        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', TTS_RATE)
            self.engine.setProperty('volume', TTS_VOLUME)
            self.engine_initialized = True
        except Exception as e:
            self.init_error = str(e)

    def speak(self, text):
        """Add text to the speech queue."""
        self.queue.put(text)

    def stop_speaking(self):
        """Instant kill switch for TTS output (Barge-in)."""
        # Clear the queue
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
            except queue.Empty:
                break

        # If currently speaking, stop the pyttsx3 engine
        if self._is_speaking:
            try:
                self.engine.stop()
            except Exception as e:
                print(f"[TTS Stop Error] {e}")

        self.intensity_signal.emit(0.0)

    def run(self):
        if not self.engine_initialized:
            self.log_signal.emit(f"TTS INIT ERROR: {self.init_error}. Please check espeak/audio dependencies.")
            return

        self.log_signal.emit("TTS Engine initialized.")
        while self.running:
            try:
                # Wait for text to speak (timeout allows checking self.running)
                text = self.queue.get(timeout=0.5)
                self._is_speaking = True

                # Simulate intensity while speaking for the UI
                # pyttsx3 is blocking, so we emit a fake high RMS before it starts
                # and zero when it finishes.
                # In a more advanced implementation (like piper or a custom pyaudio stream),
                # you'd read the audio stream chunks and calculate actual RMS.
                self.intensity_signal.emit(0.8)

                try:
                    self.engine.say(text)
                    self.engine.runAndWait()
                except Exception as e:
                    print(f"[TTS Runtime Error] {e}")

                self._is_speaking = False
                self.intensity_signal.emit(0.0)
                self.finished_signal.emit()
                self.queue.task_done()

            except queue.Empty:
                continue

    def stop(self):
        self.running = False
        self.stop_speaking()
        self.wait()
