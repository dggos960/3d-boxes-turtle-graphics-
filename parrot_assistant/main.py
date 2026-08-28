import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, Signal, Slot, QTimer, QThread

from config import WORKSPACE_DIR
from modules.stt_engine import STTEngineThread
from modules.tts_engine import TTSEngineThread
from modules.wake_word import WakeWordDetector
from modules.intent_classifier import IntentClassifier
from modules.router import Router, NetworkCheckThread
from modules.memory import MemoryManager
from modules.system_tools import SystemTools
from modules.scraper import WebScraper
from modules.ui_overlay import HighTechDashboard
import queue
import psutil

class ScraperWorkerThread(QThread):
    result_generated = Signal(str, str, str) # query, result, original_text

    def __init__(self, scraper, parent=None):
        super().__init__(parent)
        self.scraper = scraper
        self.running = True
        self.queue = queue.Queue()

    def enqueue(self, query: str, original_text: str):
        self.queue.put((query, original_text))

    def run(self):
        while self.running:
            try:
                query, original_text = self.queue.get(timeout=0.5)
                search_results = self.scraper.search(query)
                self.result_generated.emit(query, search_results, original_text)
                self.queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[ScraperWorker Error] {e}")

    def stop(self):
        self.running = False
        self.wait()


class AssistantOrchestrator(QObject):
    """
    Central Event Loop, Async Orchestration & Thread Management.
    Connects UI signals with STT, TTS, Router, Tools, and Memory in a thread-safe manner.
    """
    def __init__(self, ui):
        super().__init__()
        self.ui = ui

        # Core Managers
        self.memory = MemoryManager()
        self.tools = SystemTools(WORKSPACE_DIR)
        self.scraper = WebScraper()
        self.router = Router()

        # Threads
        self.stt_thread = STTEngineThread()
        self.tts_thread = TTSEngineThread()
        self.wake_detector = WakeWordDetector()
        self.network_thread = NetworkCheckThread()

        self.scraper_worker = ScraperWorkerThread(self.scraper)

        self._setup_connections()

        # System Metrics Timer
        self.metrics_timer = QTimer(self)
        self.metrics_timer.timeout.connect(self.update_metrics)
        self.metrics_timer.start(1000) # Update every 1 second

        self.scraper_worker.start()

        self.ui.update_status("Starting up...")
        self.stt_thread.start()
        self.tts_thread.start()
        self.network_thread.start()

    @Slot()
    def update_metrics(self):
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        self.ui.update_metrics(cpu, ram)

    def _setup_connections(self):
        # UI Operations Logging
        self.stt_thread.log_signal.connect(self.ui.log_operation)
        self.tts_thread.log_signal.connect(self.ui.log_operation)
        # STT -> Wake Detector
        self.stt_thread.text_signal.connect(self.wake_detector.process_text)

        # Visualizer mapping (Mic or TTS output)
        self.stt_thread.intensity_signal.connect(self.ui.update_visualizer)
        self.tts_thread.intensity_signal.connect(self.ui.update_visualizer)

        # Wake Detector Actions
        self.wake_detector.stop_signal.connect(self.handle_stop)
        self.wake_detector.wake_signal.connect(self.handle_wake)

        # LLM Router
        self.router.response_generated.connect(self.handle_llm_response)

        # Network Status
        self.network_thread.status_changed.connect(self.update_network_status)

        # Scraper routing
        self.scraper_worker.result_generated.connect(self.handle_search_result)

        # We need a slot to process text when awake, we can dynamically connect/disconnect or use state.
        self.is_awake = False
        self.stt_thread.text_signal.connect(self.process_awake_text)

    @Slot()
    def handle_stop(self):
        self.tts_thread.stop_speaking()
        self.is_awake = False
        self.ui.update_status(f"Listening... [Offline]" if not self.router.is_online else "Listening... [Online]")

    @Slot()
    def handle_wake(self):
        self.is_awake = True
        self.ui.update_status("Awake. How can I help?")
        # Clear short term context on new conversation? Optional.
        # self.memory.clear_short_term()

    @Slot(str)
    def process_awake_text(self, text):
        if not self.is_awake:
            return

        # Ignore if it's just the wake word alone that triggered it
        if text.lower().strip() == "hey assistant":
             return

        self.ui.update_status("Processing...")
        self.memory.add_to_short_term("user", text)

        intent = IntentClassifier.classify(text)
        print(f"[Intent Classifier] Evaluated intent: {intent}")

        context = self.memory.get_short_term_context()

        if intent == "SEARCH":
            # Very basic extraction for demo. In prod, use LLM to extract query.
            query = text.replace("search", "").strip()
            self.scraper_worker.enqueue(query, text)
            # Will be handled by handle_search_result slot

        elif intent == "SYS_CMD":
            # Needs LLM to formulate tool payload
            prompt = f"User asked: {text}. Convert this into a direct tool action if possible, else just reply."
            self.router.route_query(prompt, "You are a system assistant. You can direct the user how to do things.")
            # In a full implementation, you'd parse LLM JSON output to call self.tools methods.

        else: # CHAT
            self.router.route_query(text, f"You are a helpful desktop assistant. Recent context:\n{context}")

        self.is_awake = False # Wait for next wake word

    @Slot(str, str, str)
    def handle_search_result(self, query, search_results, original_text):
        prompt = f"User asked: {original_text}\nSearch Results:\n{search_results}\nSynthesize a short answer."
        self.router.route_query(prompt, "You are an assistant summarizing search results.")

    @Slot(str)
    def handle_llm_response(self, response):
        self.memory.add_to_short_term("assistant", response)
        self.ui.update_response(response)
        self.tts_thread.speak(response)
        mode = "[Online]" if self.router.is_online else "[Offline]"
        self.ui.update_status(f"Listening... {mode}")

    @Slot(bool)
    def update_network_status(self, is_online):
        self.ui.update_network(is_online)
        mode = "[Online]" if is_online else "[Offline]"
        if not self.is_awake:
             self.ui.update_status(f"Listening... {mode}")

    def cleanup(self):
        self.stt_thread.stop()
        self.tts_thread.stop()
        self.network_thread.quit()
        self.network_thread.wait()
        self.scraper_worker.stop()
        self.router.cleanup()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # We must only show UI if we are in an environment that supports it.
    if "--help" not in sys.argv:
        ui = HighTechDashboard()
        ui.show()
        orchestrator = AssistantOrchestrator(ui)

        # Cleanup on exit
        app.aboutToQuit.connect(orchestrator.cleanup)
        sys.exit(app.exec())
    else:
        print("Assistant configured successfully. Run without arguments to start.")
        sys.exit(0)
