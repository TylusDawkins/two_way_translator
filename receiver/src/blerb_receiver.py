'''blerb_receiver.py'''
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import redis
import uuid
import os
import json
import ffmpeg  # add this to your imports at the top


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

# ─── Shared Volume Setup ─────────────────────────────────────────────────────
SHARED_VOLUME_PATH = os.getenv("SHARED_VOLUME_PATH", "/shared_volume")
AUDIO_DIR = os.path.join(SHARED_VOLUME_PATH, "blerbs")
os.makedirs(AUDIO_DIR, exist_ok=True)

@app.post("/upload-audio/")
async def upload_audio(
    file: UploadFile = File(...),
    speaker_id: str = Form(...),
    session_id: str = Form(...),
    timestamp: int = Form(...),
    prim_lang: str = Form(...),
    fall_lang: str = Form(...)
):
    extension = os.path.splitext(file.filename)[-1].lower()
    unique_id = uuid.uuid4().hex

    raw_filename = f"{session_id}_{speaker_id}_{timestamp}_{unique_id}{extension}"
    raw_path = os.path.join(AUDIO_DIR, raw_filename)

    print(f"📥 Received file: {raw_filename}")
    with open(raw_path, "wb") as f:
        f.write(await file.read())

    # Convert to 16kHz WAV format
    processed_filename = f"{session_id}_{speaker_id}_{timestamp}_{unique_id}_processed.wav"
    processed_path = os.path.join(AUDIO_DIR, processed_filename)
    try:
        ffmpeg.input(raw_path).output(
            processed_path,
            ar=16000,      # Set sample rate to 16kHz
            ac=1,          # Set audio channels to mono
            format='wav'   # Output format
        ).overwrite_output().run(quiet=True)
        os.remove(raw_path)  # Clean up original
    except ffmpeg.Error as e:
        print(f"❌ FFmpeg error:\n{e.stderr.decode()}")
        return JSONResponse({"error": "Audio conversion failed"}, status_code=500)

    redis_client.rpush(f"translator:queue:{session_id}", json.dumps({
        "filename": processed_filename,
        "speaker_id": speaker_id,
        "session_id": session_id,
        "timestamp": timestamp,
        "prim_lang": prim_lang,
        "fall_lang": fall_lang
    }))
    return JSONResponse({"status": "queued", "filename": processed_filename})
