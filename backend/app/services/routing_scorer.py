"""Layer A — Routing Scorer.

Corridor-agnostic: every rail, FX rate, fee and last-mile rule comes from the
corridor config (backend/config/corridors/<code>.json). The corridor is modeled
as a directed graph —

    send ──▶ rail node ──▶ payout node

— paths are priced end-to-end (rail edge carries FX + wire fee + hours; the
payout edge adds the last-mile partner fee) and ranked by True Net Receive.
Uses NetworkX when available, with an identical pure-Python fallback.
"""
from functools import lru_cache

from app.services import corridor as corridor_cfg
from app.services.incentive import calculate_true_net_receive

try:
    import networkx as nx
except ImportError:  # pragma: no cover - fallback path
    nx = None

SEND_NODE = "send"


@lru_cache(maxsize=8)
def _build_graph(corridor_code: str):
    cfg = corridor_cfg.load_corridor(corridor_code)
    g = nx.DiGraph() if nx else None
    if g is not None:
        g.add_node(SEND_NODE)
        for rail in cfg["rails"]:
            g.add_edge(SEND_NODE, f"rail:{rail['name']}", rail=rail)
        for payout, per_rail in cfg["last_mile"].items():
            for rail_name, (fee, extra_h, succ) in per_rail.items():
                g.add_edge(f"rail:{rail_name}", f"payout:{payout}",
                           rail_name=rail_name, fee=fee, hours=extra_h, success=succ)
    return g


def _paths_to_payout(corridor: dict, payout_method: str):
    """Yield (rail_name, fee, hours, fx, success) for every viable path."""
    payout_method = payout_method.upper() if payout_method else corridor["default_payout"]
    if payout_method not in corridor["last_mile"]:
        raise ValueError(
            f"Unknown payout method '{payout_method}' for corridor '{corridor['code']}'"
        )
    target = f"payout:{payout_method}"
    graph = _build_graph(corridor["code"])
    if graph is not None and graph.has_node(target):
        for path in nx.all_simple_paths(graph, SEND_NODE, target):
            rail_edge, last_mile_edge = graph.edges[path[0], path[1]], graph.edges[path[1], path[2]]
            rail = rail_edge["rail"]
            fee = rail["fee_source"] + last_mile_edge["fee"]
            hours = rail["hours"] + last_mile_edge["hours"]
            yield rail["name"], fee, hours, rail["fx"], rail["success_rate"] * last_mile_edge["success"]
        return
    # pure-Python fallback — identical pricing
    for rail in corridor["rails"]:
        fee, extra_h, succ = corridor["last_mile"][payout_method][rail["name"]]
        yield rail["name"], rail["fee_source"] + fee, rail["hours"] + extra_h, rail["fx"], rail["success_rate"] * succ


def score_routes(amount_source: float, payout_method: str = "BKASH",
                 corridor_code: str = corridor_cfg.DEFAULT_CORRIDOR) -> list[dict]:
    """Enumerate corridor paths, price each with True Net Receive, rank best-first."""
    corridor = corridor_cfg.load_corridor(corridor_code)
    payout_method = (payout_method or corridor["default_payout"]).upper()
    mid = corridor["mid_market_rate"]
    src_ccy = corridor["source_currency"]

    scored = []
    for rail_name, fee, hours, rate, success in _paths_to_payout(corridor, payout_method):
        name = f"{rail_name} → {payout_method}"
        breakdown = calculate_true_net_receive(
            amount_source, rate, fee, route=name, settlement_time_hrs=hours,
            govt_incentive_rate=corridor["govt_incentive_rate"],
        )
        scored.append({
            "name": name,
            "rail": rail_name,
            "payout_method": payout_method,
            "fx_rate": rate,
            "mid_market_rate": mid,
            "spread_bdt_per_aed": round(mid - rate, 2),
            "fee_aed": round(fee, 2),
            "settlement_time_hrs": hours,
            "success_rate": round(success, 4),
            "is_best": False,
            "advantage_bdt_vs_best": 0.0,
            "breakdown": breakdown,
        })
    scored.sort(key=lambda r: r["breakdown"]["true_net_receive_bdt"], reverse=True)
    best_net = scored[0]["breakdown"]["true_net_receive_bdt"]
    for i, route in enumerate(scored):
        route["is_best"] = i == 0
        route["advantage_bdt_vs_best"] = round(best_net - route["breakdown"]["true_net_receive_bdt"], 2)
    return scored
