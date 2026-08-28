import sys
import os
from PySide6.QtCore import QObject, Signal, Slot

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import WAKE_WORD, STOP_WORD

class WakeWordDetector(QObject):
    """
    Evaluates transcribed text stream for wake words or stop commands.
    Provides barge-in functionality to halt TTS when user speaks.
    """
    wake_signal = Signal()
    stop_signal = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.active = False # True when TTS is speaking

    @Slot(str)
    def process_text(self, text):
        """Called whenever the STT engine emits transcribed text."""
        text = text.lower().strip()

        # Check for stop command (barge-in condition)
        if STOP_WORD in text:
            print(f"[WakeWord] Detected stop command: {text}")
            self.stop_signal.emit()
            return

        # Check for wake word
        if WAKE_WORD in text:
            print(f"[WakeWord] Detected wake word: {text}")
            # Even if the wake word is detected, we want to stop any ongoing TTS
            self.stop_signal.emit()
            self.wake_signal.emit()
