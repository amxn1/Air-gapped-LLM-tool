#!/usr/bin/env python
"""Quick test to verify GUI loads without errors."""
import tkinter as tk
import sys
import os
from pathlib import Path

# Setup path
sys.path.append(str(Path("scripts")))

def test_gui_import():
    """Test that we can import the GUI module."""
    try:
        from gui_app import ModelGUI
        print("✓ GUI module imported successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to import GUI module: {e}")
        return False

def test_tkinter_basic():
    """Test that tkinter works."""
    try:
        root = tk.Tk()
        root.withdraw()  # Don't show window
        label = tk.Label(root, text="Test")
        label.pack()
        root.update()
        root.destroy()
        print("✓ Tkinter basic functionality works")
        return True
    except Exception as e:
        print(f"✗ Tkinter basic test failed: {e}")
        return False

def test_model_files_exist():
    """Test that required model files exist."""
    required_files = [
        "data/tokenizer/tokenizer.json",
        "checkpoints/best_model.pt"
    ]

    all_good = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✓ Found: {file_path}")
        else:
            print(f"✗ Missing: {file_path}")
            all_good = False

    return all_good

if __name__ == "__main__":
    print("Running quick GUI tests...\n")

    tests = [
        test_tkinter_basic,
        test_gui_import,
        test_model_files_exist
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()  # Empty line between tests

    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("✓ All basic tests passed - GUI should work!")
        sys.exit(0)
    else:
        print("✗ Some tests failed - check the issues above")
        sys.exit(1)