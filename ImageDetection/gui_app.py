#!/usr/bin/env python3
"""
GUI Application for Object Detection
Provides a graphical interface to select images and detect landmines and square objects.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import cv2
import numpy as np
import os
from PIL import Image, ImageTk
import threading

# Import our detection functions
from object_detector import (
    load_and_preprocess_image,
    detect_circles,
    detect_squares,
    draw_detections
)

class ObjectDetectionGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Landmine & Square Object Detection")
        self.root.geometry("1000x700")
        self.root.resizable(True, True)

        # Variables
        self.image_path = None
        self.original_image = None
        self.processed_image = None
        self.pixels_per_cm = None
        self.sensitivity = "real_image_optimized"  # Default to optimized method
        self.detection_results = None

        # Create GUI elements
        self.create_widgets()

        # Center the window
        self.center_window()

    def create_widgets(self):
        """Create all GUI widgets"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)

        # Title
        title_label = ttk.Label(main_frame, text="Landmine & Square Object Detection",
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))

        # Control panel (left side)
        control_frame = ttk.LabelFrame(main_frame, text="Controls", padding="10")
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))

        # File selection button
        self.select_button = ttk.Button(control_frame, text="Select Image",
                                       command=self.select_image, width=20)
        self.select_button.grid(row=0, column=0, pady=(0, 10))

        # Calibration frame
        calib_frame = ttk.LabelFrame(control_frame, text="Calibration", padding="5")
        calib_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(calib_frame, text="Pixels per cm:").grid(row=0, column=0, sticky=tk.W)
        self.calib_var = tk.StringVar(value="")
        self.calib_entry = ttk.Entry(calib_frame, textvariable=self.calib_var, width=10)
        self.calib_entry.grid(row=0, column=1, padx=(5, 0))
        ttk.Label(calib_frame, text="(leave empty for auto)").grid(row=1, column=0, columnspan=2, sticky=tk.W)

        # Sensitivity frame
        sens_frame = ttk.LabelFrame(control_frame, text="Detection Sensitivity", padding="5")
        sens_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        self.sensitivity_var = tk.StringVar(value="real_image_optimized")
        ttk.Radiobutton(sens_frame, text="Low (Fewer detections)", variable=self.sensitivity_var,
                       value="low").grid(row=0, column=0, sticky=tk.W)
        ttk.Radiobutton(sens_frame, text="Medium (Balanced)", variable=self.sensitivity_var,
                       value="medium").grid(row=1, column=0, sticky=tk.W)
        ttk.Radiobutton(sens_frame, text="High (More detections)", variable=self.sensitivity_var,
                       value="high").grid(row=2, column=0, sticky=tk.W)
        ttk.Radiobutton(sens_frame, text="Real Image Optimized (Best for real mines)",
                       variable=self.sensitivity_var, value="real_image_optimized").grid(row=3, column=0, sticky=tk.W)

        # Detect button
        self.detect_button = ttk.Button(control_frame, text="Detect Objects",
                                       command=self.run_detection, state=tk.DISABLED, width=20)
        self.detect_button.grid(row=3, column=0, pady=(10, 10))

        # Save button
        self.save_button = ttk.Button(control_frame, text="Save Result",
                                     command=self.save_result, state=tk.DISABLED, width=20)
        self.save_button.grid(row=4, column=0, pady=(0, 10))

        # Results frame
        results_frame = ttk.LabelFrame(control_frame, text="Results", padding="5")
        results_frame.grid(row=5, column=0, sticky=(tk.W, tk.E))

        self.results_text = tk.Text(results_frame, height=8, width=25, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.results_text.yview)
        self.results_text.configure(yscrollcommand=scrollbar.set)

        self.results_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)

        # Image display area (right side)
        image_frame = ttk.LabelFrame(main_frame, text="Image", padding="10")
        image_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Canvas for image display
        self.canvas = tk.Canvas(image_frame, bg="gray", width=600, height=400)
        self.canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Scrollbars for canvas
        h_scrollbar = ttk.Scrollbar(image_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        v_scrollbar = ttk.Scrollbar(image_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set)

        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        image_frame.columnconfigure(0, weight=1)
        image_frame.rowconfigure(0, weight=1)

        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready - Select an image to begin")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))

        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(5, 0))

    def center_window(self):
        """Center the window on screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def select_image(self):
        """Open file dialog to select an image"""
        file_types = [
            ('Image files', '*.jpg *.jpeg *.png *.bmp *.tiff *.tif'),
            ('JPEG files', '*.jpg *.jpeg'),
            ('PNG files', '*.png'),
            ('BMP files', '*.bmp'),
            ('TIFF files', '*.tiff *.tif'),
            ('All files', '*.*')
        ]

        file_path = filedialog.askopenfilename(
            title="Select an image file",
            filetypes=file_types
        )

        if file_path:
            self.image_path = file_path
            self.load_and_display_image()
            self.detect_button.config(state=tk.NORMAL)
            self.status_var.set(f"Image loaded: {os.path.basename(file_path)}")
        else:
            self.status_var.set("No image selected")

    def load_and_display_image(self):
        """Load and display the selected image"""
        try:
            # Load image with OpenCV
            self.original_image = cv2.imread(self.image_path)
            if self.original_image is None:
                raise ValueError("Could not load image")

            # Convert to RGB for display
            rgb_image = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2RGB)

            # Convert to PIL Image
            pil_image = Image.fromarray(rgb_image)

            # Resize if too large (max 800x600 for display)
            max_width, max_height = 800, 600
            width, height = pil_image.size

            if width > max_width or height > max_height:
                ratio = min(max_width/width, max_height/height)
                new_width = int(width * ratio)
                new_height = int(height * ratio)
                pil_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Convert to PhotoImage
            self.photo_image = ImageTk.PhotoImage(pil_image)

            # Display on canvas
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo_image)

            # Configure canvas scroll region
            self.canvas.config(scrollregion=(0, 0, pil_image.width, pil_image.height))

            self.processed_image = None
            self.save_button.config(state=tk.DISABLED)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image: {str(e)}")
            self.status_var.set("Error loading image")

    def run_detection(self):
        """Run object detection in a separate thread"""
        if not self.image_path or self.original_image is None:
            messagebox.showwarning("Warning", "Please select an image first")
            return

        # Get calibration value
        try:
            calib_text = self.calib_var.get().strip()
            self.pixels_per_cm = float(calib_text) if calib_text else None
        except ValueError:
            messagebox.showerror("Error", "Invalid calibration value. Please enter a number or leave empty.")
            return

        # Get sensitivity setting
        self.sensitivity = self.sensitivity_var.get()

        # Disable buttons during processing
        self.detect_button.config(state=tk.DISABLED)
        self.select_button.config(state=tk.DISABLED)
        self.save_button.config(state=tk.DISABLED)

        # Clear previous results
        self.results_text.delete(1.0, tk.END)

        # Start detection in background thread
        detection_thread = threading.Thread(target=self.perform_detection)
        detection_thread.daemon = True
        detection_thread.start()

    def perform_detection(self):
        """Perform the actual detection (runs in background thread)"""
        try:
            self.progress_var.set(10)
            self.status_var.set("Preprocessing image...")

            # Preprocess image
            _, blurred = load_and_preprocess_image(self.image_path)

            self.progress_var.set(30)
            self.status_var.set("Detecting landmines...")

            # Detect circles (landmines)
            circles = detect_circles(blurred, self.pixels_per_cm, self.sensitivity, os.path.basename(self.image_path))

            self.progress_var.set(60)
            self.status_var.set("Detecting square objects...")

            # Detect squares
            squares = detect_squares(blurred)

            self.progress_var.set(80)
            self.status_var.set("Drawing results...")

            # Draw detections
            result_image = draw_detections(self.original_image.copy(), circles, squares)

            self.progress_var.set(100)
            self.status_var.set("Detection completed")

            # Store results
            self.processed_image = result_image
            self.detection_results = (circles, squares)

            # Update GUI in main thread
            self.root.after(0, self.display_results)

        except Exception as e:
            self.root.after(0, lambda: self.show_error(str(e)))

    def display_results(self):
        """Display detection results (called from main thread)"""
        circles, squares = self.detection_results

        # Convert result to display format
        rgb_result = cv2.cvtColor(self.processed_image, cv2.COLOR_BGR2RGB)
        pil_result = Image.fromarray(rgb_result)

        # Resize if needed
        max_width, max_height = 800, 600
        width, height = pil_result.size

        if width > max_width or height > max_height:
            ratio = min(max_width/width, max_height/height)
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            pil_result = pil_result.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Display result
        self.photo_image = ImageTk.PhotoImage(pil_result)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo_image)
        self.canvas.config(scrollregion=(0, 0, pil_result.width, pil_result.height))

        # Update results text
        results_text = f"Detection Results:\n\n"
        results_text += f"Landmines detected: {len(circles)}\n"

        for i, (x, y, r) in enumerate(circles, 1):
            diameter_pixels = r * 2
            if self.pixels_per_cm:
                diameter_cm = diameter_pixels / self.pixels_per_cm
                results_text += f"  {i}. Center: ({x},{y})\n"
                results_text += f"     Size: {diameter_cm:.1f} cm diameter\n"
            else:
                results_text += f"  {i}. Center: ({x},{y}), Radius: {r} pixels\n"

        results_text += f"\nSquare objects detected: {len(squares)}\n"

        for i, (x, y, w, h) in enumerate(squares, 1):
            results_text += f"  {i}. Position: ({x},{y}), Size: {w}x{h} pixels\n"

        self.results_text.insert(tk.END, results_text)

        # Enable buttons
        self.detect_button.config(state=tk.NORMAL)
        self.select_button.config(state=tk.NORMAL)
        self.save_button.config(state=tk.NORMAL)

        # Reset progress
        self.progress_var.set(0)

    def save_result(self):
        """Save the detection result to file"""
        if self.processed_image is None:
            messagebox.showwarning("Warning", "No processed image to save")
            return

        # Suggest filename
        base_name = os.path.splitext(os.path.basename(self.image_path))[0]
        default_name = f"{base_name}_detected.jpg"

        file_path = filedialog.asksaveasfilename(
            defaultextension=".jpg",
            initialfile=default_name,
            filetypes=[
                ("JPEG files", "*.jpg"),
                ("PNG files", "*.png"),
                ("All files", "*.*")
            ]
        )

        if file_path:
            try:
                cv2.imwrite(file_path, self.processed_image)
                self.status_var.set(f"Result saved to: {file_path}")
                messagebox.showinfo("Success", f"Image saved successfully!\n\n{file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save image: {str(e)}")

    def show_error(self, error_msg):
        """Show error message (called from background thread)"""
        messagebox.showerror("Detection Error", f"An error occurred during detection:\n\n{error_msg}")

        # Reset UI
        self.detect_button.config(state=tk.NORMAL)
        self.select_button.config(state=tk.NORMAL)
        self.progress_var.set(0)
        self.status_var.set("Error occurred during detection")

def main():
    """Main function to run the GUI application"""
    root = tk.Tk()
    app = ObjectDetectionGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()