#!/usr/bin/env python3
"""
Example script showing how to use the object detector with your own images.
Supports both command line arguments and interactive file selection.
"""

import sys
import os
from object_detector import main

def example_usage():
    """
    Example of how to use the object detector.
    """
    print("Object Detection Example")
    print("=" * 30)

    # Check if an image path was provided as command line argument
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        use_dialog = False
        print(f"Using image from command line: {image_path}")
    else:
        # Use file dialog for interactive selection
        image_path = None
        use_dialog = True
        print("No image path provided. Opening file selection dialog...")
        print("Usage: python example.py <path_to_image>")
        print()

    # Check if image exists (only if provided via command line)
    if image_path and not os.path.exists(image_path):
        print(f"Error: Image file '{image_path}' not found.")
        print("Please provide a valid image path or run without arguments to use file dialog.")
        return

    # Example 1: Basic detection with default parameters
    print("=== Running Object Detection ===")
    result1, circles1, squares1 = main(
        image_path=image_path,
        use_file_dialog=use_dialog,
        display=False,
        save_output=False
    )

    if result1 is None:
        print("Detection cancelled.")
        return

    print(f"Detected {len(circles1)} landmines and {len(squares1)} squares")

    # Example 2: Detection with display and save
    print("\n=== Displaying Results ===")
    result2, circles2, squares2 = main(
        image_path=image_path,
        use_file_dialog=False,  # Don't show dialog again
        pixels_per_cm=None,  # Using defaults
        display=True,  # Show the result
        save_output=True  # Save output image
    )

    # Print detailed results
    print("\n=== Detailed Results ===")
    print("Landmines detected:")
    for i, (x, y, r) in enumerate(circles2, 1):
        diameter_pixels = r * 2
        print(f"  {i}. Center: ({x}, {y}), Radius: {r} pixels")

    print("Square objects detected:")
    for i, (x, y, w, h) in enumerate(squares2, 1):
        print(f"  {i}. Position: ({x}, {y}), Size: {w}x{h} pixels")

if __name__ == "__main__":
    example_usage()