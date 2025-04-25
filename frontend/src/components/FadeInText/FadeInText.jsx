import { createSignal, onMount } from "solid-js";

/**
 * Props:
 * - text (string): The string to animate in
 * - onDone (function): Callback when animation is finished
 * - mode: "char" or "word"
 */
export default function FadeInText(props) {
  const { text, onDone, mode = "char" } = props;
  const parts = mode === "word" ? text.split(" ") : text.split("");

  const [done, setDone] = createSignal(false);

  const animationSpeed = 10

  onMount(() => {
    const totalDuration = parts.length * animationSpeed + 500; // 60ms stagger + 500ms base
    setTimeout(() => {
      setDone(true);
      onDone?.();
    }, totalDuration);
  });

  return (
    <span class="fade-char" style={{ "animation-delay": `0ms` }}>
      {text === " " ? "\u00A0" : text}
    </span>
  );
  
}
