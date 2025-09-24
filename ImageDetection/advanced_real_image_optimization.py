#!/usr/bin/env python3
"""
Advanced Real Image Detection Optimization Script
Uses stricter validation and more targeted parameter testing.
"""

import cv2
import numpy as np
import os
import sys
import time
from datetime import datetime

# Add the ImageDetection directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from object_detector import load_and_preprocess_image, detect_circles_hough, validate_circle_real_image, remove_duplicate_circles

def test_strict_parameters_on_real_images():
    """
    Test stricter parameter combinations with advanced validation.
    Target: 3 mines in 500px-Minen.jpg, 1 mine in tm-46_ap-mine.jpeg.jpg
    """

    # Define test images and their expected mine counts
    test_cases = [
        {
            "image_path": "500px-Minen.jpg",
            "expected_mines": 3,
            "description": "500px mine field image"
        },
        {
            "image_path": "tm-46_ap-mine.jpeg.jpg",
            "expected_mines": 1,
            "description": "TM-46 anti-personnel mine"
        }
    ]

    # Define stricter parameter ranges for advanced validation
    param_combinations = [
        # Very strict settings - high param2, large min_dist
        {"param1": 30, "param2": 30, "min_dist": 60, "min_radius": 25, "max_radius": 55},
        {"param1": 25, "param2": 35, "min_dist": 70, "min_radius": 25, "max_radius": 55},
        {"param1": 20, "param2": 40, "min_dist": 80, "min_radius": 25, "max_radius": 55},

        # Medium strict settings
        {"param1": 35, "param2": 28, "min_dist": 55, "min_radius": 20, "max_radius": 60},
        {"param1": 40, "param2": 25, "min_dist": 50, "min_radius": 20, "max_radius": 60},

        # Size-focused variations
        {"param1": 30, "param2": 30, "min_dist": 60, "min_radius": 30, "max_radius": 50},
        {"param1": 30, "param2": 30, "min_dist": 60, "min_radius": 15, "max_radius": 45},
        {"param1": 30, "param2": 30, "min_dist": 60, "min_radius": 20, "max_radius": 40},
    ]

    print("Advanced Real Image Detection Optimization")
    print("=" * 55)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    best_results = {}

    for test_case in test_cases:
        image_path = test_case["image_path"]
        expected_mines = test_case["expected_mines"]
        description = test_case["description"]

        print(f"Testing: {description}")
        print(f"Image: {image_path}")
        print(f"Expected mines: {expected_mines}")
        print("-" * 40)

        # Check if image exists
        if not os.path.exists(image_path):
            print(f"ERROR: Image not found: {image_path}")
            print()
            continue

        # Load and preprocess image
        try:
            image, blurred = load_and_preprocess_image(image_path)
            print(f"Image loaded successfully: {image.shape}")
        except Exception as e:
            print(f"ERROR loading image: {e}")
            print()
            continue

        best_score = float('inf')  # Lower is better (closer to expected)
        best_params = None
        best_detections = []

        # Test each parameter combination
        for i, params in enumerate(param_combinations):
            print(f"Testing parameter set {i+1}/{len(param_combinations)}: param1={params['param1']}, param2={params['param2']}, min_dist={params['min_dist']}, radius={params['min_radius']}-{params['max_radius']}")

            try:
                # Detect circles with custom parameters
                circles = cv2.HoughCircles(
                    blurred,
                    cv2.HOUGH_GRADIENT,
                    dp=1,
                    minDist=params["min_dist"],
                    param1=params["param1"],
                    param2=params["param2"],
                    minRadius=params["min_radius"],
                    maxRadius=params["max_radius"]
                )

                detections = []
                if circles is not None:
                    circles = np.round(circles[0, :]).astype("int")

                    for (x, y, r) in circles:
                        if validate_circle_real_image(blurred, x, y, r):
                            detections.append((x, y, r))

                # Remove duplicates
                detections = remove_duplicate_circles(detections)

                num_detections = len(detections)
                score = abs(num_detections - expected_mines)  # How close to expected count

                print(f"  Detected: {num_detections} mines (score: {score})")

                # Track best result for this image
                if score < best_score:
                    best_score = score
                    best_params = params.copy()
                    best_detections = detections.copy()

                # If we hit the exact target, we can stop early for this image
                if num_detections == expected_mines:
                    print(f"  PERFECT MATCH! Found exactly {expected_mines} mines")
                    break

            except Exception as e:
                print(f"  ERROR in detection: {e}")
                continue

        # Store best result for this image
        best_results[image_path] = {
            "expected": expected_mines,
            "detected": len(best_detections),
            "score": best_score,
            "params": best_params,
            "detections": best_detections
        }

        print(f"\nBest result for {description}:")
        print(f"  Expected: {expected_mines} mines")
        print(f"  Detected: {len(best_detections)} mines")
        print(f"  Score: {best_score} (lower is better)")
        print(f"  Parameters: {best_params}")
        print()

    # Summary
    print("SUMMARY")
    print("=" * 55)

    total_score = 0
    perfect_matches = 0

    for image_path, result in best_results.items():
        expected = result["expected"]
        detected = result["detected"]
        score = result["score"]

        total_score += score

        if detected == expected:
            perfect_matches += 1
            status = "✓ PERFECT"
        elif abs(detected - expected) <= 1:
            status = "~ CLOSE"
        else:
            status = "✗ FAR"

        print(f"{os.path.basename(image_path)}: {status}")
        print(f"  Expected: {expected}, Detected: {detected}, Score: {score}")
        print(f"  Best params: {result['params']}")
        print()

    print(f"Overall Results:")
    print(f"  Perfect matches: {perfect_matches}/{len(best_results)}")
    print(f"  Total score: {total_score} (lower is better)")
    print(f"  Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return best_results

if __name__ == "__main__":
    # Change to the ImageDetection directory if not already there
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.basename(script_dir) != "ImageDetection":
        image_dir = os.path.join(script_dir, "ImageDetection")
        if os.path.exists(image_dir):
            os.chdir(image_dir)
            print(f"Changed directory to: {image_dir}")

    # Run the optimization
    results = test_strict_parameters_on_real_images()

    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"advanced_real_image_optimization_{timestamp}.txt"

    with open(results_file, 'w') as f:
        f.write("Advanced Real Image Detection Optimization Results\n")
        f.write("=" * 55 + "\n")
        f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        for image_path, result in results.items():
            f.write(f"Image: {image_path}\n")
            f.write(f"Expected mines: {result['expected']}\n")
            f.write(f"Detected mines: {result['detected']}\n")
            f.write(f"Score: {result['score']}\n")
            f.write(f"Best parameters: {result['params']}\n")
            f.write(f"Detection details: {result['detections']}\n\n")

    print(f"\nResults saved to: {results_file}")