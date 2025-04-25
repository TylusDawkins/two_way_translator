import { createSignal, onCleanup, onMount } from "solid-js";
import { MediaRecorder, register } from "extendable-media-recorder";
import { connect } from "extendable-media-recorder-wav-encoder";

import './recorder.css';

export default function Recorder() {
  const [recording, setRecording] = createSignal(false);
  const speakerId = "speaker_1";
  const RECORDING_DURATION = 5000;
  const OVERLAP_TIME = 100; // ms

  let stream;
  let recorderA;
  let recorderB;
  let current = "A"; // "A" or "B"
  let recordingStartTime = Date.now();

  const MIN_BLOB_SIZE = 8000;

  const setupWavEncoder = async () => {
    try {
      await register(await connect());
      console.log("✅ WAV encoder connected.");
    } catch (err) {
      console.error("❌ Failed to connect WAV encoder:", err);
    }
  };

  const sendChunk = async (blob) => {
    if (blob.size < MIN_BLOB_SIZE) {
      console.warn("⛔ Skipping small or empty blob:", blob.size);
      return;
    }

    const formData = new FormData();
    formData.append("file", blob, `chunk-${Date.now()}.wav`);
    formData.append("speaker_id", speakerId);
    formData.append("recording_start_time", recordingStartTime);
    formData.append("timestamp", Date.now());

    try {
      const res = await fetch("http://localhost:8005/upload-audio/", {
        method: "POST",
        body: formData,
      });
      const json = await res.json();
      console.log("✅ Chunk sent:", json);
    } catch (err) {
      console.error("❌ Failed to send chunk:", err);
    }
  };

  const initRecorders = () => {
    recorderA = new MediaRecorder(stream, { mimeType: "audio/wav" });
    recorderB = new MediaRecorder(stream, { mimeType: "audio/wav" });

    recorderA.ondataavailable = (e) => {
      if (e.data.size > 0) sendChunk(e.data);
    };
    recorderB.ondataavailable = (e) => {
      if (e.data.size > 0) sendChunk(e.data);
    };
  };

  let interval;

  const startRecording = async () => {

    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    initRecorders();

    setRecording(true);

    // Start with Recorder A
    recorderA.start();
    current = "A";
    console.log("🎙️ Recorder A started.");

    interval = setInterval(() => {
      if (!recording()) {
        clearInterval(interval);
        return;
      }

      recordingStartTime = Date.now();


      if (current === "A") {
        recorderB.start();
        console.log("🔁 Recorder B started.");
        setTimeout(() => {
          recorderA.stop();
          console.log("⏹️ Recorder A stopped.");
          current = "B";
        }, OVERLAP_TIME);
      } else {
        recorderA.start();
        console.log("🔁 Recorder A started.");
        setTimeout(() => {
          recorderB.stop();
          console.log("⏹️ Recorder B stopped.");
          current = "A";
        }, OVERLAP_TIME);
      }
    }, RECORDING_DURATION);
  };

  const stopRecording = () => {
    setRecording(false);
    clearInterval(interval);

    try {
      if (recorderA?.state !== "inactive") recorderA.stop();
      if (recorderB?.state !== "inactive") recorderB.stop();
    } catch (e) {}

    stream?.getTracks().forEach((t) => t.stop());
    console.log("🛑 Recording stopped.");
  };

  const toggleRecording = () => {
    recording() ? stopRecording() : startRecording();
  };

  onCleanup(() => stopRecording());

  onMount(() => {
    setupWavEncoder()
  });

  return (
    <div>
      <button onClick={toggleRecording} class="record-button">
        {recording() ? "Mute Mic" : "Unmute Mic"}
      </button>
    </div>
  );
}
