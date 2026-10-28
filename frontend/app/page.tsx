"use client";

import { useEffect, useState } from "react";
import MicButton from "@/components/MicButton";
import ChainTrail from "@/components/ChainTrail";
import AgentPipeline from "@/components/AgentPipeline";
import { executeTransfer, fmtBDT, fmtCurrency, getQuote } from "@/lib/api";
import { STRINGS, applyDocLang, savedLang, type Lang } from "@/lib/i18n";
import type { AgentStateResponse, DemoScenario, RouteOption } from "@/lib/types";

type Screen = "send" | "quote" | "review" | "receipt";
type T = (typeof STRINGS)["en"];

/* Single demo corridor — the only priced one. The backend serves AED→BDT for
   every quote; a corridor picker that does not change the API call would be a
   fake control, and showing Malaysia numbers in the UI is on the cut list. */
const DEMO_CORRIDOR = { sourceCur: "AED", destCur: "BDT" };

const PAYOUT_OPTIONS = (t: T) => [
  { value: "BKASH", label: "bKash", detail: t.payoutWalletInstant, badge: t.payoutBadgeBonus },
  { value: "NAGAD", label: "Nagad", detail: t.payoutWalletPostal, badge: t.payoutBadgeBonus },
  { value: "UPAY", label: "Upay", detail: t.payoutWalletUcb, badge: t.payoutBadgeBonus },
  { value: "DEBIT_CARD", label: t.payoutDebit, detail: t.payoutCardNetworks, badge: t.payoutBadgeDirect },
  { value: "CREDIT_CARD", label: t.payoutCredit, detail: t.payoutCardCredit, badge: t.payoutBadgeDirect },
  { value: "VISA_CARD", label: t.payoutVisa, detail: t.payoutPushToCard, badge: t.payoutBadgeFast },
];

const SCENARIOS = (t: T) => [
  { key: "default" as DemoScenario, label: t.scDefault, desc: t.scDefaultDesc },
  { key: "fuzzy_review" as DemoScenario, label: t.scFuzzy, desc: t.scFuzzyDesc },
  { key: "high_risk" as DemoScenario, label: t.scHigh, desc: t.scHighDesc },
];

function Icon({ name, size = 18 }: { name: "arrow" | "check" | "shield" | "spark" | "clock" | "globe" | "chevron" | "info" | "cpu"; size?: number }) {
  const common = { width: size, height: size, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
  const paths = {
    arrow: <><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></>,
    check: <path d="m5 12 4 4L19 6"/>,
    shield: <><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></>,
    spark: <path d="m12 3 1.9 6.1L20 11l-6.1 1.9L12 19l-1.9-6.1L4 11l6.1-1.9L12 3Z"/>,
    clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3"/></>,
    globe: <><circle cx="12" cy="12" r="9"/><path d="M3.6 9h16.8M3.6 15h16.8M12 3a14.5 14.5 0 0 0 0 18M12 3a14.5 14.5 0 0 1 0 18"/></>,
    chevron: <path d="m9 6 6 6-6 6"/>,
    info: <><circle cx="12" cy="12" r="9"/><path d="M12 8h.01M12 12v4"/></>,
    cpu: <><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M15 2v2M9 2v2M15 20v2M9 20v2M2 15h2M2 9h2M20 15h2M20 9h2"/></>
  };
  return <svg {...common} aria-hidden="true">{paths[name]}</svg>;
}

function Brand() {
  return (
    <div className="flex items-center gap-3">
      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-amber-400 to-amber-600 shadow-[0_0_20px_rgba(245,158,11,0.35)] text-slate-950 font-black text-xl">
        ↗
      </div>
      <div>
        <p className="text-base font-extrabold tracking-tight text-white flex items-center gap-1">
          x<span className="text-amber-400">Pay</span>
          <span className="text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-amber-400/10 text-amber-300 border border-amber-400/20">AI</span>
        </p>
        <p className="text-[10px] text-slate-400 font-medium">Agentic Remittance</p>
      </div>
    </div>
  );
}

function Shell({ children, active = "send", lang }: { children: React.ReactNode; active?: string; lang: Lang }) {
  const t = STRINGS[lang];
  return (
    <div className="xpay-shell flex min-h-screen flex-col lg:flex-row text-slate-100">
      <aside className="flex w-full flex-col border-b border-white/10 bg-[#080d16]/95 backdrop-blur-xl px-5 py-5 lg:min-h-screen lg:w-[260px] lg:border-r lg:border-b-0 lg:px-6 lg:py-7">
        <Brand />

        <div className="mt-8 hidden flex-1 lg:block">
          <p className="mb-3 px-3 text-[10px] font-bold uppercase tracking-[.2em] text-slate-500">
            {t.platformNav}
          </p>
          <nav className="space-y-1.5">
            <NavItem icon="↗" label={t.navSend} active={active === "send"} href="/" />
            <NavItem icon="◈" label={t.navRoi} active={active === "roi"} href="/roi" />
          </nav>

          <div className="mt-8 rounded-2xl border border-white/10 bg-white/[0.02] p-4">
            <div className="flex items-center gap-2 text-xs font-semibold text-emerald-400">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75 animate-ping" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
              </span>
              {t.engineOkTitle}
            </div>
            <p className="mt-2 text-[11px] leading-relaxed text-slate-400">
              {t.systemsNote}
            </p>
          </div>
        </div>

        <div className="mt-auto hidden pt-4 border-t border-white/10 text-[11px] text-slate-500 lg:block">
          <p className="font-semibold text-slate-400">{t.teamLine}</p>
          <p className="mt-0.5">{t.congressLine}</p>
        </div>
      </aside>

      <main className="min-w-0 flex-1">{children}</main>
    </div>
  );
}

function NavItem({ icon, label, active, href }: { icon: string; label: string; active?: boolean; href: string }) {
  return (
    <a
      href={href}
      className={`flex items-center gap-3 rounded-xl px-3.5 py-3 text-sm font-medium transition ${
        active
          ? "border border-amber-400/30 bg-amber-500/10 text-white font-semibold shadow-[0_0_15px_rgba(245,158,11,0.15)]"
          : "text-slate-400 hover:border-white/10 hover:bg-white/5 hover:text-white border border-transparent"
      }`}
    >
      <span className={active ? "text-amber-400" : "text-slate-500"}>{icon}</span>
      {label}
    </a>
  );
}

function LangToggle({ lang, onLang }: { lang: Lang; onLang: (l: Lang) => void }) {
  return (
    <div className="flex rounded-xl border border-white/15 bg-white/5 p-1 text-[11px] font-bold">
      <button
        type="button"
        onClick={() => onLang("en")}
        className={`rounded-lg px-2.5 py-1 transition ${
          lang === "en" ? "bg-white/20 text-white shadow" : "text-slate-400 hover:text-white"
        }`}
      >
        EN
      </button>
      <button
        type="button"
        onClick={() => onLang("bn")}
        className={`rounded-lg px-2.5 py-1 transition ${
          lang === "bn" ? "bg-white/20 text-white shadow" : "text-slate-400 hover:text-white"
        }`}
      >
        বাং
      </button>
    </div>
  );
}

function Topbar({
  lang,
  onLang,
  scenario,
  onScenario,
}: {
  lang: Lang;
  onLang: (l: Lang) => void;
  scenario: DemoScenario;
  onScenario: (s: DemoScenario) => void;
}) {
  const t = STRINGS[lang];
  return (
    <header className="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 bg-[#080d16]/80 backdrop-blur-md px-5 py-4 sm:px-8 lg:px-12">
      <div className="flex flex-wrap items-center gap-3">
        {/* Demo status label — deliberately NOT a live feed indicator (F2) */}
        <div className="hidden sm:flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-medium text-slate-300">
          <span className="h-1.5 w-1.5 rounded-full bg-slate-400" />
          {t.demoCorridor}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        {/* Demo Scenario Selector for Judges */}
        <div className="flex items-center gap-1.5 rounded-xl border border-white/15 bg-white/5 p-1 text-xs">
          <span className="px-2 text-[10px] font-bold uppercase tracking-wider text-slate-400 hidden sm:inline">
            {t.demoScenarioLabel}:
          </span>
          {SCENARIOS(t).map((sc) => (
            <button
              key={sc.key}
              type="button"
              onClick={() => onScenario(sc.key)}
              title={sc.desc}
              className={`rounded-lg px-2.5 py-1 text-[11px] font-semibold transition ${
                scenario === sc.key
                  ? "bg-amber-500 text-slate-950 font-bold shadow"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              {sc.label}
            </button>
          ))}
        </div>

        {/* Language Toggle */}
        <LangToggle lang={lang} onLang={onLang} />
      </div>
    </header>
  );
}

export default function Home() {
  const [screen, setScreen] = useState<Screen>("send");
  const [lang, setLang] = useState<Lang>("en");
  const [amount, setAmount] = useState("1,000");
  const [recipient, setRecipient] = useState("");
  const [payoutMethod, setPayoutMethod] = useState("BKASH");
  const [deadline, setDeadline] = useState("");
  const [transcript, setTranscript] = useState<string | null>(null);
  const [scenario, setScenario] = useState<DemoScenario>("default");
  const [quote, setQuote] = useState<AgentStateResponse | null>(null);
  const [result, setResult] = useState<AgentStateResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [waking, setWaking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [llmOn, setLlmOn] = useState(false);

  const t = STRINGS[lang];

  useEffect(() => {
    const l = savedLang();
    setLang(l);
    applyDocLang(l);
    const s = new URLSearchParams(window.location.search).get("scenario");
    if (s === "fuzzy_review" || s === "fuzzy") setScenario("fuzzy_review");
    else if (s === "high_risk") setScenario("high_risk");

    fetch(`${process.env.NEXT_PUBLIC_API_BASE || ""}/api/health`)
      .then((r) => r.json())
      .then((h) => setLlmOn(Boolean(h?.engines?.llm_fallback)))
      .catch(() => setLlmOn(false));
  }, []);

  const switchLang = (l: Lang) => {
    setLang(l);
    window.localStorage.setItem("xpay-lang", l);
    applyDocLang(l);
  };

  const amountValue = Number(amount.replace(/,/g, ""));

  const reset = () => {
    setQuote(null);
    setResult(null);
    setTranscript(null);
    setError(null);
    setScreen("send");
  };

  const getBestRate = async () => {
    setBusy(true);
    setWaking(false);
    setError(null);
    setResult(null);
    try {
      const state = await getQuote(
        {
          amount: amountValue,
          recipient_name: recipient.trim() || undefined,
          payout_method: payoutMethod,
          deadline_hours: deadline ? Number(deadline) : undefined,
          demo_scenario: scenario,
        },
        () => setWaking(true)
      );
      if (!state.routes.length) throw new Error(t.noRoutes);
      setQuote(state);
      setScreen("quote");
    } catch (e) {
      setError(e instanceof Error ? (e.message === "API_UNREACHABLE" ? t.apiDown : e.message) : t.rateError);
    } finally {
      setBusy(false);
      setWaking(false);
    }
  };

  const send = async (routeName: string) => {
    setBusy(true);
    setWaking(false);
    setError(null);
    try {
      const state = await executeTransfer(
        {
          amount: amountValue,
          recipient_name: recipient.trim() || undefined,
          payout_method: payoutMethod,
          selected_route_name: routeName,
          demo_scenario: scenario,
          quote_id: quote?.quote_id ?? undefined,
          confirmed: Boolean(quote?.quote_id),
        },
        () => setWaking(true)
      );
      setResult(state);
      if (state.error === "quote_expired" || state.error === "quote_already_used") {
        setError(t.quoteExpiredMsg);
        setScreen("send");
        return;
      }
      if (state.decision === "CLEAR") setScreen("receipt");
      else if (state.decision === "BLOCKED") setError(t.blocked);
      else setScreen("review");
    } catch (e) {
      setError(e instanceof Error ? (e.message === "API_UNREACHABLE" ? t.apiDown : e.message) : t.sendError);
    } finally {
      setBusy(false);
      setWaking(false);
    }
  };

  if (screen === "quote" && quote) {
    return (
      <QuoteScreen
        quote={quote}
        lang={lang}
        onLang={switchLang}
        busy={busy}
        waking={waking}
        error={error}
        onSend={send}
        onBack={() => setScreen("send")}
      />
    );
  }

  if (screen === "review") {
    return <ReviewScreen lang={lang} onLang={switchLang} onDone={reset} />;
  }

  if (screen === "receipt" && result) {
    return (
      <ReceiptScreen
        result={result}
        lang={lang}
        onLang={switchLang}
        arrivalHours={
          quote?.routes.find((r) => r.name === result.transaction?.route_selected)
            ?.settlement_time_hrs
        }
        onRestart={reset}
      />
    );
  }

  return (
    <Shell lang={lang}>
      <Topbar lang={lang} onLang={switchLang} scenario={scenario} onScenario={setScenario} />

      <div className="mx-auto max-w-[1240px] px-5 py-8 sm:px-8 lg:px-12">
        <div className="grid gap-10 lg:grid-cols-[1.1fr_.9fr] items-start">
          {/* Left Column: Hero & Explanations */}
          <section className="min-w-0 space-y-6 pt-2 lg:pt-6">
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3.5 py-1.5 text-xs font-semibold text-emerald-400">
              <span className="h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399]" />
              {t.noHiddenFees}
            </div>

            <h1 className="text-4xl font-black tracking-tight text-white sm:text-6xl sm:leading-[1.08]">
              {t.heroLine1}
              <br />
              <span className="bg-gradient-to-r from-amber-400 via-amber-300 to-yellow-500 bg-clip-text text-transparent">
                {t.heroLine2}
              </span>
            </h1>

            <p className="max-w-xl text-base leading-relaxed text-slate-300 sm:text-lg">
              {t.heroBody}
            </p>

            {/* Quick Metrics — values bound to the corridor config (F4) */}
            <div className="grid max-w-xl grid-cols-3 gap-3">
              <Stat icon="spark" value="2.5%" label={t.statIncentiveLabel} highlight />
              <Stat icon="clock" value={t.statArrivalValue} label={t.statArrivalLabel} />
              <Stat icon="shield" value={t.statExpiryValue} label={t.statExpiryLabel} />
            </div>

            {/* AI Agent Pipeline Visualizer */}
            <div className="mt-8 pt-4">
              <AgentPipeline quote={quote} busy={busy} t={t} />
            </div>
          </section>

          {/* Right Column: Send Money Card */}
          <section className="min-w-0">
            <SendCard
              amount={amount}
              setAmount={setAmount}
              recipient={recipient}
              setRecipient={setRecipient}
              transcript={transcript}
              setTranscript={setTranscript}
              busy={busy}
              waking={waking}
              error={error}
              llmOn={llmOn}
              scenario={scenario}
              payoutMethod={payoutMethod}
              setPayoutMethod={setPayoutMethod}
              canSubmit={Number.isFinite(amountValue) && amountValue > 0 && !busy}
              onSubmit={getBestRate}
              deadline={deadline}
              setDeadline={setDeadline}
              t={t}
            />
          </section>
        </div>
      </div>

      <footer className="mt-12 border-t border-white/10 px-5 py-6 text-xs text-slate-400 sm:px-8 lg:px-12 flex flex-col sm:flex-row justify-between items-center gap-3">
        <span>{t.footerBrand}</span>
        <span>{t.footerFormal}</span>
      </footer>
    </Shell>
  );
}

function Stat({
  icon,
  value,
  label,
  highlight,
}: {
  icon: "spark" | "clock" | "shield";
  value: string;
  label: string;
  highlight?: boolean;
}) {
  return (
    <div
      className={`rounded-2xl border p-4 backdrop-blur-md transition ${
        highlight
          ? "border-amber-400/40 bg-amber-500/[0.08] shadow-[0_0_20px_rgba(245,158,11,0.15)]"
          : "border-white/10 bg-white/[0.03]"
      }`}
    >
      <div className={`mb-2 ${highlight ? "text-amber-400" : "text-slate-400"}`}>
        <Icon name={icon} size={16} />
      </div>
      <p className="xpay-mono text-xl font-black text-white">{value}</p>
      <p className="mt-0.5 text-[10px] font-bold uppercase tracking-wider text-slate-400">
        {label}
      </p>
    </div>
  );
}

function SendCard({
  amount,
  setAmount,
  recipient,
  setRecipient,
  transcript,
  setTranscript,
  busy,
  waking,
  error,
  llmOn,
  scenario,
  payoutMethod,
  setPayoutMethod,
  deadline,
  setDeadline,
  canSubmit,
  onSubmit,
  t,
}: {
  [k: string]: any;
  t?: T;
}) {
  const T = t ?? STRINGS["en"];
  const quickPills = ["500", "1,000", "2,500", "5,000"];

  return (
    <div className="xpay-card xpay-fade-up overflow-hidden">
      <div className="border-b border-white/10 bg-[#0d1627] px-6 py-5 sm:px-8 flex items-center justify-between">
        <div>
          <p className="xpay-eyebrow">{T.instantRateCheck}</p>
          <h2 className="mt-0.5 text-lg font-bold text-white">{T.compareRoutes}</h2>
        </div>
        <div className="flex items-center gap-1.5 rounded-full border border-white/15 bg-white/5 px-3 py-1 font-mono text-xs text-amber-300">
          <span>{DEMO_CORRIDOR.sourceCur}</span>
          <span>→</span>
          <span>{DEMO_CORRIDOR.destCur}</span>
        </div>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (canSubmit) onSubmit();
        }}
        className="space-y-5 p-6 sm:p-8"
      >
        {/* Amount Input */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label htmlFor="amount" className="text-xs font-bold uppercase tracking-wider text-slate-300">
              {T.youSend}
            </label>
            <div className="flex items-center gap-1">
              {quickPills.map((val) => (
                <button
                  key={val}
                  type="button"
                  onClick={() => setAmount(val)}
                  className="px-2 py-0.5 rounded text-[10px] font-mono font-medium border border-white/10 bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white transition"
                >
                  +{val}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center rounded-2xl border-2 border-amber-400/60 bg-[#070b13] px-4 py-2.5 xpay-glow transition-all">
            <input
              id="amount"
              inputMode="decimal"
              autoComplete="off"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="min-w-0 flex-1 bg-transparent text-3xl sm:text-4xl font-black tracking-tight text-white outline-none"
            />
            <span className="mr-3 text-sm font-bold text-slate-400 font-mono">
              {DEMO_CORRIDOR.sourceCur}
            </span>
            <MicButton
              onTranscript={(text) => {
                setTranscript(text);
                const m = text.replace(/,/g, "").match(/(\d+(?:\.\d+)?)/);
                if (m) setAmount(m[1]);
              }}
              disabled={busy}
              titleMic={T.micTitle}
              titleListening={T.micListening}
              titleUnsupported={T.micUnsupported}
            />
          </div>

          {transcript && (
            <p className="mt-2 text-xs text-amber-300/80 font-mono flex items-center gap-1.5">
              <span>🎙️</span> {T.heard}: “{transcript}”
            </p>
          )}
        </div>

        {/* Payout Method */}
        <div>
          <label htmlFor="payout-method" className="mb-2 block text-xs font-bold uppercase tracking-wider text-slate-300">
            {T.recipientChannel}
          </label>
          <div className="relative">
            <select
              id="payout-method"
              value={payoutMethod}
              onChange={(e) => setPayoutMethod(e.target.value)}
              className="w-full min-w-0 appearance-none rounded-xl border border-white/15 bg-[#0a101d] px-4 py-3 text-sm font-semibold text-white outline-none focus:border-amber-400"
            >
              {PAYOUT_OPTIONS(T).map((option) => (
                <option key={option.value} value={option.value} className="bg-slate-900 text-white">
                  {option.label} · {option.detail} ({option.badge})
                </option>
              ))}
            </select>
            <span className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-slate-400">
              ⌄
            </span>
          </div>
        </div>

        {/* Arrival Urgency / Deadline */}
        <div>
          <label htmlFor="deadline" className="mb-2 block text-xs font-bold uppercase tracking-wider text-slate-300">
            {T.deadlineLabel}
          </label>
          <div className="relative">
            <select
              id="deadline"
              value={deadline}
              onChange={(e) => setDeadline(e.target.value)}
              className="w-full min-w-0 appearance-none rounded-xl border border-white/15 bg-[#0a101d] px-4 py-3 text-sm font-semibold text-white outline-none focus:border-amber-400"
            >
              <option value="" className="bg-slate-900">{T.deadlineAny}</option>
              <option value="3" className="bg-slate-900">{T.deadline3h}</option>
              <option value="12" className="bg-slate-900">{T.deadline12h}</option>
              <option value="24" className="bg-slate-900">{T.deadline24h}</option>
            </select>
            <span className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-slate-400">
              ⌄
            </span>
          </div>
        </div>

        {/* Recipient Field */}
        <div>
          <label htmlFor="recipient" className="mb-2 block text-xs font-bold uppercase tracking-wider text-slate-300">
            {T.recipientOptional}
          </label>
          <div className="flex items-center gap-3 rounded-xl border border-white/15 bg-[#0a101d] px-4 py-3 focus-within:border-amber-400">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-emerald-500/20 text-emerald-400 text-xs">
              ✓
            </span>
            <input
              id="recipient"
              autoComplete="off"
              value={recipient}
              onChange={(e) => setRecipient(e.target.value)}
              placeholder={T.recipientNamePlaceholder}
              className="min-w-0 flex-1 bg-transparent text-sm text-white outline-none placeholder:text-slate-500"
            />
          </div>
        </div>

        {error && (
          <div className="flex items-center justify-between gap-3 rounded-xl border border-red-500/30 bg-red-500/10 p-3.5 text-xs font-medium text-red-300">
            <span className="min-w-0 flex items-center gap-2">
              <span>⚠️</span>
              <span>{error}</span>
            </span>
            <button
              type="button"
              onClick={() => onSubmit()}
              className="shrink-0 rounded-lg border border-red-400/40 px-3 py-1.5 text-xs font-bold text-red-300 hover:bg-red-500/20 transition"
            >
              {T.retry}
            </button>
          </div>
        )}

        <button
          type="submit"
          disabled={!canSubmit}
          className="flex h-13 w-full items-center justify-center gap-2.5 rounded-xl bg-gradient-to-r from-amber-400 to-amber-500 text-sm font-black text-slate-950 transition hover:from-amber-300 hover:to-amber-400 disabled:cursor-not-allowed disabled:opacity-40 shadow-[0_0_25px_rgba(245,158,11,0.3)]"
        >
          {busy ? (
            <span className="flex items-center gap-2">
              <span className="h-4 w-4 border-2 border-slate-950 border-t-transparent rounded-full animate-spin" />
              {waking ? T.wakingUp : T.evaluating}
            </span>
          ) : (
            <>
              {T.getBestRate}
              <Icon name="arrow" size={16} />
            </>
          )}
        </button>

        <div className="flex items-center justify-between border-t border-white/10 pt-3 text-[11px] text-slate-400">
          <span className="flex items-center gap-1.5">
            <Icon name="shield" size={13} />
            {T.ofacChecked}
          </span>
          <span className="font-mono text-slate-400">
            {scenario !== "default" ? T.demoScenario(scenario) : T.deterministicQuote}
          </span>
        </div>
      </form>
    </div>
  );
}

function QuoteScreen({
  quote,
  lang,
  onLang,
  busy,
  waking,
  error,
  onSend,
  onBack,
}: {
  quote: AgentStateResponse;
  lang: Lang;
  onLang: (l: Lang) => void;
  busy: boolean;
  waking: boolean;
  error: string | null;
  onSend: (route: string) => void;
  onBack: () => void;
}) {
  const t = STRINGS[lang];
  // F1: the default selection is the BACKEND's EV winner — never a client-side
  // sort by raw net, which would pre-select the incentive-ineligible teaser rail.
  const bestPossible =
    quote.routes.find((r) => r.is_best) ??
    quote.routes.find((r) => r.pricing_completeness === "complete" && r.breakdown.true_net_receive_bdt != null) ??
    quote.routes[0];

  const [selectedName, setSelectedName] = useState(bestPossible.name);
  const selected = quote.routes.find((r) => r.name === selectedName) ?? bestPossible;
  const marketValue = (selected.breakdown.amount_source ?? 0) * selected.mid_market_rate;
  const netValue = selected.breakdown.true_net_receive_bdt ?? 0;
  const valueDifference = marketValue - netValue;
  const forfeitRate =
    quote.routes.find((r) => r.incentive_eligible && (r.breakdown.govt_incentive_rate ?? 0) > 0)?.breakdown.govt_incentive_rate ?? null;

  return (
    <Shell lang={lang}>
      <header className="flex items-center justify-between border-b border-white/10 bg-[#080d16]/80 backdrop-blur-md px-5 py-4 sm:px-8 lg:px-12">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-xs font-bold text-amber-400 hover:text-amber-300 transition"
        >
          {t.changeTransfer}
        </button>
        <div className="flex items-center gap-3">
          <span className="text-xs font-mono text-slate-400">
            {t.quoteIdLabel}: {quote.quote_id?.slice(0, 10)}…
          </span>
          <LangToggle lang={lang} onLang={onLang} />
        </div>
      </header>

      <div className="mx-auto max-w-[1240px] px-5 py-8 sm:px-8 lg:px-12">
        {/* Hero Payout Announcement */}
        <div className="mb-8 rounded-3xl border border-white/10 bg-gradient-to-br from-[#0e172a] via-[#101b33] to-[#0a101d] p-6 sm:p-10 shadow-2xl flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <p className="xpay-eyebrow">{t.recipientReceives}</p>
            <h1 className="xpay-mono mt-2 text-4xl sm:text-6xl font-black tracking-tight text-white">
              {fmtBDT(selected.breakdown.true_net_receive_bdt)}
            </h1>
            {selected.breakdown.govt_incentive_added_bdt != null && (
              <p className="mt-3 flex items-center gap-2 text-sm font-semibold text-emerald-400">
                <Icon name="check" size={16} />
                {t.includesBonus(fmtBDT(selected.breakdown.govt_incentive_added_bdt))}
              </p>
            )}
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 text-xs space-y-2 shrink-0 md:min-w-[240px]">
            <div className="flex justify-between gap-4">
              <span className="text-slate-400">{t.corridorLabel}</span>
              <span className="font-semibold text-white">{t.demoCorridorName}</span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-slate-400">{t.decisionGate}</span>
              <span className={`font-bold ${quote.decision === "CLEAR" ? "text-emerald-400" : "text-amber-300"}`}>{quote.decision}</span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-slate-400">{t.routeStatus}</span>
              <span className="font-semibold text-amber-300">{selected.rail}</span>
            </div>
          </div>
        </div>

        {/* Route Cards & Inspector */}
        <div className="grid gap-8 lg:grid-cols-[1.1fr_.9fr]">
          <section className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="xpay-eyebrow">{t.rankedRoutes}</p>
                <h2 className="text-xl font-bold text-white">{t.compareAllRoutes}</h2>
                <p className="mt-0.5 text-[11px] text-slate-400">{t.rankedBy}</p>
              </div>
              <span className="text-xs font-mono text-slate-400">
                {t.optionsEvaluated(quote.routes.length)}
              </span>
            </div>

            <div className="space-y-3">
              {quote.routes.map((route, index) => (
                <RouteCard
                  key={route.name}
                  route={route}
                  selected={route.name === selected.name}
                  index={index}
                  onClick={() => setSelectedName(route.name)}
                  t={t}
                  forfeitRate={forfeitRate}
                />
              ))}
            </div>

            {/* AI Reasoning Log on Quote Screen */}
            <div className="mt-6">
              <AgentPipeline quote={quote} busy={busy} t={t} />
            </div>
          </section>

          <aside className="space-y-5">
            <div className="xpay-card p-6">
              <p className="xpay-eyebrow">{t.routeEconomics}</p>
              <h3 className="mt-1 text-lg font-bold text-white flex items-center gap-2">
                <span>{selected.rail}</span>
                {selected.is_best && (
                  <span className="text-[10px] font-bold uppercase tracking-wider bg-amber-400/20 text-amber-300 border border-amber-400/30 px-2 py-0.5 rounded-full">
                    {t.bestValue}
                  </span>
                )}
              </h3>

              <div className="mt-4 space-y-2 border-t border-white/10 pt-4 text-xs">
                <CompareRow label={t.amountSent} value={fmtCurrency(selected.breakdown.amount_source, DEMO_CORRIDOR.sourceCur)} />
                <CompareRow label={t.fxRateLabel} value={t.fxRate(selected.fx_rate.toFixed(2))} />
                <CompareRow label={t.fxMidLabel} value={`1 ${DEMO_CORRIDOR.sourceCur} = ${selected.mid_market_rate.toFixed(2)} BDT`} />
                <CompareRow label={t.routeFee} value={fmtCurrency(selected.fee_total_source, DEMO_CORRIDOR.sourceCur)} />
                {(selected.platform_fee_source ?? 0) > 0 && (
                  <CompareRow label={t.ofWhichXpay} value={fmtCurrency(selected.platform_fee_source, DEMO_CORRIDOR.sourceCur)} />
                )}
                <CompareRow label={t.arrivalLabel} value={t.arrivalHours(selected.settlement_time_hrs)} />

                <div className="my-2 border-t border-dashed border-white/15 pt-2">
                  <CompareRow label={t.midMarketValue} value={fmtBDT(marketValue)} />
                  <CompareRow label={t.recipientNet} value={fmtBDT(netValue)} />
                  <CompareRow
                    label={t.difference}
                    value={`${valueDifference >= 0 ? "−" : "+"}${fmtBDT(Math.abs(valueDifference))}`}
                  />
                </div>
              </div>
            </div>

            {/* F3: the banner is CONDITIONAL on the quote's decision — never an
                unconditional "cleared" claim */}
            {quote.decision === "CLEAR" ? (
              <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-5">
                <div className="flex gap-3">
                  <div className="text-emerald-400 mt-0.5">
                    <Icon name="shield" size={20} />
                  </div>
                  <div>
                    <p className="font-bold text-emerald-300 text-sm">{t.complianceCleared}</p>
                    <p className="mt-1 text-xs leading-relaxed text-emerald-200/80">{t.complianceClearedBody}</p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-5">
                <div className="flex gap-3">
                  <div className="text-amber-400 mt-0.5">
                    <Icon name="shield" size={20} />
                  </div>
                  <div>
                    <p className="font-bold text-amber-300 text-sm">
                      {quote.decision === "FUZZY_MATCH_REVIEW" ? t.complianceHoldTitle : t.complianceReviewTitle}
                    </p>
                    <p className="mt-1 text-xs leading-relaxed text-amber-200/80">
                      {quote.decision === "FUZZY_MATCH_REVIEW" ? t.holdBody : t.reviewBody}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {error && <p className="rounded-xl bg-red-500/20 border border-red-500/30 p-3 text-xs text-red-300">{error}</p>}

            <button
              onClick={() => onSend(selected.name)}
              disabled={busy}
              className="flex h-14 w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-amber-400 to-amber-500 text-base font-black text-slate-950 transition hover:from-amber-300 hover:to-amber-400 disabled:opacity-50 shadow-[0_0_30px_rgba(245,158,11,0.35)]"
            >
              {busy ? (waking ? t.wakingUp : t.sending) : t.sendWith(selected.rail)}
              <Icon name="arrow" size={18} />
            </button>

            <p className="text-center text-[11px] text-slate-400">
              {t.confirmNote}
            </p>
          </aside>
        </div>
      </div>
    </Shell>
  );
}

function RouteCard({
  route,
  selected,
  index,
  onClick,
  t,
  forfeitRate,
}: {
  route: RouteOption;
  selected: boolean;
  index: number;
  onClick: () => void;
  t: T;
  forfeitRate?: number | null;
}) {
  const forfeited =
    route.incentive_eligible || route.breakdown.gross_bdt == null || !(forfeitRate && forfeitRate > 0)
      ? null
      : route.breakdown.gross_bdt * forfeitRate;
  return (
    <button
      type="button"
      onClick={onClick}
      className={`xpay-fade-up w-full rounded-2xl border p-5 text-left transition-all ${
        selected
          ? "border-amber-400 bg-amber-500/10 shadow-[0_0_25px_rgba(245,158,11,0.2)]"
          : "border-white/10 bg-white/[0.02] hover:border-white/20 hover:bg-white/[0.04]"
      }`}
    >
      <div className="flex items-start gap-4">
        <div
          className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-xs font-mono font-bold ${
            selected
              ? "bg-amber-400 text-slate-950 font-black shadow"
              : "bg-white/5 text-slate-400 border border-white/10"
          }`}
        >
          0{index + 1}
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <p className="font-bold text-white text-base">{route.rail}</p>
                {route.is_best && (
                  <span className="rounded-full bg-amber-400/20 text-amber-300 border border-amber-400/30 px-2 py-0.5 text-[9px] font-black uppercase tracking-wider">
                    {t.recommended}
                  </span>
                )}
              </div>
              <p className="mt-0.5 text-xs text-slate-400">
                {route.payout_method} · {route.incentive_eligible ? t.incentiveEligible : t.noIncentive}
              </p>
            </div>

            <p className="xpay-mono text-xl font-black text-amber-400">
              {fmtBDT(route.breakdown.true_net_receive_bdt)}
            </p>
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-slate-300 font-medium">
            <span className="flex items-center gap-1.5 text-slate-400">
              <Icon name="clock" size={13} /> {t.hoursArrival(route.settlement_time_hrs)}
            </span>
            <span className="text-slate-400">
              {t.feeTag(fmtCurrency(route.fee_total_source, DEMO_CORRIDOR.sourceCur))}
            </span>
            <span className={route.incentive_eligible ? "text-emerald-400 font-semibold" : "text-slate-500"}>
              {route.incentive_eligible ? t.bonusTag : forfeited && forfeited > 0.5 ? t.forfeitsBonus(fmtBDT(forfeited)) : t.noBonusTag}
            </span>
          </div>
        </div>

        <div
          className={`mt-1 h-5 w-5 rounded-full border-2 flex items-center justify-center ${
            selected ? "border-amber-400 bg-amber-400 text-slate-950" : "border-slate-600"
          }`}
        >
          {selected && <span className="h-2 w-2 rounded-full bg-slate-950" />}
        </div>
      </div>
    </button>
  );
}

function CompareRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 py-1">
      <span className="text-slate-400">{label}</span>
      <span className="xpay-mono font-semibold text-white">{value}</span>
    </div>
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
    <Shell lang={lang}>
      <header className="flex items-center justify-between border-b border-white/10 px-5 py-4 sm:px-8">
        <span className="text-xs font-bold uppercase tracking-wider text-amber-400">{t.eyebrowReview}</span>
        <LangToggle lang={lang} onLang={onLang} />
      </header>
      <div className="mx-auto max-w-[620px] px-5 py-20 text-center sm:px-8">
        <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-3xl border border-amber-400/40 bg-amber-500/10 text-amber-400 shadow-[0_0_30px_rgba(245,158,11,0.2)]">
          <Icon name="shield" size={38} />
        </div>
        <p className="xpay-eyebrow mt-8">{t.inReview}</p>
        <h1 className="mt-2 text-4xl font-black tracking-tight text-white">{t.reviewPauseTitle}</h1>
        <p className="mx-auto mt-4 max-w-md text-base leading-relaxed text-slate-300">
          {t.reviewSentence} {t.reviewSafeNote}
        </p>
        <button
          onClick={onDone}
          className="mt-8 rounded-xl bg-amber-400 px-8 py-3.5 font-bold text-slate-950 hover:bg-amber-300 transition"
        >
          {t.gotIt}
        </button>
      </div>
    </Shell>
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
    <Shell lang={lang}>
      <header className="flex items-center justify-between border-b border-white/10 px-5 py-4 sm:px-8">
        <span className="text-xs font-bold uppercase tracking-wider text-emerald-400">{t.executedBadge}</span>
        <LangToggle lang={lang} onLang={onLang} />
      </header>

      <div className="mx-auto max-w-[840px] px-5 py-10 sm:px-8 lg:px-12">
        <div className="mb-8 flex items-center gap-4">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-emerald-500/40 bg-emerald-500/10 text-emerald-400 shadow-[0_0_20px_rgba(16,185,129,0.3)]">
            <Icon name="check" size={28} />
          </div>
          <div>
            <p className="xpay-eyebrow">{t.cleared}</p>
            <h1 className="text-3xl font-black tracking-tight text-white">{t.sent}</h1>
          </div>
        </div>

        <div className="xpay-card overflow-hidden">
          <div className="bg-gradient-to-r from-[#0d1627] to-[#101b33] p-7 sm:p-9 border-b border-white/10">
            <p className="text-xs text-slate-400">{t.recipientReceives}</p>
            <p className="xpay-mono mt-1 text-4xl sm:text-5xl font-black text-amber-400">
              {fmtBDT(tx.true_net_receive_bdt)}
            </p>
            <p className="mt-2 text-sm text-slate-300">
              {t.arrivingVia(arrivalHours ?? 2, tx.route_selected ?? "—")}
            </p>
          </div>

          <div className="p-6 sm:p-9 space-y-6">
            <div className="grid gap-x-10 gap-y-2 sm:grid-cols-2">
              <Row label={t.amountRow} value={fmtCurrency(tx.amount_source, DEMO_CORRIDOR.sourceCur)} />
              <Row label={t.recipientLabel} value={`${tx.recipient_name} (${tx.recipient_handle})`} />
              <Row label={t.routeRow} value={tx.route_selected ?? "—"} />
              <Row label={t.referenceRow} value={tx.transaction_id} mono />
            </div>

            {tx.stellar_hash && (
              <div className="border-t border-white/10 pt-6">
                <ChainTrail
                  hash={tx.stellar_hash}
                  network={execution?.network ?? "SIMULATED"}
                  labels={{
                    title: t.chainTrailTitle,
                    prev: t.blockPrev,
                    yours: t.blockYours,
                    next: t.blockNext,
                    copyHash: t.ctCopyHash,
                    copied: t.ctCopied,
                  }}
                />
              </div>
            )}

            <details className="mt-4 rounded-xl border border-white/10 bg-white/[0.02] p-4">
              <summary className="cursor-pointer text-xs font-bold text-slate-300 hover:text-white">
                {t.technicalDetails} {t.payloadSuffix}
              </summary>
              <pre className="mt-3 overflow-x-auto rounded-lg bg-black/50 p-4 text-[11px] font-mono text-emerald-300 leading-relaxed">
                {JSON.stringify(tx.iso_20022, null, 2)}
              </pre>
            </details>

            <button
              onClick={onRestart}
              className="mt-6 h-13 w-full rounded-xl border border-white/20 bg-white/5 font-bold text-white hover:bg-white/10 transition"
            >
              {t.sendAnother}
            </button>
          </div>
        </div>
      </div>
    </Shell>
  );
}

function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-dashed border-white/10 py-3 text-sm">
      <dt className="text-slate-400">{label}</dt>
      <dd className={`text-right font-semibold text-white ${mono ? "font-mono text-xs text-amber-300" : ""}`}>
        {value}
      </dd>
    </div>
  );
}
