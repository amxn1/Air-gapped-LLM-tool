#!/usr/bin/env python
"""
Desktop GUI for testing the trained GPT model.
Provides an interface for text generation with adjustable parameters.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import torch
import torch.nn.functional as F
from pathlib import Path
import sys
import time
import queue
from typing import Optional

# Import our model
sys.path.append(str(Path("scripts")))
from model import GPT, GPTConfig

# Import tokenizer
from tokenizers import Tokenizer


class ModelGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("LLM Text Generation Interface")
        self.root.geometry("800x600")
        self.root.minsize(700, 500)

        # Model state
        self.model = None
        self.tokenizer = None
        self.device = None
        self.is_loading = False
        self.is_generating = False

        # Thread communication queue
        self.queue = queue.Queue()

        # Create GUI
        self.create_widgets()

        # Schedule model loading to start after mainloop begins
        self.root.after(100, self.start_model_loading)

        # Start processing queue
        self.process_queue()

        # Automatically quit after 10 seconds for testing
        self.root.after(10000, self.root.quit)

    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)  # Text area row

        # Title
        title_label = ttk.Label(main_frame, text="LLM Text Generation Interface",
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))

        # Model status
        self.status_var = tk.StringVar(value="Loading model...")
        status_label = ttk.Label(main_frame, textvariable=self.status_var,
                                foreground="blue")
        status_label.grid(row=1, column=0, columnspan=3, pady=(0, 10))

        # Prompt input
        ttk.Label(main_frame, text="Prompt:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.prompt_var = tk.StringVar()
        prompt_entry = ttk.Entry(main_frame, textvariable=self.prompt_var, width=50)
        prompt_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(5, 5), pady=5)
        prompt_entry.bind("<Return>", self.start_generation)

        # Generate button
        self.generate_btn = ttk.Button(main_frame, text="Generate",
                                      command=self.start_generation)
        self.generate_btn.grid(row=2, column=2, padx=(5, 0), pady=5)

        # Parameters frame
        params_frame = ttk.LabelFrame(main_frame, text="Generation Parameters", padding="10")
        params_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        params_frame.columnconfigure(1, weight=1)
        params_frame.columnconfigure(3, weight=1)

        # Temperature
        ttk.Label(params_frame, text="Temperature:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.temp_var = tk.DoubleVar(value=0.8)
        temp_scale = ttk.Scale(params_frame, from_=0.1, to=2.0,
                              variable=self.temp_var, orient=tk.HORIZONTAL)
        temp_scale.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        temp_label = ttk.Label(params_frame, textvariable=tk.StringVar(value="0.8"))
        temp_label.grid(row=0, column=2, padx=5)
        # Update label when scale changes
        self.temp_var.trace('w', lambda *args: temp_label.config(text=f"{self.temp_var.get():.2f}"))

        # Top-k
        ttk.Label(params_frame, text="Top-k:").grid(row=0, column=3, sticky=tk.W, padx=(20, 5))
        self.topk_var = tk.IntVar(value=50)
        topk_spin = ttk.Spinbox(params_frame, from_=0, to=100,
                               textvariable=self.topk_var, width=10)
        topk_spin.grid(row=0, column=4, padx=5)
        ttk.Label(params_frame, text="(0=disabled)").grid(row=0, column=5, sticky=tk.W, padx=5)

        # Top-p
        ttk.Label(params_frame, text="Top-p:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.topp_var = tk.DoubleVar(value=0.9)
        topp_scale = ttk.Scale(params_frame, from_=0.0, to=1.0,
                              variable=self.topp_var, orient=tk.HORIZONTAL)
        topp_scale.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        topp_label = ttk.Label(params_frame, textvariable=tk.StringVar(value="0.9"))
        topp_label.grid(row=1, column=2, padx=5, pady=5)
        self.topp_var.trace('w', lambda *args: topp_label.config(text=f"{self.topp_var.get():.2f}"))

        # Max tokens
        ttk.Label(params_frame, text="Max Tokens:").grid(row=1, column=3, sticky=tk.W, padx=(20, 5), pady=5)
        self.maxtokens_var = tk.IntVar(value=100)
        maxtokens_spin = ttk.Spinbox(params_frame, from_=1, to=500,
                                    textvariable=self.maxtokens_var, width=10)
        maxtokens_spin.grid(row=1, column=4, padx=5, pady=5)

        # Output text area
        ttk.Label(main_frame, text="Generated Text:").grid(row=4, column=0, sticky=tk.NW, pady=(10, 5))
        self.output_text = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD,
                                                    width=70, height=15)
        self.output_text.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S),
                             pady=(0, 10))

        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))

        # Clear button
        clear_btn = ttk.Button(main_frame, text="Clear Output",
                              command=self.clear_output)
        clear_btn.grid(row=7, column=0, columnspan=3, pady=5)

        # Bind Enter key to generate
        self.root.bind('<Control-Return>', lambda e: self.start_generation())

    def start_model_loading(self):
        """Start the model loading in a background thread."""
        print("Starting model loading...")
        self.load_model()

    def load_model(self):
        """Load model in background thread."""
        def load_in_background():
            try:
                print("  Loading tokenizer...")
                self.queue.put(("status", "Loading tokenizer..."))
                tokenizer_path = Path("data/tokenizer/tokenizer.json")
                self.tokenizer = Tokenizer.from_file(str(tokenizer_path))

                print("  Loading model checkpoint...")
                self.queue.put(("status", "Loading model checkpoint..."))
                # Try to load best model first, then final
                checkpoint_paths = [
                    "checkpoints/best_model.pt",
                    "checkpoints/final_model.pt",
                    "checkpoints/model_step1000.pt",
                    "checkpoints/model_step500.pt"
                ]

                checkpoint_path = None
                for path in checkpoint_paths:
                    if Path(path).exists():
                        checkpoint_path = path
                        break

                if checkpoint_path is None:
                    raise FileNotFoundError("No model checkpoint found")

                checkpoint = torch.load(checkpoint_path, map_location='cpu')

                print("  Creating model architecture...")
                self.queue.put(("status", "Creating model architecture..."))
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

                print("  Moving model to device...")
                self.queue.put(("status", "Moving model to device..."))
                self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
                self.model = self.model.to(self.device)
                self.model.eval()

                print(f"  Model loaded successfully on {self.device}")
                self.queue.put(("status", f"Model loaded successfully on {self.device}"))
                self.queue.put(("button_state", "normal"))

            except Exception as e:
                print(f"  Error loading model: {e}")
                self.queue.put(("status", f"Error loading model: {str(e)}"))
                self.queue.put(("error", f"Failed to load model:\n{str(e)}"))
            finally:
                print("  Model loading thread finished.")
                self.queue.put(("loading_done", None))

        # Start loading in background thread
        self.is_loading = True
        self.generate_btn.config(state="disabled")
        thread = threading.Thread(target=load_in_background, daemon=True)
        thread.start()

    def process_queue(self):
        """Process messages from the queue (called periodically from main thread)."""
        try:
            while True:
                msg_type, msg_data = self.queue.get_nowait()
                if msg_type == "status":
                    self.status_var.set(msg_data)
                    print(f"  Status update: {msg_data}")
                elif msg_type == "button_state":
                    self.generate_btn.config(state=msg_data)
                elif msg_type == "error":
                    messagebox.showerror("Error", msg_data)
                elif msg_type == "loading_done":
                    self.is_loading = False
                elif msg_type == "gen_status":
                    self.status_var.set(msg_data)
                    print(f"  Generation status: {msg_data}")
                elif msg_type == "append_text":
                    self.output_text.insert(tk.END, msg_data)
                    self.output_text.see(tk.END)
                elif msg_type == "gen_complete":
                    self.is_generating = False
                    self.generate_btn.config(state="normal")
                    self.progress.stop()
                    self.status_var.set("Generation complete")
                    print("  Generation completed.")

                    # Add final newline and full text summary
                    self.output_text.insert(tk.END, "\n\n" + "="*50 + "\n")
                    self.output_text.insert(tk.END, f"Full generation ({len(msg_data[0])} chars):\n{msg_data[0]}\n")
                    self.output_text.see(tk.END)
                elif msg_type == "gen_error":
                    self.is_generating = False
                    self.generate_btn.config(state="normal")
                    self.progress.stop()
                    self.status_var.set("Generation failed")
                    print(f"  Generation error: {msg_data}")
                    messagebox.showerror("Generation Error", f"Failed to generate text:\n{msg_data}")
        except queue.Empty:
            pass
        finally:
            # Schedule next check
            self.root.after(100, self.process_queue)

    def start_generation(self, event=None):
        """Start text generation in background thread."""
        if self.is_loading or self.is_generating or self.model is None:
            messagebox.showwarning("Warning", "Model is still loading or already generating")
            return

        prompt = self.prompt_var.get().strip()
        if not prompt:
            messagebox.showwarning("Warning", "Please enter a prompt")
            return

        # Disable UI during generation
        self.is_generating = True
        self.generate_btn.config(state="disabled")
        self.progress.start()
        self.queue.put(("gen_status", "Generating text..."))
        print("  Starting generation...")

        # Clear output and show prompt
        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(tk.END, f"Prompt: {prompt}\n")
        self.output_text.insert(tk.END, "Generating: ")
        self.output_text.see(tk.END)

        # Start generation in background
        thread = threading.Thread(
            target=self.generate_text_thread,
            args=(prompt,),
            daemon=True
        )
        thread.start()

    def generate_text_thread(self, prompt: str):
        """Generate text in background thread."""
        try:
            # Get parameters
            temperature = max(0.1, min(2.0, self.temp_var.get()))
            top_k = self.topk_var.get()
            top_k = None if top_k == 0 else top_k
            top_p = self.topp_var.get()
            top_p = None if top_p == 0.0 else max(0.0, min(1.0, top_p))
            max_new_tokens = self.maxtokens_var.get()
            pad_token_id = self.tokenizer.token_to_id("<pad>")

            print(f"    Generation parameters: temp={temperature}, top_k={top_k}, top_p={top_p}, max_tokens={max_new_tokens}")

            # Encode prompt
            encoding = self.tokenizer.encode(prompt)
            input_ids = torch.tensor([encoding.ids], dtype=torch.long, device=self.device)
            generated_tokens = encoding.ids.copy()

            # Generate tokens
            with torch.no_grad():
                for i in range(max_new_tokens):
                    # Get model predictions
                    logits, _ = self.model(input_ids)
                    logits = logits[0, -1, :]  # Get logits for last token

                    # Apply temperature
                    logits = logits / temperature

                    # Apply top-k filtering
                    if top_k is not None:
                        top_k_actual = min(top_k, logits.size(-1))
                        indices_to_remove = logits < torch.topk(logits, top_k_actual)[0][..., -1, None]
                        logits[indices_to_remove] = float('-inf')

                    # Apply top-p filtering
                    if top_p is not None:
                        sorted_logits, sorted_indices = torch.sort(logits, descending=True)
                        cumulative_probs = torch.cumsum(F.softmax(sorted_logits, dim=-1), dim=-1)
                        sorted_indices_to_remove = cumulative_probs > top_p
                        sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[..., :-1].clone()
                        sorted_indices_to_remove[..., 0] = 0
                        indices_to_remove = sorted_indices[sorted_indices_to_remove]
                        logits[indices_to_remove] = float('-inf')

                    # Sample from distribution
                    probs = F.softmax(logits, dim=-1)
                    next_token_id = torch.multinomial(probs, num_samples=1).item()

                    # Stop if pad token (optional)
                    if next_token_id == pad_token_id:
                        break

                    # Append token
                    generated_tokens.append(next_token_id)
                    input_ids = torch.tensor([generated_tokens], dtype=torch.long, device=self.device)

                    # Update display in real-time (thread-safe)
                    new_token_text = self.tokenizer.decode([next_token_id])
                    self.queue.put(("append_text", new_token_text))

                    # Small delay for visibility
                    time.sleep(0.01)

            # Final update
            full_text = self.tokenizer.decode(generated_tokens)
            self.queue.put(("gen_complete", (full_text, prompt)))
            print("    Generation thread finished.")

        except Exception as e:
            print(f"    Error in generation thread: {e}")
            self.queue.put(("gen_error", str(e)))

    def clear_output(self):
        """Clear the output text area."""
        self.output_text.delete(1.0, tk.END)


def main():
    root = tk.Tk()
    app = ModelGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()