import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "offline_llm.db")

OLLAMA_MODELS = [
    # Meta Llama Family
    {"name": "llama3.3:70b", "version": "3.3", "format": "Ollama / GGUF", "quantization": "q4_K_M", "context": 128000, "max_out": 4096, "status": "active"},
    {"name": "llama3.2:3b", "version": "3.2", "format": "Ollama / GGUF", "quantization": "q4_K_M", "context": 128000, "max_out": 4096, "status": "active"},
    {"name": "llama3.2:1b", "version": "3.2", "format": "Ollama / GGUF", "quantization": "q4_K_M", "context": 128000, "max_out": 2048, "status": "active"},
    {"name": "llama3.1:8b", "version": "3.1", "format": "Ollama / GGUF", "quantization": "q4_0", "context": 128000, "max_out": 4096, "status": "active"},
    {"name": "llama3:8b", "version": "3.0", "format": "Ollama / GGUF", "quantization": "q4_0", "context": 8192, "max_out": 2048, "status": "active"},
    {"name": "llama-2-7b-chat", "version": "2.0", "format": "GGUF", "quantization": "q4_0", "context": 4096, "max_out": 1024, "status": "active"},
    
    # DeepSeek Reasoning & Coding
    {"name": "deepseek-r1:7b", "version": "1.0", "format": "Ollama / GGUF", "quantization": "q4_K_M", "context": 64000, "max_out": 4096, "status": "active"},
    {"name": "deepseek-r1:8b", "version": "1.0", "format": "Ollama / GGUF", "quantization": "q4_K_M", "context": 64000, "max_out": 4096, "status": "active"},
    {"name": "deepseek-r1:14b", "version": "1.0", "format": "Ollama / GGUF", "quantization": "q4_K_M", "context": 64000, "max_out": 4096, "status": "active"},
    {"name": "deepseek-coder:6.7b", "version": "1.5", "format": "Ollama / GGUF", "quantization": "q4_0", "context": 16384, "max_out": 4096, "status": "active"},
    
    # Mistral & Mixtral
    {"name": "mistral-7b-instruct", "version": "0.3", "format": "Ollama / GGUF", "quantization": "q4_0", "context": 32768, "max_out": 2048, "status": "active"},
    {"name": "mixtral:8x7b", "version": "0.1", "format": "Ollama / GGUF", "quantization": "q4_0", "context": 32768, "max_out": 4096, "status": "active"},
    
    # Qwen Family
    {"name": "qwen2.5:7b", "version": "2.5", "format": "Ollama / GGUF", "quantization": "q4_K_M", "context": 32768, "max_out": 4096, "status": "active"},
    {"name": "qwen2.5-coder:7b", "version": "2.5", "format": "Ollama / GGUF", "quantization": "q4_K_M", "context": 32768, "max_out": 4096, "status": "active"},
    
    # Microsoft Phi Family
    {"name": "phi3.5:3.8b", "version": "3.5", "format": "Ollama / GGUF", "quantization": "q4_0", "context": 128000, "max_out": 4096, "status": "active"},
    {"name": "phi3:mini", "version": "3.0", "format": "Ollama / GGUF", "quantization": "q4_0", "context": 4096, "max_out": 2048, "status": "active"},
    
    # Google Gemma Family
    {"name": "gemma2:9b", "version": "2.0", "format": "Ollama / GGUF", "quantization": "q4_K_M", "context": 8192, "max_out": 2048, "status": "active"},
    {"name": "gemma2:2b", "version": "2.0", "format": "Ollama / GGUF", "quantization": "q4_K_M", "context": 8192, "max_out": 2048, "status": "active"},
    
    # Code & Compact
    {"name": "codellama:7b", "version": "1.0", "format": "Ollama / GGUF", "quantization": "q4_0", "context": 16384, "max_out": 2048, "status": "active"},
    {"name": "tinyllama:1.1b", "version": "1.0", "format": "Ollama / GGUF", "quantization": "q4_0", "context": 2048, "max_out": 1024, "status": "active"}
]

def seed():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Clear old duplicated model entries to keep registry clean
    cursor.execute("DELETE FROM model_profiles")
    
    for m in OLLAMA_MODELS:
        cursor.execute("""
            INSERT INTO model_profiles 
            (model_name, version, format, quantization, context_length, max_output, hardware_profile, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (m["name"], m["version"], m["format"], m["quantization"], m["context"], m["max_out"], "CPU/GPU (Air-Gapped)", m["status"]))
        
    conn.commit()
    conn.close()
    print(f"Successfully seeded {len(OLLAMA_MODELS)} Ollama models into {DB_PATH}")

if __name__ == "__main__":
    seed()
