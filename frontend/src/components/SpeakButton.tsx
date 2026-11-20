// Reads an answer aloud; click again to stop.
import { useEffect, useState } from "react";
import { canSpeak, speak, stopSpeaking } from "../hooks/useSpeech";

export default function SpeakButton({ text, autoPlay = false }: { text: string; autoPlay?: boolean }) {
  const [speaking, setSpeaking] = useState(false);

  function play() {
    setSpeaking(true);
    speak(text, () => setSpeaking(false));
  }

  useEffect(() => {
    if (autoPlay) play(); // the question was asked by voice, so answer by voice
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only when the answer first appears
  }, []);

  if (!canSpeak) return null;
  return (
    <button
      type="button"
      className={`feedback-button speak-button${speaking ? " feedback-selected" : ""}`}
      aria-pressed={speaking}
      aria-label={speaking ? "Stop reading" : "Read aloud"}
      title={speaking ? "Stop reading" : "Read aloud"}
      onClick={() => {
        if (speaking) {
          stopSpeaking();
          setSpeaking(false);
        } else {
          play();
        }
      }}
    >
      {speaking ? "⏹" : "🔊"}
    </button>
  );
}
