"use client";

import { useState } from "react";
import type { STRINGS } from "@/lib/i18n";
import type { AgentStateResponse } from "@/lib/types";

type T = (typeof STRINGS)["en"];

export interface AgentPipelineProps {
  quote?: AgentStateResponse | null;
  busy?: boolean;
  activeStep?: number;
  t: T;
}

export default function AgentPipeline({ quote, busy, t }: AgentPipelineProps) {
  const [showLogs, setShowLogs] = useState(false);

  const steps = [
    {
      id: "intent",
      num: "01",
      title: t.pipeline.intentTitle,
      desc: quote?.parsed_intent
        ? `${quote.parsed_intent.amount} ${quote.parsed_intent.source_currency} → ${quote.parsed_intent.dest_currency} via ${quote.parsed_intent.payout_method || "optimal rail"}`
        : t.pipeline.intentIdle,
      status: busy ? "processing" : quote ? "completed" : "idle",
      badge: quote?.parsed_intent?.confidence
        ? `${Math.round(quote.parsed_intent.confidence * 100)}%`
        : null,
    },
    {
      id: "routing",
      num: "02",
      title: t.pipeline.routingTitle,
      desc: quote?.routes?.length
        ? t.pipeline.routingDesc(quote.routes.length)
        : t.pipeline.routingIdle,
      status: busy ? "processing" : quote?.routes ? "completed" : "idle",
      badge: quote?.routes?.length ? `${quote.routes.length}` : null,
    },
    {
      id: "incentive",
      num: "03",
      title: t.pipeline.incentiveTitle,
      desc: t.pipeline.incentiveIdle,
      status: busy ? "processing" : quote ? "completed" : "idle",
      badge: t.pipeline.incentiveBadge,
    },
    {
      id: "compliance",
      num: "04",
      title: t.pipeline.complianceTitle,
      desc: quote?.compliance
        ? `OFAC: ${quote.compliance.ofac_match_status || "-"} · ${quote.risk?.risk_band || "-"}`
        : t.pipeline.complianceIdle,
      status: busy ? "processing" : quote?.compliance ? "completed" : "idle",
      badge: quote?.decision === "CLEAR" ? t.pipeline.compliancePassed : quote?.decision ? String(quote.decision) : null,
    },
    {
      id: "quote_binding",
      num: "05",
      title: t.pipeline.bindingTitle,
      desc: quote?.quote_id
        ? t.pipeline.bindingDesc(quote.quote_id.slice(0, 8))
        : t.pipeline.bindingIdle,
      status: busy ? "processing" : quote?.quote_id ? "completed" : "idle",
      badge: quote?.quote_id ? t.pipeline.bindingBadge : null,
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
            {t.pipeline.title}
          </h3>
        </div>
        <span className="text-xs px-2.5 py-1 rounded-full border border-white/10 bg-white/5 text-slate-300 font-mono">
          {busy ? t.pipeline.evaluating : quote ? t.pipeline.ready : t.pipeline.standby}
        </span>
      </div>

      <div className="mt-4 space-y-3">
        {steps.map((step) => {
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
            <span>{t.pipeline.logsLabel(quote.explanation_log.length)}</span>
            <span>{showLogs ? `▲ ${t.pipeline.hide}` : `▼ ${t.pipeline.show}`}</span>
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
