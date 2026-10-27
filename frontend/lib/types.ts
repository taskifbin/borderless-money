export interface ParsedIntent {
  raw_text: string;
  amount: number | null;
  source_currency: string;
  dest_currency: string;
  recipient: string | null;
  payout_method: string | null;
  corridor: string;
  language_detected: string;
  confidence: number;
  defaults_applied: string[];
}

export interface Breakdown {
  amount_source: number;
  currency_source: string;
  fx_rate: number;
  fee_source: number | null;
  platform_fee_source?: number | null;
  gross_bdt: number | null;
  fees_deducted_bdt: number | null;
  govt_incentive_rate: number;
  govt_incentive_added_bdt: number | null;
  true_net_receive_bdt: number | null;
  route: string;
  settlement_time_hrs?: number;
  // exact decimal strings from the money engine (authoritative values)
  true_net_receive_exact?: string;
  gross_exact?: string;
  platform_fee_exact?: string;
  pricing_completeness?: "complete" | "incomplete";
  missing_fields?: string[];
}

export interface RouteOption {
  name: string;
  rail: string;
  payout_method: string;
  fx_rate: number;
  mid_market_rate: number;
  spread_per_source_unit: number;
  fee_total_source: number | null;
  platform_fee_source?: number | null;
  fee_source_components?: {
    rail_fee_source: number | null;
    last_mile_fee_source: number;
    platform_fee_source: number;
  };
  settlement_time_hrs: number;
  success_rate: number;
  is_best: boolean;
  advantage_bdt_vs_best: number | null;
  incentive_eligible: boolean;
  expected_value_bdt: number | null;
  pricing_completeness: "complete" | "incomplete";
  eligibility: { eligible: boolean; reason: string | null; note: string | null };
  breakdown: Breakdown;
}

export interface RiskAssessment {
  gnn_risk_score: number;
  risk_band: "LOW" | "MEDIUM" | "HIGH";
  graph_nodes_evaluated: string[];
  requires_manual_review: boolean;
  engine: string;
  ai_explanation: string;
  checked_at: string;
}

export interface ScreenedParty {
  role: string;
  name: string;
  status: "CLEAR" | "FUZZY_MATCH_REVIEW" | "BLOCKED";
  best_match: { name: string; similarity: number } | null;
}

export interface ComplianceResult {
  ofac_match_status: ScreenedParty["status"];
  screened_parties: ScreenedParty[];
}

export interface ExecutionResult {
  status: string;
  stellar_hash: string;
  network: "TESTNET" | "SIMULATED";
  simulated: boolean;
  memo: string;
  explorer_url?: string | null;
  fallback_reason?: string;
}

export interface TransactionRecord {
  transaction_id: string;
  sender_id: string;
  sender_name: string;
  recipient_name: string;
  recipient_handle: string;
  amount_source: number;
  currency_source: string;
  fx_rate_applied: number | null;
  fee_deducted_aed?: number | null;
  fee_deducted_source?: number | null;
  govt_incentive_2_5_pct: number | null;
  true_net_receive_bdt: number | null;
  route_selected: string | null;
  quote_id?: string | null;
  quote_binding?: "bound" | "fresh_unbound_demo" | null;
  stellar_hash: string | null;
  status: string;
  created_at: string;
  breakdown: Breakdown;
  iso_20022?: Record<string, unknown>;
  hold_reason?: string;
  reconciliation_required?: boolean;
  execution_status?: string;
}

export type Decision =
  | "PENDING"
  | "CLEAR"
  | "FUZZY_MATCH_REVIEW"
  | "HIGH_RISK_REVIEW"
  | "BLOCKED";

export interface AgentStateResponse {
  mode: "quote" | "execute";
  parsed_intent: ParsedIntent | null;
  amount: number | null;
  payout_method: string | null;
  recipient_name: string | null;
  routes: RouteOption[];
  selected_route: RouteOption | null;
  risk: RiskAssessment | null;
  compliance: ComplianceResult | null;
  decision: Decision;
  execution: ExecutionResult | null;
  transaction: TransactionRecord | null;
  explanation_log: string[];
  error: string | null;
  quote_id?: string | null;
  quote_expires_at?: string | null;
  quote_binding?: "bound" | "fresh_unbound_demo" | null;
  idempotent_replay?: boolean;
}

export type DemoScenario = "default" | "fuzzy_review" | "high_risk";
