#!/usr/bin/env python
"""
Download OpenWebText dataset (Skylion007/openwebtext) streaming and save to text file until reaching target size.
Target: at least 1GB of text.
"""

import os
from datasets import load_dataset
from tqdm import tqdm

def main():
    target_size = 1024 * 1024 * 1024  # 1 GB in bytes
    output_file = os.path.join("data", "raw", "openwebtext.txt")
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    print(f"Loading OpenWebText dataset (Skylion007/openwebtext) streaming...")
    try:
        dataset = load_dataset("Skylion007/openwebtext", split="train", streaming=True)
    except Exception as e:
        print(f"Failed to load dataset: {e}")
        return

    print("Streaming and writing text...")
    total_bytes = 0
    example_count = 0

    with open(output_file, "w", encoding="utf-8") as f:
        for example in tqdm(dataset, desc="Examples"):
            text = example["text"]
            # Write text plus a separator (double newline) to mimic document boundaries
            f.write(text)
            f.write("\n\n")
            total_bytes += len(text) + 2
            example_count += 1

            if total_bytes >= target_size:
                print(f"\nReached target size of {target_size // (1024*1024)} MB after {example_count} examples.")
                break

    # Report final size
    total_mb = total_bytes / (1024 * 1024)
    print(f"Finished. Written {total_mb:.2f} MB ({total_bytes} bytes) to {output_file}")
    print(f"Number of examples: {example_count}")

if __name__ == "__main__":
    main()