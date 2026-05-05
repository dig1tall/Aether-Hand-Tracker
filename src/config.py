import os
from typing import Final
from src.utils import get_resource_path

# --- FILE SYSTEM PATHS ---
# Base directory of the current file (src folder)
BASE_DIR: Final[str] = os.path.dirname(os.path.abspath(__file__))

# Assets directory located at the project root
ASSETS_DIR: Final[str] = get_resource_path("assets")

# UI and visual resource paths
UI_MAIN_PATH: Final[str] = get_resource_path("src/main_window.ui")
ICON_PATH: Final[str] = get_resource_path("assets/icon.png")
LOGO_PATH: Final[str] = get_resource_path("assets/logo.png")

# --- MEDIAPIPE CONFIGURATION ---
# Minimum confidence value for hand detection
DEFAULT_DET_CONF: Final[float] = 0.8

# Minimum confidence value for landmark tracking
DEFAULT_TRACK_CONF: Final[float] = 0.7

# Maximum number of hands to be processed simultaneously
MAX_HANDS: Final[int] = 2

# --- GESTURE PARAMETERS (Defaults) ---
"""
The following constants define the physical and temporal thresholds 
required to trigger specific system commands.
"""

# Swipe: Sensitivity (normalized distance) and cooldown between triggers
DEFAULT_SWIPE_DIST: Final[float] = 0.05
DEFAULT_SWIPE_COOLDOWN: Final[float] = 3.0

# Volume: Distance between fingers to activate and vertical movement sensitivity
DEFAULT_VOL_THRESHOLD: Final[float] = 0.037
DEFAULT_VOL_SENSITIVITY: Final[float] = 0.05

# Fist: Minimum time interval between play/pause toggles
DEFAULT_FIST_COOLDOWN: Final[float] = 1.5

# --- INTERFACE SETTINGS ---
# Duration of on-screen status messages in milliseconds
STATUS_DURATION: Final[int] = 2000

# WinAPI DWM attribute index for enabling system-level dark mode (immersive dark mode)
DARK_MODE_ATTRIBUTE: Final[int] = 20
