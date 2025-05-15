import { createSignal, onCleanup, onMount, Show } from "solid-js";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";

import './message.css';

dayjs.extend(relativeTime);

export default function TranscriptLine(props) {
  const { line } = props;
  const [relative, setRelative] = createSignal(dayjs(line.start_timestamp).fromNow());

  let interval;
  onMount(() => {
    interval = setInterval(() => {
      setRelative(dayjs(line.start_timestamp).fromNow());
    }, 10000);
  });

  onCleanup(() => clearInterval(interval));

  return (
    <div class="transcript-line">
      <div class="line-header">
        <span class="timestamp" title={dayjs(line.start_timestamp).format('YYYY-MM-DD HH:mm:ss')}>
          {relative()}
        </span>
        <span class="player-id">{line.speaker_id}</span>
      </div>

      {/* Transcript Text Box */}
      <div class="line-content original">
        <Show when={line.text_error}>
          <div class="error">
            <span class="label">Transcription Error:</span> {line.text_error}
          </div>
        </Show>
        {line.text}
      </div>

      {/* Translation Box */}
      <Show when={line.translation || line.translation_error}>
        <div class="line-content translation">
          <Show when={line.translation_error}>
            <div class="error">
              <span class="label">Translation Error:</span> {line.translation_error}
            </div>
          </Show>
          <span class="label">Translated:</span> {line.translation}
        </div>
      </Show>

    </div>
  );
}
