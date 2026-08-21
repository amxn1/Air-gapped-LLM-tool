import os
import time
import math
import json
from pathlib import Path
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset
from torch.utils.checkpoint import checkpoint
import numpy as np

# Try to import tqdm for progress bars
try:
    from tqdm.auto import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    print("Warning: tqdm not installed. Using simple progress prints.")

# Try to import matplotlib for plotting
try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("Warning: matplotlib not installed. Loss plotting will be skipped.")

# Import our model from the scripts we created
import sys
sys.path.append(str(Path("scripts")))
from model import GPT, GPTConfig

# Define the TextTokenDataset class (to avoid import issues)
class TextTokenDataset(Dataset):
    """Dataset for tokenized text data."""

    def __init__(self, token_ids: list, seq_length: int, pad_token_id: int):
        self.seq_length = seq_length
        self.pad_token_id = pad_token_id
        # Create sequences of fixed length with non-overlapping chunks
        self.sequences = []
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

def load_tokenizer_and_text():
    """Load the tokenizer and the combined text data."""
    # Load tokenizer using the tokenizers library
    tokenizer_path = Path("data/tokenizer/tokenizer.json")
    from tokenizers import Tokenizer
    tokenizer = Tokenizer.from_file(str(tokenizer_path))

    # Get vocab size and pad token id
    vocab_size = tokenizer.get_vocab_size()
    pad_token_id = tokenizer.token_to_id("<pad>")
    print(f"Loaded tokenizer: vocab size = {vocab_size}, pad token id = {pad_token_id}")

    # Load combined text
    combined_path = Path("data/raw/combined_text.txt")
    with open(combined_path, 'r', encoding='utf-8') as f:
        combined_text = f.read()
    print(f"Loaded combined text: {len(combined_text)} characters")

    return tokenizer, combined_text, vocab_size, pad_token_id

def create_data_loaders(tokenizer, combined_text, block_size, batch_size, pad_token_id, train_split=0.8):
    """Create train and validation data loaders from combined text."""
    # Tokenize the entire text (without truncation/padding for now)
    print("Tokenizing text...")
    encoding = tokenizer.encode(combined_text)
    token_ids = encoding.ids
    print(f"Total tokens: {len(token_ids)}")

    # Split into train and validation
    split_idx = int(len(token_ids) * train_split)
    train_tokens = token_ids[:split_idx]
    val_tokens = token_ids[split_idx:]
    print(f"Train tokens: {len(train_tokens):,}")
    print(f"Validation tokens: {len(val_tokens):,}")

    # Create datasets
    train_dataset = TextTokenDataset(train_tokens, seq_length=block_size, pad_token_id=pad_token_id)
    val_dataset = TextTokenDataset(val_tokens, seq_length=block_size, pad_token_id=pad_token_id)

    # Create data loaders
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        drop_last=False,  # We already padded in the dataset
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        drop_last=False,
    )

    print(f"Train batches: {len(train_loader)}")
    print(f"Validation batches: {len(val_loader)}")

    return train_loader, val_loader

def train():
    """Main training function."""
    # Set device
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")

    # Hyperparameters
    block_size = 128  # Context length
    batch_size = 4
    gradient_accumulation_steps = 1  # Simulate larger batch sizes
    max_epochs = 3
    learning_rate = 3e-4
    weight_decay = 0.1
    betas = (0.9, 0.95)
    warmup_steps = 100
    checkpoint_every = 500  # Save checkpoint every N steps
    eval_every = 100        # Evaluate every N steps

    # Load tokenizer and data
    tokenizer, combined_text, vocab_size, pad_token_id = load_tokenizer_and_text()

    # Create data loaders
    train_loader, val_loader = create_data_loaders(
        tokenizer, combined_text, block_size, batch_size, pad_token_id
    )

    # Create model
    print("\nCreating model...")
    config = GPTConfig(
        vocab_size=vocab_size,
        block_size=block_size,
        n_layer=12,
        n_head=12,
        n_embd=768,
        embd_pdrop=0.1,
        resid_pdrop=0.1,
        attn_pdrop=0.1,
    )
    model = GPT(config)
    model = model.to(device)
    print(f"Model parameters: {model.get_num_params():,}")

    # Optimizer and scheduler
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=learning_rate,
        betas=betas,
        weight_decay=weight_decay
    )

    # Learning rate scheduler with warmup
    def lr_lambda(current_step):
        if current_step < warmup_steps:
            return float(current_step) / float(max(1, warmup_steps))
        return max(
            0.0,
            float(len(train_loader) * max_epochs - current_step)
            / float(max(1, len(train_loader) * max_epochs - warmup_steps)),
        )
    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)

    # Mixed precision scaler
    scaler = torch.cuda.amp.GradScaler()

    # Track losses for plotting
    train_losses = []
    val_losses = []
    steps = []

    # Training loop
    global_step = 0
    best_val_loss = float('inf')
    model.train()

    print(f"\nStarting training for {max_epochs} epochs...")
    print(f"Steps per epoch: {len(train_loader)}")
    print(f"Total steps: {len(train_loader) * max_epochs}")

    # Create checkpoint directory
    checkpoint_dir = Path("checkpoints")
    checkpoint_dir.mkdir(exist_ok=True)

    for epoch in range(max_epochs):
        epoch_start_time = time.time()
        epoch_loss = 0.0
        num_batches = 0

        # Progress bar for this epoch
        if HAS_TQDM:
            train_iter = tqdm(train_loader, desc=f"Epoch {epoch+1}/{max_epochs}")
        else:
            train_iter = train_loader
            print(f"\nEpoch {epoch+1}/{max_epochs}")

        for batch_idx, batch in enumerate(train_iter):
            # Move batch to device
            batch = batch.to(device)

            # Forward pass with mixed precision
            with torch.cuda.amp.autocast():
                logits, loss = model(batch, targets=batch)
                loss = loss / gradient_accumulation_steps

            # Backward pass
            scaler.scale(loss).backward()

            # Update weights every gradient_accumulation_steps
            if (batch_idx + 1) % gradient_accumulation_steps == 0:
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad()
                scheduler.step()

            # Accumulate loss
            epoch_loss += loss.item() * gradient_accumulation_steps
            num_batches += 1
            global_step += 1

            # Logging and checkpointing
            if global_step % checkpoint_every == 0:
                checkpoint_path = checkpoint_dir / f"model_step{global_step}.pt"
                torch.save({
                    'model_state_dict': model.state_dict(),
                    'optimizer_state_dict': optimizer.state_dict(),
                    'scaler_state_dict': scaler.state_dict(),
                    'scheduler_state_dict': scheduler.state_dict(),
                    'global_step': global_step,
                    'epoch': epoch,
                    'loss': loss.item(),
                }, checkpoint_path)
                print(f"Saved checkpoint to {checkpoint_path}")

            # Evaluation
            if global_step % eval_every == 0:
                model.eval()
                val_loss = 0.0
                val_batches = 0
                with torch.no_grad():
                    for val_batch in val_loader:
                        val_batch = val_batch.to(device)
                        with torch.cuda.amp.autocast():
                            _, v_loss = model(val_batch, targets=val_batch)
                        val_loss += v_loss.item()
                        val_batches += 1
                val_loss /= val_batches
                model.train()

                # Record losses
                train_losses.append(epoch_loss / num_batches if num_batches > 0 else 0)
                val_losses.append(val_loss)
                steps.append(global_step)

                print(f"\nStep {global_step}: Train Loss = {epoch_loss/num_batches:.4f}, Val Loss = {val_loss:.4f}")

                # Save best model
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    best_path = checkpoint_dir / "best_model.pt"
                    torch.save({
                        'model_state_dict': model.state_dict(),
                        'optimizer_state_dict': optimizer.state_dict(),
                        'scaler_state_dict': scaler.state_dict(),
                        'scheduler_state_dict': scheduler.state_dict(),
                        'global_step': global_step,
                        'epoch': epoch,
                        'val_loss': best_val_loss,
                    }, best_path)
                    print(f"New best model saved to {best_path} with val loss {best_val_loss:.4f}")

            # Update progress bar
            if HAS_TQDM:
                train_iter.set_postfix({
                    'loss': f"{loss.item()*gradient_accumulation_steps:.4f}",
                    'lr': f"{scheduler.get_last_lr()[0]:.2e}"
                })
            else:
                if batch_idx % 100 == 0:
                    print(f"  Batch {batch_idx}/{len(train_loader)} - Loss: {loss.item()*gradient_accumulation_steps:.4f}")

        # End of epoch
        epoch_time = time.time() - epoch_start_time
        avg_epoch_loss = epoch_loss / num_batches if num_batches > 0 else 0
        print(f"Epoch {epoch+1} completed in {epoch_time:.2f}s - Average Loss: {avg_epoch_loss:.4f}")

        # Optional: break early if loss stabilizes (simple check)
        if len(train_losses) > 5 and abs(train_losses[-1] - train_losses[-5]) < 0.01:
            print("Loss appears to have stabilized. Stopping early.")
            break

    # Final evaluation
    print("\nRunning final evaluation...")
    model.eval()
    val_loss = 0.0
    val_batches = 0
    with torch.no_grad():
        for val_batch in val_loader:
            val_batch = val_batch.to(device)
            with torch.cuda.amp.autocast():
                _, v_loss = model(val_batch, targets=val_batch)
            val_loss += v_loss.item()
            val_batches += 1
    val_loss /= val_batches
    print(f"Final Validation Loss: {val_loss:.4f}")

    # Save final model
    final_path = checkpoint_dir / "final_model.pt"
    torch.save({
        'model_state_dict': model.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
        'scaler_state_dict': scaler.state_dict(),
        'scheduler_state_dict': scheduler.state_dict(),
        'global_step': global_step,
        'epoch': epoch,
        'val_loss': val_loss,
    }, final_path)
    print(f"Final model saved to {final_path}")

    # Plot loss curve if matplotlib is available
    if HAS_MATPLOTLIB and steps:
        plt.figure(figsize=(10, 6))
        plt.plot(steps, train_losses, label='Training Loss')
        plt.plot(steps, val_losses, label='Validation Loss')
        plt.xlabel('Steps')
        plt.ylabel('Loss')
        plt.title('Training and Validation Loss')
        plt.legend()
        plt.grid(True)
        plt.savefig('loss_curve.png', dpi=150, bbox_inches='tight')
        print("Loss curve saved to 'loss_curve.png'")
        plt.show()

    print("\nTraining completed!")

if __name__ == "__main__":
    train()