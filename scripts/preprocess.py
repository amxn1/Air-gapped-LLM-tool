#!/usr/bin/env python
"""
Data preprocessing pipeline for language model training.
Downloads a text dataset, trains a GPT-2 style tokenizer,
creates tokenized data loaders with train/val split.
"""

import os
import random
import numpy as np
from pathlib import Path
from typing import List, Tuple, Iterator
import torch
from torch.utils.data import Dataset, DataLoader
from datasets import load_dataset
from tokenizers import ByteLevelBPETokenizer
from tokenizers.processors import BertProcessing

# Configuration
DATASET_NAME = "wikitext"
DATASET_CONFIG = "wikitext-2-raw-v1"
MAX_SEQ_LENGTH = 16  # Fixed sequence length for training
BATCH_SIZE = 4
TRAIN_SPLIT = 0.8
VOCAB_SIZE = 5000   # Increased vocab size to get more meaningful tokens
MIN_FREQUENCY = 2
# Special tokens: end of text, padding, newline, space, mask
SPECIAL_TOKENS = ["", "<pad>", "\n", " ", "<mask>"]

# Paths
DATA_DIR = Path("data")
RAW_DATA_DIR = DATA_DIR / "raw"
TOKENIZER_DIR = DATA_DIR / "tokenizer"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
DATA_DIR.mkdir(exist_ok=True)
RAW_DATA_DIR.mkdir(exist_ok=True)
TOKENIZER_DIR.mkdir(exist_ok=True)
PROCESSED_DATA_DIR.mkdir(exist_ok=True)

def download_and_prepare_dataset() -> List[str]:
    """Download and prepare a public domain text dataset."""
    print(f"Downloading public domain text dataset...")
    # URL for Pride and Prejudice from Project Gutenberg
    url = "https://www.gutenberg.org/files/1342/1342-0.txt"
    raw_path = RAW_DATA_DIR / "pride_and_prejudice.txt"

    try:
        # Download the file
        import urllib.request
        import ssl
        # Disable SSL certificate verification for simplicity (not recommended for production)
        ssl._create_default_https_context = ssl._create_unverified_context
        urllib.request.urlretrieve(url, raw_path)
        print(f"Downloaded dataset to {raw_path}")

        # Read the file
        with open(raw_path, "r", encoding="utf-8") as f:
            text = f.read()

        # Split into lines and filter empty lines
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        print(f"Total lines: {len(lines)}")

        # Save combined text for tokenizer training
        combined_path = RAW_DATA_DIR / "combined_text.txt"
        with open(combined_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"Saved combined text to {combined_path}")

        return lines
    except Exception as e:
        print(f"Failed to download dataset from {url}: {e}")
        print("Falling back to creating a sample dataset from repeated paragraphs...")
        # Create a sample dataset by repeating a paragraph many times
        base_text = "It was the best of times, it was the worst of times, it was the age of wisdom, it was the age of foolishness, it was the epoch of belief, it was the epoch of incredulity, it was the season of Light, it was the season of Darkness, it was the spring of hope, it was the winter of despair. "
        # We want at least 100000 characters to get a good number of tokens
        long_text = ""
        target_length = 100000
        while len(long_text) < target_length:
            long_text += base_text
        # Trim to exact target length for consistency
        long_text = long_text[:target_length]
        sample_texts = [long_text]  # Return as a list with one element

        # Save raw texts for inspection
        raw_path = RAW_DATA_DIR / "combined_text.txt"
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write(long_text)
        print(f"Saved sample combined text to {raw_path} (length: {len(long_text)} chars)")

        return sample_texts

def train_tokenizer(texts: List[str]) -> ByteLevelBPETokenizer:
    """Train a ByteLevel BPE tokenizer similar to GPT-2."""
    print(f"Training tokenizer with vocab size {VOCAB_SIZE}...")

    # Initialize tokenizer
    tokenizer = ByteLevelBPETokenizer()

    # Train on the texts
    tokenizer.train(
        files=[str(RAW_DATA_DIR / "combined_text.txt")],
        vocab_size=VOCAB_SIZE,
        min_frequency=MIN_FREQUENCY,
        special_tokens=SPECIAL_TOKENS,
        show_progress=True,
    )

    # We do not enable truncation/padding here; we'll handle it in the dataset
    # Just make sure the special tokens are in the vocabulary
    # Save tokenizer
    tokenizer.save(str(TOKENIZER_DIR / "tokenizer.json"))
    print(f"Tokenizer saved to {TOKENIZER_DIR / 'tokenizer.json'}")
    print(f"Vocab size: {tokenizer.get_vocab_size()}")

    return tokenizer

class TextTokenDataset(Dataset):
    """Dataset for tokenized text data."""

    def __init__(self, token_ids: List[int], seq_length: int = MAX_SEQ_LENGTH, pad_token_id: int = 0):
        self.seq_length = seq_length
        self.pad_token_id = pad_token_id
        # Create sequences of fixed length with non-overlapping chunks
        self.sequences = []
        # We'll create chunks that are exactly seq_length, padding the last one if necessary
        for i in range(0, len(token_ids), seq_length):
            chunk = token_ids[i:i + seq_length]
            if len(chunk) < seq_length:
                # Pad the chunk
                chunk = chunk + [self.pad_token_id] * (seq_length - len(chunk))
            self.sequences.append(chunk)

        print(f"Created {len(self.sequences)} sequences of length {seq_length}")

    def __len__(self) -> int:
        return len(self.sequences)

    def __getitem__(self, idx: int) -> torch.Tensor:
        return torch.tensor(self.sequences[idx], dtype=torch.long)

def create_data_loaders(tokenizer: ByteLevelBPETokenizer, texts: List[str]) -> Tuple[DataLoader, DataLoader]:
    """Create train and validation data loaders."""
    # Combine and shuffle texts
    combined_texts = "\n\n".join(texts)  # Join with double newline to separate documents

    # Tokenize without truncation/padding
    print("Tokenizing texts...")
    encoding = tokenizer.encode(combined_texts)
    token_ids = encoding.ids
    print(f"Total tokens: {len(token_ids)}")

    # Get the pad token ID
    pad_token_id = tokenizer.token_to_id("<pad>")
    print(f"Pad token ID: {pad_token_id}")

    # Split into train and validation tokens (before chunking)
    split_idx = int(len(token_ids) * TRAIN_SPLIT)
    train_tokens = token_ids[:split_idx]
    val_tokens = token_ids[split_idx:]

    print(f"Train tokens: {len(train_tokens)}")
    print(f"Validation tokens: {len(val_tokens)}")

    # Create datasets
    train_dataset = TextTokenDataset(train_tokens, seq_length=MAX_SEQ_LENGTH, pad_token_id=pad_token_id)
    val_dataset = TextTokenDataset(val_tokens, seq_length=MAX_SEQ_LENGTH, pad_token_id=pad_token_id)

    # Create data loaders
    train_loader = DataLoader(
        train_dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
        drop_last=False,  # We already padded, so we can keep all batches
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=BATCH_SIZE,
        shuffle=False,
        drop_last=False,
    )

    return train_loader, val_loader

def show_samples(tokenizer: ByteLevelBPETokenizer, train_loader: DataLoader, num_batches: int = 2):
    """Show sample tokenized outputs."""
    print("\n" + "="*50)
    print("SAMPLE TOKENIZED OUTPUTS")
    print("="*50)

    # Get a few batches
    for i, batch in enumerate(train_loader):
        if i >= num_batches:
            break

        print(f"\nBatch {i+1} (shape: {batch.shape}):")
        # Show first sequence in batch
        seq = batch[0].tolist()
        tokens = tokenizer.decode(seq)

        print(f"Token IDs (first 20): {seq[:20]}")
        print(f"Decoded text: {repr(tokens[:200])}")  # Use repr to see special chars
        print("-" * 30)

def main():
    """Main preprocessing pipeline."""
    print("Starting data preprocessing pipeline for LLM training...")
    print("="*60)

    # Step 1: Download and prepare dataset
    texts = download_and_prepare_dataset()

    # Step 2: Train tokenizer
    tokenizer = train_tokenizer(texts)

    # Step 3: Create data loaders
    train_loader, val_loader = create_data_loaders(tokenizer, texts)

    # Step 4: Show samples
    show_samples(tokenizer, train_loader)

    # Step 5: Save processed data info
    info = {
        "dataset": f"{DATASET_NAME}/{DATASET_CONFIG}",
        "vocab_size": tokenizer.get_vocab_size(),
        "max_seq_length": MAX_SEQ_LENGTH,
        "batch_size": BATCH_SIZE,
        "train_batches": len(train_loader),
        "val_batches": len(val_loader),
        "special_tokens": SPECIAL_TOKENS,
    }

    import json
    info_path = PROCESSED_DATA_DIR / "dataset_info.json"
    with open(info_path, "w") as f:
        json.dump(info, f, indent=2)
    print(f"\nDataset info saved to {info_path}")

    print("\n" + "="*60)
    print("PREPROCESSING PIPELINE COMPLETE!")
    print("="*60)
    print(f"Saved tokenizer to: {TOKENIZER_DIR}")
    print(f"Processed data info: {info_path}")
    print(f"Train batches: {len(train_loader)}, Validation batches: {len(val_loader)}")

if __name__ == "__main__":
    main()