import cv2
import numpy as np
import tkinter as tk
from tkinter import filedialog
import os

def load_and_preprocess_image(image_path):
    """
    Load an image and preprocess it for object detection.

    Args:
        image_path (str): Path to the input image file

    Returns:
        tuple: (original_image, blurred_image) where blurred_image is preprocessed for detection
    """
    # Load the image
    image = cv2.imread(image_path)

    if image is None:
        raise ValueError(f"Could not load image from path: {image_path}")

    # Convert to grayscale for processing
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (9, 9), 2)

    return image, blurred

def detect_circles(blurred_image, pixels_per_cm=None, sensitivity="medium"):
    """
    Detect circular objects (landmines) in the preprocessed image with improved filtering.

    Args:
        blurred_image: Preprocessed grayscale image
        pixels_per_cm (float, optional): Pixels per centimeter calibration factor
        sensitivity (str): Detection sensitivity ("low", "medium", "high")

    Returns:
        list: List of detected circles as (x, y, radius) tuples
    """
    # Calculate pixel radii based on landmine diameters (15-50 cm)
    # If pixels_per_cm is known, use it to calculate min/max radius in pixels
    if pixels_per_cm:
        min_radius_pixels = int((15 / 2) * pixels_per_cm)  # 7.5 cm radius
        max_radius_pixels = int((50 / 2) * pixels_per_cm)  # 25 cm radius
    else:
        # Default pixel values - adjust based on your camera setup and distance
        min_radius_pixels = 20  # Approximate for typical setups
        max_radius_pixels = 80  # Approximate for typical setups

    # Adjust parameters based on sensitivity
    if sensitivity == "low":
        param1, param2, min_dist = 80, 30, 60
    elif sensitivity == "high":
        param1, param2, min_dist = 40, 20, 40
    else:  # medium (default) - balanced settings
        param1, param2, min_dist = 50, 25, 50

    # Use Hough Circle Transform to detect circles
    circles = cv2.HoughCircles(
        blurred_image,
        cv2.HOUGH_GRADIENT,
        dp=1,
        minDist=min_dist,  # Minimum distance between circle centers
        param1=param1,     # Edge detection threshold
        param2=param2,     # Accumulator threshold (higher = fewer false positives)
        minRadius=min_radius_pixels,
        maxRadius=max_radius_pixels
    )

    detected_circles = []
    if circles is not None:
        circles = np.round(circles[0, :]).astype("int")

        for (x, y, r) in circles:
            # Additional filtering to reduce false positives
            if validate_circle(blurred_image, x, y, r):
                detected_circles.append((x, y, r))

    return detected_circles

def validate_circle(image, x, y, r):
    """
    Additional validation for detected circles to reduce false positives.

    Args:
        image: Grayscale image
        x, y: Circle center coordinates
        r: Circle radius

    Returns:
        bool: True if circle passes validation
    """
    height, width = image.shape

    # Check if circle is within image bounds (with some margin)
    margin = r // 2
    if (x - r - margin < 0 or x + r + margin >= width or
        y - r - margin < 0 or y + r + margin >= height):
        return False

    # Sample points around the circle perimeter
    angles = np.linspace(0, 2*np.pi, 32, endpoint=False)
    circle_points = []
    edge_pixels = []

    for angle in angles:
        # Calculate point on circle perimeter
        px = int(x + r * np.cos(angle))
        py = int(y + r * np.sin(angle))

        if 0 <= px < width and 0 <= py < height:
            circle_points.append((px, py))
            edge_pixels.append(image[py, px])

    if len(edge_pixels) < 16:  # Not enough valid points
        return False

    # Check edge strength (contrast) around the circle - more lenient
    edge_pixels = np.array(edge_pixels)
    edge_std = np.std(edge_pixels)
    edge_mean = np.mean(edge_pixels)

    # Only reject if there's almost no contrast (very uniform area)
    if edge_std < 3:  # Even lower threshold for synthetic images
        return False

    # Check circularity by comparing distances from center - more lenient
    distances = []
    for px, py in circle_points:
        dist = np.sqrt((px - x)**2 + (py - y)**2)
        distances.append(abs(dist - r))

    # Good circles should have consistent radius - more lenient
    radius_variation = np.std(distances)
    if radius_variation > r * 1.2:  # Allow 120% variation
        return False

    # Check for symmetry (sample in different quadrants) - more lenient
    quadrants = [0, 0, 0, 0]  # top-left, top-right, bottom-left, bottom-right
    for px, py in circle_points:
        if px < x and py < y:
            quadrants[0] += 1
        elif px >= x and py < y:
            quadrants[1] += 1
        elif px < x and py >= y:
            quadrants[2] += 1
        else:
            quadrants[3] += 1

    # All quadrants should have some edge points - more lenient
    quad_std = np.std(quadrants)
    if quad_std > 20:  # Allow much more variation
        return False

    return True

def detect_squares(blurred_image):
    """
    Detect square/rectangular objects in the preprocessed image.

    Args:
        blurred_image: Preprocessed grayscale image

    Returns:
        list: List of detected squares as (x, y, width, height) tuples
    """
    # Apply Canny edge detection
    edges = cv2.Canny(blurred_image, 50, 150)

    # Dilate edges to connect nearby edges
    kernel = np.ones((3, 3), np.uint8)
    dilated = cv2.dilate(edges, kernel, iterations=2)

    # Find contours
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

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

            # More lenient aspect ratio check
            if 0.7 <= aspect_ratio <= 1.3:
                # Check minimum size (avoid noise)
                area = cv2.contourArea(contour)
                if area > 500:  # Minimum area threshold
                    detected_squares.append((x, y, w, h))

    return detected_squares

def draw_detections(image, circles, squares):
    """
    Draw bounding squares and labels on detected objects.

    Args:
        image: Original color image to draw on
        circles: List of detected circles
        squares: List of detected squares

    Returns:
        Image with detections drawn
    """
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

def main(image_path=None, pixels_per_cm=None, display=True, save_output=True, use_file_dialog=False):
    """
    Main function to run the complete object detection pipeline.

    Args:
        image_path (str, optional): Path to the input image. If None and use_file_dialog=True, opens file dialog.
        pixels_per_cm (float, optional): Pixels per centimeter calibration factor
        display (bool): Whether to display the result
        save_output (bool): Whether to save the output image
        use_file_dialog (bool): Whether to show file selection dialog if image_path is None
    """
    # Handle file selection
    if image_path is None and use_file_dialog:
        print("Opening file selection dialog...")
        image_path = select_image_file()
        if image_path is None:
            print("No image selected. Exiting.")
            return None, [], []

    if image_path is None:
        raise ValueError("No image path provided. Set image_path or use_file_dialog=True")

    try:
        # Load and preprocess image
        print(f"Loading image: {image_path}")
        image, blurred = load_and_preprocess_image(image_path)

        # Detect circles (landmines)
        print("Detecting landmines...")
        circles = detect_circles(blurred, pixels_per_cm)
        print(f"Found {len(circles)} potential landmines")

        # Detect squares
        print("Detecting square objects...")
        squares = detect_squares(blurred)
        print(f"Found {len(squares)} square objects")

        # Draw detections
        result_image = draw_detections(image.copy(), circles, squares)

        # Display result
        if display:
            cv2.imshow("Detected Objects", result_image)
            print("Press any key to close the window...")
            cv2.waitKey(0)
            cv2.destroyAllWindows()

        # Save the result
        if save_output:
            output_path = image_path.rsplit('.', 1)[0] + "_detected.jpg"
            cv2.imwrite(output_path, result_image)
            print(f"Output saved to: {output_path}")

        return result_image, circles, squares

    except Exception as e:
        print(f"Error during detection: {str(e)}")
        return None, [], []

def select_image_file():
    """
    Open a file dialog to select an image file.

    Returns:
        str: Path to selected image file, or None if cancelled
    """
    # Create a hidden root window for the file dialog
    root = tk.Tk()
    root.withdraw()  # Hide the main window

    # Set up file dialog options
    file_types = [
        ('Image files', '*.jpg *.jpeg *.png *.bmp *.tiff *.tif'),
        ('JPEG files', '*.jpg *.jpeg'),
        ('PNG files', '*.png'),
        ('BMP files', '*.bmp'),
        ('TIFF files', '*.tiff *.tif'),
        ('All files', '*.*')
    ]

    # Show file dialog
    file_path = filedialog.askopenfilename(
        title="Select an image file",
        filetypes=file_types
    )

    # Destroy the hidden root window
    root.destroy()

    return file_path if file_path else None

if __name__ == "__main__":
    # Run detection with file selection dialog
    print("Object Detection for Landmines and Square Objects")
    print("=" * 50)

    # Calculate pixels_per_cm based on your camera setup
    # Example: If a 10cm object appears as 100 pixels in the image, pixels_per_cm = 10
    pixels_per_cm = None  # Set to your calculated value, or None for defaults

    # Run detection with file dialog
    result, circles, squares = main(use_file_dialog=True, pixels_per_cm=pixels_per_cm)

    # Print detection results
    if result is not None:
        print(f"\nDetection Summary:")
        print(f"Landmines detected: {len(circles)}")
        for i, (x, y, r) in enumerate(circles, 1):
            print(f"  Landmine {i}: Center=({x},{y}), Radius={r} pixels")

        print(f"Square objects detected: {len(squares)}")
        for i, (x, y, w, h) in enumerate(squares, 1):
            print(f"  Square {i}: Position=({x},{y}), Size={w}x{h} pixels")
    else:
        print("Detection cancelled or failed.")