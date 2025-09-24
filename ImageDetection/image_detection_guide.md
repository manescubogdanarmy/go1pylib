# Image Detection Algorithm for Round and Square Objects

This document outlines the steps to implement a Python program that detects round (circular) and square objects in an image. The program will mark detected objects with green labeled bounding squares.

## Requirements

- Python 3.x
- OpenCV library (`pip install opencv-python`)
- NumPy library (`pip install numpy`)

## Algorithm Overview

The image detection algorithm is designed to detect landmines (round objects with diameters between 15 cm and 50 cm) and square objects in images. The program will mark detected objects with green labeled bounding squares.

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

### Step 3: Detect Circular Objects (Landmines)

```python
def detect_circles(blurred_image, pixels_per_cm=None):
    # Calculate pixel radii based on landmine diameters (15-50 cm)
    # If pixels_per_cm is known, use it to calculate min/max radius in pixels
    if pixels_per_cm:
        min_radius_pixels = int((15 / 2) * pixels_per_cm)  # 7.5 cm radius
        max_radius_pixels = int((50 / 2) * pixels_per_cm)  # 25 cm radius
    else:
        # Default pixel values - adjust based on your camera setup and distance
        min_radius_pixels = 20  # Approximate for typical setups
        max_radius_pixels = 80  # Approximate for typical setups
    
    # Use Hough Circle Transform to detect circles
    circles = cv2.HoughCircles(
        blurred_image,
        cv2.HOUGH_GRADIENT,
        dp=1,
        minDist=50,
        param1=50,
        param2=30,
        minRadius=min_radius_pixels,
        maxRadius=max_radius_pixels
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
    # Draw circles (landmines)
    for (x, y, r) in circles:
        # Draw green bounding square
        cv2.rectangle(image, (x - r, y - r), (x + r, y + r), (0, 255, 0), 2)
        
        # Add label
        cv2.putText(image, "Landmine", (x - r, y - r - 10), 
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
def main(image_path, pixels_per_cm=None):
    # Load and preprocess image
    image, blurred = load_and_preprocess_image(image_path)
    
    # Detect circles (landmines)
    circles = detect_circles(blurred, pixels_per_cm)
    
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
    
    # Calculate pixels_per_cm based on your camera setup
    # Example: If a 10cm object appears as 100 pixels in the image, pixels_per_cm = 10
    pixels_per_cm = None  # Set to your calculated value, or None for defaults
    
    main(image_path, pixels_per_cm)
```

## Usage

1. Save the code above into a Python file (e.g., `object_detector.py`)
2. Install required libraries: `pip install opencv-python numpy`
3. Replace `image_path` with the path to your input image
4. Run the script: `python object_detector.py`

## Notes

- **Landmine Detection Parameters**: The algorithm is specifically tuned for detecting landmines with diameters between 15 cm and 50 cm. The `pixels_per_cm` parameter should be calculated based on your camera's field of view and distance from the ground.
  
  **To calculate `pixels_per_cm`:**
  1. Place a known-size object (e.g., 10 cm wide) in the scene at the expected distance
  2. Capture an image and measure how many pixels the object spans
  3. Divide the pixel measurement by the real-world measurement (e.g., 100 pixels / 10 cm = 10 pixels_per_cm)
  
- The circle detection parameters (minDist, param1, param2) may need adjustment based on image quality and environmental conditions.
- The square detection uses a simple aspect ratio check. For more complex scenarios, you might need to implement additional checks (e.g., angle measurements).
- This is a basic implementation for landmine detection. For safety-critical applications, consider adding multiple validation steps and expert review.
- The algorithm assumes landmines appear as circular shapes in the image. Camouflaged or partially buried landmines may not be detected reliably.

## Potential Improvements

- Add color-based filtering to focus on specific landmine colors or patterns
- Implement more sophisticated shape detection algorithms
- Add confidence scores for detections
- Support for video stream processing from drone or ground vehicle cameras
- Integration with machine learning models for better accuracy in varied terrain
- Add distance estimation based on detected object size
- Implement safety zones around detected landmines