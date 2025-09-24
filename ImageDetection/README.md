# Image Detection for Landmines and Square Objects

This Python implementation detects landmines (circular objects 15-50 cm diameter) and square objects in images, marking them with green labeled bounding squares.

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the test to verify everything works:
```bash
python test_detection.py
```

3. **Use the GUI application (recommended):**
```bash
python run_gui.py
# or directly:
python gui_app.py
```

4. **Or use other options:**
```bash
# Interactive file selection (command line)
python object_detector.py

# Simple demo with file selection
python demo.py

# Specify image path directly
python example.py path/to/your/image.jpg
```

## GUI Application

The `gui_app.py` provides a complete graphical user interface for object detection:

### Features:
- **File Selection Dialog**: Browse and select images from your computer
- **Real-time Image Display**: View selected images and detection results
- **Calibration Input**: Enter pixels-per-centimeter for accurate sizing
- **Progress Tracking**: Visual progress bar during detection
- **Results Display**: Detailed detection results in a text panel
- **Save Results**: Export processed images with detections marked
- **Error Handling**: User-friendly error messages and status updates

### How to Use:
1. Run `python gui_app.py`
2. Click "Select Image" to choose an image file
3. Optionally enter calibration value (pixels per cm)
4. Click "Detect Objects" to run analysis
5. View results in the image area and results panel
6. Click "Save Result" to export the marked image

### GUI Layout:
- **Left Panel**: Controls, calibration, results
- **Right Panel**: Image display with scrollbars
- **Bottom**: Status bar and progress indicator

## Usage Examples

### Interactive Mode (File Dialog)
```bash
python object_detector.py
```
This will open a file selection window where you can browse and choose any image file.

### Command Line Mode
```bash
python example.py /path/to/your/image.jpg
```

### Python API
```python
from object_detector import main

# With file dialog
result, circles, squares = main(use_file_dialog=True)

# With specific path
result, circles, squares = main("path/to/image.jpg")
```

## Files

- `run_gui.py`: **NEW** Simple launcher for the GUI application
- `gui_app.py`: **NEW** Complete GUI application for interactive object detection
- `object_detector.py`: Main detection implementation with file selection dialog
- `test_detection.py`: Test script that creates and processes a sample image
- `example.py`: Example script showing different usage modes
- `demo.py`: Simple demo script to test file selection dialog
- `requirements.txt`: Python dependencies
- `image_detection_guide.md`: Detailed algorithm documentation
- `README.md`: This file

## API Reference

### main(image_path, pixels_per_cm=None, display=True, save_output=True)

Main function for object detection.

**Parameters:**
- `image_path` (str): Path to input image
- `pixels_per_cm` (float, optional): Calibration factor for accurate sizing
- `display` (bool): Show result window (default: True)
- `save_output` (bool): Save result image (default: True)

**Returns:**
- `result_image`: Image with detections drawn
- `circles`: List of detected landmines as (x, y, radius)
- `squares`: List of detected squares as (x, y, width, height)

## Calibration

To get accurate landmine detection, you need to calibrate `pixels_per_cm`:

1. Place a known-size object (e.g., 10 cm wide) in your camera's view at the expected distance
2. Capture an image and measure how many pixels the object spans
3. Calculate: `pixels_per_cm = pixel_measurement / real_world_measurement`

Example: If a 10 cm object measures 100 pixels, then `pixels_per_cm = 10`

## Output

The program will:
- Display the image with detected objects marked in green
- Save a new image with "_detected.jpg" suffix
- Print detection statistics to console

## Detection Parameters

### Landmine Detection
- **Size Range**: 15-50 cm diameter (7.5-25 cm radius)
- **Method**: Hough Circle Transform
- **Label**: "Landmine"

### Square Detection
- **Shape**: Quadrilaterals with aspect ratio 0.8-1.2
- **Method**: Contour analysis
- **Label**: "Square"

## Safety Note

This is a computer vision demonstration. **Do not use this for actual landmine detection** without proper validation, expert review, and safety protocols. Landmine detection requires specialized equipment and trained personnel.

## Files

- `object_detector.py`: Main detection implementation
- `requirements.txt`: Python dependencies
- `image_detection_guide.md`: Detailed algorithm documentation