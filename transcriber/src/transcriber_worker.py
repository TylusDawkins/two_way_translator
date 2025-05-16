'''Script to transcribe audio files with translations included'''

import signal
import sys
import time
import os
import json
import torch
import redis
from faster_whisper import WhisperModel
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

# ─── Graceful Shutdown Handler ───────────────────────────────────────────────
def shutdown_handler():
    '''Handle shutdown signals gracefully.'''
    print("\n🛑 Caught shutdown signal. Cleaning up...")
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

# ─── Device Setup ────────────────────────────────────────────────────────────
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"CUDA Available: {torch.cuda.is_available()}")
print(f"Using CUDA Version: {torch.version.cuda}")
print(f"GPU Name: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A'}")
print(f"⚙️  Using device: {DEVICE}")

# ─── Redis Setup ─────────────────────────────────────────────────────────────
redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

# ─── Whisper Model Setup ─────────────────────────────────────────────────────
whisper_model = WhisperModel(
    model_size_or_path="large-v3",
    device=DEVICE,
    compute_type="float16" if DEVICE == "cuda" else "int8"
)

BEAM_SIZE = 10

# ─── NLLB Translator Setup ───────────────────────────────────────────────────
tokenizer = AutoTokenizer.from_pretrained("facebook/nllb-200-distilled-600M")
translator = AutoModelForSeq2SeqLM.from_pretrained("facebook/nllb-200-distilled-600M")
if DEVICE == "cuda":
    translator = translator.to(DEVICE)

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
    '''Check if text contains Arabic characters.'''
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

        TEXT = None
        TEXT_ERROR = None
        TRANSLATION = None
        TRANSLATION_ERROR = None
        SRC_LANG = None
        LANG = None
        LANG_CONF = None

        try:
            # Primary transcription attempt
            # Try to let it process naturally, and if confidence is low fall back to default
            print(f"🔠 Trying primary language: {prim_lang}")
            segments, info = whisper_model.transcribe(
                file_path,
                language=None,
                beam_size=BEAM_SIZE,
                task="transcribe",
                vad_filter=True,
                word_timestamps=False,
                multilingual=False,
                temperature=0.7,
                best_of=5
            )
            TEXT = " ".join(seg.text for seg in segments).strip()
            LANG = info.language
            LANG_CONF = info.language_probability
            print(f"🧠 Detected: {LANG} ({LANG_CONF:.2%})")
            print(f"📜 Transcript: {TEXT}")

            # Determine fallback need
            # Retry in primary lang

            print(fall_lang)

            fallback_needed = (
                not TEXT or
                LANG != prim_lang or
                LANG_CONF < 0.9
            ) and fall_lang != prim_lang

            if fallback_needed:
                print(f"⚠️ Fallback triggered. Retrying with {fall_lang}")
                segments, info = whisper_model.transcribe(
                    file_path,
                    language=fall_lang,
                    beam_size=BEAM_SIZE,
                    task="transcribe",
                    vad_filter=True,
                    word_timestamps=False,
                    multilingual=False
                )
                TEXT = " ".join(seg.text for seg in segments).strip()
                LANG = info.language
                LANG_CONF = info.language_probability
                print(f"📜 Fallback transcript: {TEXT}")
                print(f"🧠 Fallback language: {LANG} ({LANG_CONF:.2%})")
                if not TEXT:
                    TEXT_ERROR = "ERROR: Fallback transcription returned empty string"

            SRC_LANG = ISO2NLLB.get(LANG)

        except Exception as e:
            TEXT_ERROR = f"Transcription error: {e}"
            print(f"❌ {TEXT_ERROR}")
            TEXT, SRC_LANG = "", None

        finally:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)

        # — Translation —
        if TEXT and SRC_LANG:
            TGT_LANG = "eng_Latn" if SRC_LANG != "eng_Latn" else "arb_Arab"
            print(f"🔄 Translating from {SRC_LANG} to {TGT_LANG}")

            tokenizer.src_lang = SRC_LANG
            tokenizer.tgt_lang = TGT_LANG

            inputs = tokenizer(TEXT, return_tensors="pt", padding=True)
            if DEVICE == "cuda":
                inputs = {k: v.to(DEVICE) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = translator.generate(
                    **inputs,
                    forced_bos_token_id=tokenizer.convert_tokens_to_ids(TGT_LANG),
                    max_length=512
                )
            TRANSLATION = tokenizer.batch_decode(outputs, skip_special_tokens=True)[0].strip()
            if not TRANSLATION:
                TRANSLATION_ERROR = "ERROR: Translation returned empty string"
                print("❌ Translation failed.")
            else:
                print(f"✅ Translated text: {TRANSLATION}")

        elapsed = round(time.perf_counter() - start_time, 2)
        print(f"✅ Done in {elapsed}s: {speaker_id}")

        result = {
            "speaker_id": speaker_id,
            "start_timestamp": timestamp,
            "text": TEXT,
            "text_error": TEXT_ERROR,
            "translation": TRANSLATION or "[Translation failed]",
            "translation_error": TRANSLATION_ERROR,
            "language": SRC_LANG,
            "raw_language": LANG,
            "language_confidence": LANG_CONF,
        }

        redis_client.rpush("translator:unmerged", json.dumps(result))

except KeyboardInterrupt:
    print("\n🛑 Received KeyboardInterrupt — shutting down gracefully.")
finally:
    if DEVICE == "cuda":
        print("🧹 Releasing GPU memory...")
        torch.cuda.empty_cache()
    print("👋 Shutdown complete.")
