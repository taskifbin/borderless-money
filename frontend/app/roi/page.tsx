"use client";

/**
 * B2B ROI Calculator — for remittance operators evaluating the xPay
 * routing API. Pure client-side; mirrors backend/app/services/roi.py
 * (which has hand-computed test coverage). Every output is a MODELED ESTIMATE
 * from the user's assumptions — nothing here is measured. Recipient benefit is
 * shown separately and is NEVER counted as vendor revenue.
 */
import { useEffect, useMemo, useState } from "react";
import { STRINGS, applyDocLang, savedLang } from "@/lib/i18n";

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
    breakevenNote = "none";
  } else if (savingPerAdopted <= 0 || eligibility === 0 || adoption === 0) {
    breakeven = null;
    breakevenNote = "negative";
  } else {
    breakeven = ceil(fixedDrag / (eligibility * adoption * savingPerAdopted));
    breakevenNote = "payoff";
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
  const [lang, setLang] = useState<"en" | "bn">("en");
  const [i, setI] = useState<Inputs>(DEFAULTS);
  const [active, setActive] = useState<ScenarioKey>("base");
  const r = useMemo(() => compute(i, active), [i, active]);
  const set = (k: keyof Inputs) => (v: number) => setI((p) => ({ ...p, [k]: v }));
  const t = STRINGS[lang];
  useEffect(() => { const l = savedLang(); setLang(l); applyDocLang(l); }, []);
  const breakevenNoteText =
    r.breakevenNote === "none" ? t.roi.breakevenNone
    : r.breakevenNote === "negative" ? t.roi.breakevenNegative
    : t.roi.breakevenPayoff;

  return (
    <main className="mx-auto max-w-5xl px-4 py-10">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{t.roi.title}</h1>
          <p className="text-sm text-gray-600">
            {t.roi.lead}
            {" "}{t.roi.formulasPrefix} <code className="rounded bg-gray-100 px-1">backend/app/services/roi.py</code> {t.roi.formulasSuffix}
          </p>
        </div>
        <a href="/" className="rounded-lg border border-gray-300 px-3 py-2 text-sm hover:bg-gray-50">
          {t.roi.backToDemo}
        </a>
      </div>

      <div className="mb-4 flex gap-2">
        {(Object.keys(SCENARIOS) as ScenarioKey[]).map((k) => (
          <button key={k} onClick={() => setActive(k)}
            className={`rounded-full px-4 py-1.5 text-sm font-medium ${active === k ? "bg-emerald-600 text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"}`}>
            {t.roi.scenarios[k]}
          </button>
        ))}
        <span className="self-center text-xs text-gray-500">
          {t.roi.scenarioNote(SCENARIOS[active].adoptMult, SCENARIOS[active].eligMult)}
        </span>
      </div>

      <div className="grid gap-8 md:grid-cols-2">
        <section className="rounded-2xl border border-gray-200 p-5">
          <h2 className="mb-4 font-semibold">{t.roi.yourAssumptions} <span className="text-xs font-normal text-gray-500">{t.roi.assumptionsNote}</span></h2>
          <div className="grid grid-cols-2 gap-4">
            <Field label={t.roi.fields.monthlyTransfers.label} hint={t.roi.fields.monthlyTransfers.hint} value={i.monthlyTransfers} onChange={set("monthlyTransfers")} min={1} />
            <Field label={t.roi.fields.avgPrincipal.label} hint={t.roi.fields.avgPrincipal.hint} value={i.avgPrincipal} onChange={set("avgPrincipal")} step={50} suffix="AED" />
            <Field label={t.roi.fields.baselineCost.label} hint={t.roi.fields.baselineCost.hint} value={i.baselinePct} onChange={set("baselinePct")} step={0.1} suffix="%" />
            <Field label={t.roi.fields.proposedCost.label} hint={t.roi.fields.proposedCost.hint} value={i.proposedPct} onChange={set("proposedPct")} step={0.1} suffix="%" />
            <Field label={t.roi.fields.eligibilityShare.label} hint={t.roi.fields.eligibilityShare.hint} value={i.eligibilityShare} onChange={set("eligibilityShare")} step={0.05} max={1} />
            <Field label={t.roi.fields.adoptionRate.label} hint={t.roi.fields.adoptionRate.hint} value={i.adoptionRate} onChange={set("adoptionRate")} step={0.05} max={1} />
            <Field label={t.roi.fields.apiPrice.label} hint={t.roi.fields.apiPrice.hint} value={i.apiPricePerTx} onChange={set("apiPricePerTx")} step={0.1} suffix="AED" />
            <Field label={t.roi.fields.apiMonthlyFee.label} hint={t.roi.fields.apiMonthlyFee.hint} value={i.apiMonthlyFee} onChange={set("apiMonthlyFee")} step={50} suffix="AED" />
            <Field label={t.roi.fields.bearingShare.label} hint={t.roi.fields.bearingShare.hint} value={i.bearingShare} onChange={set("bearingShare")} step={0.1} max={1} />
            <Field label={t.roi.fields.monthlyCosts.label} hint={t.roi.fields.monthlyCosts.hint} value={i.customerMonthlyCosts} onChange={set("customerMonthlyCosts")} step={50} suffix="AED" />
            <Field label={t.roi.fields.vendorCost.label} hint={t.roi.fields.vendorCost.hint} value={i.vendorVariableCostPerTx ?? 0} onChange={(v) => setI((p) => ({ ...p, vendorVariableCostPerTx: v }))} step={0.05} suffix="AED" />
          </div>
        </section>

        <section className="rounded-2xl border border-gray-200 p-5">
          <h2 className="mb-4 font-semibold">{t.roi.outcomeTitle(t.roi.scenarios[active])} <span className="text-xs font-normal text-gray-500">{t.roi.outcomeNote}</span></h2>
          <dl className="space-y-2 text-sm">
            {[
              [t.roi.rows.eligibleTransfers, fmt(r.eligible, "")],
              [t.roi.rows.adoptedTransfers, fmt(r.adopted, "")],
              [t.roi.rows.principalRouted, fmt(r.principalMoved)],
              [t.roi.rows.recipientBenefit, fmt(r.recipientBenefit)],
              [t.roi.rows.costSavings, fmt(r.customerSavings)],
              [t.roi.rows.apiRevenue, fmt(r.apiRevenue)],
              [t.roi.rows.netBenefit, fmt(r.customerNet)],
              [t.roi.rows.costPerTx, fmt(r.costPerTx)],
              [t.roi.rows.vendorMargin, r.marginPct == null ? "—" : `${r.marginPct}%`],
              [t.roi.rows.breakevenVolume, r.breakeven == null ? "—" : t.roi.transfersPerMonth(r.breakeven)],
            ].map(([k, v]) => (
              <div key={k} className="flex items-baseline justify-between gap-4 border-b border-dashed border-gray-100 pb-1.5">
                <dt className="text-gray-600">{k}</dt>
                <dd className="font-semibold">{v}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-3 text-xs text-gray-500">{breakevenNoteText}.</p>
          <p className="mt-4 rounded-lg bg-amber-50 p-3 text-xs text-amber-800">
            <strong>{t.roi.honestyTitle}</strong> {t.roi.honestyBody}
          </p>
        </section>
      </div>
    </main>
  );
}
