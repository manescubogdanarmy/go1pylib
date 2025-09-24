#!/usr/bin/env python3
"""
Simple demo script to test the file selection dialog.
Run this to see the file selection dialog in action.
"""

from object_detector import main

def demo():
    """
    Demo the file selection and object detection functionality.
    """
    print("Object Detection Demo")
    print("=" * 20)
    print("This will open a file selection dialog.")
    print("Choose any image file (JPG, PNG, BMP, etc.) to analyze.")
    print("Press Ctrl+C to cancel if needed.")
    print()

    try:
        # Run detection with file dialog
        result, circles, squares = main(use_file_dialog=True)

        if result is not None:
            print("\n✅ Detection completed successfully!")
            print(f"Landmines found: {len(circles)}")
            print(f"Squares found: {len(squares)}")
        else:
            print("\n❌ Detection was cancelled or failed.")

    except KeyboardInterrupt:
        print("\n\nDemo cancelled by user.")
    except Exception as e:
        print(f"\n❌ Error during demo: {e}")

if __name__ == "__main__":
    demo()