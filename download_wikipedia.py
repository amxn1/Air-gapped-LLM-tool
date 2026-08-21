#!/usr/bin/env python
"""
Download Wikipedia dataset (streaming) and save to text file until reaching target size.
Target: at least 1GB of text.
"""

import os
from datasets import load_dataset
from tqdm import tqdm

def main():
    target_size = 1024 * 1024 * 1024  # 1 GB in bytes
    output_file = os.path.join("data", "raw", "wikipedia.txt")
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    print(f"Loading Wikipedia dataset (streaming)...")
    try:
        # Try loading the Wikipedia dataset (English, 20200501 version)
        dataset = load_dataset("wikipedia", "20200501.en", split="train", streaming=True)
    except Exception as e:
        print(f"Failed to load wikipedia 20200501.en: {e}")
        print("Trying wikipedia latest...")
        try:
            dataset = load_dataset("wikipedia", "20220301.en", split="train", streaming=True)
        except Exception as e2:
            print(f"Failed to load wikipedia 20220301.en: {e2}")
            print("Trying generic wikipedia...")
            dataset = load_dataset("wikipedia", split="train", streaming=True)

    print("Streaming and writing text...")
    total_bytes = 0
    article_count = 0

    with open(output_file, "w", encoding="utf-8") as f:
        for article in tqdm(dataset, desc="Articles"):
            text = article["text"]
            # Write article text plus a separator
            f.write(text)
            f.write("\n\n")  # separator between articles
            total_bytes += len(text) + 2  # +2 for newlines
            article_count += 1

            if total_bytes >= target_size:
                print(f"\nReached target size of {target_size // (1024*1024)} MB after {article_count} articles.")
                break

    # Report final size
    total_mb = total_bytes / (1024 * 1024)
    print(f"Finished. Written {total_mb:.2f} MB ({total_bytes} bytes) to {output_file}")
    print(f"Number of articles: {article_count}")

if __name__ == "__main__":
    main()