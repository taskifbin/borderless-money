"use client";

import { useState } from "react";

interface SpeechRecognitionLike {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start: () => void;
  stop: () => void;
  onresult: ((event: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
}

export default function MicButton({
  onTranscript,
  disabled,
  titleMic = "Fill amount by voice",
  titleListening = "Listening",
  titleUnsupported = "Voice input is not supported in this browser",
}: {
  onTranscript: (text: string) => void;
  disabled?: boolean;
  titleMic?: string;
  titleListening?: string;
  titleUnsupported?: string;
}) {
  const [listening, setListening] = useState(false);
  const [unsupported, setUnsupported] = useState(false);

  const start = () => {
    const w = window as unknown as {
      SpeechRecognition?: new () => SpeechRecognitionLike;
      webkitSpeechRecognition?: new () => SpeechRecognitionLike;
    };
    const Ctor = w.SpeechRecognition ?? w.webkitSpeechRecognition;
    if (!Ctor) {
      setUnsupported(true);
      return;
    }
    const rec = new Ctor();
    rec.lang = typeof navigator !== "undefined" && navigator.language ? navigator.language : "en-US";
    rec.continuous = false;
    rec.interimResults = false;
    rec.onresult = (event) => onTranscript(event.results[0][0].transcript);
    rec.onerror = () => setListening(false);
    rec.onend = () => setListening(false);
    rec.start();
    setListening(true);
  };

  return (
    <button
      type="button"
      onClick={start}
      disabled={disabled || listening || unsupported}
      aria-label={listening ? titleListening : titleMic}
      title={unsupported ? titleUnsupported : titleMic}
      className={
        "flex h-12 w-12 shrink-0 items-center justify-center rounded-lg border text-muted disabled:opacity-50 " +
        (listening ? "border-accent text-accent" : "border-line")
      }
    >
      <svg
        width="20"
        height="20"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <rect x="9" y="3" width="6" height="11" rx="3" />
        <path d="M5 11a7 7 0 0 0 14 0" />
        <line x1="12" y1="18" x2="12" y2="22" />
      </svg>
    </button>
  );
}
