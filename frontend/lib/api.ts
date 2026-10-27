import type { AgentStateResponse, DemoScenario } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "";

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const err = await res.json();
      detail = err.detail ?? detail;
    } catch {
      /* keep statusText */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export interface QuoteParams {
  text?: string;
  amount?: number;
  payout_method?: string;
  recipient_name?: string;
  deadline_hours?: number;
  demo_scenario?: DemoScenario;
}

export function getQuote(params: QuoteParams): Promise<AgentStateResponse> {
  return post<AgentStateResponse>("/api/agent/quote", params);
}

export interface ExecuteParams extends QuoteParams {
  selected_route_name?: string;
  /** Bind execution to the quote the user confirmed (from the quote response). */
  quote_id?: string;
  /** Must be true when quote_id is supplied — the explicit confirmation gate. */
  confirmed?: boolean;
  /** Demo hook: inject an uncertain settlement outcome (reconciliation path). */
  settlement_outcome?: "COMPLETED" | "TIMEOUT" | "FAILED";
}

export function executeTransfer(params: ExecuteParams): Promise<AgentStateResponse> {
  return post<AgentStateResponse>("/api/agent/execute", params);
}

/** Fetch a persisted quote with its live expiry status. */
export function getQuoteById(quoteId: string): Promise<Record<string, unknown>> {
  return fetch(`${API_BASE}/api/quotes/${encodeURIComponent(quoteId)}`).then(res => {
    if (!res.ok) throw new Error(res.statusText);
    return res.json() as Promise<Record<string, unknown>>;
  });
}

export const fmtBDT = (v: number | null | undefined) =>
  v == null
    ? "—"
    : `৳${v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export const fmtAED = (v: number | null | undefined) =>
  v == null
    ? "—"
    : `AED ${v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
