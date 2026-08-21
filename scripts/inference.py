#!/usr/bin/env python
"""
Inference script for the trained GPT model.
Loads the trained model and generates text from prompts with temperature control and sampling.
"""

import os
import json
import torch
import torch.nn.functional as F
from pathlib import Path
import time
from typing import List, Optional

# Import our model
import sys
sys.path.append(str(Path("scripts")))
from model import GPT, GPTConfig

# Import tokenizer
from tokenizers import Tokenizer


def load_model_and_tokenizer(checkpoint_path: str = "checkpoints/best_model.pt"):
    """Load the trained model and tokenizer."""

    # Load tokenizer
    tokenizer_path = Path("data/tokenizer/tokenizer.json")
    tokenizer = Tokenizer.from_file(str(tokenizer_path))
    vocab_size = tokenizer.get_vocab_size()
    pad_token_id = tokenizer.token_to_id("<pad>")

    print(f"Loaded tokenizer: vocab size = {vocab_size}, pad token id = {pad_token_id}")

    # Load checkpoint to get model configuration
    checkpoint = torch.load(checkpoint_path, map_location='cpu')

    # Create model with same configuration as used in training
    config = GPTConfig(
        vocab_size=vocab_size,
        block_size=128,  # Same as used in training
        n_layer=12,
        n_head=12,
        n_embd=768,
        embd_pdrop=0.1,
        resid_pdrop=0.1,
        attn_pdrop=0.1,
    )

    model = GPT(config)
    model.load_state_dict(checkpoint['model_state_dict'])

    # Move to appropriate device
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = model.to(device)
    model.eval()

    print(f"Model loaded from {checkpoint_path}")
    print(f"Model parameters: {model.get_num_params():,}")
    print(f"Using device: {device}")

    return model, tokenizer, device


def sample_logits(logits: torch.Tensor, temperature: float = 1.0, top_k: Optional[int] = None, top_p: Optional[float] = None) -> int:
    """
    Sample from logits with temperature, top-k, and top-p (nucleus) sampling.

    Args:
        logits: Logits tensor of shape (vocab_size,)
        temperature: Temperature for sampling (higher = more random)
        top_k: Keep only top k tokens for sampling
        top_p: Keep tokens with cumulative probability <= top_p (nucleus sampling)

    Returns:
        Selected token id
    """
    logits = logits / temperature

    # Apply top-k filtering
    if top_k is not None:
        top_k = min(top_k, logits.size(-1))
        indices_to_remove = logits < torch.topk(logits, top_k)[0][..., -1, None]
        logits[indices_to_remove] = float('-inf')

    # Apply top-p (nucleus) filtering
    if top_p is not None:
        sorted_logits, sorted_indices = torch.sort(logits, descending=True)
        cumulative_probs = torch.cumsum(F.softmax(sorted_logits, dim=-1), dim=-1)

        # Remove tokens with cumulative probability above the threshold
        sorted_indices_to_remove = cumulative_probs > top_p
        # Shift the indices to the right to keep also the first token above the threshold
        sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[..., :-1].clone()
        sorted_indices_to_remove[..., 0] = 0

        indices_to_remove = sorted_indices[sorted_indices_to_remove]
        logits[indices_to_remove] = float('-inf')

    # Sample from the filtered distribution
    probs = F.softmax(logits, dim=-1)
    next_token = torch.multinomial(probs, num_samples=1)

    return next_token.item()


def generate_text(
    model: GPT,
    tokenizer: Tokenizer,
    device: torch.device,
    prompt: str,
    max_new_tokens: int = 100,
    temperature: float = 0.8,
    top_k: Optional[int] = 50,
    top_p: Optional[float] = 0.9,
    pad_token_id: int = 1
) -> str:
    """
    Generate text from a prompt using the trained model.

    Args:
        model: Trained GPT model
        tokenizer: Tokenizer for encoding/decoding
        device: Device to run inference on
        prompt: Input text prompt
        max_new_tokens: Maximum number of tokens to generate
        temperature: Sampling temperature
        top_k: Top-k sampling parameter
        top_p: Top-p (nucleus) sampling parameter
        pad_token_id: ID of padding token

    Returns:
        Generated text (prompt + completion)
    """
    # Encode the prompt
    encoding = tokenizer.encode(prompt)
    input_ids = torch.tensor([encoding.ids], dtype=torch.long, device=device)

    # Track generated tokens for display
    generated_tokens = encoding.ids.copy()

    print(f"Prompt: {prompt}")
    print("Generating: ", end="", flush=True)

    # Generate tokens one by one
    with torch.no_grad():
        for _ in range(max_new_tokens):
            # Get model predictions
            logits, _ = model(input_ids)
            logits = logits[0, -1, :]  # Get logits for the last token

            # Sample next token
            next_token_id = sample_logits(logits, temperature=temperature, top_k=top_k, top_p=top_p)

            # Stop if we generate the pad token (optional)
            if next_token_id == pad_token_id:
                break

            # Append generated token
            generated_tokens.append(next_token_id)
            input_ids = torch.tensor([generated_tokens], dtype=torch.long, device=device)

            # Decode and display the new token in real-time
            new_token_text = tokenizer.decode([next_token_id])
            print(new_token_text, end="", flush=True)

            # Optional: stop at natural breaking points
            if new_token_text.strip() in ['.', '!', '?', '\n']:
                # Small pause for readability
                time.sleep(0.05)

    print()  # New line after generation

    # Decode full generated text
    generated_text = tokenizer.decode(generated_tokens)
    return generated_text


def interactive_inference():
    """Run interactive inference session."""
    print("Loading model and tokenizer...")
    model, tokenizer, device = load_model_and_tokenizer()

    print("\n" + "="*50)
    print("INTERACTIVE TEXT GENERATION")
    print("="*50)
    print("Enter prompts to generate text. Type 'quit' to exit.")
    print("You can adjust parameters:")
    print("  - Temperature (default: 0.8): Higher = more random")
    print("  - Top-k (default: 50): Keep only top k tokens")
    print("  - Top-p (default: 0.9): Nucleus sampling threshold")
    print("  - Max tokens (default: 100): Maximum generation length")
    print("-" * 50)

    while True:
        try:
            # Get user input
            prompt = input("\nPrompt: ").strip()

            if prompt.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break

            if not prompt:
                print("Please enter a prompt.")
                continue

            # Get generation parameters
            try:
                temp_input = input("Temperature (0.1-2.0, default 0.8): ").strip()
                temperature = float(temp_input) if temp_input else 0.8
                temperature = max(0.1, min(2.0, temperature))  # Clamp to reasonable range
            except ValueError:
                temperature = 0.8

            try:
                top_k_input = input("Top-k (default 50, 0 to disable): ").strip()
                top_k = int(top_k_input) if top_k_input else 50
                top_k = None if top_k == 0 else top_k
            except ValueError:
                top_k = 50

            try:
                top_p_input = input("Top-p (0.0-1.0, default 0.9, 0 to disable): ").strip()
                top_p = float(top_p_input) if top_p_input else 0.9
                top_p = None if top_p == 0.0 else max(0.0, min(1.0, top_p))
            except ValueError:
                top_p = 0.9

            try:
                max_tokens_input = input("Max new tokens (default 100): ").strip()
                max_new_tokens = int(max_tokens_input) if max_tokens_input else 100
                max_new_tokens = max(1, max_new_tokens)
            except ValueError:
                max_new_tokens = 100

            print("\n" + "-"*30)
            # Generate text
            start_time = time.time()
            generated_text = generate_text(
                model=model,
                tokenizer=tokenizer,
                device=device,
                prompt=prompt,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_k=top_k,
                top_p=top_p,
                pad_token_id=tokenizer.token_to_id("<pad>")
            )
            generation_time = time.time() - start_time

            print("-"*30)
            print(f"Generated in {generation_time:.2f} seconds")
            print(f"Full text: {generated_text}")

        except KeyboardInterrupt:
            print("\n\nInterrupted by user. Goodbye!")
            break
        except Exception as e:
            print(f"Error during generation: {e}")
            print("Please try again.")


if __name__ == "__main__":
    interactive_inference()