"use client";

import { useState } from "react";

export default function ChainTrail({
  hash,
  network,
  labels,
}: {
  hash: string;
  network: string;
  labels: {
    title: string;
    prev: string;
    yours: string;
    next: string;
    copyHash?: string;
    copied?: string;
  };
}) {
  const [copied, setCopied] = useState(false);
  const shortHash = hash ? `${hash.slice(0, 8)}…${hash.slice(-6)}` : "—";

  const copyHash = () => {
    if (!hash) return;
    navigator.clipboard?.writeText(hash);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const blocks = [
    { label: labels.prev, value: "···", accent: false },
    { label: labels.yours, value: shortHash, accent: true },
    { label: labels.next, value: "···", accent: false },
  ];

  return (
    <section aria-label={labels.title} className="rounded-2xl border border-white/10 bg-[#0b1220]/70 p-5">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <div className="flex items-center gap-2">
          <span className="flex h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399]" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
            {labels.title}
          </h3>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-md border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 font-mono text-[10px] font-bold text-emerald-400">
            {network}
          </span>
          {hash && (
            <button
              type="button"
              onClick={copyHash}
              className="text-[10px] text-slate-400 hover:text-white transition px-2 py-0.5 rounded border border-white/10 bg-white/5"
            >
              {copied ? labels.copied ?? "Copied" : labels.copyHash ?? "Copy hash"}
            </button>
          )}
        </div>
      </div>

      <div className="flex items-stretch gap-2">
        {blocks.map((block, i) => (
          <div key={block.label} className="flex min-w-0 flex-1 items-center">
            {i > 0 && <span className="h-px w-3 shrink-0 bg-white/10" aria-hidden="true" />}
            <div
              className={`min-w-0 flex-1 rounded-xl border p-2.5 text-center transition-all ${
                block.accent
                  ? "border-amber-400/50 bg-amber-500/10 shadow-[0_0_15px_rgba(245,158,11,0.15)]"
                  : "border-white/5 bg-white/[0.02]"
              }`}
            >
              <p
                className={`truncate font-mono text-xs font-semibold ${
                  block.accent ? "text-amber-300" : "text-slate-400"
                }`}
              >
                {block.value}
              </p>
              <p className="mt-1 truncate text-[10px] text-slate-500 font-medium">
                {block.label}
              </p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
