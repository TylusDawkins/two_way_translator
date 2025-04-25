import { createSignal, onCleanup, onMount, Show } from "solid-js";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";

import './feed.css'

import Message from '@components/message/Message';

export default function Feed() {
    dayjs.extend(relativeTime);


    const [lines, setLines] = createSignal([]);

    let socket;

    onMount(() => {
        socket = new WebSocket("ws://localhost:8006/ws/transcript");

        socket.onmessage = (event) => {
            const incoming = JSON.parse(event.data);
            setLines(prev => {
                // Try to replace a previous line from the same speaker with the same base timestamp
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
        };


        socket.onopen = () => {
            console.log("📡 WebSocket connected.");
        };

        socket.onclose = (event) => {
            console.warn("🛑 WebSocket closed.", {
                code: event.code,
                reason: event.reason,
                wasClean: event.wasClean
            });
        };

        socket.onerror = (err) => {
            console.error("⚠️ WebSocket error (no details, check onclose or server logs):", err);
        };

        console.log(lines)
    });

    onCleanup(() => {
        socket?.close();
    });
    return (
        <div class="main-container">
            <div class="main-content">
                {/* future controls or gameplay content */}
            </div>
            <div class="transcript-log">
                <Show when={lines().length === 0} fallback={
                    <For each={[...lines()].sort((a, b) => a.start_timestamp - b.start_timestamp)}>
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