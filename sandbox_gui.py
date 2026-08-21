#!/usr/bin/env python
"""
Sandbox GUI to test model loading with threading.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import torch
from pathlib import Path
import sys
import time

# Import our model
sys.path.append(str(Path("scripts")))
from model import GPT, GPTConfig

# Import tokenizer
from tokenizers import Tokenizer


class SimpleGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Simple LLM GUI Test")
        self.root.geometry("400x200")

        # Model state
        self.model = None
        self.tokenizer = None
        self.is_loading = False

        # Create widgets
        self.create_widgets()

        # Start loading model
        self.load_model()

    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(main_frame, text="LLM GUI Test",
                               font=("Arial", 14, "bold"))
        title_label.pack(pady=(0, 10))

        # Status label
        self.status_var = tk.StringVar(value="Loading model...")
        status_label = ttk.Label(main_frame, textvariable=self.status_var,
                                foreground="blue")
        status_label.pack(pady=5)

        # Test button
        self.test_btn = ttk.Button(main_frame, text="Test Responsiveness",
                                  command=self.test_responsiveness)
        self.test_btn.pack(pady=10)

    def load_model(self):
        """Load model in background thread."""
        def load_in_background():
            try:
                self.update_status("Loading tokenizer...")
                tokenizer_path = Path("data/tokenizer/tokenizer.json")
                self.tokenizer = Tokenizer.from_file(str(tokenizer_path))

                self.update_status("Loading model...")
                checkpoint = torch.load("checkpoints/best_model.pt", map_location='cpu')

                self.update_status("Creating model...")
                config = GPTConfig(
                    vocab_size=self.tokenizer.get_vocab_size(),
                    block_size=128,
                    n_layer=12,
                    n_head=12,
                    n_embd=768,
                    embd_pdrop=0.1,
                    resid_pdrop=0.1,
                    attn_pdrop=0.1,
                )

                self.model = GPT(config)
                self.model.load_state_dict(checkpoint['model_state_dict'])
                self.model.eval()

                self.update_status("Model loaded successfully!")
            except Exception as e:
                self.update_status(f"Error: {str(e)}")
                messagebox.showerror("Error", f"Failed to load model:\n{str(e)}")
            finally:
                self.is_loading = False

        self.is_loading = True
        thread = threading.Thread(target=load_in_background, daemon=True)
        thread.start()

    def update_status(self, message):
        """Update status label (thread-safe)."""
        self.root.after(0, lambda: self._update_status_internal(message))

    def _update_status_internal(self, message):
        """Internal method to update status label (called from main thread)."""
        self.status_var.set(message)
        self.root.update_idletasks()

    def test_responsiveness(self):
        """Test if GUI is responsive."""
        self.test_btn.config(text="Responsive!")
        self.root.after(1000, lambda: self.test_btn.config(text="Test Responsiveness"))


def main():
    root = tk.Tk()
    app = SimpleGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()