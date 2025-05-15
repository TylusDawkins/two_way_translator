#cleaner.py
import os
import sys
import signal
from huggingface_hub import hf_hub_download
# from llama_cpp import Llama
import torch
from transformers import MT5ForConditionalGeneration, MT5Tokenizer

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

# # ─── Configuration ───────────────────────────────────────────────────────────
# LOCAL_MODEL_PATH = "./models/phi-2.Q4_K_M.gguf"
# CACHE_DIR = "./hf_cache"

# # ─── Ensure Model is Available ────────────────────────────────────────────────
# def ensure_gguf_model(local_path=LOCAL_MODEL_PATH):
#     if not os.path.exists(local_path):
#         print("📥 Downloading Phi-2 quantized model from Hugging Face...")
#         hf_hub_download(
#             repo_id="TheBloke/phi-2-GGUF",
#             filename="phi-2.Q4_K_M.gguf",
#             cache_dir=CACHE_DIR,
#             local_dir="./models",
#             local_dir_use_symlinks=False
#         )
#     else:
#         print("✅ Phi-2 GGUF model already available locally.")

# ensure_gguf_model()

# ─── Load Llama Model ─────────────────────────────────────────────────────────
# print("📦 Loading Phi-2 quantized model into llama_cpp...")

# llm = Llama(
#     model_path=LOCAL_MODEL_PATH,
#     n_ctx=2048,
#     n_threads=8,  # Tune based on your CPU cores
#     n_batch=64
# )

# ─── Prewarm Model ────────────────────────────────────────────────────────────
# def prewarm_model():
#     _ = llm("Hello!", max_tokens=5)
#     print("🔥 Model prewarmed and ready!")

# prewarm_model()

# ─── Cleaning Function ────────────────────────────────────────────────────────
# def clean_text(text: str, mode: str = "transcription") -> str:
#     if not text:
#         return ""

#     if mode == "transcription":
#         prompt = f"""Fix obvious errors without changing the meaning. 
# Respond only with the corrected transcription text. 

# Original: {text}
# Corrected:"""
#     else:  # mode == "translation"
#         prompt = f"""Fix minor grammar or phrasing mistakes without changing meaning.
# Respond only with the corrected translation text.

# Original: {text}
# Corrected:"""

#     try:
#         print(f"🧹 Cleaning text: {text}")
        
#         response = llm(prompt, max_tokens=128, stop=["Corrected:", "\n\n"])
#         output = response['choices'][0]['text'].strip()

#         # Optionally postprocess to really slice out any duplicate prompt echoes
#         if "Corrected:" in output:
#             output = output.split("Corrected:")[-1].strip()

#         print(f"✅ Cleaned text: {output}")
#         return output

#     except Exception as e:
#         print(f"⚠️ Cleaning failed: {e}")
#         return text  # Fallback