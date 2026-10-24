"use client";

import { useEffect, useState } from "react";
import MicButton from "@/components/MicButton";
import FlowDiagram from "@/components/FlowDiagram";
import ChainTrail from "@/components/ChainTrail";
import { executeTransfer, fmtAED, fmtBDT, getQuote } from "@/lib/api";
import { STRINGS, type Lang } from "@/lib/i18n";
import type { AgentStateResponse, DemoScenario } from "@/lib/types";

type Screen = "send" | "quote" | "review" | "receipt";

const SCENARIO_LINKS: Array<{ param: string; label: string }> = [
  { param: "default", label: "default" },
  { param: "fuzzy_review", label: "review" },
  { param: "high_risk", label: "high risk" },
];

export default function Home() {
  const [screen, setScreen] = useState<Screen>("send");
  const [lang, setLang] = useState<Lang>("en");
  const [amount, setAmount] = useState("1,000");
  const [recipient, setRecipient] = useState("");
  const [transcript, setTranscript] = useState<string | null>(null);
  const [scenario, setScenario] = useState<DemoScenario>("default");
  const [quote, setQuote] = useState<AgentStateResponse | null>(null);
  const [result, setResult] = useState<AgentStateResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const t = STRINGS[lang];

  useEffect(() => {
    const saved = window.localStorage.getItem("bm-lang");
    if (saved === "bn" || saved === "en") setLang(saved);
    const s = new URLSearchParams(window.location.search).get("scenario");
    if (s === "fuzzy" || s === "fuzzy_review") setScenario("fuzzy_review");
    else if (s === "high_risk") setScenario("high_risk");
  }, []);

  const switchLang = (l: Lang) => {
    setLang(l);
    window.localStorage.setItem("bm-lang", l);
    document.documentElement.lang = l === "bn" ? "bn" : "en";
  };

  const amountValue = Number(amount.replace(/,/g, ""));
  const canSubmit = Number.isFinite(amountValue) && amountValue > 0 && !busy;

  const onTranscript = (text: string) => {
    setTranscript(text);
    const m = text.replace(/,/g, "").match(/(\d+(?:\.\d+)?)/);
    if (m) setAmount(m[1]);
  };

  const reset = () => {
    setQuote(null);
    setResult(null);
    setTranscript(null);
    setError(null);
    setScreen("send");
  };

  const getBestRate = async () => {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const state = await getQuote({
        amount: amountValue,
        recipient_name: recipient.trim() || undefined,
        demo_scenario: scenario,
      });
      if (!state.routes.length) throw new Error(t.noRoutes);
      setQuote(state);
      setScreen("quote");
    } catch (e) {
      setError(e instanceof Error ? e.message : t.rateError);
    } finally {
      setBusy(false);
    }
  };

  const send = async (routeName: string) => {
    setBusy(true);
    setError(null);
    try {
      const state = await executeTransfer({
        amount: amountValue,
        recipient_name: recipient.trim() || undefined,
        selected_route_name: routeName,
        demo_scenario: scenario,
      });
      setResult(state);
      if (state.decision === "CLEAR") setScreen("receipt");
      else if (state.decision === "BLOCKED") setError(t.blocked);
      else setScreen("review");
    } catch (e) {
      setError(e instanceof Error ? e.message : t.sendError);
    } finally {
      setBusy(false);
    }
  };

  if (screen === "quote" && quote)
    return (
      <QuoteScreen
        quote={quote}
        lang={lang}
        onLang={switchLang}
        busy={busy}
        error={error}
        onSend={send}
        onBack={() => setScreen("send")}
      />
    );
  if (screen === "review")
    return <ReviewScreen lang={lang} onLang={switchLang} onDone={reset} />;
  if (screen === "receipt" && result)
    return (
      <ReceiptScreen
        result={result}
        lang={lang}
        onLang={switchLang}
        arrivalHours={quote?.routes.find((r) => r.name === result.transaction?.route_selected)?.settlement_time_hrs}
        onRestart={reset}
      />
    );

  return (
    <main className="relative mx-auto w-full max-w-md px-5 py-12">
      <div className="absolute right-5 top-8">
        <LangToggle lang={lang} onLang={switchLang} />
      </div>
      <h1 className="text-[28px] font-semibold tracking-tight">{t.heading}</h1>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (canSubmit) getBestRate();
        }}
      >
        <label htmlFor="amount" className="mt-8 block text-muted">
          {t.amountLabel}
        </label>
        <div className="mt-2 flex items-stretch gap-2">
          <div className="relative flex-1">
            <input
              id="amount"
              inputMode="decimal"
              autoComplete="off"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="h-14 w-full rounded-lg border border-line py-3 pl-4 pr-16 text-2xl tabular-nums focus:border-accent focus:outline-none"
            />
            <span className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-muted">AED</span>
          </div>
          <MicButton onTranscript={onTranscript} disabled={busy} />
        </div>
        {transcript && <p className="mt-2 text-muted">{t.heard}: &ldquo;{transcript}&rdquo;</p>}

        <label htmlFor="recipient" className="mt-6 block text-muted">
          {t.recipientLabel}
        </label>
        <input
          id="recipient"
          autoComplete="off"
          value={recipient}
          onChange={(e) => setRecipient(e.target.value)}
          placeholder={t.recipientPlaceholder}
          className="mt-2 h-12 w-full rounded-lg border border-line px-4 focus:border-accent focus:outline-none placeholder:text-muted"
        />

        {error && <p className="mt-4 font-medium">{error}</p>}

        <button
          type="submit"
          disabled={!canSubmit}
          className="mt-8 h-12 w-full rounded-lg bg-accent text-lg font-semibold text-white disabled:opacity-50"
        >
          {busy ? t.checkingRate : t.getBestRate}
        </button>
      </form>

      <details className="mt-8">
        <summary className="cursor-pointer py-2 text-sm text-muted underline">{t.howItWorks}</summary>
        <FlowDiagram steps={t.flow} />
      </details>

      {scenario !== "default" && <p className="mt-6 text-[12px] text-review">Simulating scenario: {scenario}</p>}
      <footer className="mt-16 text-[12px] text-muted">
        Demo scenarios:{" "}
        {SCENARIO_LINKS.map((s, i) => (
          <span key={s.param}>
            {i > 0 && " · "}
            <a href={`/?scenario=${s.param}`} className="underline">
              {s.label}
            </a>
          </span>
        ))}
      </footer>
    </main>
  );
}

function LangToggle({ lang, onLang }: { lang: Lang; onLang: (l: Lang) => void }) {
  return (
    <div className="flex items-center gap-1 text-sm" role="group" aria-label="Language / ভাষা">
      <button
        type="button"
        onClick={() => onLang("en")}
        aria-pressed={lang === "en"}
        className={"rounded-lg px-2 py-2 " + (lang === "en" ? "font-semibold text-ink" : "text-muted")}
      >
        EN
      </button>
      <span className="text-muted">|</span>
      <button
        type="button"
        onClick={() => onLang("bn")}
        aria-pressed={lang === "bn"}
        className={"rounded-lg px-2 py-2 " + (lang === "bn" ? "font-semibold text-ink" : "text-muted")}
      >
        বাংলা
      </button>
    </div>
  );
}

function QuoteScreen({
  quote,
  lang,
  onLang,
  busy,
  error,
  onSend,
  onBack,
}: {
  quote: AgentStateResponse;
  lang: Lang;
  onLang: (l: Lang) => void;
  busy: boolean;
  error: string | null;
  onSend: (routeName: string) => void;
  onBack: () => void;
}) {
  const t = STRINGS[lang];
  const [selectedName, setSelectedName] = useState(quote.routes[0].name);
  const selected = quote.routes.find((r) => r.name === selectedName) ?? quote.routes[0];
  const best = quote.routes[0];
  const baseline =
    quote.routes.find((r) => r.rail === "Traditional SWIFT") ?? quote.routes[quote.routes.length - 1];
  const isBestSelected = selected.name === best.name;

  const comparison = isBestSelected
    ? t.routedMore(
        best.rail,
        Math.round(best.breakdown.true_net_receive_bdt - baseline.breakdown.true_net_receive_bdt)
          .toLocaleString("en-US"),
      )
    : t.routedLess(
        selected.rail,
        Math.round(selected.advantage_bdt_vs_best).toLocaleString("en-US"),
        best.rail,
      );

  return (
    <main className="relative mx-auto w-full max-w-md px-5 py-12">
      <div className="absolute right-5 top-8">
        <LangToggle lang={lang} onLang={onLang} />
      </div>
      <p className="text-muted">{t.theyReceive}</p>
      <p className="mt-1 text-[44px] font-bold leading-none tracking-tight tabular-nums">
        {fmtBDT(selected.breakdown.true_net_receive_bdt)}
      </p>
      <p className="mt-3 text-accent">
        {t.includesBonus(fmtBDT(selected.breakdown.govt_incentive_added_bdt))}
      </p>

      <div role="radiogroup" aria-label={lang === "bn" ? "রুট" : "Route"} className="mt-10 rounded-lg border border-line">
        {quote.routes.map((r, i) => {
          const isSelected = r.name === selected.name;
          return (
            <button
              key={r.name}
              type="button"
              role="radio"
              aria-checked={isSelected}
              onClick={() => setSelectedName(r.name)}
              className={
                "flex w-full items-start gap-3 px-4 py-4 text-left text-ink" +
                (i > 0 ? " border-t border-line" : "")
              }
            >
              <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true" className="mt-1 shrink-0">
                <circle cx="9" cy="9" r="8" fill="none" stroke={isSelected ? "#0F766E" : "#6B7280"} strokeWidth="1.5" />
                {isSelected && <circle cx="9" cy="9" r="4" fill="#0F766E" />}
              </svg>
              <span className="min-w-0 flex-1">
                <span className="flex items-baseline justify-between gap-3">
                  <span className="font-medium">
                    {r.rail}
                    {r.is_best && <span className="ml-2 text-accent">{t.recommended}</span>}
                  </span>
                  <span className="shrink-0 tabular-nums">{fmtBDT(r.breakdown.true_net_receive_bdt)}</span>
                </span>
                <span className="block text-muted">{t.feeArrives(fmtAED(r.fee_aed), r.settlement_time_hrs)}</span>
              </span>
            </button>
          );
        })}
      </div>

      <p className="mt-4">{comparison}</p>

      {error && <p className="mt-4 font-medium">{error}</p>}

      <button
        onClick={() => onSend(selected.name)}
        disabled={busy}
        className="mt-8 h-12 w-full rounded-lg bg-accent text-lg font-semibold text-white disabled:opacity-50"
      >
        {busy ? t.sending : t.sendWith(selected.rail)}
      </button>
      <button
        onClick={onBack}
        disabled={busy}
        className="mt-3 h-12 w-full rounded-lg border border-line text-lg font-medium disabled:opacity-50"
      >
        {t.changeAmount}
      </button>

      <p className="mt-6 text-[12px] leading-relaxed text-muted">{t.footnote}</p>
    </main>
  );
}

function ReviewScreen({
  lang,
  onLang,
  onDone,
}: {
  lang: Lang;
  onLang: (l: Lang) => void;
  onDone: () => void;
}) {
  const t = STRINGS[lang];
  return (
    <main className="relative mx-auto w-full max-w-md px-5 py-16">
      <div className="absolute right-5 top-8">
        <LangToggle lang={lang} onLang={onLang} />
      </div>
      <p className="font-medium text-review">{t.inReview}</p>
      <p className="mt-4">{t.reviewSentence}</p>
      <button
        onClick={onDone}
        className="mt-8 h-12 w-full rounded-lg bg-accent text-lg font-semibold text-white"
      >
        {t.gotIt}
      </button>
    </main>
  );
}

function ReceiptScreen({
  result,
  lang,
  onLang,
  arrivalHours,
  onRestart,
}: {
  result: AgentStateResponse;
  lang: Lang;
  onLang: (l: Lang) => void;
  arrivalHours?: number;
  onRestart: () => void;
}) {
  const t = STRINGS[lang];
  const tx = result.transaction;
  if (!tx) return null;
  const execution = result.execution;

  return (
    <main className="relative mx-auto w-full max-w-md px-5 py-12">
      <div className="absolute right-5 top-8">
        <LangToggle lang={lang} onLang={onLang} />
      </div>
      <h1 className="text-[28px] font-semibold tracking-tight text-accent">{t.sent}</h1>
      <p className="mt-1 text-sm font-medium text-accent">{t.cleared}</p>

      <dl className="mt-8">
        <Row label={t.amountRow} value={fmtAED(tx.amount_source)} />
        <Row label={t.theyReceive} value={fmtBDT(tx.true_net_receive_bdt)} accent />
        <Row label={t.recipientLabel} value={`${tx.recipient_name} · ${tx.recipient_handle}`} />
        <Row label={t.routeRow} value={tx.route_selected ?? "—"} />
        <Row label={t.arrivesRow} value={t.inAboutHours(arrivalHours ?? 2)} />
        <Row label={t.referenceRow} value={tx.transaction_id} mono />
      </dl>

      {tx.stellar_hash && (
        <div className="mt-6">
          <ChainTrail
            hash={tx.stellar_hash}
            network={execution?.network ?? "SIMULATED"}
            labels={{
              title: t.chainTrailTitle,
              prev: t.blockPrev,
              yours: t.blockYours,
              next: t.blockNext,
            }}
          />
        </div>
      )}

      <details className="mt-6">
        <summary className="cursor-pointer py-2 text-sm text-muted underline">{t.technicalDetails}</summary>
        <pre className="mt-2 overflow-x-auto text-[13px] leading-relaxed">
          {JSON.stringify(tx.iso_20022, null, 2)}
        </pre>
        <p className="mt-3 text-[13px] leading-relaxed text-muted">
          Settlement: {execution?.network ?? "SIMULATED"} · Hash: {tx.stellar_hash} · Memo:{" "}
          {execution?.memo} · Created: {tx.created_at}
        </p>
      </details>

      <button
        onClick={onRestart}
        className="mt-8 h-12 w-full rounded-lg border border-line text-lg font-medium"
      >
        {t.sendAnother}
      </button>
    </main>
  );
}

function Row({
  label,
  value,
  accent,
  mono,
}: {
  label: string;
  value: string;
  accent?: boolean;
  mono?: boolean;
}) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-b border-line py-3 last:border-b-0">
      <dt className="text-muted">{label}</dt>
      <dd
        className={
          "text-right tabular-nums" +
          (accent ? " font-semibold text-accent" : "") +
          (mono ? " font-mono text-sm" : "")
        }
      >
        {value}
      </dd>
    </div>
  );
}
