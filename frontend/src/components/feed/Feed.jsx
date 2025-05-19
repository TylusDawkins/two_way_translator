import { createSignal, onCleanup, onMount, Show, For } from "solid-js";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import languages from "@utils/languages.json"; // or relative path if no alias
import { useApp } from "@context/AppContext";

import './feed.css'

import Message from '@components/message/Message';

export default function Feed() {
    dayjs.extend(relativeTime);

    const [lines, setLines] = createSignal([]);
    const { sessionId } = useApp();
    const [primLang, setPrimLang] = createSignal("");
    const [fallLang, setFallLang] = createSignal("");
    let socket;
    let transcriptLogRef;

    onMount(() => {
        socket = new WebSocket(`ws://localhost:8006/ws/transcript/${sessionId()}`);

        socket.onmessage = (event) => {
            const incoming = JSON.parse(event.data);

            if (!transcriptLogRef) return;

            const isAtBottom =
                transcriptLogRef.scrollHeight - transcriptLogRef.scrollTop <=
                transcriptLogRef.clientHeight + 10; // small padding

            setLines(prev => {
                const index = prev.findIndex(line =>
                    line.speaker_id === incoming.speaker_id &&
                    line.start_timestamp === incoming.start_timestamp
                );

                if (index !== -1) {
                    const updated = [...prev];
                    updated[index] = incoming;
                    return updated.sort((a, b) => a.start_timestamp - b.start_timestamp);
                } else {
                    return [...prev, incoming].sort((a, b) => a.start_timestamp - b.start_timestamp);
                }
            });

            requestAnimationFrame(() => {
                if (isAtBottom && transcriptLogRef) {
                    transcriptLogRef.scrollTo({
                        top: transcriptLogRef.scrollHeight,
                        behavior: 'smooth'
                    });
                }
            });
        };

        socket.onopen = () => {
            console.log("📡 WebSocket connected to session:", sessionId());
        };

        socket.onclose = (event) => {
            console.warn("🛑 WebSocket closed for session:", sessionId(), {
                code: event.code,
                reason: event.reason,
                wasClean: event.wasClean
            });
        };

        socket.onerror = (err) => {
            console.error("⚠️ WebSocket error for session:", sessionId(), err);
        };
    });

    onCleanup(() => {
        socket?.close();
    });

    return (
        <div class="main-container">
            <div class="main-content">
                {/* future controls or gameplay content */}
            </div>
            <div class="transcript-log" ref={el => transcriptLogRef = el}>
                <Show when={lines().length === 0} fallback={
                    <For each={lines()}>
                        {(line) => (
                            <div class="transcript-line">
                                <Message line={line} />
                            </div>
                        )}
                    </For>
                }>
                    <div class="no-dialogue">No dialogue history here</div>
                </Show>
            </div>
        </div>
    );
}
