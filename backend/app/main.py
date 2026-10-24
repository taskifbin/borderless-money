"""Borderless Money — B2B Remittance-as-a-Service API (FastAPI).

Endpoints (contracts in docs/api-contracts.md):
  GET  /api/health
  POST /api/agent/parse-intent
  POST /api/agent/quote
  POST /api/agent/execute
  GET  /api/transactions/{transaction_id}
  GET  /api/routes/compare
"""
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app import config
from app.agent import orchestrator
from app.services import compliance, gnn_risk, horizon, intent_parser, llm, metrics, routing_scorer, store
from app.services import corridor as corridor_cfg

app = FastAPI(
    title="Borderless Money",
    description="Remittance intelligence that maximizes the money that actually arrives. UAE (AED) → Bangladesh (BDT).",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ParseIntentRequest(BaseModel):
    text: str = Field(..., min_length=1)
    default_corridor: str = "AED_TO_BDT"


class QuoteRequest(BaseModel):
    text: Optional[str] = None
    amount: Optional[float] = None
    payout_method: Optional[str] = None
    recipient_name: Optional[str] = None
    demo_scenario: Literal["default", "fuzzy_review", "high_risk"] = "default"


class ExecuteRequest(QuoteRequest):
    selected_route_name: Optional[str] = None


def _engine_flags() -> dict:
    import importlib.util

    return {
        "langgraph": importlib.util.find_spec("langgraph") is not None,
        "networkx": importlib.util.find_spec("networkx") is not None,
        "torch_geometric": importlib.util.find_spec("torch_geometric") is not None,
        "stellar_sdk": importlib.util.find_spec("stellar_sdk") is not None,
    }


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "corridor": config.CORRIDOR,
        "corridors_available": corridor_cfg.available_corridors(),
        "engines": {**_engine_flags(), "llm_fallback": llm.is_enabled()},
    }


@app.post("/api/agent/parse-intent")
def parse_intent(req: ParseIntentRequest):
    return intent_parser.parse_intent(req.text, req.default_corridor)


def _run_or_raise(**kwargs) -> dict:
    state = orchestrator.run(**kwargs)
    if state.get("error"):
        raise HTTPException(status_code=400, detail=state["error"])
    # trim internal-only fields from the response
    return {k: v for k, v in state.items() if k not in {"text"}}


@app.post("/api/agent/quote")
def quote(req: QuoteRequest):
    return _run_or_raise(
        mode="quote", text=req.text, amount=req.amount,
        payout_method=req.payout_method, recipient_name=req.recipient_name,
        demo_scenario=req.demo_scenario,
    )


@app.post("/api/agent/execute")
def execute(req: ExecuteRequest):
    return _run_or_raise(
        mode="execute", text=req.text, amount=req.amount,
        payout_method=req.payout_method, recipient_name=req.recipient_name,
        selected_route_name=req.selected_route_name, demo_scenario=req.demo_scenario,
    )


@app.get("/api/transactions/{transaction_id}")
def get_transaction(transaction_id: str):
    tx = store.get_transaction(transaction_id)
    if tx is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tx


@app.get("/api/routes/compare")
def compare_routes(amount: float = 1000.0, payout_method: str = "BKASH",
                   corridor: str = corridor_cfg.DEFAULT_CORRIDOR,
                   deadline_hours: float | None = None):
    """Direct Layer A access: incentive-aware expected-value ranking plus the
    naive cheapest-fee baseline, with every data source and its timestamp."""
    try:
        routes = routing_scorer.score_routes(amount, payout_method,
                                             corridor_code=corridor,
                                             deadline_hours=deadline_hours)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    cfg = corridor_cfg.load_corridor(corridor)
    baseline = routing_scorer.naive_baseline(routes)
    return {
        "routes": routes,
        "baseline": {
            "strategy": "naive cheapest-fee",
            "name": baseline["name"] if baseline else None,
            "fee_aed": baseline["fee_aed"] if baseline else None,
            "expected_value_bdt": baseline["expected_value_bdt"] if baseline else None,
            "incentive_eligible": baseline["incentive_eligible"] if baseline else None,
        },
        "data_sources": {
            "fx": {"source": cfg.get("fx_source"), "as_of": cfg.get("sourced_at")},
            "stellar_horizon": horizon.probe(),
        },
    }


@app.get("/metrics")
def metrics_endpoint():
    """Measured demo KPIs (computed once from the eval sets — not invented)."""
    return metrics.compute_metrics()
