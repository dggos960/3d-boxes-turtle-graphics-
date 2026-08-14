#!/usr/bin/env python3
"""
Parrot OS Alarm & Relaxation Suite (PyQt5 Edition)
Features:
 - Dedicated "Stop Playing Alarm" button on the Alarms page
 - Working Transparency Toggle & Restore Standard View Engine
 - 100% Window-Filling Wallpaper Canvas (No black bars or borders)
 - Clean Process Cleanup (Prevents lingering paplay background audio)
 - Dynamic Sound Selector inside Nap Mode
 - Independent Audio Volume Controls
"""

import sys
import os
import json
import glob
import subprocess
import math
import wave
import struct
import random
import shutil
from datetime import datetime

# Enforce X11 compatibility mode for Linux / Wayland environments
os.environ["QT_QPA_PLATFORM"] = "xcb;wayland"

from PyQt5.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QTime, QUrl
)
from PyQt5.QtGui import (
    QPixmap, QMovie, QFont
)
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem, QComboBox,
    QTimeEdit, QLineEdit, QTabWidget, QProgressBar, QSlider,
    QFileDialog, QFrame, QCheckBox, QDialog
)
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget

# ------------------------------------------------------------------------------
# ALARM DIALOG
# ------------------------------------------------------------------------------
class AlarmDialog(QDialog):
    def __init__(self, title, message, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(self.windowFlags() | Qt.CustomizeWindowHint)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowCloseButtonHint)

        self.setModal(True)
        self.setFixedSize(300, 150)

        layout = QVBoxLayout(self)

        lbl_message = QLabel(message, self)
        lbl_message.setAlignment(Qt.AlignCenter)
        lbl_message.setWordWrap(True)
        layout.addWidget(lbl_message)

        btn_layout = QHBoxLayout()

        self.btn_snooze = QPushButton("Snooze (5 mins)", self)
        self.btn_snooze.clicked.connect(self.snooze)

        self.btn_dismiss = QPushButton("Dismiss", self)
        self.btn_dismiss.clicked.connect(self.dismiss)

        btn_layout.addWidget(self.btn_snooze)
        btn_layout.addWidget(self.btn_dismiss)

        layout.addLayout(btn_layout)

        self.result_action = None

    def snooze(self):
        self.result_action = "snooze"
        self.accept()

    def dismiss(self):
        self.result_action = "dismiss"
        self.accept()

    def closeEvent(self, event):
        if self.result_action is None:
            event.ignore()
        else:
            super().closeEvent(event)


# ------------------------------------------------------------------------------
# CONSTANTS & DIRECTORY SETUP
# ------------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ALARM_DIR = os.path.join(BASE_DIR, "alarm_ringtone")
RELAX_DIR = os.path.join(BASE_DIR, "relaxing_music")
BG_DIR = os.path.join(BASE_DIR, "backgrounds")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

for directory in [ALARM_DIR, RELAX_DIR, BG_DIR]:
    os.makedirs(directory, exist_ok=True)


# ------------------------------------------------------------------------------
# DEFAULT NATURE AUDIO GENERATOR
# ------------------------------------------------------------------------------
def generate_nature_fallback_sounds():
    """Generates synthetic rain and ocean ambient audio files if folder is empty."""
    rain_path = os.path.join(RELAX_DIR, "Rain_Storm_Ambient.wav")
    waves_path = os.path.join(RELAX_DIR, "Ocean_Waves_Relax.wav")

    if not os.path.exists(rain_path):
        sample_rate = 22050
        duration = 5
        num_samples = sample_rate * duration
        with wave.open(rain_path, 'w') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            for _ in range(num_samples):
                val = int((random.random() * 2.0 - 1.0) * 4000)
                wav.writeframes(struct.pack('<h', val))

    if not os.path.exists(waves_path):
        sample_rate = 22050
        duration = 6
        num_samples = sample_rate * duration
        with wave.open(waves_path, 'w') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            for i in range(num_samples):
                t = i / sample_rate
                modulation = (math.sin(2 * math.pi * 0.1 * t) + 1.0) / 2.0
                val = int(((random.random() * 2.0 - 1.0) * 5000) * modulation)
                wav.writeframes(struct.pack('<h', val))


generate_nature_fallback_sounds()


# ------------------------------------------------------------------------------
# AUDIO WORKER THREAD
# ------------------------------------------------------------------------------
class PaplayThread(QThread):
    finished_signal = pyqtSignal()

    def __init__(self, file_path, loop=False, volume=100):
        super().__init__()
        self.file_path = file_path
        self.loop = loop
        self.volume = volume
        self._is_running = True
        self.process = None

    def set_volume(self, volume):
        self.volume = volume
        if self.process and self.process.poll() is None:
            try:
                self.process.kill()
            except Exception:
                pass

    def run(self):
        if not self.file_path or not os.path.exists(self.file_path):
            self.finished_signal.emit()
            return

        while self._is_running:
            pa_vol = int((self.volume / 100.0) * 65536)
            cmd = ["paplay", f"--volume={pa_vol}", self.file_path]
            try:
                self.process = subprocess.Popen(cmd, start_new_session=True)
                self.process.wait()
            except Exception as e:
                print(f"[Audio Error] {e}")
                break

            if not self.loop or not self._is_running:
                break

        self.finished_signal.emit()

    def stop(self):
        self._is_running = False
        if self.process and self.process.poll() is None:
            try:
                self.process.kill()
            except Exception:
                pass
        self.quit()
        self.wait()


# ------------------------------------------------------------------------------
# FULL-SCREEN FITTED DYNAMIC BACKGROUND CANVAS
# ------------------------------------------------------------------------------
class DynamicBackgroundWidget(QWidget):
    background_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_path = None
        self.current_pixmap = None
        self.current_movie = None

        self.lbl_bg = QLabel(self)
        self.lbl_bg.setAlignment(Qt.AlignCenter)
        self.lbl_bg.setScaledContents(True)

        self.video_widget = QVideoWidget(self)
        self.video_widget.setAspectRatioMode(Qt.IgnoreAspectRatio)
        self.media_player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.media_player.setVideoOutput(self.video_widget)
        self.media_player.mediaStatusChanged.connect(self._handle_video_loop)

        self.video_widget.hide()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.background_clicked.emit()
        super().mousePressEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.lbl_bg.setGeometry(0, 0, self.width(), self.height())
        self.video_widget.setGeometry(0, 0, self.width(), self.height())
        self._rescale_image()

    def set_background(self, file_path):
        self._stop_current()
        self.current_path = file_path

        if not file_path or not os.path.exists(file_path):
            self.lbl_bg.show()
            self.video_widget.hide()
            self.lbl_bg.setText("Click anywhere to change wallpaper / GIF / video")
            self.lbl_bg.setStyleSheet("background: #050508; color: #888; font-size: 16px;")
            return

        ext = os.path.splitext(file_path)[1].lower()

        if ext in ['.png', '.jpg', '.jpeg', '.bmp', '.webp']:
            self.video_widget.hide()
            self.lbl_bg.show()
            self.current_pixmap = QPixmap(file_path)
            self._rescale_image()

        elif ext == '.gif':
            self.video_widget.hide()
            self.lbl_bg.show()
            self.current_movie = QMovie(file_path)
            self.lbl_bg.setMovie(self.current_movie)
            self.current_movie.start()

        elif ext in ['.mp4', '.mkv', '.avi', '.webm', '.mov']:
            self.lbl_bg.hide()
            self.video_widget.show()
            if self.media_player.isAvailable():
                self.media_player.setMedia(QMediaContent(QUrl.fromLocalFile(file_path)))
                self.media_player.play()

    def _rescale_image(self):
        if self.current_pixmap and not self.current_pixmap.isNull():
            scaled = self.current_pixmap.scaled(
                self.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation
            )
            self.lbl_bg.setPixmap(scaled)

    def _handle_video_loop(self, status):
        if status == QMediaPlayer.EndOfMedia:
            self.media_player.setPosition(0)
            self.media_player.play()

    def _stop_current(self):
        if self.current_movie:
            self.current_movie.stop()
            self.current_movie = None
        if self.media_player.state() == QMediaPlayer.PlayingState:
            self.media_player.stop()


# ------------------------------------------------------------------------------
# MAIN APPLICATION WINDOW
# ------------------------------------------------------------------------------
class ParrotSuite(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Parrot OS Alarm & Relaxation Suite")
        self.setGeometry(100, 100, 950, 650)

        self.background_files = []
        self.bg_index = 0
        self.is_transparent_mode = False

        self.alarm_thread = None
        self.relax_thread = None
        self.nap_thread = None

        self.nap_remaining_seconds = 0
        self.nap_timer = QTimer(self)
        self.nap_timer.timeout.connect(self._update_nap_timer)

        self.alarm_stop_timer = QTimer(self)
        self.alarm_stop_timer.setSingleShot(True)
        self.alarm_stop_timer.timeout.connect(self._stop_alarm)

        self.config = self._load_config()

        self._init_ui()
        self._load_files()
        self._apply_theme(self.config.get("theme", "Dark Cyberpunk"))

        self.last_triggered_min = None

        self.temporary_alarms = []

        # Master Alarm Check Loop
        self.master_timer = QTimer(self)
        self.master_timer.timeout.connect(self._check_alarms)
        self.master_timer.start(1000)

    def _init_ui(self):
        # Base Background Canvas
        self.bg_widget = DynamicBackgroundWidget(self)
        self.bg_widget.background_clicked.connect(self._cycle_background)
        self.setCentralWidget(self.bg_widget)

        # Glass Panel Wrapper Layout
        main_layout = QVBoxLayout(self.bg_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)

        self.overlay_panel = QWidget(self.bg_widget)
        self.overlay_panel.setObjectName("glassPanel")
        main_layout.addWidget(self.overlay_panel)

        panel_layout = QVBoxLayout(self.overlay_panel)

        self.tabs = QTabWidget()
        panel_layout.addWidget(self.tabs)

        self._build_alarm_tab()
        self._build_relaxation_tab()
        self._build_nap_tab()
        self._build_settings_tab()

    def _build_alarm_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Alarm Status Indicator
        self.lbl_alarm_status = QLabel("Status: Idle", tab)
        self.lbl_alarm_status.setFont(QFont("Arial", 11, QFont.Bold))
        layout.addWidget(self.lbl_alarm_status)

        input_box = QHBoxLayout()
        self.time_edit = QTimeEdit(QTime.currentTime())
        self.txt_label = QLineEdit()
        self.txt_label.setPlaceholderText("Alarm Label (e.g., Wake Up)")
        self.cmb_alarm_sound = QComboBox()

        btn_add = QPushButton("Add Alarm")
        btn_add.clicked.connect(self._add_alarm)

        input_box.addWidget(QLabel("Time:"))
        input_box.addWidget(self.time_edit)
        input_box.addWidget(self.txt_label)
        input_box.addWidget(QLabel("Sound:"))
        input_box.addWidget(self.cmb_alarm_sound)
        input_box.addWidget(btn_add)
        layout.addLayout(input_box)

        self.alarm_list = QListWidget()
        layout.addWidget(self.alarm_list)

        # Controls: Stop Alarm & Delete
        h_alarm_btns = QHBoxLayout()

        self.btn_stop_alarm = QPushButton("STOP PLAYING ALARM")
        self.btn_stop_alarm.setStyleSheet("background-color: #FF3366; color: white; font-weight: bold; font-size: 14px; padding: 8px;")
        self.btn_stop_alarm.clicked.connect(self._stop_alarm)
        self.btn_stop_alarm.setEnabled(False)

        btn_delete = QPushButton("Delete Selected Alarm")
        btn_delete.clicked.connect(self._delete_alarm)

        h_alarm_btns.addWidget(self.btn_stop_alarm)
        h_alarm_btns.addWidget(btn_delete)
        layout.addLayout(h_alarm_btns)

        self.tabs.addTab(tab, "Alarms")

    def _build_relaxation_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        layout.addWidget(QLabel("<b>Relaxation & Ambient Tracks</b>"))
        self.relax_list = QListWidget()
        layout.addWidget(self.relax_list)

        h_ctrls = QHBoxLayout()
        btn_play = QPushButton("Play Track")
        btn_play.clicked.connect(self._play_relax)
        btn_stop = QPushButton("Stop Sound")
        btn_stop.clicked.connect(self._stop_relax)
        btn_nap = QPushButton("Go To Nap Page ->")
        btn_nap.clicked.connect(lambda: self.tabs.setCurrentIndex(2))

        h_ctrls.addWidget(btn_play)
        h_ctrls.addWidget(btn_stop)
        h_ctrls.addWidget(btn_nap)
        layout.addLayout(h_ctrls)

        self.tabs.addTab(tab, "Relaxation")

    def _build_nap_tab(self):
        tab = QWidget()
        tab.setObjectName("napTab")

        outer_layout = QVBoxLayout(tab)
        outer_layout.setAlignment(Qt.AlignCenter)

        self.hud_box = QFrame()
        self.hud_box.setObjectName("napHudBox")
        self.hud_box.setFixedWidth(500)

        hud_layout = QVBoxLayout(self.hud_box)
        hud_layout.setContentsMargins(25, 20, 25, 20)

        # Countdown Timer Display
        self.lbl_nap_countdown = QLabel("00:00")
        self.lbl_nap_countdown.setAlignment(Qt.AlignCenter)
        self.lbl_nap_countdown.setStyleSheet("font-size: 54px; font-weight: bold; color: #00FF99;")
        hud_layout.addWidget(self.lbl_nap_countdown)

        self.nap_progress_bar = QProgressBar()
        hud_layout.addWidget(self.nap_progress_bar)

        # Selectors
        h_ctrls = QHBoxLayout()

        self.cmb_nap_duration = QComboBox()
        self.cmb_nap_duration.addItems(["5 Mins", "10 Mins", "15 Mins", "20 Mins", "30 Mins", "45 Mins", "60 Mins"])

        self.cmb_nap_music = QComboBox()
        self.cmb_nap_music.addItem("None")
        self.cmb_nap_music.currentIndexChanged.connect(self._change_nap_music_live)

        h_ctrls.addWidget(QLabel("Duration:"))
        h_ctrls.addWidget(self.cmb_nap_duration)
        h_ctrls.addWidget(QLabel("Sound:"))
        h_ctrls.addWidget(self.cmb_nap_music)
        hud_layout.addLayout(h_ctrls)

        # Volume Slider
        h_vol = QHBoxLayout()
        h_vol.addWidget(QLabel("Volume:"))
        self.slider_nap_vol = QSlider(Qt.Horizontal)
        self.slider_nap_vol.setRange(0, 100)
        self.slider_nap_vol.setValue(self.config.get("bg_volume", 75))
        self.slider_nap_vol.valueChanged.connect(self._update_nap_volume)
        h_vol.addWidget(self.slider_nap_vol)
        hud_layout.addLayout(h_vol)

        # Action & Transparency Toggle Buttons
        h_btns = QHBoxLayout()
        self.btn_start_nap = QPushButton("Start Nap")
        self.btn_start_nap.clicked.connect(self._start_nap_timer)
        self.btn_stop_nap = QPushButton("Stop Nap")
        self.btn_stop_nap.clicked.connect(self._stop_nap_timer)

        h_btns.addWidget(self.btn_start_nap)
        h_btns.addWidget(self.btn_stop_nap)
        hud_layout.addLayout(h_btns)

        # Dynamic Transparency Control Button
        self.btn_toggle_transparency = QPushButton("Enable Ultra-Transparent Mode")
        self.btn_toggle_transparency.clicked.connect(self._toggle_transparency_mode)
        hud_layout.addWidget(self.btn_toggle_transparency)

        outer_layout.addWidget(self.hud_box)
        self.tabs.addTab(tab, "Nap Mode")

    def _build_settings_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        vol_group = QVBoxLayout()
        vol_group.addWidget(QLabel("<b>Independent Audio Controls</b>"))

        # Alarm Volume
        h_vol1 = QHBoxLayout()
        h_vol1.addWidget(QLabel("Alarm Voice/Volume:"))
        self.slider_alarm_vol = QSlider(Qt.Horizontal)
        self.slider_alarm_vol.setRange(0, 100)
        self.slider_alarm_vol.setValue(self.config.get("alarm_volume", 100))
        self.slider_alarm_vol.valueChanged.connect(self._save_audio_settings)
        h_vol1.addWidget(self.slider_alarm_vol)
        vol_group.addLayout(h_vol1)

        # Relaxation Volume
        h_vol2 = QHBoxLayout()
        h_vol2.addWidget(QLabel("Relaxation Sound/Volume:"))
        self.slider_bg_vol = QSlider(Qt.Horizontal)
        self.slider_bg_vol.setRange(0, 100)
        self.slider_bg_vol.setValue(self.config.get("bg_volume", 75))
        self.slider_bg_vol.valueChanged.connect(self._save_audio_settings)
        h_vol2.addWidget(self.slider_bg_vol)
        vol_group.addLayout(h_vol2)

        layout.addLayout(vol_group)
        layout.addSpacing(20)

        # Theme Selector
        h_theme = QHBoxLayout()
        h_theme.addWidget(QLabel("<b>Application Theme:</b>"))
        self.cmb_theme = QComboBox()
        self.cmb_theme.addItems(["Dark Cyberpunk", "Light Clean", "Parrot Green"])
        self.cmb_theme.setCurrentText(self.config.get("theme", "Dark Cyberpunk"))
        self.cmb_theme.currentTextChanged.connect(self._apply_theme)
        h_theme.addWidget(self.cmb_theme)
        layout.addLayout(h_theme)

        btn_bg = QPushButton("Browse & Add Wallpaper / GIF / Video")
        btn_bg.clicked.connect(self._add_custom_background)
        layout.addWidget(btn_bg)

        layout.addStretch()
        self.tabs.addTab(tab, "Settings")

    # --------------------------------------------------------------------------
    # FILE & BACKGROUND LOGIC
    # --------------------------------------------------------------------------
    def _load_files(self):
        valid_exts = ("*.png", "*.jpg", "*.jpeg", "*.bmp", "*.gif", "*.webp",
                      "*.mp4", "*.mkv", "*.avi", "*.webm", "*.mov")
        self.background_files = []

        # Case insensitive file finding since Linux file system is usually case sensitive
        all_bg_files = os.listdir(BG_DIR)
        for f in all_bg_files:
            if f.lower().endswith(tuple(ext.replace("*", "") for ext in valid_exts)):
                self.background_files.append(os.path.join(BG_DIR, f))

        self.background_files = sorted(list(set(self.background_files)))

        if self.background_files:
            self.bg_widget.set_background(self.background_files[0])
        else:
            self.bg_widget.set_background(None)

        self.cmb_alarm_sound.clear()
        for f in glob.glob(os.path.join(ALARM_DIR, "*.*")):
            self.cmb_alarm_sound.addItem(os.path.basename(f), f)

        self.relax_list.clear()
        self.cmb_nap_music.clear()
        self.cmb_nap_music.addItem("None")

        for f in glob.glob(os.path.join(RELAX_DIR, "*.*")):
            item = QListWidgetItem(os.path.basename(f))
            item.setData(Qt.UserRole, f)
            self.relax_list.addItem(item)
            self.cmb_nap_music.addItem(os.path.basename(f), f)

        self.alarm_list.clear()
        for alarm in self.config.get("alarms", []):
            self.alarm_list.addItem(f"{alarm['time']} - {alarm['label']} [{alarm['sound']}]")

    def _cycle_background(self):
        if not self.background_files:
            return
        self.bg_index = (self.bg_index + 1) % len(self.background_files)
        self.bg_widget.set_background(self.background_files[self.bg_index])

    def _add_custom_background(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Background Media", BASE_DIR,
            "Media Files (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.mp4 *.mkv *.avi *.webm *.mov)"
        )
        if file_path and os.path.exists(file_path):
            try:
                dest = os.path.join(BG_DIR, os.path.basename(file_path))
                if file_path != dest:
                    shutil.copy(file_path, dest)
                self._load_files()
                self.bg_widget.set_background(dest)
            except Exception as e:
                print(f"[File Error] {e}")

    # --------------------------------------------------------------------------
    # TRANSPARENCY TOGGLE & NAP LOGIC
    # --------------------------------------------------------------------------
    def _toggle_transparency_mode(self):
        self.is_transparent_mode = not self.is_transparent_mode

        if self.is_transparent_mode:
            self.overlay_panel.setStyleSheet("background-color: transparent; border: none;")
            self.hud_box.setStyleSheet("background-color: transparent; border: none;")
            self.btn_toggle_transparency.setText("Restore Standard View")
        else:
            self.overlay_panel.setStyleSheet("")
            self.hud_box.setStyleSheet("")
            self.btn_toggle_transparency.setText("Enable Ultra-Transparent Mode")
            self._apply_theme(self.cmb_theme.currentText())

    def _update_nap_volume(self, val):
        self.slider_bg_vol.setValue(val)
        if self.nap_thread and self.nap_thread.isRunning():
            self.nap_thread.set_volume(val)

    def _change_nap_music_live(self, index):
        if self.nap_thread:
            self.nap_thread.stop()
            self.nap_thread = None

        file_path = self.cmb_nap_music.currentData()
        if file_path and os.path.exists(file_path):
            vol = self.slider_nap_vol.value()
            self.nap_thread = PaplayThread(file_path, loop=True, volume=vol)
            self.nap_thread.start()

    def _start_nap_timer(self):
        mins_text = self.cmb_nap_duration.currentText().split()[0]
        mins = int(mins_text)
        self.nap_remaining_seconds = mins * 60
        self.nap_progress_bar.setMaximum(self.nap_remaining_seconds)
        self.nap_progress_bar.setValue(self.nap_remaining_seconds)

        self._change_nap_music_live(self.cmb_nap_music.currentIndex())
        self.nap_timer.start(1000)
        self.btn_start_nap.setEnabled(False)

    def _update_nap_timer(self):
        if self.nap_remaining_seconds > 0:
            self.nap_remaining_seconds -= 1
            self.nap_progress_bar.setValue(self.nap_remaining_seconds)
            mins, secs = divmod(self.nap_remaining_seconds, 60)
            self.lbl_nap_countdown.setText(f"{mins:02d}:{secs:02d}")
        else:
            self.nap_timer.stop()
            self.lbl_nap_countdown.setText("Time's Up!")
            self.btn_start_nap.setEnabled(True)
            if self.nap_thread:
                self.nap_thread.stop()
                self.nap_thread = None
            self._trigger_nap_alarm()

    def _trigger_nap_alarm(self):
        vol = self.slider_alarm_vol.value()
        # Find default or first alarm sound
        sound_path = ""
        if self.cmb_alarm_sound.count() > 0:
            sound_path = self.cmb_alarm_sound.itemData(0)

        if sound_path and os.path.exists(sound_path):
            self.alarm_thread = PaplayThread(sound_path, loop=True, volume=vol)
            self.alarm_thread.start()

        dialog = AlarmDialog("Nap Finished!", "Your nap time is up!", self)
        dialog.exec_()

        if self.alarm_thread and self.alarm_thread.isRunning():
            self.alarm_thread.stop()
            self.alarm_thread = None

        if dialog.result_action == "snooze":
            # Add 5 minutes to nap
            self.nap_remaining_seconds = 5 * 60
            self.nap_progress_bar.setMaximum(self.nap_remaining_seconds)
            self.nap_progress_bar.setValue(self.nap_remaining_seconds)
            self.nap_timer.start(1000)
            self.btn_start_nap.setEnabled(False)

    def _stop_nap_timer(self):
        self.nap_timer.stop()
        self.lbl_nap_countdown.setText("00:00")
        self.btn_start_nap.setEnabled(True)
        if self.nap_thread:
            self.nap_thread.stop()
            self.nap_thread = None

    # --------------------------------------------------------------------------
    # ALARM CONTROLS
    # --------------------------------------------------------------------------
    def _add_alarm(self):
        time_str = self.time_edit.time().toString("HH:mm")
        label = self.txt_label.text().strip() or "Alarm"
        sound_path = self.cmb_alarm_sound.currentData() or ""
        sound_name = self.cmb_alarm_sound.currentText() or "Default"

        alarm_item = {"time": time_str, "label": label, "sound": sound_name, "path": sound_path}
        self.config.setdefault("alarms", []).append(alarm_item)
        self._save_config()

        self.alarm_list.addItem(f"{time_str} - {label} [{sound_name}]")

    def _delete_alarm(self):
        row = self.alarm_list.currentRow()
        if row >= 0:
            self.alarm_list.takeItem(row)
            if row < len(self.config.get("alarms", [])):
                del self.config["alarms"][row]
                self._save_config()

    def _check_alarms(self):
        now_str = datetime.now().strftime("%H:%M")
        if now_str == self.last_triggered_min:
            return

        all_alarms = self.config.get("alarms", []) + self.temporary_alarms
        for alarm in all_alarms:
            if alarm["time"] == now_str and datetime.now().second == 0:
                self.last_triggered_min = now_str
                # If this was a temporary snoozed alarm, remove it so it doesn't ring tomorrow
                if alarm in self.temporary_alarms:
                    self.temporary_alarms.remove(alarm)
                self._trigger_alarm(alarm)

    def _trigger_alarm(self, alarm):
        self._stop_alarm()
        vol = self.slider_alarm_vol.value()
        sound_path = alarm.get("path")

        if sound_path and os.path.exists(sound_path):
            self.alarm_thread = PaplayThread(sound_path, loop=True, volume=vol)
            self.alarm_thread.start()
            self.lbl_alarm_status.setText(f"Status: RINGING - {alarm['label']}")
            self.lbl_alarm_status.setStyleSheet("color: #FF3366; font-size: 14px;")
            self.btn_stop_alarm.setEnabled(True)

            dialog = AlarmDialog("Alarm Ringing!", f"Alarm: {alarm['label']} ({alarm['time']})", self)
            dialog.exec_()

            if dialog.result_action == "snooze":
                self._stop_alarm()
                # Calculate snooze time (+5 mins)
                now = datetime.now()
                snooze_time = QTime(now.hour, now.minute).addSecs(5 * 60)
                time_str = snooze_time.toString("HH:mm")

                snoozed_alarm = {
                    "time": time_str,
                    "label": f"Snoozed: {alarm['label']}",
                    "sound": alarm.get("sound", "Default"),
                    "path": alarm.get("path", "")
                }
                self.temporary_alarms.append(snoozed_alarm)

                # Refresh list
                self.alarm_list.clear()
                all_alarms = self.config.get("alarms", []) + self.temporary_alarms
                for a in all_alarms:
                    self.alarm_list.addItem(f"{a['time']} - {a['label']} [{a['sound']}]")
            else:
                self._stop_alarm()

    def _stop_alarm(self):
        if self.alarm_thread and self.alarm_thread.isRunning():
            self.alarm_thread.stop()
            self.alarm_thread = None

        if hasattr(self, 'lbl_alarm_status'):
            self.lbl_alarm_status.setText("Status: Idle")
            self.lbl_alarm_status.setStyleSheet("color: #00FF99;")
            self.btn_stop_alarm.setEnabled(False)

        subprocess.run(["killall", "-9", "paplay"], stderr=subprocess.DEVNULL)

    def _play_relax(self):
        item = self.relax_list.currentItem()
        if item:
            file_path = item.data(Qt.UserRole)
            self._stop_relax()
            vol = self.slider_bg_vol.value()
            self.relax_thread = PaplayThread(file_path, loop=True, volume=vol)
            self.relax_thread.start()

    def _stop_relax(self):
        if self.relax_thread and self.relax_thread.isRunning():
            self.relax_thread.stop()
            self.relax_thread = None

    # --------------------------------------------------------------------------
    # THEME ENGINE & CONFIG
    # --------------------------------------------------------------------------
    def _apply_theme(self, theme_name):
        self.config["theme"] = theme_name
        self._save_config()

        if self.is_transparent_mode:
            return

        if theme_name == "Dark Cyberpunk":
            stylesheet = """
                QWidget#glassPanel { background-color: rgba(18, 18, 18, 0.82); border-radius: 12px; border: 1px solid #00FF99; }
                QFrame#napHudBox { background-color: rgba(10, 15, 20, 0.35); border-radius: 16px; border: 1px solid rgba(0, 255, 153, 0.5); }
                QWidget { color: #00FF99; font-family: 'Consolas', monospace; }
                QTabWidget::pane { border: 1px solid #00FF99; background: transparent; }
                QPushButton { background-color: rgba(30, 30, 30, 0.8); border: 1px solid #00FF99; padding: 6px; border-radius: 4px; color: #00FF99; }
                QPushButton:hover { background-color: #00FF99; color: #000000; }
                QListWidget, QComboBox, QLineEdit, QTimeEdit { background-color: rgba(30, 30, 30, 0.85); border: 1px solid #333; color: #FFFFFF; }
                QSlider::handle:horizontal { background: #00FF99; height: 12px; width: 12px; }
            """
        elif theme_name == "Light Clean":
            stylesheet = """
                QWidget#glassPanel { background-color: rgba(245, 245, 245, 0.85); border-radius: 12px; border: 1px solid #CCC; }
                QFrame#napHudBox { background-color: rgba(255, 255, 255, 0.40); border-radius: 16px; border: 1px solid rgba(0, 122, 204, 0.5); }
                QWidget { color: #222222; font-family: 'Arial', sans-serif; }
                QTabWidget::pane { border: 1px solid #CCC; background: transparent; }
                QPushButton { background-color: rgba(220, 220, 220, 0.8); border: 1px solid #BBB; padding: 6px; border-radius: 4px; color: #222; }
                QPushButton:hover { background-color: #007ACC; color: #FFF; }
                QListWidget, QComboBox, QLineEdit, QTimeEdit { background-color: rgba(255, 255, 255, 0.85); border: 1px solid #CCC; color: #000; }
                QSlider::handle:horizontal { background: #007ACC; height: 12px; width: 12px; }
            """
        else:  # Parrot Green
            stylesheet = """
                QWidget#glassPanel { background-color: rgba(10, 25, 19, 0.85); border-radius: 12px; border: 1px solid #20E570; }
                QFrame#napHudBox { background-color: rgba(5, 15, 11, 0.35); border-radius: 16px; border: 1px solid rgba(32, 229, 112, 0.5); }
                QWidget { color: #20E570; font-family: 'Monospace'; }
                QTabWidget::pane { border: 1px solid #20E570; background: transparent; }
                QPushButton { background-color: rgba(13, 40, 30, 0.8); border: 1px solid #20E570; padding: 6px; color: #20E570; }
                QPushButton:hover { background-color: #20E570; color: #0A1913; }
                QListWidget, QComboBox, QLineEdit, QTimeEdit { background-color: rgba(5, 15, 11, 0.85); border: 1px solid #145233; color: #20E570; }
                QSlider::handle:horizontal { background: #20E570; height: 12px; width: 12px; }
            """
        self.setStyleSheet(stylesheet)

    def _save_audio_settings(self):
        alarm_vol = self.slider_alarm_vol.value()
        bg_vol = self.slider_bg_vol.value()

        self.config["alarm_volume"] = alarm_vol
        self.config["bg_volume"] = bg_vol
        self._save_config()

        if self.alarm_thread and self.alarm_thread.isRunning():
            self.alarm_thread.set_volume(alarm_vol)

        if self.relax_thread and self.relax_thread.isRunning():
            self.relax_thread.set_volume(bg_vol)

        if self.nap_thread and self.nap_thread.isRunning():
            self.nap_thread.set_volume(bg_vol)

    def _load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"theme": "Dark Cyberpunk", "alarm_volume": 100, "bg_volume": 75, "alarms": []}

    def _save_config(self):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def closeEvent(self, event):
        """Kills any active paplay audio subprocesses when the app closes."""
        self._stop_alarm()
        if self.relax_thread:
            self.relax_thread.stop()
        if self.nap_thread:
            self.nap_thread.stop()
        subprocess.run(["killall", "-9", "paplay"], stderr=subprocess.DEVNULL)
        super().closeEvent(event)


# ------------------------------------------------------------------------------
# ENTRY POINT
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ParrotSuite()
    window.show()
    sys.exit(app.exec_())
