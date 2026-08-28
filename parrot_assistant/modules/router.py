import sys
import os
import socket
from PySide6.QtCore import QObject, Signal, Slot, QThread

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import PING_HOST, PING_PORT, PING_TIMEOUT
from modules.llm_online import LLMOnline
from modules.llm_offline import LLMOffline

class NetworkCheckThread(QThread):
    status_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_online = False

    def run(self):
        try:
            # Check internet connection by connecting to a public DNS
            socket.create_connection((PING_HOST, PING_PORT), timeout=PING_TIMEOUT)
            is_online = True
        except OSError:
            is_online = False

        if self.is_online != is_online:
            self.is_online = is_online
            self.status_changed.emit(self.is_online)


import queue

class LLMWorkerThread(QThread):
    response_generated = Signal(str)

    def __init__(self, router, parent=None):
        super().__init__(parent)
        self.router = router
        self.running = True
        self.queue = queue.Queue()

    def enqueue(self, query: str, system_prompt: str):
        self.queue.put((query, system_prompt))

    def run(self):
        while self.running:
            try:
                query, system_prompt = self.queue.get(timeout=0.5)

                is_connected = self.router.check_connection()

                if is_connected:
                    print("[Router] Sending to Online LLM")
                    response = self.router.llm_online.generate(query, system_prompt)
                    if "encountered an error" in response:
                        print("[Router] Online LLM failed, falling back to Offline LLM")
                        response = self.router.llm_offline.generate(query, system_prompt)
                else:
                    print("[Router] Offline mode, sending to Local LLM")
                    response = self.router.llm_offline.generate(query, system_prompt)

                self.response_generated.emit(response)
                self.queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[LLMWorker Error] {e}")

    def stop(self):
        self.running = False
        self.wait()


class Router(QObject):
    """
    Dual-engine manager handling internet connection checks and seamless fallback.
    """
    online_status_changed = Signal(bool)
    response_generated = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.llm_online = LLMOnline()
        self.llm_offline = LLMOffline()
        self.is_online = False

        self.worker = LLMWorkerThread(self)
        self.worker.response_generated.connect(self.response_generated.emit)
        self.worker.start()

    def check_connection(self):
        try:
            socket.create_connection((PING_HOST, PING_PORT), timeout=PING_TIMEOUT)
            status = True
        except OSError:
            status = False

        if self.is_online != status:
            self.is_online = status
            self.online_status_changed.emit(self.is_online)

        return status

    @Slot(str, str)
    def route_query(self, query: str, system_prompt: str = "You are a helpful AI assistant."):
        """Enqueues the query to be processed by the LLM worker thread."""
        self.worker.enqueue(query, system_prompt)

    def cleanup(self):
        self.worker.stop()
