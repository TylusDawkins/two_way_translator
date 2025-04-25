import { createSignal, onCleanup, onMount } from "solid-js";
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

      <div class="line-content original">
        {line.text}
      </div>

      <Show when={line.translation && line.translation !== line.text}>
        <div class="line-content translation">
          <span class="label">Translated:</span> {line.translation}
        </div>
      </Show>
    </div>
  );
}
