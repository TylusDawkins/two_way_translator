#cleaner.py
import os
import sys
import signal
from huggingface_hub import hf_hub_download
# from llama_cpp import Llama
import torch
from transformers import MT5ForConditionalGeneration, MT5Tokenizer


# ------------------- THIS IS NO LONGER USED ... RETAINED FOR FUTURE REFERENCE-------------------


tokenizer = MT5Tokenizer.from_pretrained("google/mt5-small")
model = MT5ForConditionalGeneration.from_pretrained("google/mt5-small") 

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

def clean_text(text: str, mode: str = "transcription") -> str:
    print(f"Start Clean Text: text: {text}\nMode:{mode}")
    global cleaned
    if mode == "transcription":
        if not text.strip():
            return ""

        prefix = "Please fix grammar mistakes while keeping the meaning the same: "
        input_text = prefix + text

        inputs = tokenizer(input_text, return_tensors="pt", padding=True, truncation=True, max_length=512)
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model.generate(**inputs, max_new_tokens=128)
            print(f"Outputs: {outputs}")

        cleaned = tokenizer.decode(outputs[0], skip_special_tokens=True)
    elif mode == "translation":
        if not text.strip():
            return ""

        prefix = "Please fix grammar mistakes in the same language while keeping the meaning the same: "
        input_text = prefix + text

        inputs = tokenizer(input_text, return_tensors="pt", padding=True, truncation=True, max_length=512)
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model.generate(**inputs, max_new_tokens=128)
            print(f"Outputs: {outputs}")

        cleaned = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
    print(f"Cleaned Text:{cleaned}")
    cleaned = cleaned.strip()
    return cleaned

# ─── Graceful Shutdown Handler ───────────────────────────────────────────────
def shutdown_handler():
    print("\n🛑 Caught shutdown signal. Cleaning up...")
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

