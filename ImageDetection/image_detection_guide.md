# Image Detection Algorithm for Round and Square Objects

This document outlines the steps to implement a Python program that detects round (circular) and square objects in an image. The program will mark detected objects with green labeled bounding squares.

## Requirements

- Python 3.x
- OpenCV library (`pip install opencv-python`)
- NumPy library (`pip install numpy`)

## Algorithm Overview

The image detection algorithm consists of the following main steps:

1. Load and preprocess the image
2. Detect circular objects using Hough Circle Transform
3. Detect square/rectangular objects using contour detection
4. Draw green bounding squares around detected objects with labels
5. Display or save the result

## Implementation Steps

### Step 1: Import Required Libraries

```python
import cv2
import numpy as np
```

### Step 2: Load and Preprocess the Image

```python
def load_and_preprocess_image(image_path):
    # Load the image
    image = cv2.imread(image_path)
    
    # Convert to grayscale for processing
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (9, 9), 2)
    
    return image, blurred
```

### Step 3: Detect Circular Objects

```python
def detect_circles(blurred_image):
    # Use Hough Circle Transform to detect circles
    circles = cv2.HoughCircles(
        blurred_image,
        cv2.HOUGH_GRADIENT,
        dp=1,
        minDist=50,
        param1=50,
        param2=30,
        minRadius=10,
        maxRadius=100
    )
    
    detected_circles = []
    if circles is not None:
        circles = np.round(circles[0, :]).astype("int")
        for (x, y, r) in circles:
            detected_circles.append((x, y, r))
    
    return detected_circles
```

### Step 4: Detect Square Objects

```python
def detect_squares(blurred_image):
    # Apply threshold to get binary image
    _, thresh = cv2.threshold(blurred_image, 127, 255, cv2.THRESH_BINARY)
    
    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    detected_squares = []
    for contour in contours:
        # Approximate the contour
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.04 * peri, True)
        
        # Check if it's a quadrilateral
        if len(approx) == 4:
            # Check if it's roughly a square (aspect ratio close to 1)
            x, y, w, h = cv2.boundingRect(approx)
            aspect_ratio = float(w) / h
            
            if 0.8 <= aspect_ratio <= 1.2:  # Adjust tolerance as needed
                detected_squares.append((x, y, w, h))
    
    return detected_squares
```

### Step 5: Draw Bounding Squares and Labels

```python
def draw_detections(image, circles, squares):
    # Draw circles
    for (x, y, r) in circles:
        # Draw green bounding square
        cv2.rectangle(image, (x - r, y - r), (x + r, y + r), (0, 255, 0), 2)
        
        # Add label
        cv2.putText(image, "Circle", (x - r, y - r - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    
    # Draw squares
    for (x, y, w, h) in squares:
        # Draw green bounding square
        cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)
        
        # Add label
        cv2.putText(image, "Square", (x, y - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    
    return image
```

### Step 6: Main Function

```python
def main(image_path):
    # Load and preprocess image
    image, blurred = load_and_preprocess_image(image_path)
    
    # Detect circles
    circles = detect_circles(blurred)
    
    # Detect squares
    squares = detect_squares(blurred)
    
    # Draw detections
    result_image = draw_detections(image.copy(), circles, squares)
    
    # Display result
    cv2.imshow("Detected Objects", result_image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    
    # Optionally save the result
    cv2.imwrite("detected_objects.jpg", result_image)

if __name__ == "__main__":
    image_path = "path/to/your/image.jpg"  # Replace with actual image path
    main(image_path)
```

## Usage

1. Save the code above into a Python file (e.g., `object_detector.py`)
2. Install required libraries: `pip install opencv-python numpy`
3. Replace `image_path` with the path to your input image
4. Run the script: `python object_detector.py`

## Notes

- The circle detection parameters (minDist, param1, param2, minRadius, maxRadius) may need adjustment based on your specific images and object sizes.
- The square detection uses a simple aspect ratio check. For more complex scenarios, you might need to implement additional checks (e.g., angle measurements).
- This is a basic implementation. For production use, consider adding error handling, parameter tuning, and performance optimizations.
- The algorithm assumes objects are well-separated and clearly visible in the image. Noisy or complex images may require additional preprocessing steps.

## Potential Improvements

- Add color-based filtering to focus on specific object colors
- Implement more sophisticated shape detection algorithms
- Add confidence scores for detections
- Support for video stream processing
- Integration with machine learning models for better accuracy