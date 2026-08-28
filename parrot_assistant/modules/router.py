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

        # We can periodically check, or check right before generating.
        # For simplicity, we check before generating.

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
        """Routes the query based on current network status."""
        is_connected = self.check_connection()

        if is_connected:
            print("[Router] Sending to Online LLM")
            response = self.llm_online.generate(query, system_prompt)
            # If the online model fails and returns a specific error string, we might fallback here too
            if "encountered an error" in response:
                print("[Router] Online LLM failed, falling back to Offline LLM")
                response = self.llm_offline.generate(query, system_prompt)
        else:
            print("[Router] Offline mode, sending to Local LLM")
            response = self.llm_offline.generate(query, system_prompt)

        self.response_generated.emit(response)
