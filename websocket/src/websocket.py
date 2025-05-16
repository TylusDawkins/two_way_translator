'''WebSocket server for real-time updates using FastAPI and Redis.'''
import asyncio
import hashlib
from typing import List
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

# Track connected WebSocket clients
clients: List[WebSocket] = []

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

    # Notify all connected clients
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


@app.websocket("/ws/transcript")
async def transcript_ws(websocket: WebSocket):
    '''Handles WebSocket connections for real-time transcription updates.'''
    await websocket.accept()
    clients.append(websocket)
    print(f"🔌 Client connected. Total: {len(clients)}")

    try:
        content_hashes = {}  # Track last seen hash per key
        while True:
            await asyncio.sleep(0.5)
            keys = redis_client.keys("translator:transcription:*")
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
                for client in clients:
                    try:
                        for message in updated:
                            await client.send_text(message)
                        alive_clients.append(client)
                    except Exception as e:
                        print(f"❌ Dropped a client: {e}")
                clients[:] = alive_clients  # Replace with only live ones

    except WebSocketDisconnect:
        if websocket in clients:
            clients.remove(websocket)
        print(f"❌ Client disconnected. Remaining: {len(clients)}")
    except Exception as e:
        print(f"❌ Error in WebSocket loop: {e}")
        if websocket in clients:
            clients.remove(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("websocket_server:app", host="0.0.0.0", port=8006, reload=True)
