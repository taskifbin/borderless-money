"use client";

/**
 * B2B ROI Calculator — for remittance operators evaluating the Borderless
 * Money routing API. Pure client-side; mirrors backend/app/services/roi.py
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
  x == null ? "—" : `${cur} ${x.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

function Field(props: { label: string; hint: string; value: number; onChange: (v: number) => void; step?: number; min?: number; max?: number; suffix?: string }) {
  return (
    <label className="block">
      <span className="text-sm font-medium text-ink">{props.label}</span>
      <span className="ml-1 text-xs text-gray-500">{props.hint}</span>
      <span className="mt-1 flex items-center gap-2">
        <input
          type="number" className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm
                                    focus:border-emerald-500 focus:outline-none"
          value={props.value} step={props.step ?? 1} min={props.min ?? 0} max={props.max}
          onChange={(e) => props.onChange(Number(e.target.value))}
        />
        {props.suffix && <span className="text-xs text-gray-500">{props.suffix}</span>}
      </span>
    </label>
  );
}

export default function RoiPage() {
  const [i, setI] = useState<Inputs>(DEFAULTS);
  const [active, setActive] = useState<ScenarioKey>("base");
  const r = useMemo(() => compute(i, active), [i, active]);
  const set = (k: keyof Inputs) => (v: number) => setI((p) => ({ ...p, [k]: v }));

  return (
    <main className="mx-auto max-w-5xl px-4 py-10">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">B2B ROI Calculator</h1>
          <p className="text-sm text-gray-600">
            What a remittance operator gains by routing through Borderless Money.
            Same formulas as <code className="rounded bg-gray-100 px-1">backend/app/services/roi.py</code> (unit-tested).
          </p>
        </div>
        <a href="/" className="rounded-lg border border-gray-300 px-3 py-2 text-sm hover:bg-gray-50">
          ← Send money demo
        </a>
      </div>

      <div className="mb-4 flex gap-2">
        {(Object.keys(SCENARIOS) as ScenarioKey[]).map((k) => (
          <button key={k} onClick={() => setActive(k)}
            className={`rounded-full px-4 py-1.5 text-sm font-medium ${active === k ? "bg-emerald-600 text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"}`}>
            {k}
          </button>
        ))}
        <span className="self-center text-xs text-gray-500">
          scenarios scale adoption ×{SCENARIOS[active].adoptMult} and eligibility ×{SCENARIOS[active].eligMult} — modeled, not measured
        </span>
      </div>

      <div className="grid gap-8 md:grid-cols-2">
        <section className="rounded-2xl border border-gray-200 p-5">
          <h2 className="mb-4 font-semibold">Your assumptions <span className="text-xs font-normal text-gray-500">(user inputs — replace pilot data when you have it)</span></h2>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Monthly transfers" hint="count" value={i.monthlyTransfers} onChange={set("monthlyTransfers")} min={1} />
            <Field label="Avg principal" hint="per transfer" value={i.avgPrincipal} onChange={set("avgPrincipal")} step={50} suffix="AED" />
            <Field label="Baseline all-in cost" hint="fees + FX spread today" value={i.baselinePct} onChange={set("baselinePct")} step={0.1} suffix="%" />
            <Field label="Proposed all-in cost" hint="via recommended routes" value={i.proposedPct} onChange={set("proposedPct")} step={0.1} suffix="%" />
            <Field label="Route eligibility share" hint="0–1" value={i.eligibilityShare} onChange={set("eligibilityShare")} step={0.05} max={1} />
            <Field label="Adoption rate" hint="0–1" value={i.adoptionRate} onChange={set("adoptionRate")} step={0.05} max={1} />
            <Field label="API price / transfer" hint="usage pricing" value={i.apiPricePerTx} onChange={set("apiPricePerTx")} step={0.1} suffix="AED" />
            <Field label="API monthly fee" hint="0 = usage-only" value={i.apiMonthlyFee} onChange={set("apiMonthlyFee")} step={50} suffix="AED" />
            <Field label="Cost bearing share" hint="how much of the all-in cost you bear" value={i.bearingShare} onChange={set("bearingShare")} step={0.1} max={1} />
            <Field label="Your monthly costs" hint="integration + ops" value={i.customerMonthlyCosts} onChange={set("customerMonthlyCosts")} step={50} suffix="AED" />
            <Field label="Vendor variable cost / tx" hint="enables margin line" value={i.vendorVariableCostPerTx ?? 0} onChange={(v) => setI((p) => ({ ...p, vendorVariableCostPerTx: v }))} step={0.05} suffix="AED" />
          </div>
        </section>

        <section className="rounded-2xl border border-gray-200 p-5">
          <h2 className="mb-4 font-semibold">Modeled outcome — {active} <span className="text-xs font-normal text-gray-500">(derived estimates, monthly)</span></h2>
          <dl className="space-y-2 text-sm">
            {[
              ["Eligible transfers", fmt(r.eligible, "")],
              ["Adopted transfers", fmt(r.adopted, "")],
              ["Principal routed", fmt(r.principalMoved)],
              ["Gross recipient benefit", fmt(r.recipientBenefit)],
              ["Your cost savings", fmt(r.customerSavings)],
              ["API revenue (vendor)", fmt(r.apiRevenue)],
              ["Your net benefit", fmt(r.customerNet)],
              ["API cost per transaction", fmt(r.costPerTx)],
              ["Vendor gross margin", r.marginPct == null ? "—" : `${r.marginPct}%`],
              ["Break-even volume", r.breakeven == null ? "—" : `${r.breakeven.toLocaleString()} transfers / month`],
            ].map(([k, v]) => (
              <div key={k} className="flex items-baseline justify-between gap-4 border-b border-dashed border-gray-100 pb-1.5">
                <dt className="text-gray-600">{k}</dt>
                <dd className="font-semibold">{v}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-3 text-xs text-gray-500">{r.breakevenNote}.</p>
          <p className="mt-4 rounded-lg bg-amber-50 p-3 text-xs text-amber-800">
            <strong>Honesty note:</strong> every number above is a modeled estimate from
            your assumptions — none are measured. Recipient benefit is money that stays
            with recipients and is never counted as vendor revenue. Margin appears only
            because you supplied a cost input; without it the honest answer is “unknown”.
          </p>
        </section>
      </div>
    </main>
  );
}
