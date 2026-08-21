// Workflow script to set up Python environment for LLM training
export const meta = {
  name: 'setup-llm-environment',
  description: 'Create project structure, set up venv, install PyTorch with CUDA, transformers, etc.',
  phases: [
    { title: 'Setup', detail: 'Create directories, venv, install packages, verify CUDA' },
  ],
};

// Phase 1: Setup
phase('Setup');

const setupPrompt = `
  // Create project directories
  mkdir -p data models scripts

  // Create virtual environment
  python -m venv llm-env

  // Activate environment (this won't persist in agent, but we can source it for subsequent commands)
  source llm-env/Scripts/activate

  // Upgrade pip
  pip install --upgrade pip

  // Install PyTorch with CUDA support (CUDA 12.1)
  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

  // Install other required libraries
  pip install transformers datasets tokenizers numpy matplotlib tqdm

  // Verify installation and CUDA detection
  python -c "
import torch
print('PyTorch version:', torch.__version__)
print('CUDA available:', torch.cuda.is_available())
if torch.cuda.is_available():
    print('CUDA version:', torch.version.cuda)
    print('GPU count:', torch.cuda.device_count())
    for i in range(torch.cuda.device_count()):
        print(f'  GPU {i}: {torch.cuda.get_device_name(i)}')
else:
    print('CUDA not available, checking for ROCm or CPU')
"
`;

const result = await agent(setupPrompt, {
  label: 'Setup LLM environment',
  phase: 'Setup',
  // We want the output
});

return result;