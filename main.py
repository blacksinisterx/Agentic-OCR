"""
main.py — ScribeAI Entry Point
Run: python main.py
"""

import sys, os

# Python version guard
if sys.version_info < (3, 10):
    print(f"❌  Python 3.10+ required. You have {sys.version}")
    sys.exit(1)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.makedirs("outputs", exist_ok=True)


def main():
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QFont
        from ui.main_window import MainWindow

        app = QApplication(sys.argv)
        app.setApplicationName("ScribeAI")
        app.setApplicationVersion("2.0")

        # Set base font
        font = QFont("Segoe UI", 10)
        app.setFont(font)

        win = MainWindow()
        win.show()
        sys.exit(app.exec())

    except ImportError as e:
        print(f"\n❌  Missing dependency: {e}")
        print("\nFix:\n  pip install -r requirements.txt\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌  Startup error: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
