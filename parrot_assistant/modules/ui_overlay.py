from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Qt, Slot, QTimer
from PySide6.QtGui import QColor, QPalette

class OverlayUI(QWidget):
    """
    PySide6 transparent HUD with futuristic dark theme.
    Displays dynamic visualizer bar and status indicators.
    """
    def __init__(self):
        super().__init__()

        # Transparent HUD setup
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Dimensions and positioning (bottom right corner for example)
        self.setGeometry(100, 100, 300, 150)

        # Layout
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Status Label
        self.status_label = QLabel("Initializing...")
        self.status_label.setStyleSheet("color: #00ffcc; font-size: 14px; font-weight: bold; background-color: rgba(0,0,0,150); padding: 5px; border-radius: 5px;")
        self.layout.addWidget(self.status_label)

        # Response Label
        self.response_label = QLabel("")
        self.response_label.setWordWrap(True)
        self.response_label.setStyleSheet("color: white; font-size: 12px; background-color: rgba(0,0,0,150); padding: 5px; border-radius: 5px;")
        self.layout.addWidget(self.response_label)

        # Visualizer Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #00ffcc;
                border-radius: 3px;
                background-color: rgba(0,0,0,150);
                height: 10px;
            }
            QProgressBar::chunk {
                background-color: #00ffcc;
            }
        """)
        self.layout.addWidget(self.progress_bar)

        self._smooth_val = 0.0

        # Decay timer for smooth visualizer animation
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.decay_visualizer)
        self.timer.start(50)

    @Slot(float)
    def update_visualizer(self, intensity: float):
        """Updates the visualizer bar based on RMS intensity (0.0 to 1.0)"""
        # Scale intensity to 0-100. Apply a multiplier for better visibility.
        target_val = min(100, int(intensity * 300))
        # Instant jump up
        if target_val > self._smooth_val:
             self._smooth_val = target_val
        self.progress_bar.setValue(int(self._smooth_val))

    def decay_visualizer(self):
        """Gradually reduces the visualizer value to create a smooth animation."""
        if self._smooth_val > 0:
            self._smooth_val -= 5
            if self._smooth_val < 0:
                self._smooth_val = 0
            self.progress_bar.setValue(int(self._smooth_val))

    @Slot(str)
    def update_status(self, text: str):
        self.status_label.setText(text)

    @Slot(str)
    def update_response(self, text: str):
        # Truncate for UI if too long
        display_text = text[:150] + "..." if len(text) > 150 else text
        self.response_label.setText(display_text)
