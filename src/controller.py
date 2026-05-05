import pyautogui


class SystemController:
    """
    Interface for controlling system-level media and audio functions.

    Uses virtual key codes via pyautogui to simulate multimedia button presses,
    allowing control over applications like Spotify, YouTube, or system volume.
    """

    @staticmethod
    def play_pause() -> None:
        """
        Toggles the current media playback between play and pause.
        Sends the 'playpause' virtual key command.
        """
        pyautogui.press('playpause')

    @staticmethod
    def next_track() -> None:
        """
        Skips to the next track in the current media playlist.
        Sends the 'nexttrack' virtual key command.
        """
        pyautogui.press('nexttrack')

    @staticmethod
    def prev_track() -> None:
        """
        Returns to the previous track in the current media playlist.
        Sends the 'prevtrack' virtual key command.
        """
        pyautogui.press('prevtrack')

    @staticmethod
    def volume_up() -> None:
        """
        Increases the system master volume by one step.
        Sends the 'volumeup' virtual key command.
        """
        pyautogui.press('volumeup')

    @staticmethod
    def volume_down() -> None:
        """
        Decreases the system master volume by one step.
        Sends the 'volumedown' virtual key command.
        """
        pyautogui.press('volumedown')
