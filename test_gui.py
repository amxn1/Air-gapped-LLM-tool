#!/usr/bin/env python
"""
Test script for the GUI model loading.
"""
import tkinter as tk
import sys
import time
from pathlib import Path

# Add the scripts directory to the path
sys.path.append(str(Path("scripts")))
from gui_app import ModelGUI

def test_model_loading():
    # Create the main window but withdraw it so it doesn't show
    root = tk.Tk()
    root.withdraw()  # Hide the window

    # Create the GUI app
    app = ModelGUI(root)

    # Wait for the model to load or timeout
    timeout = 20  # seconds
    start = time.time()
    model_loaded = False
    error_occurred = False

    while time.time() - start < timeout:
        # Process Tk events to keep the GUI responsive
        root.update()
        # Check if model is loaded
        if app.model is not None:
            model_loaded = True
            break
        # Check if loading failed (is_loading is False and model is still None)
        if not app.is_loading and app.model is None:
            error_occurred = True
            break
        time.sleep(0.1)

    # Clean up
    root.quit()
    root.destroy()

    if model_loaded:
        print("SUCCESS: Model loaded successfully.")
        print(f"Final status: {app.status_var.get()}")
        return True
    elif error_occurred:
        print("FAILURE: Model loading failed.")
        print(f"Final status: {app.status_var.get()}")
        return False
    else:
        print("FAILURE: Timeout waiting for model to load.")
        print(f"Final status: {app.status_var.get()}")
        return False

if __name__ == "__main__":
    success = test_model_loading()
    sys.exit(0 if success else 1)