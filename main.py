import sys
from PyQt6.QtWidgets import QApplication
from src.render import MainWindow
from src.utils import apply_windows_dark_theme


def main() -> None:
    """
    Entry point for the Aether Hand Tracker application.
    Initializes the Qt application, applies system themes, and starts the event loop.
    """
    app = QApplication(sys.argv)

    # Create the main window instance
    window = MainWindow()

    # Apply Windows-specific dark theme to the title bar
    apply_windows_dark_theme(window.winId())

    # Show the UI
    window.show()

    # Execute the application and ensure clean exit
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
