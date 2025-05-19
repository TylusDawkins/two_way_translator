'''WebSocket server for real-time updates using FastAPI and Redis.'''
import asyncio
import hashlib
from typing import Dict, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import redis

app = FastAPI()

# Allow frontend (adjust origin as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis setup
redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

# Track connected WebSocket clients per session
session_clients: Dict[str, List[WebSocket]] = {}

@app.get("/ping")
def ping():
    '''Returns a simple "pong" response.'''
    return {"status": "pong"}

@app.get("/admin/clear-translations")
async def clear_transcripts():
    '''Clears all translation data from Redis and notifies connected clients.'''
    deleted_keys = []

    for key in redis_client.scan_iter("translator:*"):
        redis_client.delete(key)
        deleted_keys.append(key)

    # Notify all connected clients across all sessions
    for clients in session_clients.values():
        for client in clients.copy():
            try:
                await client.send_json({"type": "clear"})
            except Exception:
                clients.remove(client)

    return JSONResponse({
        "status": "cleared",
        "deleted": deleted_keys,
        "count": len(deleted_keys)
    })

@app.websocket("/ws/transcript/{session_id}")
async def transcript_ws(websocket: WebSocket, session_id: str):
    '''Handles WebSocket connections for real-time transcription updates.'''
    await websocket.accept()
    
    # Initialize session clients list if it doesn't exist
    if session_id not in session_clients:
        session_clients[session_id] = []
    
    session_clients[session_id].append(websocket)
    print(f"🔌 Client connected to session {session_id}. Total clients: {len(session_clients[session_id])}")

    try:
        content_hashes = {}  # Track last seen hash per key
        while True:
            await asyncio.sleep(0.5)
            # Only look for keys matching this session
            keys = redis_client.keys(f"translator:transcription:{session_id}:*")
            updated = []
            
            for key in keys:
                value = redis_client.get(key)
                if not value:
                    continue

                hash_ = hashlib.md5(value.encode()).hexdigest()
                if content_hashes.get(key) != hash_:
                    content_hashes[key] = hash_
                    updated.append(value)

            if updated:
                alive_clients = []
                for client in session_clients[session_id]:
                    try:
                        for message in updated:
                            await client.send_text(message)
                        alive_clients.append(client)
                    except Exception as e:
                        print(f"❌ Dropped a client from session {session_id}: {e}")
                session_clients[session_id] = alive_clients  # Replace with only live ones

    except WebSocketDisconnect:
        if websocket in session_clients[session_id]:
            session_clients[session_id].remove(websocket)
        print(f"❌ Client disconnected from session {session_id}. Remaining: {len(session_clients[session_id])}")
    except Exception as e:
        print(f"❌ Error in WebSocket loop for session {session_id}: {e}")
        if websocket in session_clients[session_id]:
            session_clients[session_id].remove(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("websocket_server:app", host="0.0.0.0", port=8006, reload=True)
