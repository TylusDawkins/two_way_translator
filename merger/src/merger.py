#merger.py
import asyncio
import time
import json
import sys; print(sys.executable)
import redis
from cleaner import clean_text

# Redis connection
redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

MERGE_WINDOW_MS = 15000  # 15 seconds of silence to finalize a thread

# Store current merging state
merger_state = {
    "current": None,
    "last_merge_time": 0,
    "base_timestamp": None
}

def get_unmerged_blerbs():
    blerbs = []
    while True:
        item = redis_client.lpop("translator:unmerged")
        if not item:
            break
        try:
            blerb = json.loads(item)
            if "start_timestamp" in blerb and "speaker_id" in blerb and "text" in blerb and "translation" in blerb:
                blerbs.append(blerb)
            else:
                print("⚠️ Skipping invalid blerb:", blerb)
        except json.JSONDecodeError:
            print("⚠️ Could not decode blerb:", item)
    return blerbs

def update_merged_line(entry, timestamp, speaker_id):
    key = f"translator:transcription:{speaker_id}:{timestamp}"
    # print(clean_text(entry["text"], "transcription"))
    redis_client.set(key, json.dumps(entry))
    merger_state["last_merge_time"] = time.time()

def finalize_current_merge():
    current = merger_state["current"]
    if not current:
        return

    print("🔚 FINALIZING MERGE THREAD")

    # try:
    #     # Clean current text and translation
    #     current["text"] = clean_text(current["text"], "transcription")
    #     # current["translation"] = clean_text(current["translation"], "translation")
    # except Exception as e:
    #     print(f"⚠️ Cleaning failed: {e}")

    update_merged_line(current, merger_state["base_timestamp"], current["speaker_id"])

    # Reset merger state
    merger_state["current"] = None
    merger_state["base_timestamp"] = None
    merger_state["last_merge_time"] = time.time()

def merge_blerbs(blerbs):
    for blerb in sorted(blerbs, key=lambda x: x["start_timestamp"]):
        current = merger_state["current"]
        now = time.time()

        if not current:
            merger_state["current"] = blerb
            merger_state["base_timestamp"] = blerb["start_timestamp"]
            update_merged_line(blerb, merger_state["base_timestamp"], blerb["speaker_id"])
            continue

        time_since_last = (now - merger_state["last_merge_time"]) * 1000
        same_speaker = blerb["speaker_id"] == current["speaker_id"]
        same_language = blerb["language"] == current["language"]
        close_in_time = time_since_last <= MERGE_WINDOW_MS

        if same_speaker and same_language and close_in_time:
            print(f"🔄 MERGING {blerb['start_timestamp']} → {merger_state['base_timestamp']}")
            current["text"] += " " + blerb["text"]
            current["translation"] += " " + blerb["translation"]
            update_merged_line(current, merger_state["base_timestamp"], current["speaker_id"])
        else:
            finalize_current_merge()
            merger_state["current"] = blerb
            merger_state["base_timestamp"] = blerb["start_timestamp"]
            update_merged_line(blerb, merger_state["base_timestamp"], blerb["speaker_id"])

async def run_merger_loop():
    print("🌀 Merger service running on key scan mode")

    while True:
        start = time.perf_counter()
        blerbs = get_unmerged_blerbs()
        time_since_last_merge = (time.time() - merger_state["last_merge_time"]) * 1000

        if blerbs:
            merge_blerbs(blerbs)
        elif time_since_last_merge > MERGE_WINDOW_MS:
            finalize_current_merge()

        duration = round((time.perf_counter() - start) * 1000)
        await asyncio.sleep(0.5)

if __name__ == "__main__":
    asyncio.run(run_merger_loop())
