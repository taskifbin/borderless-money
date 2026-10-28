"use client";

import { useEffect, useState } from "react";
import MicButton from "@/components/MicButton";
import ChainTrail from "@/components/ChainTrail";
import AgentPipeline from "@/components/AgentPipeline";
import { executeTransfer, fmtBDT, fmtCurrency, getQuote } from "@/lib/api";
import { STRINGS, type Lang } from "@/lib/i18n";
import type { AgentStateResponse, DemoScenario, RouteOption } from "@/lib/types";

type Screen = "send" | "quote" | "review" | "receipt";

interface Corridor {
  id: string;
  name: string;
  flag: string;
  sourceCur: string;
  destCur: string;
  defaultAmount: string;
}

const CORRIDORS: Corridor[] = [
  { id: "uae_bd", name: "UAE → Bangladesh", flag: "🇦🇪", sourceCur: "AED", destCur: "BDT", defaultAmount: "1,000" },
  { id: "my_bd", name: "Malaysia → Bangladesh", flag: "🇲🇾", sourceCur: "MYR", destCur: "BDT", defaultAmount: "1,200" },
  { id: "ksa_bd", name: "Saudi Arabia → Bangladesh", flag: "🇸🇦", sourceCur: "SAR", destCur: "BDT", defaultAmount: "1,000" },
];

const PAYOUT_OPTIONS = [
  { value: "BKASH", label: "bKash", detail: "Instant Mobile Wallet", badge: "2.5% Bonus" },
  { value: "NAGAD", label: "Nagad", detail: "Postal Mobile Wallet", badge: "2.5% Bonus" },
  { value: "UPAY", label: "Upay", detail: "UCB Mobile Wallet", badge: "2.5% Bonus" },
  { value: "DEBIT_CARD", label: "Debit Card", detail: "Visa / Mastercard Payout", badge: "Direct" },
  { value: "CREDIT_CARD", label: "Credit Card", detail: "Card Account Credit", badge: "Direct" },
  { value: "VISA_CARD", label: "Visa Direct", detail: "Real-time Push-to-Card", badge: "Fast" },
];

const SCENARIOS: { key: DemoScenario; label: string; desc: string }[] = [
  { key: "default", label: "Clean / Normal", desc: "Clean sender & recipient (auto-approved)" },
  { key: "fuzzy_review", label: "Fuzzy Review", desc: "Similar name to OFAC alias (held for review)" },
  { key: "high_risk", label: "Sanctioned Block", desc: "Exact SDN match / high AML risk score" },
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

function Shell({ children, active = "send" }: { children: React.ReactNode; active?: string }) {
  return (
    <div className="xpay-shell flex min-h-screen flex-col lg:flex-row text-slate-100">
      <aside className="flex w-full flex-col border-b border-white/10 bg-[#080d16]/95 backdrop-blur-xl px-5 py-5 lg:min-h-screen lg:w-[260px] lg:border-r lg:border-b-0 lg:px-6 lg:py-7">
        <Brand />

        <div className="mt-8 hidden flex-1 lg:block">
          <p className="mb-3 px-3 text-[10px] font-bold uppercase tracking-[.2em] text-slate-500">
            Platform Navigation
          </p>
          <nav className="space-y-1.5">
            <NavItem icon="↗" label="Send money" active={active === "send"} href="/" />
            <NavItem icon="◈" label="B2B ROI Calculator" active={active === "roi"} href="/roi" />
          </nav>

          <div className="mt-8 rounded-2xl border border-white/10 bg-white/[0.02] p-4">
            <div className="flex items-center gap-2 text-xs font-semibold text-emerald-400">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75 animate-ping" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
              </span>
              Engine Operational
            </div>
            <p className="mt-2 text-[11px] leading-relaxed text-slate-400">
              Quotes are cryptographically bound, OFAC/AML pre-screened, and maximized for net payout.
            </p>
          </div>
        </div>

        <div className="mt-auto hidden pt-4 border-t border-white/10 text-[11px] text-slate-500 lg:block">
          <p className="font-semibold text-slate-400">Team CTRL V</p>
          <p className="mt-0.5">International AI Builders Congress 2026</p>
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

function Topbar({
  lang,
  onLang,
  corridor,
  onCorridor,
  scenario,
  onScenario,
}: {
  lang: Lang;
  onLang: (l: Lang) => void;
  corridor: Corridor;
  onCorridor: (c: Corridor) => void;
  scenario: DemoScenario;
  onScenario: (s: DemoScenario) => void;
}) {
  return (
    <header className="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 bg-[#080d16]/80 backdrop-blur-md px-5 py-4 sm:px-8 lg:px-12">
      <div className="flex flex-wrap items-center gap-3">
        {/* Corridor Switcher */}
        <div className="relative">
          <select
            value={corridor.id}
            onChange={(e) => {
              const found = CORRIDORS.find((c) => c.id === e.target.value);
              if (found) onCorridor(found);
            }}
            className="appearance-none rounded-xl border border-white/15 bg-white/5 py-2 pl-3 pr-8 text-xs font-semibold text-white outline-none hover:bg-white/10 cursor-pointer focus:border-amber-400"
          >
            {CORRIDORS.map((c) => (
              <option key={c.id} value={c.id} className="bg-slate-900 text-white">
                {c.flag} {c.name} ({c.sourceCur})
              </option>
            ))}
          </select>
          <span className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 text-[10px]">
            ▼
          </span>
        </div>

        {/* Live Corridor Status Badge */}
        <div className="hidden sm:flex items-center gap-2 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-400">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
          Active Rail Feed
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        {/* Demo Scenario Selector for Judges */}
        <div className="flex items-center gap-1.5 rounded-xl border border-white/15 bg-white/5 p-1 text-xs">
          <span className="px-2 text-[10px] font-bold uppercase tracking-wider text-slate-400 hidden sm:inline">
            Demo Scenario:
          </span>
          {SCENARIOS.map((sc) => (
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
      </div>
    </header>
  );
}

export default function Home() {
  const [screen, setScreen] = useState<Screen>("send");
  const [lang, setLang] = useState<Lang>("en");
  const [corridor, setCorridor] = useState<Corridor>(CORRIDORS[0]);
  const [amount, setAmount] = useState(CORRIDORS[0].defaultAmount);
  const [recipient, setRecipient] = useState("");
  const [payoutMethod, setPayoutMethod] = useState("BKASH");
  const [deadline, setDeadline] = useState("");
  const [transcript, setTranscript] = useState<string | null>(null);
  const [scenario, setScenario] = useState<DemoScenario>("default");
  const [quote, setQuote] = useState<AgentStateResponse | null>(null);
  const [result, setResult] = useState<AgentStateResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [llmOn, setLlmOn] = useState(false);

  const t = STRINGS[lang];

  useEffect(() => {
    const saved = window.localStorage.getItem("xpay-lang");
    if (saved === "bn" || saved === "en") setLang(saved);
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
    document.documentElement.lang = l === "bn" ? "bn" : "en";
  };

  const handleCorridorChange = (c: Corridor) => {
    setCorridor(c);
    setAmount(c.defaultAmount);
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
    setError(null);
    setResult(null);
    try {
      const state = await getQuote({
        amount: amountValue,
        recipient_name: recipient.trim() || undefined,
        payout_method: payoutMethod,
        deadline_hours: deadline ? Number(deadline) : undefined,
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
        payout_method: payoutMethod,
        selected_route_name: routeName,
        demo_scenario: scenario,
        quote_id: quote?.quote_id ?? undefined,
        confirmed: Boolean(quote?.quote_id),
      });
      setResult(state);
      if (state.error === "quote_expired" || state.error === "quote_already_used") {
        setError(
          lang === "bn"
            ? "কোটটির মেয়াদ শেষ — আবার রেট নিন।"
            : "That quote expired — please fetch a fresh rate."
        );
        setScreen("send");
        return;
      }
      if (state.decision === "CLEAR") setScreen("receipt");
      else if (state.decision === "BLOCKED") setError(t.blocked);
      else setScreen("review");
    } catch (e) {
      setError(e instanceof Error ? e.message : t.sendError);
    } finally {
      setBusy(false);
    }
  };

  if (screen === "quote" && quote) {
    return (
      <QuoteScreen
        quote={quote}
        corridor={corridor}
        lang={lang}
        onLang={switchLang}
        busy={busy}
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
        corridor={corridor}
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
    <Shell>
      <Topbar
        lang={lang}
        onLang={switchLang}
        corridor={corridor}
        onCorridor={handleCorridorChange}
        scenario={scenario}
        onScenario={setScenario}
      />

      <div className="mx-auto max-w-[1240px] px-5 py-8 sm:px-8 lg:px-12">
        <div className="grid gap-10 lg:grid-cols-[1.1fr_.9fr] items-start">
          {/* Left Column: Hero & Explanations */}
          <section className="space-y-6 pt-2 lg:pt-6">
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3.5 py-1.5 text-xs font-semibold text-emerald-400">
              <span className="h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399]" />
              Guaranteed Recipient Net Receive · No Hidden Spreads
            </div>

            <h1 className="text-4xl font-black tracking-tight text-white sm:text-6xl sm:leading-[1.08]">
              Send more home.
              <br />
              <span className="bg-gradient-to-r from-amber-400 via-amber-300 to-yellow-500 bg-clip-text text-transparent">
                See what arrives.
              </span>
            </h1>

            <p className="max-w-xl text-base leading-relaxed text-slate-300 sm:text-lg">
              xPay evaluates multi-rail corridors ({corridor.sourceCur} → {corridor.destCur}), automatically claims the{" "}
              <strong className="text-amber-400 font-semibold">2.5% Bangladesh Bank cash subsidy</strong>, and executes on the highest net payout.
            </p>

            {/* Quick Metrics */}
            <div className="grid max-w-xl grid-cols-3 gap-3">
              <Stat icon="spark" value="+2.5%" label="Govt. Incentive" highlight />
              <Stat icon="clock" value="~2 hr" label="Fastest Arrival" />
              <Stat icon="shield" value="100%" label="OFAC Screened" />
            </div>

            {/* Live AI Agent Pipeline Visualizer */}
            <div className="mt-8 pt-4">
              <AgentPipeline quote={quote} busy={busy} />
            </div>
          </section>

          {/* Right Column: Send Money Card */}
          <section>
            <SendCard
              corridor={corridor}
              amount={amount}
              setAmount={setAmount}
              recipient={recipient}
              setRecipient={setRecipient}
              transcript={transcript}
              setTranscript={setTranscript}
              busy={busy}
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
        <span>© 2026 xPay · International AI Builders Congress Demonstration</span>
        <span>Formal-channel remittance · Bangladesh Bank 2.5% incentive verified</span>
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
  corridor,
  amount,
  setAmount,
  recipient,
  setRecipient,
  transcript,
  setTranscript,
  busy,
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
}: any) {
  const quickPills = ["500", "1,000", "2,500", "5,000"];

  return (
    <div className="xpay-card xpay-fade-up overflow-hidden">
      <div className="border-b border-white/10 bg-[#0d1627] px-6 py-5 sm:px-8 flex items-center justify-between">
        <div>
          <p className="xpay-eyebrow">Instant Rate Check</p>
          <h2 className="mt-0.5 text-lg font-bold text-white">Compare Transfer Routes</h2>
        </div>
        <div className="flex items-center gap-1.5 rounded-full border border-white/15 bg-white/5 px-3 py-1 font-mono text-xs text-amber-300">
          <span>{corridor.sourceCur}</span>
          <span>→</span>
          <span>{corridor.destCur}</span>
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
              You Send
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
              {corridor.sourceCur}
            </span>
            <MicButton
              onTranscript={(text) => {
                setTranscript(text);
                const m = text.replace(/,/g, "").match(/(\d+(?:\.\d+)?)/);
                if (m) setAmount(m[1]);
              }}
              disabled={busy}
            />
          </div>

          {transcript && (
            <p className="mt-2 text-xs text-amber-300/80 font-mono flex items-center gap-1.5">
              <span>🎙️</span> Heard: “{transcript}”
            </p>
          )}
        </div>

        {/* Payout Method */}
        <div>
          <label htmlFor="payout-method" className="mb-2 block text-xs font-bold uppercase tracking-wider text-slate-300">
            Recipient Payout Channel
          </label>
          <div className="relative">
            <select
              id="payout-method"
              value={payoutMethod}
              onChange={(e) => setPayoutMethod(e.target.value)}
              className="w-full appearance-none rounded-xl border border-white/15 bg-[#0a101d] px-4 py-3 text-sm font-semibold text-white outline-none focus:border-amber-400"
            >
              {PAYOUT_OPTIONS.map((option) => (
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
            {t.deadlineLabel}
          </label>
          <div className="relative">
            <select
              id="deadline"
              value={deadline}
              onChange={(e) => setDeadline(e.target.value)}
              className="w-full appearance-none rounded-xl border border-white/15 bg-[#0a101d] px-4 py-3 text-sm font-semibold text-white outline-none focus:border-amber-400"
            >
              <option value="" className="bg-slate-900">{t.deadlineAny}</option>
              <option value="3" className="bg-slate-900">{t.deadline3h}</option>
              <option value="12" className="bg-slate-900">{t.deadline12h}</option>
              <option value="24" className="bg-slate-900">{t.deadline24h}</option>
            </select>
            <span className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-slate-400">
              ⌄
            </span>
          </div>
        </div>

        {/* Recipient Field */}
        <div>
          <label htmlFor="recipient" className="mb-2 block text-xs font-bold uppercase tracking-wider text-slate-300">
            Recipient (Optional handle or name)
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
              placeholder="e.g. Rokeya Begum or 017XXXXXXXX"
              className="min-w-0 flex-1 bg-transparent text-sm text-white outline-none placeholder:text-slate-500"
            />
          </div>
        </div>

        {error && (
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-3.5 text-xs font-medium text-red-300 flex items-center gap-2">
            <span>⚠️</span>
            <span>{error}</span>
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
              Evaluating Routes & Screening...
            </span>
          ) : (
            <>
              {t.getBestRate}
              <Icon name="arrow" size={16} />
            </>
          )}
        </button>

        <div className="flex items-center justify-between border-t border-white/10 pt-3 text-[11px] text-slate-400">
          <span className="flex items-center gap-1.5">
            <Icon name="shield" size={13} />
            OFAC sanctions checked
          </span>
          <span className="font-mono text-slate-400">
            {scenario !== "default" ? `Demo: ${scenario}` : "Deterministic quote"}
          </span>
        </div>
      </form>
    </div>
  );
}

function QuoteScreen({
  quote,
  corridor,
  lang,
  onLang,
  busy,
  error,
  onSend,
  onBack,
}: {
  quote: AgentStateResponse;
  corridor: Corridor;
  lang: Lang;
  onLang: (l: Lang) => void;
  busy: boolean;
  error: string | null;
  onSend: (route: string) => void;
  onBack: () => void;
}) {
  const t = STRINGS[lang];
  const bestPossible =
    [...quote.routes]
      .filter((r) => r.pricing_completeness === "complete" && r.breakdown.true_net_receive_bdt != null)
      .sort(
        (a, b) =>
          (b.breakdown.true_net_receive_bdt ?? 0) - (a.breakdown.true_net_receive_bdt ?? 0)
      )[0] ?? quote.routes[0];

  const [selectedName, setSelectedName] = useState(bestPossible.name);
  const selected = quote.routes.find((r) => r.name === selectedName) ?? bestPossible;
  const marketValue = (selected.breakdown.amount_source ?? 0) * selected.mid_market_rate;
  const netValue = selected.breakdown.true_net_receive_bdt ?? 0;
  const valueDifference = marketValue - netValue;

  return (
    <Shell>
      <header className="flex items-center justify-between border-b border-white/10 bg-[#080d16]/80 backdrop-blur-md px-5 py-4 sm:px-8 lg:px-12">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-xs font-bold text-amber-400 hover:text-amber-300 transition"
        >
          ← Change Transfer Parameters
        </button>
        <div className="flex items-center gap-3">
          <span className="text-xs font-mono text-slate-400">Quote ID: {quote.quote_id?.slice(0, 10)}…</span>
        </div>
      </header>

      <div className="mx-auto max-w-[1240px] px-5 py-8 sm:px-8 lg:px-12">
        {/* Hero Payout Announcement */}
        <div className="mb-8 rounded-3xl border border-white/10 bg-gradient-to-br from-[#0e172a] via-[#101b33] to-[#0a101d] p-6 sm:p-10 shadow-2xl flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <p className="xpay-eyebrow">Guaranteed Recipient Amount</p>
            <h1 className="xpay-mono mt-2 text-4xl sm:text-6xl font-black tracking-tight text-white">
              {fmtBDT(selected.breakdown.true_net_receive_bdt)}
            </h1>
            <p className="mt-3 flex items-center gap-2 text-sm font-semibold text-emerald-400">
              <Icon name="check" size={16} />
              Includes {fmtBDT(selected.breakdown.govt_incentive_added_bdt)} Bangladesh Bank 2.5% Cash Incentive
            </p>
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 text-xs space-y-2 shrink-0 md:min-w-[240px]">
            <div className="flex justify-between gap-4">
              <span className="text-slate-400">Corridor</span>
              <span className="font-semibold text-white">{corridor.name}</span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-slate-400">Decision Gate</span>
              <span className="font-bold text-emerald-400">{quote.decision}</span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-slate-400">Route Status</span>
              <span className="font-semibold text-amber-300">{selected.rail}</span>
            </div>
          </div>
        </div>

        {/* Route Cards & Inspector */}
        <div className="grid gap-8 lg:grid-cols-[1.1fr_.9fr]">
          <section className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="xpay-eyebrow">Ranked Payout Rails</p>
                <h2 className="text-xl font-bold text-white">Compare All Routes</h2>
              </div>
              <span className="text-xs font-mono text-slate-400">
                {quote.routes.length} options evaluated
              </span>
            </div>

            <div className="space-y-3">
              {quote.routes.map((route, index) => (
                <RouteCard
                  key={route.name}
                  route={route}
                  corridor={corridor}
                  selected={route.name === selected.name}
                  index={index}
                  onClick={() => setSelectedName(route.name)}
                />
              ))}
            </div>

            {/* AI Reasoning Log on Quote Screen */}
            <div className="mt-6">
              <AgentPipeline quote={quote} busy={busy} />
            </div>
          </section>

          <aside className="space-y-5">
            <div className="xpay-card p-6">
              <p className="xpay-eyebrow">Route Economics Breakdown</p>
              <h3 className="mt-1 text-lg font-bold text-white flex items-center gap-2">
                <span>{selected.rail}</span>
                {selected.is_best && (
                  <span className="text-[10px] font-bold uppercase tracking-wider bg-amber-400/20 text-amber-300 border border-amber-400/30 px-2 py-0.5 rounded-full">
                    Best Value
                  </span>
                )}
              </h3>

              <div className="mt-4 space-y-2 border-t border-white/10 pt-4 text-xs">
                <CompareRow label="Amount Sent" value={fmtCurrency(selected.breakdown.amount_source, corridor.sourceCur)} />
                <CompareRow label="Applied FX Rate" value={`1 ${corridor.sourceCur} = ${selected.fx_rate.toFixed(2)} BDT`} />
                <CompareRow label="Mid-market Rate" value={`1 ${corridor.sourceCur} = ${selected.mid_market_rate.toFixed(2)} BDT`} />
                <CompareRow label="Total Route Fee" value={fmtCurrency(selected.fee_total_source, corridor.sourceCur)} />
                {(selected.platform_fee_source ?? 0) > 0 && (
                  <CompareRow label="— of which xPay fee" value={fmtCurrency(selected.platform_fee_source, corridor.sourceCur)} />
                )}
                <CompareRow label="Estimated Arrival" value={`~${selected.settlement_time_hrs} hours`} />
                
                <div className="my-2 border-t border-dashed border-white/15 pt-2">
                  <CompareRow label="Mid-market Benchmark" value={fmtBDT(marketValue)} />
                  <CompareRow label="Net Delivered" value={fmtBDT(netValue)} />
                  <CompareRow
                    label="Variance from Mid-market"
                    value={`${valueDifference >= 0 ? "−" : "+"}${fmtBDT(Math.abs(valueDifference))}`}
                  />
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-5">
              <div className="flex gap-3">
                <div className="text-emerald-400 mt-0.5">
                  <Icon name="shield" size={20} />
                </div>
                <div>
                  <p className="font-bold text-emerald-300 text-sm">Pre-Screening Cleared</p>
                  <p className="mt-1 text-xs leading-relaxed text-emerald-200/80">
                    Sanctions verification and predictive AML checks passed. Executing binds this exact quote with no slippage.
                  </p>
                </div>
              </div>
            </div>

            {error && <p className="rounded-xl bg-red-500/20 border border-red-500/30 p-3 text-xs text-red-300">{error}</p>}

            <button
              onClick={() => onSend(selected.name)}
              disabled={busy}
              className="flex h-14 w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-amber-400 to-amber-500 text-base font-black text-slate-950 transition hover:from-amber-300 hover:to-amber-400 disabled:opacity-50 shadow-[0_0_30px_rgba(245,158,11,0.35)]"
            >
              {busy ? t.sending : `Confirm & Send with ${selected.rail}`}
              <Icon name="arrow" size={18} />
            </button>

            <p className="text-center text-[11px] text-slate-400">
              Deterministic quote locked. No rate fluctuation allowed during execution.
            </p>
          </aside>
        </div>
      </div>
    </Shell>
  );
}

function RouteCard({
  route,
  corridor,
  selected,
  index,
  onClick,
}: {
  route: RouteOption;
  corridor: Corridor;
  selected: boolean;
  index: number;
  onClick: () => void;
}) {
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
                    Recommended
                  </span>
                )}
              </div>
              <p className="mt-0.5 text-xs text-slate-400">
                {route.payout_method} · {route.incentive_eligible ? "2.5% Cash Subsidy" : "No subsidy"}
              </p>
            </div>

            <p className="xpay-mono text-xl font-black text-amber-400">
              {fmtBDT(route.breakdown.true_net_receive_bdt)}
            </p>
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-slate-300 font-medium">
            <span className="flex items-center gap-1.5 text-slate-400">
              <Icon name="clock" size={13} /> ~{route.settlement_time_hrs}h
            </span>
            <span className="text-slate-400">
              Fee: {fmtCurrency(route.fee_total_source, corridor.sourceCur)}
            </span>
            <span className={route.incentive_eligible ? "text-emerald-400 font-semibold" : "text-slate-500"}>
              {route.incentive_eligible ? "✓ 2.5% Bonus Eligible" : "— Non-eligible Rail"}
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
    <Shell>
      <header className="border-b border-white/10 px-5 py-4 sm:px-8">
        <span className="text-xs font-bold uppercase tracking-wider text-amber-400">Compliance Hold</span>
      </header>
      <div className="mx-auto max-w-[620px] px-5 py-20 text-center sm:px-8">
        <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-3xl border border-amber-400/40 bg-amber-500/10 text-amber-400 shadow-[0_0_30px_rgba(245,158,11,0.2)]">
          <Icon name="shield" size={38} />
        </div>
        <p className="xpay-eyebrow mt-8">{t.inReview}</p>
        <h1 className="mt-2 text-4xl font-black tracking-tight text-white">Transfer Paused for Review</h1>
        <p className="mx-auto mt-4 max-w-md text-base leading-relaxed text-slate-300">
          {t.reviewSentence}
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
  corridor,
  lang,
  onLang,
  arrivalHours,
  onRestart,
}: {
  result: AgentStateResponse;
  corridor: Corridor;
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
    <Shell>
      <header className="border-b border-white/10 px-5 py-4 sm:px-8">
        <span className="text-xs font-bold uppercase tracking-wider text-emerald-400">Transfer Executed</span>
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
            <p className="text-xs text-slate-400">Your recipient receives</p>
            <p className="xpay-mono mt-1 text-4xl sm:text-5xl font-black text-amber-400">
              {fmtBDT(tx.true_net_receive_bdt)}
            </p>
            <p className="mt-2 text-sm text-slate-300">
              Arriving in ~{arrivalHours ?? 2} hours via {tx.route_selected}
            </p>
          </div>

          <div className="p-6 sm:p-9 space-y-6">
            <div className="grid gap-x-10 gap-y-2 sm:grid-cols-2">
              <Row label={t.amountRow} value={fmtCurrency(tx.amount_source, corridor.sourceCur)} />
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
                  }}
                />
              </div>
            )}

            <details className="mt-4 rounded-xl border border-white/10 bg-white/[0.02] p-4">
              <summary className="cursor-pointer text-xs font-bold text-slate-300 hover:text-white">
                {t.technicalDetails} (ISO 20022 Payload)
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
