import type { AgentStateResponse, DemoScenario } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "";

async function post<T>(path: string, body: unknown, onSlow?: () => void): Promise<T> {
  // Free-tier cold starts can take well over 5s; onSlow lets the UI show a
  // "waking up" state while the request is still in flight.
  let slowTimer: ReturnType<typeof setTimeout> | undefined;
  if (onSlow) slowTimer = setTimeout(onSlow, 5000);
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    if (slowTimer) clearTimeout(slowTimer);
    // fetch only throws on network-level failure (server down/asleep/DNS)
    throw new Error("API_UNREACHABLE");
  }
  if (slowTimer) clearTimeout(slowTimer);
  if (!res.ok) {
    let detail: string | null = null;
    try {
      const err = await res.json();
      detail = err.detail ?? null;
    } catch {
      /* no JSON body */
    }
    if (detail) throw new Error(detail);
    // A 5xx with no error detail means the backend itself was not reached
    // (local proxy ECONNREFUSED, gateway 502/503, or an unhandled crash) —
    // surface the friendly "server may be asleep" message, not "Internal Server Error".
    if (res.status >= 500) throw new Error("API_UNREACHABLE");
    throw new Error(res.statusText);
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

export function getQuote(params: QuoteParams, onSlow?: () => void): Promise<AgentStateResponse> {
  return post<AgentStateResponse>("/api/agent/quote", params, onSlow);
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

export function executeTransfer(params: ExecuteParams, onSlow?: () => void): Promise<AgentStateResponse> {
  return post<AgentStateResponse>("/api/agent/execute", params, onSlow);
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

export const fmtCurrency = (v: number | null | undefined, cur = "AED") =>
  v == null
    ? "—"
    : `${cur} ${v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
