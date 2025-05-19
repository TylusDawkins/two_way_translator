"""merger.py"""
import asyncio
import time
import json
import redis

# Redis connection
redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

MERGE_WINDOW_MS = 15000  # 15 seconds of silence to finalize a thread

# Store current merging state per session
session_states = {}

def get_session_state(session_id):
    """Get or create merger state for a session."""
    if session_id not in session_states:
        session_states[session_id] = {
            "current": None,
            "last_merge_time": 0,
            "base_timestamp": None
        }
    return session_states[session_id]

def get_unmerged_blerbs(session_id):
    """""Accesses blerbs from Redis for merging."""
    blerbs = []
    while True:
        item = redis_client.lpop(f"translator:unmerged:{session_id}")
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

def update_merged_line(entry, timestamp, speaker_id, session_id):
    '''Saves line to Redis using a stable key.'''
    key = f"translator:transcription:{session_id}:{speaker_id}:{timestamp}"
    # print(clean_text(entry["text"], "transcription"))
    redis_client.set(key, json.dumps(entry))
    session_states[session_id]["last_merge_time"] = time.time()

def finalize_current_merge(session_id):
    '''Finalize the current merge thread for a session.'''
    state = get_session_state(session_id)
    current = state["current"]
    if not current:
        return

    print(f"🔚 FINALIZING MERGE THREAD for session {session_id}")
    update_merged_line(current, state["base_timestamp"], current["speaker_id"], session_id)

    # Reset merger state for this session
    state["current"] = None
    state["base_timestamp"] = None
    state["last_merge_time"] = time.time()

def merge_blerbs(blerbs, session_id):
    '''Merge new message into the current thread for a session.'''
    state = get_session_state(session_id)
    
    for blerb in sorted(blerbs, key=lambda x: x["start_timestamp"]):
        current = state["current"]
        now = time.time()

        if not current:
            state["current"] = blerb
            state["base_timestamp"] = blerb["start_timestamp"]
            update_merged_line(blerb, state["base_timestamp"], blerb["speaker_id"], session_id)
            continue

        time_since_last = (now - state["last_merge_time"]) * 1000
        same_speaker = blerb["speaker_id"] == current["speaker_id"]
        same_language = blerb["language"] == current["language"]
        close_in_time = time_since_last <= MERGE_WINDOW_MS

        if same_speaker and same_language and close_in_time:
            print(f"🔄 MERGING {blerb['start_timestamp']} → {state['base_timestamp']} for session {session_id}")
            current["text"] += " " + blerb["text"]
            current["translation"] += " " + blerb["translation"]
            update_merged_line(current, state["base_timestamp"], current["speaker_id"], session_id)
        else:
            finalize_current_merge(session_id)
            state["current"] = blerb
            state["base_timestamp"] = blerb["start_timestamp"]
            update_merged_line(blerb, state["base_timestamp"], blerb["speaker_id"], session_id)

async def run_merger_loop():
    """Main loop for the merger service."""
    print("🌀 Merger service running on key scan mode")

    while True:
        start = time.perf_counter()
        
        # Get all active session queues
        session_queues = redis_client.keys("translator:unmerged:*")
        
        for queue in session_queues:
            session_id = queue.split(":")[-1]  # Extract session ID from queue name
            blerbs = get_unmerged_blerbs(session_id)
            state = get_session_state(session_id)
            time_since_last_merge = (time.time() - state["last_merge_time"]) * 1000
            duration = round((time.perf_counter() - start) * 1000)

            if blerbs:
                merge_blerbs(blerbs, session_id)
                print(f"⏱️  Merging took {duration}ms for session {session_id}. Time since last merge: {time_since_last_merge:.2f}ms")
            elif time_since_last_merge > MERGE_WINDOW_MS:
                finalize_current_merge(session_id)

        await asyncio.sleep(0.5)

if __name__ == "__main__":
    asyncio.run(run_merger_loop())
