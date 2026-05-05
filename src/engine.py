import cv2
import time
from typing import Optional
from PyQt6.QtCore import QThread, pyqtSignal
from src.tracker import Tracker


class GestureEngine(QThread):
    """
    Main processing thread that bridges the camera feed, the gesture tracker,
    and the GUI signals.

    Handles the video capture loop, coordinates mode switching,
    and emits signals with processed frames and tracking data.
    """

    # Signals emit: (MediaPipe results, BGR frame, Tracker instance)
    data_signal = pyqtSignal(object, object, object)
    # Signals emit: Short string notifications (e.g., "VOLUME UP")
    status_signal = pyqtSignal(str)

    def __init__(self) -> None:
        """
        Initializes the engine with a default Tracker and control flags.
        """
        super().__init__()
        self.tracker = Tracker()

        self.session_mode = False
        self.test_mode = False
        self.draw_skeleton = True
        self.running = True
        self.last_sent_status = ""
        self.is_reinitializing = False

    def run(self) -> None:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return

        while self.running:
            if not self.session_mode or self.is_reinitializing:
                time.sleep(0.1)
                continue

            success, frame = cap.read()
            if not success:
                break

            try:
                results, frame = self.tracker.dispatch(frame, self.test_mode)

                current_status = getattr(self.tracker, 'status_text', "")
                if current_status and current_status != self.last_sent_status:
                    self.status_signal.emit(current_status)
                    self.last_sent_status = current_status
                if not current_status:
                    self.last_sent_status = ""

                if self.draw_skeleton:
                    frame = self.tracker.draw(frame, results, self.test_mode)

                self.data_signal.emit(results, frame, self.tracker)
            except Exception as e:
                print(f"Frame processing error: {e}")

            time.sleep(0.01)

        cap.release()

    def stop(self) -> None:
        """
        Safely stops the thread loop and waits for completion.
        """
        self.running = False
        self.wait()

    def set_session_mode(self, state: bool) -> None:
        """
        Toggles the global active state of the tracking session.
        """
        self.session_mode = state
        if not state:
            self.test_mode = False

    def set_test_mode(self, state: bool) -> None:
        """
        Toggles Calibration (Test) mode.
        Enabling Test mode automatically activates the session.
        """
        self.test_mode = state
        self.session_mode = state

    def update_mediapipe_conf(self, det_conf: Optional[float] = None, track_conf: Optional[float] = None) -> None:
        """
        Updates confidence thresholds with thread safety.
        """

        self.is_reinitializing = True
        time.sleep(0.05)

        if det_conf is not None:
            self.tracker.min_det_conf = det_conf
        if track_conf is not None:
            self.tracker.min_track_conf = track_conf

        self.tracker.reinit_hands()

        self.is_reinitializing = False

    def set_logic_params(
            self,
            swipe_dist: Optional[float] = None,
            vol_dist: Optional[float] = None,
            vol_sens: Optional[float] = None
    ) -> None:
        """
        Updates gesture sensitivity parameters in the tracker.
        """
        if swipe_dist is not None:
            self.tracker.swipe_distance = swipe_dist
        if vol_dist is not None:
            self.tracker.volume_distance_threshold = vol_dist
        if vol_sens is not None:
            self.tracker.volume_sensitivity = vol_sens
