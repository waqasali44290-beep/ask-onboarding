// Voice in and out with the browser's built-in Web Speech API (no server, no cost).
// Speech-to-text exists in Chrome, Edge and Safari (not Firefox), so callers hide
// the mic button when `supported` is false. Note: Chrome sends the audio to
// Google's speech service to transcribe it.
import { useCallback, useEffect, useRef, useState } from "react";

// Minimal types: TypeScript's DOM library doesn't include SpeechRecognition yet.
interface RecognitionResultEvent {
  resultIndex: number;
  results: ArrayLike<{ isFinal: boolean; 0: { transcript: string } }>;
}
interface Recognition {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  start(): void;
  stop(): void;
  onresult: ((event: RecognitionResultEvent) => void) | null;
  onend: (() => void) | null;
  onerror: ((event: { error: string }) => void) | null;
}
type RecognitionConstructor = new () => Recognition;

const SpeechRecognition: RecognitionConstructor | undefined =
  (window as unknown as { SpeechRecognition?: RecognitionConstructor }).SpeechRecognition ??
  (window as unknown as { webkitSpeechRecognition?: RecognitionConstructor }).webkitSpeechRecognition;

/** Speech-to-text. onText gets the words so far; onFinal gets the whole sentence once the user stops. */
export function useSpeechInput(onText: (text: string) => void, onFinal: (text: string) => void) {
  const [listening, setListening] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const recognition = useRef<Recognition | null>(null);
  // Keep the latest callbacks without restarting the recogniser on every render.
  const callbacks = useRef({ onText, onFinal });
  callbacks.current = { onText, onFinal };

  const stop = useCallback(() => recognition.current?.stop(), []);

  const start = useCallback(() => {
    if (!SpeechRecognition) return;
    const recogniser = new SpeechRecognition();
    recogniser.lang = navigator.language || "en-US";
    recogniser.interimResults = true; // show words while the user is still talking
    recogniser.continuous = false; // stop at the first pause
    let text = "";
    recogniser.onresult = (event) => {
      text = Array.from(event.results)
        .map((result) => result[0].transcript)
        .join("");
      callbacks.current.onText(text);
    };
    recogniser.onerror = (event) => {
      setError(event.error === "not-allowed" ? "Microphone access was blocked." : "Didn't catch that, please try again.");
    };
    recogniser.onend = () => {
      setListening(false);
      if (text.trim()) callbacks.current.onFinal(text.trim());
    };
    recognition.current = recogniser;
    setError(null);
    setListening(true);
    recogniser.start();
  }, []);

  useEffect(() => stop, [stop]); // stop listening when the page closes

  return { supported: Boolean(SpeechRecognition), listening, error, start, stop };
}

/** Text-to-speech for answers. Citation markers like [1] are not read out. */
export function speak(text: string, onEnd?: () => void) {
  if (!("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel(); // only one answer at a time
  const utterance = new SpeechSynthesisUtterance(text.replace(/\[\d+\]/g, ""));
  utterance.lang = navigator.language || "en-US";
  if (onEnd) utterance.onend = onEnd;
  window.speechSynthesis.speak(utterance);
}

export function stopSpeaking() {
  if ("speechSynthesis" in window) window.speechSynthesis.cancel();
}

export const canSpeak = "speechSynthesis" in window;
