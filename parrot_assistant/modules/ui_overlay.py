from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                                 QLabel, QProgressBar, QTextEdit,
                                 QGroupBox, QListWidget)
from PySide6.QtCore import Qt, Slot, QTimer
from PySide6.QtGui import QFont, QColor

class HighTechDashboard(QWidget):
    """
    PySide6 High-Tech Dashboard.
    Displays chat history, dynamic visualizer, system metrics, and operation logs.
    """
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Parrot OS Assistant - Core Interface")
        self.setGeometry(100, 100, 1000, 600)

        # We can make it frameless if desired, but a window is easier for a full dashboard.
        # self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setStyleSheet("""
            QWidget {
                background-color: #0b0f19;
                color: #00ffcc;
                font-family: 'Consolas', 'Courier New', monospace;
            }
            QGroupBox {
                border: 1px solid #005577;
                border-radius: 5px;
                margin-top: 10px;
                font-weight: bold;
                color: #00ffcc;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
            }
            QTextEdit, QListWidget {
                background-color: #050a10;
                border: 1px solid #005577;
                color: #00ffcc;
            }
            QProgressBar {
                border: 1px solid #005577;
                border-radius: 2px;
                background-color: #050a10;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #00ffcc;
                width: 10px;
                margin: 0.5px;
            }
        """)

        main_layout = QHBoxLayout()
        self.setLayout(main_layout)

        # LEFT PANEL: Chat History
        left_layout = QVBoxLayout()
        self.chat_group = QGroupBox("COMMUNICATION LINK")
        chat_vbox = QVBoxLayout()
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        chat_vbox.addWidget(self.chat_display)
        self.chat_group.setLayout(chat_vbox)
        left_layout.addWidget(self.chat_group)

        # CENTER PANEL: Main Status & Visualizer
        center_layout = QVBoxLayout()

        self.status_group = QGroupBox("SYSTEM STATUS")
        status_vbox = QVBoxLayout()

        self.main_status_label = QLabel("INITIALIZING NEURAL NET...")
        self.main_status_label.setAlignment(Qt.AlignCenter)
        self.main_status_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #ff0055;")
        status_vbox.addWidget(self.main_status_label)

        self.network_label = QLabel("UPLINK: [OFFLINE]")
        self.network_label.setAlignment(Qt.AlignCenter)
        self.network_label.setStyleSheet("font-size: 14px; color: #aaaaaa;")
        status_vbox.addWidget(self.network_label)

        self.status_group.setLayout(status_vbox)
        center_layout.addWidget(self.status_group)

        # Visualizer
        self.vis_group = QGroupBox("AUDIO SPECTRAL ANALYSIS")
        vis_vbox = QVBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(30)
        vis_vbox.addWidget(self.progress_bar)
        self.vis_group.setLayout(vis_vbox)
        center_layout.addWidget(self.vis_group)

        # Operations Log (in center below visualizer)
        self.ops_group = QGroupBox("OPERATIONS LOG")
        ops_vbox = QVBoxLayout()
        self.ops_log = QListWidget()
        ops_vbox.addWidget(self.ops_log)
        self.ops_group.setLayout(ops_vbox)
        center_layout.addWidget(self.ops_group)

        # RIGHT PANEL: System Metrics
        right_layout = QVBoxLayout()
        self.sys_group = QGroupBox("HARDWARE METRICS")
        sys_vbox = QVBoxLayout()

        sys_vbox.addWidget(QLabel("CPU LOAD [%]"))
        self.cpu_bar = QProgressBar()
        self.cpu_bar.setRange(0, 100)
        sys_vbox.addWidget(self.cpu_bar)

        sys_vbox.addWidget(QLabel("RAM ALLOCATION [%]"))
        self.ram_bar = QProgressBar()
        self.ram_bar.setRange(0, 100)
        sys_vbox.addWidget(self.ram_bar)

        sys_vbox.addStretch()
        self.sys_group.setLayout(sys_vbox)
        right_layout.addWidget(self.sys_group)

        # Assemble Main Layout
        main_layout.addLayout(left_layout, 2)
        main_layout.addLayout(center_layout, 3)
        main_layout.addLayout(right_layout, 1)

        self._smooth_val = 0.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.decay_visualizer)
        self.timer.start(50)

    @Slot(float)
    def update_visualizer(self, intensity: float):
        target_val = min(100, int(intensity * 300))
        if target_val > self._smooth_val:
             self._smooth_val = target_val
        self.progress_bar.setValue(int(self._smooth_val))

    def decay_visualizer(self):
        if self._smooth_val > 0:
            self._smooth_val -= 5
            if self._smooth_val < 0:
                self._smooth_val = 0
            self.progress_bar.setValue(int(self._smooth_val))

    @Slot(str)
    def update_status(self, text: str):
        self.main_status_label.setText(text.upper())
        self.log_operation(f"Status Change: {text}")

    @Slot(str)
    def append_chat(self, text: str, role: str = "assistant"):
        color = "#00ffcc" if role == "assistant" else "#ff0055"
        prefix = "ASSISTANT" if role == "assistant" else "USER"
        self.chat_display.append(f"<span style='color:{color}'><b>[{prefix}]</b> {text}</span>")

    @Slot(str)
    def update_response(self, text: str):
        self.append_chat(text, role="assistant")

    @Slot(bool)
    def update_network(self, is_online: bool):
        if is_online:
            self.network_label.setText("UPLINK: [ONLINE]")
            self.network_label.setStyleSheet("font-size: 14px; color: #00ffcc;")
        else:
            self.network_label.setText("UPLINK: [OFFLINE]")
            self.network_label.setStyleSheet("font-size: 14px; color: #ff0055;")

    @Slot(str)
    def log_operation(self, text: str):
        """Adds an entry to the operations log."""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.ops_log.addItem(f"[{timestamp}] {text}")
        self.ops_log.scrollToBottom()

    @Slot(float, float)
    def update_metrics(self, cpu: float, ram: float):
        self.cpu_bar.setValue(int(cpu))
        self.ram_bar.setValue(int(ram))
