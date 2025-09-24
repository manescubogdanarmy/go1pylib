#!/usr/bin/env python3
"""
Launcher script for the Object Detection GUI
Run this to start the graphical user interface.
"""

import sys
import os

def main():
    """Launch the GUI application"""
    try:
        from gui_app import main as gui_main
        print("Starting Object Detection GUI...")
        gui_main()
    except ImportError as e:
        print(f"Error: Could not import GUI application. {e}")
        print("Make sure all dependencies are installed:")
        print("pip install -r requirements.txt")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nGUI closed by user.")
    except Exception as e:
        print(f"Error running GUI: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()