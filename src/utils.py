import os
import sys
import math
import cv2
import ctypes
import numpy as np
from typing import Any
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import Qt


def get_resource_path(relative_path: str) -> str:
    """
    Resolves the absolute path to a resource file for both development and distribution.

    Args:
        relative_path: The path to the resource file relative to the project root
                        (e.g., 'assets/icon.png').

    Returns:
        A string containing the absolute path to the resource.
    """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(base_path), relative_path)


def get_distance(p1: Any, p2: Any) -> float:
    """
    Calculates the Euclidean distance between two MediaPipe landmarks in 3D space.

    Args:
        p1: The first landmark object (containing x, y, z attributes).
        p2: The second landmark object (containing x, y, z attributes).

    Returns:
        The distance between points as a float.
    """
    return math.sqrt(
        (p1.x - p2.x) ** 2 +
        (p1.y - p2.y) ** 2 +
        (p1.z - p2.z) ** 2
    )


def convert_cv_to_pixmap(frame: np.ndarray, width: int, height: int) -> QPixmap:
    """
    Converts an OpenCV BGR frame to a scaled PyQt6 QPixmap.

    Args:
        frame: Input image array in BGR format.
        width: Target width for scaling.
        height: Target height for scaling.

    Returns:
        A QPixmap formatted for display in a QLabel, maintaining aspect ratio.
    """
    rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb_image.shape
    bytes_per_line = ch * w

    qt_image = QImage(
        rgb_image.data,
        w, h,
        bytes_per_line,
        QImage.Format.Format_RGB888
    )

    return QPixmap.fromImage(qt_image).scaled(
        width, height,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation
    )


def apply_windows_dark_theme(window_id: Any) -> None:
    """
    Enables the dark theme for the Windows OS title bar via DWM API.

    Args:
        window_id: The Qt window or widget instance to apply the theme to.
    """
    try:
        from src.config import DARK_MODE_ATTRIBUTE
        hwnd = window_id.__int__()
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DARK_MODE_ATTRIBUTE,
            ctypes.byref(ctypes.c_int(1)),
            4
        )
    except Exception as e:
        print(f"DWM Dark Mode error: {e}")


def force_refresh_style(widget: Any) -> None:
    """
    Forces a QSS style re-polish and update for a specific widget.

    Useful when dynamic properties (like 'active') change and require
    immediate visual feedback.

    Args:
        widget: The PyQt6 widget to refresh.
    """
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()
