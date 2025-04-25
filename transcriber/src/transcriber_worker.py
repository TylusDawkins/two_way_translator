from faster_whisper import WhisperModel
import redis, os, json, time
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import torch
import signal
import sys

# ─── Graceful Shutdown Handler ───────────────────────────────────────────────
def shutdown_handler(signum, frame):
    print("\n🛑 Caught shutdown signal. Cleaning up...")
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

# ─── Device Setup ────────────────────────────────────────────────────────────
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"⚙️  Using device: {device}")

# ─── Redis Setup ─────────────────────────────────────────────────────────────
redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

# ─── Whisper Model Setup ─────────────────────────────────────────────────────
whisper_model = WhisperModel(
    model_size_or_path="large-v3",
    device=device,
    compute_type="float16" if device == "cuda" else "int8"
)

# ─── NLLB Translator Setup ───────────────────────────────────────────────────
tokenizer = AutoTokenizer.from_pretrained("facebook/nllb-200-distilled-600M")
translator = AutoModelForSeq2SeqLM.from_pretrained("facebook/nllb-200-distilled-600M")
if device == "cuda":
    translator = translator.to(device)

# ─── ISO-to-NLLB Mapping ─────────────────────────────────────────────────────
ISO2NLLB = {
    "en": "eng_Latn",
    "ar": "arb_Arab",
    # extend with other ISO codes as needed
}

print("🧠 Whisper transcriber ready.  🔄 Translator ready.")

# ─── Main Loop ───────────────────────────────────────────────────────────────
try:
    while True:
        item = redis_client.lpop("translator:queue")
        if not item:
            time.sleep(0.5)
            continue

        payload    = json.loads(item)
        file_path  = payload.get("file_path")
        speaker_id = payload.get("speaker_id")
        timestamp  = payload.get("timestamp")

        print(f"\n🔄 Transcribing {file_path}")
        start_time = time.perf_counter()

        # — Transcription —
        try:
            segments, info = whisper_model.transcribe(
                file_path,
                language=None,  # required to get language_probs
                beam_size=5,
                task="transcribe",
                vad_filter=True,
                word_timestamps=False
            )

            text = " ".join(seg.text for seg in segments).strip()
            lang = info.language
            lang_conf = info.language_probability
            # lang_conf = info.language_probs.get(lang, 0.0) if info.language_probs else 0.0

            print(f"🧠 Detected language: {lang} ({lang_conf:.2%} confidence)")
            print(f"📜 Transcript: {text}")
            src_lang = ISO2NLLB.get(lang, None)



        except Exception as e:
            print(f"❌ Transcription error: {e}")
            text, src_lang = "", None
        finally:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)

        # — Translation —
        translation, tgt_lang = None, None
        if text and src_lang:
            if src_lang == "eng_Latn":
                tgt_lang = "arb_Arab"
            elif src_lang == "arb_Arab":
                tgt_lang = "eng_Latn"
            else:
                tgt_lang = "eng_Latn"

            print(f"🔄 Translating from {src_lang} to {tgt_lang}")
            tokenizer.src_lang = src_lang
            tokenizer.tgt_lang = tgt_lang

            inputs = tokenizer(text, return_tensors="pt", padding=True)
            if device == "cuda":
                inputs = {k: v.to(device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = translator.generate(
                    **inputs,
                    forced_bos_token_id=tokenizer.convert_tokens_to_ids(tgt_lang),
                    max_length=512
                )
            translation = tokenizer.batch_decode(outputs, skip_special_tokens=True)[0]
            print(f"🔤 Translation: {translation}")

        elapsed = round(time.perf_counter() - start_time, 2)
        print(f"✅ Done in {elapsed}s: {speaker_id}")

        # — Push unified result —
        result = {
            "speaker_id":      speaker_id,
            "start_timestamp": timestamp,
            "text":            text,
            "translation":     translation,
            "source_lang":     src_lang,
            "target_lang":     tgt_lang
        }
        redis_client.rpush("translator:unmerged", json.dumps(result))

except KeyboardInterrupt:
    print("\n🛑 Received KeyboardInterrupt — shutting down gracefully.")
finally:
    if device == "cuda":
        print("🧹 Releasing GPU memory...")
        torch.cuda.empty_cache()
    print("👋 Shutdown complete.")
