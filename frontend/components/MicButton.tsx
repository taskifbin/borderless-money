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
}: {
  onTranscript: (text: string) => void;
  disabled?: boolean;
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
    <div className="relative inline-flex items-center">
      {listening && (
        <span className="absolute -inset-1 rounded-2xl bg-amber-500/30 animate-pulse-ring pointer-events-none" />
      )}
      <button
        type="button"
        onClick={start}
        disabled={disabled || listening || unsupported}
        aria-label={listening ? "Listening..." : "Fill amount by voice"}
        title={unsupported ? "Voice input not supported in this browser" : "Click to speak amount or command"}
        className={`relative flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border transition-all duration-200 ${
          listening
            ? "border-amber-400 bg-amber-500/20 text-amber-300 shadow-[0_0_15px_rgba(245,158,11,0.5)]"
            : "border-white/10 bg-white/5 text-slate-300 hover:border-amber-400/50 hover:bg-white/10 hover:text-white"
        } disabled:opacity-40 disabled:cursor-not-allowed`}
      >
        {listening ? (
          <span className="flex items-center gap-0.5">
            <span className="h-4 w-1 bg-amber-400 rounded-full animate-bounce [animation-delay:-0.3s]" />
            <span className="h-5 w-1 bg-amber-400 rounded-full animate-bounce [animation-delay:-0.15s]" />
            <span className="h-3 w-1 bg-amber-400 rounded-full animate-bounce" />
          </span>
        ) : (
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
            <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
            <line x1="12" y1="19" x2="12" y2="22" />
          </svg>
        )}
      </button>
    </div>
  );
}
