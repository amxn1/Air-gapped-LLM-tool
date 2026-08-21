#!/usr/bin/env python
"""
Test script for the GUI model loading with visible window.
"""
import tkinter as tk
import sys
import time
from pathlib import Path

# Add the scripts directory to the path
sys.path.append(str(Path("scripts")))
from gui_app import ModelGUI

def test_model_loading():
    # Create the main window
    root = tk.Tk()
    root.title("LLM GUI Test")
    root.geometry("400x200")

    # Create the GUI app
    app = ModelGUI(root)

    # Add a label to show status
    status_label = tk.Label(root, text="Initializing...", fg="blue")
    status_label.pack(pady=10)

    # Add a test button to verify responsiveness
    test_button = tk.Button(root, text="Test Responsiveness",
                           command=lambda: test_button.config(text="Responsive!"))
    test_button.pack(pady=5)

    # Function to update status from the app
    def update_status_display():
        status_label.config(text=f"Status: {app.status_var.get()}")
        if app.model is not None:
            status_label.config(text=f"Model loaded! Status: {app.status_var.get()}", fg="green")
            test_button.config(state="disabled")  # Disable button after success
        elif not app.is_loading and app.model is None:
            status_label.config(text=f"Model failed! Status: {app.status_var.get()}", fg="red")
            test_button.config(state="disabled")  # Disable button after failure
        # Schedule next update
        root.after(500, update_status_display)

    # Start updating status
    root.after(500, update_status_display)

    # Run for 20 seconds then cleanup
    def cleanup():
        print('Test completed, closing GUI')
        root.quit()
        root.destroy()

    root.after(20000, cleanup)  # Close after 20 seconds
    print("Starting GUI test - window should be visible")
    root.mainloop()
    print("GUI test completed")

if __name__ == "__main__":
    test_model_loading()