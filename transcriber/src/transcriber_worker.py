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
print(f"CUDA Available: {torch.cuda.is_available()}")
print(f"Using CUDA Version: {torch.version.cuda}")
print(f"GPU Name: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A'}")
print(f"⚙️  Using device: {device}")

# ─── Redis Setup ─────────────────────────────────────────────────────────────
redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

# ─── Whisper Model Setup ─────────────────────────────────────────────────────
whisper_model = WhisperModel(
    model_size_or_path="large-v3",
    device=device,
    compute_type="float16" if device == "cuda" else "int8"
)

beam_size = 10

# ─── NLLB Translator Setup ───────────────────────────────────────────────────
tokenizer = AutoTokenizer.from_pretrained("facebook/nllb-200-distilled-600M")
translator = AutoModelForSeq2SeqLM.from_pretrained("facebook/nllb-200-distilled-600M")
if device == "cuda":
    translator = translator.to(device)

# ─── ISO-to-NLLB Mapping ─────────────────────────────────────────────────────
ISO2NLLB = {
    "en": "eng_Latn",
    "zh": "zho_Hans",
    "hi": "hin_Deva",
    "es": "spa_Latn",
    "fr": "fra_Latn",
    "ar": "arb_Arab",
    "bn": "ben_Beng",
    "ru": "rus_Cyrl",
    "pt": "por_Latn",
    "ur": "urd_Arab",
    "ja": "jpn_Jpan",
    "de": "deu_Latn",
}

print("🧠 Whisper transcriber ready.  🔄 Translator ready.")

def contains_arabic(text):
    return any('\u0600' <= c <= '\u06FF' for c in text)

# ─── Main Loop ───────────────────────────────────────────────────────────────
try:
    while True:
        item = redis_client.lpop("translator:queue")
        if not item:
            time.sleep(0.5)
            continue

        payload = json.loads(item) 
        print(payload)
        file_path = payload.get("file_path")
        speaker_id = payload.get("speaker_id")
        timestamp = payload.get("timestamp")
        prim_lang = payload.get("prim_lang")
        fall_lang = payload.get("fall_lang")

        print(f"\n🔄 Transcribing {file_path}")
        print(f"Timestamp: {timestamp}")
        print(f"Speaker ID: {speaker_id}")
        print(f"Primary: {prim_lang}, Fallback: {fall_lang}")
        start_time = time.perf_counter()

        text = None
        text_error = None
        translation = None
        translation_error = None
        src_lang = None
        lang = None
        lang_conf = None

        try:
            # Primary transcription attempt
            # Try to let it process naturally, and if confidence is low fall back to default
            print(f"🔠 Trying primary language: {prim_lang}")
            segments, info = whisper_model.transcribe(
                file_path,
                language=None,
                beam_size=beam_size,
                task="transcribe",
                vad_filter=True,
                word_timestamps=False,
                multilingual=False,
                temperature=0.7,
                best_of=5
            )
            text = " ".join(seg.text for seg in segments).strip()
            lang = info.language
            lang_conf = info.language_probability
            print(f"🧠 Detected: {lang} ({lang_conf:.2%})")
            print(f"📜 Transcript: {text}")

            # Determine fallback need
            # Retry in primary lang

            print(fall_lang)

            fallback_needed = (
                not text or
                lang != prim_lang or
                lang_conf < 0.9
            ) and fall_lang != prim_lang

            if fallback_needed:
                print(f"⚠️ Fallback triggered. Retrying with {fall_lang}")
                segments, info = whisper_model.transcribe(
                    file_path,
                    language=fall_lang,
                    beam_size=beam_size,
                    task="transcribe",
                    vad_filter=True,
                    word_timestamps=False,
                    multilingual=False
                )
                text = " ".join(seg.text for seg in segments).strip()
                lang = info.language
                lang_conf = info.language_probability
                print(f"📜 Fallback transcript: {text}")
                print(f"🧠 Fallback language: {lang} ({lang_conf:.2%})")
                if not text:
                    text_error = "ERROR: Fallback transcription returned empty string"

            src_lang = ISO2NLLB.get(lang)

        except Exception as e:
            text_error = f"Transcription error: {e}"
            print(f"❌ {text_error}")
            text, src_lang = "", None

        finally:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)

        # — Translation —
        if text and src_lang:
            tgt_lang = "eng_Latn" if src_lang != "eng_Latn" else "arb_Arab"
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
            translation = tokenizer.batch_decode(outputs, skip_special_tokens=True)[0].strip()
            if not translation:
                translation_error = "ERROR: Translation returned empty string"
                print("❌ Translation failed.")
            else:
                print(f"✅ Translated text: {translation}")

        elapsed = round(time.perf_counter() - start_time, 2)
        print(f"✅ Done in {elapsed}s: {speaker_id}")

        result = {
            "speaker_id": speaker_id,
            "start_timestamp": timestamp,
            "text": text,
            "text_error": text_error,
            "translation": translation or "[Translation failed]",
            "translation_error": translation_error,
            "language": src_lang,
            "raw_language": lang,
            "language_confidence": lang_conf,
        }

        redis_client.rpush("translator:unmerged", json.dumps(result))

except KeyboardInterrupt:
    print("\n🛑 Received KeyboardInterrupt — shutting down gracefully.")
finally:
    if device == "cuda":
        print("🧹 Releasing GPU memory...")
        torch.cuda.empty_cache()
    print("👋 Shutdown complete.")
