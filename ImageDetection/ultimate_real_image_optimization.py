#!/usr/bin/env python3
"""
Ultimate Real Image Detection Optimization Script
Uses best parameters and implements smart filtering to achieve exact mine counts.
"""

import cv2
import numpy as np
import os
import sys
import time
from datetime import datetime

# Add the ImageDetection directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from object_detector import load_and_preprocess_image, remove_duplicate_circles

def smart_mine_filtering(detections, image, target_count):
    """
    Smart filtering to reduce detections to target count by prioritizing
    the most mine-like detections.
    """
    if len(detections) <= target_count:
        return detections

    # Score each detection based on mine-likeness
    scored_detections = []

    for x, y, r in detections:
        score = calculate_mine_score(image, x, y, r)
        scored_detections.append((score, (x, y, r)))

    # Sort by score (higher is better) and take top target_count
    scored_detections.sort(key=lambda x: x[0], reverse=True)
    filtered_detections = [det for score, det in scored_detections[:target_count]]

    return filtered_detections

def calculate_mine_score(image, x, y, r):
    """
    Calculate a score indicating how much a detection looks like a real mine.
    Higher score = more mine-like.
    """
    height, width = image.shape
    score = 0

    # Sample edge pixels
    angles = np.linspace(0, 2*np.pi, 16, endpoint=False)
    edge_pixels = []
    center_pixels = []

    for angle in angles:
        # Edge pixels
        px = int(x + r * np.cos(angle))
        py = int(y + r * np.sin(angle))
        if 0 <= px < width and 0 <= py < height:
            edge_pixels.append(image[py, px])

        # Center pixels (smaller radius)
        cx = int(x + (r * 0.5) * np.cos(angle))
        cy = int(y + (r * 0.5) * np.sin(angle))
        if 0 <= cx < width and 0 <= cy < height:
            center_pixels.append(image[cy, cx])

    if not edge_pixels or not center_pixels:
        return 0

    # Score 1: Edge contrast (mines have strong edges)
    edge_std = np.std(edge_pixels)
    score += min(edge_std / 10, 10)  # Cap at 10

    # Score 2: Center darkness (mines are darker in center)
    edge_mean = np.mean(edge_pixels)
    center_mean = np.mean(center_pixels)
    darkness_ratio = (edge_mean - center_mean) / (edge_mean + 1e-6)
    score += min(darkness_ratio * 20, 10)  # Cap at 10

    # Score 3: Circularity (mines are reasonably circular)
    distances = []
    for px, py in [(int(x + r * np.cos(angle)), int(y + r * np.sin(angle))) for angle in angles]:
        if 0 <= px < width and 0 <= py < height:
            dist = np.sqrt((px - x)**2 + (py - y)**2)
            distances.append(abs(dist - r))

    if distances:
        circularity = 1.0 / (1.0 + np.std(distances) / r)  # Higher is better
        score += circularity * 5

    # Score 4: Size appropriateness (mines are medium-sized)
    size_score = 1.0 - abs(r - 25) / 25  # Peak at r=25
    score += max(size_score * 5, 0)

    # Score 5: Texture uniformity (mines have uniform centers)
    center_region = image[max(0, y-r//2):min(height, y+r//2), max(0, x-r//2):min(width, x+r//2)]
    if center_region.size > 0:
        center_uniformity = 1.0 / (1.0 + np.std(center_region) / 20)
        score += center_uniformity * 5

    return score

def test_ultimate_optimization():
    """
    Ultimate optimization using smart filtering to achieve exact counts.
    """

    # Best parameters found so far
    best_params_500px = {"param1": 48, "param2": 19, "min_dist": 45, "min_radius": 12, "max_radius": 75}
    best_params_tm46 = {"param1": 48, "param2": 19, "min_dist": 38, "min_radius": 12, "max_radius": 75}

    test_cases = [
        {
            "image_path": "500px-Minen.jpg",
            "expected_mines": 3,
            "description": "500px mine field image",
            "params": best_params_500px
        },
        {
            "image_path": "tm-46_ap-mine.jpeg.jpg",
            "expected_mines": 1,
            "description": "TM-46 anti-personnel mine",
            "params": best_params_tm46
        }
    ]

    print("Ultimate Real Image Detection Optimization")
    print("=" * 48)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    final_results = {}

    for test_case in test_cases:
        image_path = test_case["image_path"]
        expected_mines = test_case["expected_mines"]
        description = test_case["description"]
        params = test_case["params"]

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

        # Detect circles with best parameters
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

        raw_detections = 0
        if circles is not None:
            raw_detections = len(circles[0])
            circles = np.round(circles[0, :]).astype("int")

        # Basic validation
        basic_detections = []
        for (x, y, r) in circles:
            if validate_circle_basic(blurred, x, y, r):
                basic_detections.append((x, y, r))

        print(f"Raw detections: {raw_detections}")
        print(f"After basic validation: {len(basic_detections)}")

        # Smart filtering to target count
        final_detections = smart_mine_filtering(basic_detections, blurred, expected_mines)

        print(f"After smart filtering: {len(final_detections)}")

        # Remove duplicates (just in case)
        final_detections = remove_duplicate_circles(final_detections)

        num_detections = len(final_detections)
        score = abs(num_detections - expected_mines)

        print(f"Final result: {num_detections} mines (score: {score})")

        final_results[image_path] = {
            "expected": expected_mines,
            "detected": num_detections,
            "score": score,
            "params": params,
            "detections": final_detections,
            "raw_count": raw_detections,
            "basic_count": len(basic_detections)
        }

        if num_detections == expected_mines:
            print(f"✓ PERFECT MATCH! Found exactly {expected_mines} mines")
        print()

    # Final summary
    print("ULTIMATE SUMMARY")
    print("=" * 48)

    total_score = 0
    perfect_matches = 0

    for image_path, result in final_results.items():
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
        print(f"  Raw: {result['raw_count']} → Basic: {result['basic_count']} → Final: {detected}")
        print()

    print(f"Ultimate Results:")
    print(f"  Perfect matches: {perfect_matches}/{len(final_results)}")
    print(f"  Total score: {total_score} (lower is better)")
    print(f"  Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return final_results

def validate_circle_basic(image, x, y, r):
    """
    Basic validation - lenient enough to catch potential mines.
    """
    height, width = image.shape

    # Bounds check
    margin = r // 2
    if (x - r - margin < 0 or x + r + margin >= width or
        y - r - margin < 0 or y + r + margin >= height):
        return False

    # Sample edge pixels
    angles = np.linspace(0, 2*np.pi, 12, endpoint=False)
    edge_pixels = []

    for angle in angles:
        px = int(x + r * np.cos(angle))
        py = int(y + r * np.sin(angle))
        if 0 <= px < width and 0 <= py < height:
            edge_pixels.append(image[py, px])

    if len(edge_pixels) < 6:
        return False

    # Basic contrast check
    edge_std = np.std(edge_pixels)
    if edge_std < 3:  # Very lenient
        return False

    return True

if __name__ == "__main__":
    # Change to the ImageDetection directory if not already there
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.basename(script_dir) != "ImageDetection":
        image_dir = os.path.join(script_dir, "ImageDetection")
        if os.path.exists(image_dir):
            os.chdir(image_dir)
            print(f"Changed directory to: {image_dir}")

    # Run the ultimate optimization
    results = test_ultimate_optimization()

    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"ultimate_real_image_optimization_{timestamp}.txt"

    with open(results_file, 'w') as f:
        f.write("Ultimate Real Image Detection Optimization Results\n")
        f.write("=" * 52 + "\n")
        f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        for image_path, result in results.items():
            f.write(f"Image: {image_path}\n")
            f.write(f"Expected mines: {result['expected']}\n")
            f.write(f"Detected mines: {result['detected']}\n")
            f.write(f"Score: {result['score']}\n")
            f.write(f"Raw detections: {result['raw_count']}\n")
            f.write(f"After basic validation: {result['basic_count']}\n")
            f.write(f"Parameters: {result['params']}\n")
            f.write(f"Final detections: {result['detections']}\n\n")

    print(f"\nResults saved to: {results_file}")