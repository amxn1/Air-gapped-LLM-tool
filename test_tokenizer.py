#!/usr/bin/env python
"""Test loading the tokenizer."""
from tokenizers import Tokenizer
from pathlib import Path

tokenizer_path = Path("data/tokenizer/tokenizer.json")
print(f"Loading tokenizer from {tokenizer_path}")
tokenizer = Tokenizer.from_file(str(tokenizer_path))
print(f"Tokenizer loaded: vocab size = {tokenizer.get_vocab_size()}")
print(f"Pad token ID: {tokenizer.token_to_id('<pad>')}")