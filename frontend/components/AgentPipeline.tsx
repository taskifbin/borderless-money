"use client";

import { useState } from "react";
import type { AgentStateResponse } from "@/lib/types";

export interface AgentPipelineProps {
  quote?: AgentStateResponse | null;
  busy?: boolean;
  activeStep?: number;
}

export default function AgentPipeline({ quote, busy }: AgentPipelineProps) {
  const [showLogs, setShowLogs] = useState(false);

  const steps = [
    {
      id: "intent",
      num: "01",
      title: "Intent & Corridor Parser",
      desc: quote?.parsed_intent
        ? `${quote.parsed_intent.amount} ${quote.parsed_intent.source_currency} → ${quote.parsed_intent.dest_currency} via ${quote.parsed_intent.payout_method || "optimal rail"}`
        : "Extracts amounts, corridor, recipient handle, and urgency from text or voice",
      status: busy ? "processing" : quote ? "completed" : "idle",
      badge: quote?.parsed_intent?.confidence
        ? `${Math.round(quote.parsed_intent.confidence * 100)}% confidence`
        : null,
    },
    {
      id: "routing",
      num: "02",
      title: "Multi-Rail Scorer & Ranking",
      desc: quote?.routes?.length
        ? `Ranked ${quote.routes.length} live payout rails by true net receive amount`
        : "Scans bank networks, mobile wallets, and liquidity pools for best FX & lowest spread",
      status: busy ? "processing" : quote?.routes ? "completed" : "idle",
      badge: quote?.routes?.length ? `${quote.routes.length} rails analyzed` : null,
    },
    {
      id: "incentive",
      num: "03",
      title: "Incentive Maximizer (Bangladesh Bank)",
      desc: "Automatically verifies 2.5% formal-channel government cash remittance subsidy eligibility",
      status: busy ? "processing" : quote ? "completed" : "idle",
      badge: "+2.5% govt cash subsidy",
    },
    {
      id: "compliance",
      num: "04",
      title: "Sanctions & Graph Screening",
      desc: quote?.compliance
        ? `OFAC status: ${quote.compliance.ofac_match_status || "CLEARED"} · Risk: ${quote.risk?.risk_band || "LOW"}`
        : "Predictive AML screening and graph sanctions verification before quote issuance",
      status: busy ? "processing" : quote?.compliance ? "completed" : "idle",
      badge: quote?.decision === "CLEAR" ? "Screening Passed" : quote?.decision ? String(quote.decision) : null,
    },
    {
      id: "quote_binding",
      num: "05",
      title: "Cryptographic Quote Lock",
      desc: quote?.quote_id
        ? `Immutable Quote ID #${quote.quote_id.slice(0, 8)}… signed for execution`
        : "Guarantees exact payout rate and prevents slippage or unauthorized fee injection",
      status: busy ? "processing" : quote?.quote_id ? "completed" : "idle",
      badge: quote?.quote_id ? "Bound & Locked" : null,
    },
  ];

  return (
    <div className="rounded-2xl border border-white/10 bg-[#0d1627]/80 p-5 backdrop-blur-xl">
      <div className="flex items-center justify-between pb-4 border-b border-white/10">
        <div className="flex items-center gap-2.5">
          <span className="relative flex h-3 w-3">
            <span className={`absolute inline-flex h-full w-full rounded-full opacity-75 ${busy ? "bg-amber-400 animate-ping" : "bg-emerald-400"}`} />
            <span className={`relative inline-flex h-3 w-3 rounded-full ${busy ? "bg-amber-500" : "bg-emerald-500"}`} />
          </span>
          <h3 className="text-sm font-bold text-white tracking-wide">
            Autonomous Remittance Agent Pipeline
          </h3>
        </div>
        <span className="text-xs px-2.5 py-1 rounded-full border border-white/10 bg-white/5 text-slate-300 font-mono">
          {busy ? "Evaluating..." : quote ? "Ready" : "Standby"}
        </span>
      </div>

      <div className="mt-4 space-y-3">
        {steps.map((step, idx) => {
          const isDone = step.status === "completed";
          const isBusy = step.status === "processing";

          return (
            <div
              key={step.id}
              className={`flex items-start gap-3.5 p-3 rounded-xl border transition-all ${
                isDone
                  ? "border-emerald-500/20 bg-emerald-500/[0.04]"
                  : isBusy
                  ? "border-amber-500/30 bg-amber-500/[0.05]"
                  : "border-white/5 bg-white/[0.02] opacity-75"
              }`}
            >
              <div
                className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-xs font-mono font-bold ${
                  isDone
                    ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                    : isBusy
                    ? "bg-amber-500/20 text-amber-300 border border-amber-500/40 animate-pulse"
                    : "bg-white/5 text-slate-400 border border-white/10"
                }`}
              >
                {isDone ? "✓" : step.num}
              </div>

              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-xs font-semibold text-white">{step.title}</p>
                  {step.badge && (
                    <span
                      className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${
                        isDone
                          ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                          : "bg-white/10 text-slate-300"
                      }`}
                    >
                      {step.badge}
                    </span>
                  )}
                </div>
                <p className="mt-0.5 text-[11px] leading-relaxed text-slate-400">
                  {step.desc}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      {quote?.explanation_log && quote.explanation_log.length > 0 && (
        <div className="mt-4 pt-3 border-t border-white/10">
          <button
            type="button"
            onClick={() => setShowLogs(!showLogs)}
            className="flex items-center justify-between w-full text-xs font-semibold text-amber-400 hover:text-amber-300 transition"
          >
            <span>AI Agent Reasoning Logs ({quote.explanation_log.length})</span>
            <span>{showLogs ? "▲ Hide" : "▼ Show"}</span>
          </button>
          {showLogs && (
            <div className="mt-2.5 p-3 rounded-xl bg-black/40 border border-white/10 max-h-48 overflow-y-auto space-y-1.5 font-mono text-[11px] text-slate-300">
              {quote.explanation_log.map((log, i) => (
                <div key={i} className="flex gap-2 leading-relaxed">
                  <span className="text-amber-500 shrink-0">›</span>
                  <span>{log}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
