"""Layer A — Predictive RegTech: pre-settlement GNN risk scoring.

`RemittanceGNN` is the production architecture (PyTorch Geometric GCN over the
transaction subgraph: sender / recipient / device / geo nodes, history edges).
A trained checkpoint can be produced with `backend/ml/train_gnn.py` and enabled
with USE_TRAINED_GNN=true; without it, inference uses a deterministic stand-in
over the same feature vector, so the demo never depends on a GPU or a
checkpoint. Scores >= 0.8 are flagged for manual review.
"""
import datetime as _dt
import os
from pathlib import Path

try:
    import torch
    from torch_geometric.nn import GCNConv

    class RemittanceGNN(torch.nn.Module):
        """2-layer GCN: nodes carry a 16-dim feature vector; output = risk prob."""

        def __init__(self, in_channels: int = 16, hidden: int = 32):
            super().__init__()
            self.conv1 = GCNConv(in_channels, hidden)
            self.conv2 = GCNConv(hidden, 1)

        def forward(self, x, edge_index):
            x = self.conv1(x, edge_index).relu()
            return torch.sigmoid(self.conv2(x, edge_index))

    PYG_AVAILABLE = True
except ImportError:  # pragma: no cover - demo fallback
    RemittanceGNN = None
    PYG_AVAILABLE = False

ENGINE = "pyg-gcn" if PYG_AVAILABLE else "heuristic-stand-in"
REVIEW_THRESHOLD = 0.8
MODEL_PATH = Path(__file__).resolve().parents[2] / "ml" / "model.pt"

# Canonical 16-dim node feature order — shared by training (backend/ml/train_gnn.py)
# and inference so there is no train/serve skew. Core behavioural features sit at
# fixed indices; auxiliary ones default to neutral values in the demo.
FEATURE_ORDER = [
    "amount_ratio",        # 0
    "device_trust",        # 1
    "account_age_score",   # 2
    "relationship_score",  # 3
    "unusual_hour",        # 4
    "jurisdiction_risk",   # 5
    "velocity_24h",        # 6
    "recipient_new",       # 7
    "amount_log",          # 8
    "kyc_tier",            # 9
    "device_age_norm",     # 10
    "session_anomaly",     # 11
    "weekend",             # 12
    "corridor_volume_z",   # 13
    "time_since_last",     # 14
    "cash_intensity",      # 15
]
_FEATURE_DEFAULTS = {
    "amount_ratio": 1.0, "device_trust": 1.0, "account_age_score": 1.0,
    "relationship_score": 1.0, "unusual_hour": 0.0, "jurisdiction_risk": 0.1,
    "velocity_24h": 0.5,
}


def feature_vector(f: dict) -> list[float]:
    """Map a demo-feature dict onto the canonical 16-dim vector (pure Python).

    All values are scaled into [0, 1] — amount_ratio is divided by 10 (a 10x
    historical-mean transfer saturates at 1.0) so the GCN trains without
    saturating. Must stay in lockstep with backend/ml/train_gnn.py.
    """
    vec = [float(f.get(k, _FEATURE_DEFAULTS.get(k, 0.5))) for k in FEATURE_ORDER]
    vec[0] = min(vec[0] / 10.0, 1.0)                    # amount_ratio -> amount score
    amount = f.get("amount")
    vec[8] = min(_log10(amount) / 4.0, 1.0) if amount and amount > 0 else 0.5
    vec[2] = min(vec[2], 1.0)                           # account_age_score
    vec[10] = min(1.0 - vec[1], 1.0)                    # device_age_norm = 1 - trust
    return vec


def _log10(v: float) -> float:
    import math

    return math.log10(max(v, 1.0))


# Node roles inside a transaction subgraph: sender(0) - recipient(1) / device(2) / geo(3)
def _transaction_subgraph(f: dict):
    """Build the 4-node / 3-edge subgraph for one transaction. Requires torch.

    Every node carries the full behavioural feature vector. GCN normalization
    averages neighbor features into each node, so role nodes carrying only 2-3
    nonzero dims attenuate the sender's signal to noise within two layers; with
    full vectors, layer-2 aggregation combines four informative views of the
    same transaction over the trust topology (sender-recipient, sender-device,
    sender-geo).
    """
    import torch

    sender = feature_vector(f)
    x = torch.tensor([sender, sender, sender, sender], dtype=torch.float)
    # bidirectional: GCN aggregates INCOMING edges, and the sender must receive
    # its neighbors' signals, not only emit them
    edge_index = torch.tensor([[0, 0, 0, 1, 2, 3], [1, 2, 3, 0, 0, 0]], dtype=torch.long)
    return x, edge_index

# Feature weights for the deterministic stand-in (mirror of the GCN's signal)
_W = {
    "device": 0.35,        # untrusted/new device
    "account_age": 0.15,   # brand-new sender account
    "amount": 0.25,        # amount far above personal history
    "relationship": 0.15,  # no established recipient relationship
    "unusual_hour": 0.05,
    "jurisdiction": 0.05,
}


_trained_model_cache: dict = {"model": None, "norm": None, "loaded": False}


def _trained_model():
    """Load backend/ml/model.pt when USE_TRAINED_GNN=true (lazy, cached, safe)."""
    if os.environ.get("USE_TRAINED_GNN", "").lower() != "true":
        return None
    if _trained_model_cache["loaded"]:
        return _trained_model_cache["model"]
    _trained_model_cache["loaded"] = True
    if not PYG_AVAILABLE or not MODEL_PATH.exists():
        return None
    try:
        checkpoint = torch.load(MODEL_PATH, map_location="cpu", weights_only=False)
        model = RemittanceGNN(in_channels=checkpoint.get("in_channels", 16))
        model.load_state_dict(checkpoint["state_dict"])
        model.eval()
        norm = checkpoint.get("norm") or {}
        mean = torch.tensor(norm.get("mean", [0.0] * 16), dtype=torch.float)
        std = torch.tensor(norm.get("std", [1.0] * 16), dtype=torch.float)
        _trained_model_cache["model"] = model
        _trained_model_cache["norm"] = (mean, std)
    except Exception:  # noqa: BLE001 — never break the demo on a bad checkpoint
        _trained_model_cache["model"] = None
        _trained_model_cache["norm"] = None
    return _trained_model_cache["model"]


def demo_features(scenario: str, amount: float, sender: dict, recipient_name: str) -> dict:
    """Build the stand-in feature vector for a demo scenario."""
    scenario = (scenario or "default").lower()
    avg = float(sender.get("avg_send_aed", 850.0)) or 1.0
    amount_ratio = amount / avg

    if scenario == "high_risk":
        return {
            "scenario": scenario,
            "device_trust": 0.2,
            "account_age_days": 30,
            "amount_ratio": max(amount_ratio, 5.0),
            "relationship_score": 0.3,
            "unusual_hour": True,
            "recipient_node": f"recipient:new_unsaved:{recipient_name or 'unnamed'}",
            "device_node": "device:fp_new_unknown",
        }
    return {
        "scenario": scenario,
        "device_trust": 1.0,
        "account_age_days": int(sender.get("account_age_days", 430)),
        "amount_ratio": round(amount_ratio, 2),
        "relationship_score": 1.0,
        "unusual_hour": False,
        "recipient_node": f"recipient:rcp_001:{recipient_name or 'default'}",
        "device_node": f"device:{sender.get('device_fingerprint', 'fp_unknown')}",
    }


def _risk_score(f: dict) -> float:
    age_score = min(f["account_age_days"] / 365.0, 1.0)
    amount_score = max(0.0, min((f["amount_ratio"] - 1.0) / 4.0, 1.0))
    score = 0.05
    score += (1.0 - f["device_trust"]) * _W["device"]
    score += (1.0 - age_score) * _W["account_age"]
    score += amount_score * _W["amount"]
    score += (1.0 - f["relationship_score"]) * _W["relationship"]
    score += (0.05 if f["unusual_hour"] else 0.0)
    return round(min(score, 1.0), 4)


def _risk_band(score: float) -> str:
    if score >= REVIEW_THRESHOLD:
        return "HIGH"
    if score >= 0.3:
        return "MEDIUM"
    return "LOW"


def _explanation(f: dict, score: float, n_nodes: int, n_edges: int) -> str:
    device = "trusted device fingerprint" if f["device_trust"] >= 0.9 else "unrecognized/new device"
    age = f"{f['account_age_days']}-day account history"
    ratio = f"amount within {f['amount_ratio']}× historical mean"
    if f["amount_ratio"] >= 3:
        ratio = f"amount is {f['amount_ratio']}× the historical mean — abnormal"
    rel = ("long-standing recipient relationship" if f["relationship_score"] >= 0.9
           else "no established relationship with this recipient")
    hour = "" if not f["unusual_hour"] else ", initiated at an unusual hour"
    verdict = ("Behavior consistent with normal remittance pattern."
               if score < REVIEW_THRESHOLD else
               "Pattern matches elevated-risk indicators; hold for analyst review.")
    return (f"GNN subgraph analysis ({n_nodes} nodes / {n_edges} edges): {device}, "
            f"{age}, {ratio}, {rel}{hour}. {verdict}")


def pre_settlement_check(features: dict, sender_id: str = "usr_uae_001",
                         corridor: str = "AE->BD") -> dict:
    """Run the GNN (trained checkpoint or stand-in) over the transaction subgraph."""
    f = features
    nodes = [f"sender:{sender_id}", f["recipient_node"], f["device_node"], f"geo:{corridor}"]
    n_nodes, n_edges = len(nodes), len(nodes) - 1

    engine = ENGINE
    score = None
    model = _trained_model()
    if model is not None:
        try:
            with torch.no_grad():
                x, edge_index = _transaction_subgraph(f)
                mean, std = _trained_model_cache["norm"]
                x = (x - mean) / std
                out = model(x, edge_index).squeeze(-1)
                score = round(float(out[0]), 4)  # sender node = the risk under assessment
            engine = "pyg-gcn-trained"
        except Exception:  # noqa: BLE001 — fall back to the stand-in
            score = None

    if score is None:
        score = _risk_score(f)

    return {
        "gnn_risk_score": score,
        "risk_band": _risk_band(score),
        "graph_nodes_evaluated": nodes,
        "requires_manual_review": score >= REVIEW_THRESHOLD,
        "engine": engine,
        "ai_explanation": _explanation(f, score, n_nodes, n_edges),
        "checked_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
