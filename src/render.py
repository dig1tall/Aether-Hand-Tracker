import os
import numpy as np
from typing import Any
from PyQt6 import uic
from PyQt6.QtWidgets import QMainWindow, QLabel, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt, QTimer

from src.engine import GestureEngine
from src.config import (
    ASSETS_DIR, UI_MAIN_PATH, LOGO_PATH, ICON_PATH,
    DARK_MODE_ATTRIBUTE, STATUS_DURATION
)
from src.utils import (
    convert_cv_to_pixmap, apply_windows_dark_theme, force_refresh_style
)


class MainWindow(QMainWindow):
    """
    The main application window handling UI interactions, settings, and system tray integration.

    This class acts as the controller that links the GestureEngine data
    to the graphical user interface.
    """

    def __init__(self) -> None:
        """
        Initializes the UI, sets up the gesture engine, and connects signals/slots.
        """
        super().__init__()

        # 1. UI LOADING & STYLING
        uic.loadUi(UI_MAIN_PATH, self)

        bg_path = os.path.join(ASSETS_DIR, "background.png").replace("\\", "/")
        self.centralwidget.setStyleSheet(f"""
            #centralwidget {{
                border-image: url({bg_path});
            }}
        """)

        self.setWindowTitle("Aether")
        self.setWindowIcon(QIcon(ICON_PATH))
        self.setup_simple_logo()
        self.stackedWidget.setCurrentIndex(0)

        self.real_quit = False
        self.setup_tray()

        # 2. HELPER OBJECTS
        self.status_label_main = self._create_status_label(getattr(self, 'video_label', self))
        self.status_label_settings = self._create_status_label(getattr(self, 'video_settings_label', self))

        self.status_timer = QTimer()
        self.status_timer.setSingleShot(True)
        self.status_timer.timeout.connect(self._hide_all_status)

        # 3. ENGINE INITIALIZATION
        self.engine = GestureEngine()
        self.sync_settings_with_tracker()

        # 4. NAVIGATION & BUTTONS
        self.btn_start.clicked.connect(self.toggle_session)
        self.btn_settings.clicked.connect(lambda: self.switch_page(1, test_mode=True))
        self.btn_info.clicked.connect(lambda: self.switch_page(2))

        for btn_name in ['btn_back', 'btn_back_info']:
            btn = getattr(self, btn_name, None)
            if btn:
                btn.clicked.connect(lambda: self.switch_page(0))

        # 5. PARAMETERS & CHECKBOXES
        if hasattr(self, 'check_draw_skeleton'):
            self.check_draw_skeleton.stateChanged.connect(self.toggle_draw_landmarks)
        if hasattr(self, 'check_mirror'):
            self.check_mirror.stateChanged.connect(self.toggle_mirror)
        if hasattr(self, 'btn_quit'):
            self.btn_quit.clicked.connect(self.actual_quit)

        self.setup_param_signals()

        # 6. THREAD CONNECTION & START
        self.engine.data_signal.connect(self.update_frame)
        self.engine.status_signal.connect(self.show_status)
        self.engine.start()

    def setup_tray(self) -> None:
        """
        Initializes the system tray icon and its context menu.
        """
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(ICON_PATH))

        tray_menu = QMenu()
        tray_menu.addAction("Show Aether").triggered.connect(self.show_and_raise)
        tray_menu.addAction("Exit").triggered.connect(self.actual_quit)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()

    def show_and_raise(self) -> None:
        """
        Restores the window from tray and brings it to the foreground.
        """
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def on_tray_icon_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """
        Handles tray icon interaction events.
        """
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_and_raise()

    def actual_quit(self) -> None:
        """
        Triggers a complete application shutdown.
        """
        self.real_quit = True
        self.close()

    def setup_simple_logo(self) -> None:
        """
        Loads and displays the application logo.
        """
        pixmap = QPixmap(LOGO_PATH)
        if not pixmap.isNull() and hasattr(self, 'label'):
            self.label.setPixmap(pixmap)
            self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def closeEvent(self, event: Any) -> None:
        """
        Overlays the close event to either minimize to tray or exit the app.
        """
        if self.real_quit:
            self.engine.stop()
            self.tray_icon.hide()
            event.accept()
        else:
            if self.tray_icon.isVisible():
                self.hide()
                self.tray_icon.showMessage(
                    "Aether",
                    "Application minimized to tray.",
                    self.tray_icon.icon(),
                    2000
                )
                event.ignore()

    def switch_page(self, index: int, test_mode: bool = False) -> None:
        """
        Handles navigation between stacked widget pages and toggles engine modes.
        """
        self.stackedWidget.setCurrentIndex(index)
        self.engine.set_test_mode(test_mode)

        is_session_active = self.engine.session_mode
        self.btn_start.setText("STOP SESSION" if is_session_active else "START SESSION")
        self.btn_start.setProperty("active", is_session_active)

        self.btn_settings.setProperty("active", index == 1)
        self.btn_info.setProperty("active", index == 2)

        for b in [self.btn_settings, self.btn_info, self.btn_start]:
            force_refresh_style(b)

    def toggle_session(self) -> None:
        """
        Toggles the gesture tracking session state.
        """
        is_active = not self.engine.session_mode
        self.engine.set_session_mode(is_active)
        self.btn_start.setText("STOP SESSION" if is_active else "START SESSION")
        self.btn_start.setProperty("active", is_active)
        force_refresh_style(self.btn_start)

    def sync_settings_with_tracker(self) -> None:
        """
        Synchronizes UI widgets with the current Tracker internal values.
        """
        t = self.engine.tracker
        config = [
            (getattr(self, 'spn_vol_dist', None), t.volume_distance_threshold),
            (getattr(self, 'spn_vol_sens', None), t.volume_sensitivity),
            (getattr(self, 'spn_swipe_dist', None), t.swipe_distance),
            (getattr(self, 'spn_det_conf', None), t.min_det_conf),
            (getattr(self, 'spn_track_conf', None), t.min_track_conf)
        ]
        for widget, value in config:
            if widget:
                widget.blockSignals(True)
                widget.setValue(float(value))
                widget.blockSignals(False)

        if hasattr(self, 'check_draw_skeleton'):
            self.check_draw_skeleton.blockSignals(True)
            self.engine.draw_skeleton = True
            self.check_draw_skeleton.setChecked(True)
            self.check_draw_skeleton.setText("DRAW LANDMARKS: ON")
            self.check_draw_skeleton.blockSignals(False)

        if hasattr(self, 'check_mirror'):
            actual_mirror_state = self.engine.tracker.mirror
            self.check_mirror.blockSignals(True)
            self.check_mirror.setChecked(actual_mirror_state)
            self.check_mirror.setText(f"MIRROR: {'ON' if actual_mirror_state else 'OFF'}")
            self.check_mirror.blockSignals(False)

    def setup_param_signals(self) -> None:
        """
        Connects setting widgets to their respective application logic.
        """
        for w in [getattr(self, 'spn_det_conf', None), getattr(self, 'spn_track_conf', None)]:
            if w: w.valueChanged.connect(self.apply_mp_params)
        for w in [getattr(self, 'spn_swipe_dist', None), getattr(self, 'spn_vol_dist', None),
                  getattr(self, 'spn_vol_sens', None)]:
            if w: w.valueChanged.connect(self.apply_logic_params)

    def apply_mp_params(self) -> None:
        """
        Updates MediaPipe configuration from UI spinboxes.
        """
        self.engine.update_mediapipe_conf(self.spn_det_conf.value(), self.spn_track_conf.value())

    def apply_logic_params(self) -> None:
        """
        Updates gesture logic thresholds from UI spinboxes.
        """
        t = self.engine.tracker
        t.volume_distance_threshold = self.spn_vol_dist.value()
        t.volume_sensitivity = self.spn_vol_sens.value()
        t.swipe_distance = self.spn_swipe_dist.value()

    def toggle_draw_landmarks(self, state: int) -> None:
        """
        Toggles skeleton visualization on the video feed.
        """
        self.engine.draw_skeleton = (state == 2)
        self.check_draw_skeleton.setText(f"DRAW LANDMARKS: {'ON' if state == 2 else 'OFF'}")

    def toggle_mirror(self, state: int) -> None:
        """
        Toggles horizontal mirroring of the video feed.
        """
        self.engine.tracker.mirror = (state == 2)
        self.check_mirror.setText(f"MIRROR: {'ON' if state == 2 else 'OFF'}")

    def update_frame(self, results: Any, frame: np.ndarray, tracker: Any) -> None:
        """
        Updates the UI labels with the latest processed video frame.
        """
        target_attr = 'video_settings_label' if self.stackedWidget.currentIndex() == 1 else 'video_label'
        target = getattr(self, target_attr, None)
        if target and frame is not None:
            pixmap = convert_cv_to_pixmap(frame, target.width(), target.height())
            target.setPixmap(pixmap)

    def show_status(self, text: str) -> None:
        """
        Displays a floating status notification on the active video container.
        """
        self._hide_all_status()
        active = self.status_label_settings if self.stackedWidget.currentIndex() == 1 else self.status_label_main
        container = getattr(self, 'video_settings_label' if self.stackedWidget.currentIndex() == 1 else 'video_label',
                            self)

        active.setText(text)
        active.adjustSize()
        active.move((container.width() - active.width()) // 2, 20)
        active.show()
        active.raise_()
        self.status_timer.start(STATUS_DURATION)

    def _create_status_label(self, parent: Any) -> QLabel:
        """
        Factory method for creating styled status labels.
        """
        lbl = QLabel(parent)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.hide()
        lbl.setStyleSheet("""
            background: rgba(20,20,20,200); 
            color: #00FF88; 
            border-radius: 10px; 
            padding: 8px 15px; 
            border: 1px solid #00FF88;
        """)
        return lbl

    def _hide_all_status(self) -> None:
        """
        Hides all status notification labels.
        """
        self.status_label_main.hide()
        self.status_label_settings.hide()
