[ Recorder.jsx ] ---> [ FastAPI /upload-audio ] 
                          |
                          v
               [ Redis Queue: translator:queue ]
                          |
       ┌──────────────────┴──────────────────┐
       |                                     |
[ transcriber_worker.py ]             [ merger.py ]
     (transcribe & translate)           (merge lines)
              |                             |
              v                             v
  [ Redis: translator:unmerged ] → [ Redis: translator:transcription:* ]
                                                 |
                                                 v
                                     [ websocket.py → Feed.jsx ]