import cv2
import mediapipe as mp
import time
import numpy as np
from typing import Optional, Tuple, List, Any, Type

from src.utils import get_distance
from src.controller import SystemController
from src.config import (
    MAX_HANDS, DEFAULT_DET_CONF, DEFAULT_TRACK_CONF,
    DEFAULT_SWIPE_DIST, DEFAULT_SWIPE_COOLDOWN,
    DEFAULT_VOL_THRESHOLD, DEFAULT_VOL_SENSITIVITY,
    DEFAULT_FIST_COOLDOWN
)


class Tracker:
    """
    Hand tracking and gesture recognition engine using MediaPipe.

    Processes video frames to detect hand landmarks and translates
    specific movements into system-level commands like volume control,
    track switching, and playback toggling.
    """

    def __init__(
            self,
            control_type: Type[SystemController] = SystemController,
            mirror: bool = True,
            static_mode: bool = False,
            max_hands: int = MAX_HANDS,
            det_conf: float = DEFAULT_DET_CONF,
            track_conf: float = DEFAULT_TRACK_CONF
    ) -> None:
        """
        Initializes the tracker with MediaPipe Hands and gesture thresholds.

        Args:
            control_type: Class for system-level actions.
            mirror: If True, flips the input image horizontally.
            static_mode: If True, treats each image as unrelated (static).
            max_hands: Maximum number of hands to track.
            det_conf: Detection confidence threshold (0.0 to 1.0).
            track_conf: Tracking confidence threshold (0.0 to 1.0).
        """
        # 1. System Settings & Flags
        self.control_type = control_type
        self.mirror = mirror
        self.static_image = static_mode
        self.max_hands = max_hands
        self.min_det_conf = det_conf
        self.min_track_conf = track_conf

        # 2. MediaPipe Initialization
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            static_image_mode=self.static_image,
            max_num_hands=self.max_hands,
            min_detection_confidence=self.min_det_conf,
            min_tracking_confidence=self.min_track_conf
        )

        # 3. Internal State
        self.hand_was_present = False
        self.status_text = ""
        self.status_expire_time = 0.0

        # 4. Gesture State Machines
        self.swipe_distance = DEFAULT_SWIPE_DIST
        self.swipe_cooldown = DEFAULT_SWIPE_COOLDOWN
        self.prev_x_swipe = 0.0
        self.last_swipe_time = 0.0

        self.volume_distance_threshold = DEFAULT_VOL_THRESHOLD
        self.volume_sensitivity = DEFAULT_VOL_SENSITIVITY
        self.volume_mode = False
        self.prev_y_volume = 0.0

        self.fist_cooldown = DEFAULT_FIST_COOLDOWN
        self.fist_was_closed = False
        self.last_fist_time = 0.0

    def reinit_hands(self) -> None:
        """
        Safely reinitializes the MediaPipe Hands object.
        """
        if hasattr(self, 'hands') and self.hands:
            self.hands.close()

        self.hands = self.mp_hands.Hands(
            static_image_mode=self.static_image,
            max_num_hands=self.max_hands,
            min_detection_confidence=self.min_det_conf,
            min_tracking_confidence=self.min_track_conf
        )

    def set_status(self, text: str, duration: float = 2.0) -> None:
        """
        Sets a temporary status message to be displayed on the UI.
        """
        self.status_text = text
        self.status_expire_time = time.time() + duration

    def dispatch(self, image: np.ndarray, test_mode: bool = False) -> Tuple[Optional[Any], np.ndarray]:
        """
        Main pipeline: flips image, runs detection, and triggers gesture logic.

        Args:
            image: Input BGR frame.
            test_mode: If True, system actions are replaced by status messages.

        Returns:
            A tuple containing (MediaPipe results, processed image).
        """
        if self.mirror:
            image = cv2.flip(image, 1)

        img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        img_rgb.flags.writeable = False
        results = self.hands.process(img_rgb)
        img_rgb.flags.writeable = True

        if not results.multi_hand_landmarks:
            self.hand_was_present = False
            self.volume_mode = False
            self.fist_was_closed = False
            return None, image

        hand = results.multi_hand_landmarks[0]

        self.track_fist(hand, test_mode=test_mode)

        if not self.fist_was_closed:
            self.track_volume(hand, test_mode=test_mode)
            if not self.volume_mode:
                self.track_swipe(hand, test_mode=test_mode)

        if time.time() > self.status_expire_time:
            self.status_text = ""

        return results, image

    def draw(self, image: np.ndarray, results: Any, test_mode: bool = False) -> np.ndarray:
        """
        Draws landmarks and debug information on the frame.
        """
        if not results or not results.multi_hand_landmarks:
            return image

        hand = results.multi_hand_landmarks[0]

        self.mp_drawing.draw_landmarks(
            image,
            hand,
            self.mp_hands.HAND_CONNECTIONS,
            self.mp_drawing.DrawingSpec(
                color=(0, 0, 255) if test_mode else (0, 255, 100),
                thickness=2, circle_radius=2
            ),
            self.mp_drawing.DrawingSpec(color=(255, 255, 255), thickness=2)
        )

        if test_mode:
            h, w, _ = image.shape
            p4 = hand.landmark[4]
            p12 = hand.landmark[12]

            x4, y4 = int(p4.x * w), int(p4.y * h)
            x12, y12 = int(p12.x * w), int(p12.y * h)

            distance = get_distance(p4, p12)
            threshold = self.volume_distance_threshold

            if self.volume_mode:
                cv2.line(image, (x4, y4), (x12, y12), (0, 255, 0), 4)
                cv2.putText(image, "VOL MODE", (x12 + 10, y12 - 10),
                            cv2.FONT_HERSHEY_DUPLEX, 0.6, (0, 255, 0), 1, cv2.LINE_AA)
            elif distance < threshold * 2:
                cv2.line(image, (x4, y4), (x12, y12), (0, 255, 255), 2)
                cv2.putText(image, "READY", (x12 + 10, y12 - 10),
                            cv2.FONT_HERSHEY_DUPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)

        return image

    def if_fist_now(self, hand_landmarks: Any) -> bool:
        """
        Checks if the hand is currently forming a fist (fingers folded).
        """
        tips = [8, 12, 16, 20]
        bases = [5, 9, 13, 17]
        for t, b in zip(tips, bases):
            if hand_landmarks.landmark[t].y < hand_landmarks.landmark[b].y:
                return False
        return True

    def track_fist(self, hand_landmarks: Any, test_mode: bool = False) -> None:
        """
        Detects Fist gesture for toggling Play/Pause.
        """
        is_now_fist = self.if_fist_now(hand_landmarks)
        current_time = time.time()

        if is_now_fist:
            if not self.fist_was_closed and (current_time - self.last_fist_time > self.fist_cooldown):
                if not test_mode:
                    self.control_type.play_pause()
                else:
                    self.set_status("PLAY // PAUSE")

                self.last_fist_time = current_time
                self.fist_was_closed = True
        else:
            self.fist_was_closed = False

    def track_volume(self, hand_landmarks: Any, test_mode: bool = False) -> None:
        """
        Detects Volume gesture triggered by a pinch.
        """
        distance = get_distance(hand_landmarks.landmark[4], hand_landmarks.landmark[12])

        if distance < self.volume_distance_threshold:
            if not self.volume_mode:
                self.volume_mode = True
                self.prev_y_volume = hand_landmarks.landmark[12].y
        else:
            self.volume_mode = False

        if self.volume_mode:
            current_y = hand_landmarks.landmark[12].y
            dif_y = self.prev_y_volume - current_y

            if abs(dif_y) > self.volume_sensitivity:
                if dif_y > 0:  # Upward movement
                    if not test_mode:
                        self.control_type.volume_up()
                    else:
                        self.set_status("VOLUME UP")
                else:  # Downward movement
                    if not test_mode:
                        self.control_type.volume_down()
                    else:
                        self.set_status("VOLUME DOWN")

                self.prev_y_volume = current_y

    def track_swipe(self, hand_landmarks: Any, test_mode: bool = False) -> None:
        """
        Detects Swipe gestures based on horizontal movement.
        """
        current_x = (hand_landmarks.landmark[5].x + hand_landmarks.landmark[9].x) / 2

        if self.hand_was_present:
            dif = current_x - self.prev_x_swipe

            if abs(dif) > self.swipe_distance:
                if time.time() - self.last_swipe_time > self.swipe_cooldown:
                    self.last_swipe_time = time.time()

                    if dif > 0:  # Right
                        if not test_mode:
                            self.control_type.next_track()
                        else:
                            self.set_status("SWIPE RIGHT")
                    else:  # Left
                        if not test_mode:
                            self.control_type.prev_track()
                        else:
                            self.set_status("SWIPE LEFT")
        else:
            self.hand_was_present = True

        self.prev_x_swipe = current_x
