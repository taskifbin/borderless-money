"use client";

/**
 * B2B ROI Calculator — for remittance operators evaluating the xPay
 * routing API. Pure client-side; mirrors backend/app/services/roi.py
 * (which has hand-computed test coverage). Every output is a MODELED ESTIMATE
 * from the user's assumptions — nothing here is measured. Recipient benefit is
 * shown separately and is NEVER counted as vendor revenue.
 */
import { useMemo, useState } from "react";

type ScenarioKey = "conservative" | "base" | "optimistic";

interface Inputs {
  monthlyTransfers: number;
  avgPrincipal: number;
  baselinePct: number; // customer's current all-in cost, % of principal
  proposedPct: number; // all-in cost via recommended routes, % of principal
  eligibilityShare: number; // fraction of transfers where a recommended route is eligible
  adoptionRate: number; // fraction of eligible transfers actually routed via API
  apiPricePerTx: number;
  apiMonthlyFee: number;
  bearingShare: number; // share of the all-in cost the operator itself bears
  customerMonthlyCosts: number; // operator's integration/ops cost per month
  vendorVariableCostPerTx: number | null; // vendor's infra cost per tx (for margin)
}

const DEFAULTS: Inputs = {
  monthlyTransfers: 5000,
  avgPrincipal: 1000,
  baselinePct: 1.5,
  proposedPct: 0.9,
  eligibilityShare: 0.8,
  adoptionRate: 0.5,
  apiPricePerTx: 1.0,
  apiMonthlyFee: 0,
  bearingShare: 1.0,
  customerMonthlyCosts: 500,
  vendorVariableCostPerTx: 0.25,
};

const SCENARIOS: Record<ScenarioKey, { adoptMult: number; eligMult: number }> = {
  conservative: { adoptMult: 0.5, eligMult: 0.8 },
  base: { adoptMult: 1, eligMult: 1 },
  optimistic: { adoptMult: 1.5, eligMult: 1.0 },
};

const round2 = (x: number) => Math.round(x * 100) / 100;
const ceil = (x: number) => Math.ceil(round2(x));

function compute(i: Inputs, key: ScenarioKey) {
  const { adoptMult, eligMult } = SCENARIOS[key];
  const eligibility = Math.min(i.eligibilityShare * eligMult, 1);
  const adoption = Math.min(i.adoptionRate * adoptMult, 1);
  const eligible = round2(i.monthlyTransfers * eligibility);
  const adopted = round2(eligible * adoption);
  const principalMoved = round2(adopted * i.avgPrincipal);
  const gapPct = (i.baselinePct - i.proposedPct) / 100;
  const recipientBenefit = round2(principalMoved * gapPct);
  const customerSavings = round2(recipientBenefit * i.bearingShare);
  const apiRevenue = round2(adopted * i.apiPricePerTx + i.apiMonthlyFee);
  const customerNet = round2(customerSavings - apiRevenue - i.customerMonthlyCosts);
  const costPerTx = adopted > 0 ? round2(apiRevenue / adopted) : null;
  const marginPct =
    i.vendorVariableCostPerTx != null && apiRevenue > 0
      ? round2(((apiRevenue - adopted * i.vendorVariableCostPerTx) / apiRevenue) * 100)
      : null;
  const savingPerAdopted = round2(i.avgPrincipal * gapPct * i.bearingShare - i.apiPricePerTx);
  const fixedDrag = i.apiMonthlyFee + i.customerMonthlyCosts;
  let breakeven: number | null;
  let breakevenNote: string;
  if (fixedDrag === 0) {
    breakeven = 0;
    breakevenNote = "no fixed costs or fees to recover";
  } else if (savingPerAdopted <= 0 || eligibility === 0 || adoption === 0) {
    breakeven = null;
    breakevenNote = "per-transfer saving does not exceed the per-transfer price (or zero eligibility/adoption)";
  } else {
    breakeven = ceil(fixedDrag / (eligibility * adoption * savingPerAdopted));
    breakevenNote = "monthly transfers needed for the switch to pay off";
  }
  return {
    eligible, adopted, principalMoved, recipientBenefit, customerSavings,
    apiRevenue, customerNet, costPerTx, marginPct, breakeven, breakevenNote,
  };
}

const fmt = (x: number | null, cur = "AED") =>
  x == null ? "—" : `${cur ? cur + " " : ""}${x.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

function Field(props: { label: string; hint: string; value: number; onChange: (v: number) => void; step?: number; min?: number; max?: number; suffix?: string }) {
  return (
    <label className="block">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-semibold text-slate-300">{props.label}</span>
        <span className="text-[10px] text-slate-500 font-mono">{props.hint}</span>
      </div>
      <div className="relative flex items-center">
        <input
          type="number"
          className="w-full rounded-xl border border-white/10 bg-[#070b13] px-3 py-2 text-xs text-white focus:border-amber-400 focus:outline-none"
          value={props.value}
          step={props.step ?? 1}
          min={props.min ?? 0}
          max={props.max}
          onChange={(e) => props.onChange(Number(e.target.value))}
        />
        {props.suffix && (
          <span className="absolute right-3 text-xs text-slate-500 font-mono pointer-events-none">
            {props.suffix}
          </span>
        )}
      </div>
    </label>
  );
}

export default function RoiPage() {
  const [i, setI] = useState<Inputs>(DEFAULTS);
  const [active, setActive] = useState<ScenarioKey>("base");
  const r = useMemo(() => compute(i, active), [i, active]);
  const set = (k: keyof Inputs) => (v: number) => setI((p) => ({ ...p, [k]: v }));

  return (
    <div className="xpay-shell min-h-screen text-slate-100">
      <header className="border-b border-white/10 bg-[#080d16]/80 backdrop-blur-md px-5 py-4 sm:px-8 lg:px-12 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <a href="/" className="flex h-9 w-9 items-center justify-center rounded-xl bg-amber-500 text-slate-950 font-black text-lg">
            ↗
          </a>
          <div>
            <span className="text-sm font-bold text-white">xPay B2B Suite</span>
            <span className="ml-2 text-xs text-slate-400">Enterprise Remittance Intelligence</span>
          </div>
        </div>

        <a
          href="/"
          className="flex items-center gap-2 rounded-xl border border-white/15 bg-white/5 px-3 py-1.5 text-xs font-semibold text-white hover:bg-white/10 transition"
        >
          ← Return to Send Money
        </a>
      </header>

      <main className="mx-auto max-w-6xl px-5 py-8 sm:px-8">
        <div className="mb-8">
          <div className="inline-flex items-center gap-2 rounded-full border border-amber-400/30 bg-amber-500/10 px-3 py-1 text-xs font-semibold text-amber-300 mb-3">
            Operator Economics Model
          </div>
          <h1 className="text-3xl sm:text-4xl font-black text-white">B2B Remittance ROI Simulator</h1>
          <p className="mt-2 text-sm text-slate-400 max-w-2xl leading-relaxed">
            Evaluate unit economics, route savings, and gross margin for fintechs and banks routing cross-border payments via the xPay intelligent orchestrator.
          </p>
        </div>

        {/* Scenario Toggle */}
        <div className="mb-6 flex flex-wrap items-center gap-2 rounded-2xl border border-white/10 bg-[#0d1627]/80 p-2">
          <span className="px-3 text-xs font-bold uppercase tracking-wider text-slate-400">
            Adoption Scenario:
          </span>
          {(Object.keys(SCENARIOS) as ScenarioKey[]).map((k) => (
            <button
              key={k}
              onClick={() => setActive(k)}
              className={`rounded-xl px-4 py-1.5 text-xs font-bold uppercase tracking-wide transition ${
                active === k
                  ? "bg-amber-400 text-slate-950 shadow-[0_0_15px_rgba(245,158,11,0.3)]"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              {k}
            </button>
          ))}
          <span className="text-xs text-slate-500 ml-auto pr-3 hidden md:inline">
            Scales adoption ×{SCENARIOS[active].adoptMult} and eligibility ×{SCENARIOS[active].eligMult}
          </span>
        </div>

        <div className="grid gap-8 md:grid-cols-2">
          {/* Inputs Section */}
          <section className="xpay-card p-6">
            <div className="border-b border-white/10 pb-3 mb-5">
              <h2 className="text-base font-bold text-white">Operator Assumptions</h2>
              <p className="text-xs text-slate-400">Customizable volume, cost basis, and pricing levers</p>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <Field label="Monthly transfers" hint="count" value={i.monthlyTransfers} onChange={set("monthlyTransfers")} min={1} />
              <Field label="Avg principal" hint="per transfer" value={i.avgPrincipal} onChange={set("avgPrincipal")} step={50} suffix="AED" />
              <Field label="Baseline all-in cost" hint="fees + spread today" value={i.baselinePct} onChange={set("baselinePct")} step={0.1} suffix="%" />
              <Field label="Proposed all-in cost" hint="via optimal rails" value={i.proposedPct} onChange={set("proposedPct")} step={0.1} suffix="%" />
              <Field label="Route eligibility share" hint="0–1" value={i.eligibilityShare} onChange={set("eligibilityShare")} step={0.05} max={1} />
              <Field label="Adoption rate" hint="0–1" value={i.adoptionRate} onChange={set("adoptionRate")} step={0.05} max={1} />
              <Field label="API price / transfer" hint="usage pricing" value={i.apiPricePerTx} onChange={set("apiPricePerTx")} step={0.1} suffix="AED" />
              <Field label="API monthly fee" hint="0 = usage only" value={i.apiMonthlyFee} onChange={set("apiMonthlyFee")} step={50} suffix="AED" />
              <Field label="Cost bearing share" hint="fraction operator pays" value={i.bearingShare} onChange={set("bearingShare")} step={0.1} max={1} />
              <Field label="Your monthly costs" hint="infra & ops" value={i.customerMonthlyCosts} onChange={set("customerMonthlyCosts")} step={50} suffix="AED" />
              <Field label="Vendor unit cost" hint="per tx infra" value={i.vendorVariableCostPerTx ?? 0} onChange={(v) => setI((p) => ({ ...p, vendorVariableCostPerTx: v }))} step={0.05} suffix="AED" />
            </div>
          </section>

          {/* Outcomes Section */}
          <section className="xpay-card p-6 flex flex-col justify-between">
            <div>
              <div className="border-b border-white/10 pb-3 mb-5 flex items-center justify-between">
                <div>
                  <h2 className="text-base font-bold text-white">Modeled Economics ({active})</h2>
                  <p className="text-xs text-slate-400">Monthly pro-forma financials & savings</p>
                </div>
                {r.marginPct != null && (
                  <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs font-mono font-bold text-emerald-400">
                    {r.marginPct}% Margin
                  </span>
                )}
              </div>

              <dl className="space-y-3 text-xs">
                {[
                  ["Eligible Monthly Transfers", fmt(r.eligible, "")],
                  ["Adopted via xPay Routing", fmt(r.adopted, "")],
                  ["Total Principal Routed", fmt(r.principalMoved)],
                  ["Gross Recipient Benefit", fmt(r.recipientBenefit)],
                  ["Operator Cost Savings", fmt(r.customerSavings)],
                  ["API Revenue Generated", fmt(r.apiRevenue)],
                  ["Operator Net Benefit", fmt(r.customerNet)],
                  ["API Effective Cost / Tx", fmt(r.costPerTx)],
                  ["Break-even Volume", r.breakeven == null ? "—" : `${r.breakeven.toLocaleString()} transfers / mo`],
                ].map(([k, v]) => (
                  <div key={k} className="flex items-center justify-between gap-4 border-b border-dashed border-white/10 pb-2">
                    <dt className="text-slate-400">{k}</dt>
                    <dd className="font-mono font-bold text-white">{v}</dd>
                  </div>
                ))}
              </dl>
              <p className="mt-3 text-[11px] text-slate-400 italic">{r.breakevenNote}.</p>
            </div>

            <div className="mt-6 rounded-xl border border-amber-500/20 bg-amber-500/[0.06] p-3.5 text-xs text-amber-200/90 leading-relaxed">
              <strong className="text-amber-300 font-semibold">Financial Honesty Note:</strong> All values are modeled projections based on user-supplied parameters. Recipient benefit represents funds retained by overseas families and is not treated as software platform revenue.
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
