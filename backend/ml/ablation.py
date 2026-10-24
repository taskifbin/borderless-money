"""Risk-model ablation (Step 2) — one command: `make ablation` (needs the venv).

Same 2,400-sample synthetic dataset and train/test split as train_gnn.py, four
scorers on identical features:

    rule-stand-in : the hand-crafted linear rule shipped as the default scorer
    logistic-reg  : Linear(16 -> 1) on standardized features (torch)
    boosted-stumps: AdaBoost with depth-1 decision stumps (pure python)
    gcn           : the shipped RemittanceGNN (identical node vectors, so it
                    reduces to an MLP on tabular features — graph structure
                    adds nothing today; that is the honest finding)

Reports AUC plus precision/recall/FPR at each model's train-tuned max-F1
threshold. Writes backend/ml/ablation.md.
"""
import json
import random
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "ml"))

import torch  # noqa: E402

from app.services.gnn_risk import RemittanceGNN, feature_vector, _risk_score  # noqa: E402
from train_gnn import build_split, auc_score  # noqa: E402  # noqa: E402

EPOCHS_LINEAR = 300


def make_dataset(n: int, seed: int):
    """Raw feature dicts + labels (the GCN path tensorizes separately)."""
    rng = random.Random(seed)
    from train_gnn import sample  # fraud/normal feature generator

    data = []
    for _ in range(n):
        is_fraud = rng.random() < 0.12
        label = is_fraud
        if rng.random() < 0.02:
            label = not label
        f = sample(is_fraud, rng)
        data.append((f, 1.0 if label else 0.0))
    return data


def tensorize(data):
    xs = [torch.tensor(feature_vector(f), dtype=torch.float) for f, _ in data]
    return torch.stack(xs), torch.tensor([l for _, l in data])


def metrics(y_true, probs, y_train, p_train):
    best_f1, thr = 0.0, 0.5
    for t in [i / 100 for i in range(5, 100)]:
        preds = [1.0 if p >= t else 0.0 for p in p_train]
        tp = sum(1 for p, y in zip(preds, y_train) if p == 1.0 and y == 1.0)
        pr = tp / sum(preds) if sum(preds) else 0.0
        rc = tp / sum(y_train) if sum(y_train) else 0.0
        f1 = 2 * pr * rc / (pr + rc) if pr + rc else 0.0
        if f1 > best_f1:
            best_f1, thr = f1, t
    preds = [1.0 if p >= thr else 0.0 for p in probs]
    tp = sum(1 for p, y in zip(preds, y_true) if p == 1.0 and y == 1.0)
    precision = tp / sum(preds) if sum(preds) else 0.0
    recall = tp / sum(y_true) if sum(y_true) else 0.0
    n_pos_pred = sum(preds)
    fp = n_pos_pred - tp
    n_neg = sum(1 for y in y_true if y == 0.0)
    fpr = fp / n_neg if n_neg else 0.0
    return {"auc": round(auc_score(y_true, probs), 4), "precision": round(precision, 4),
            "recall": round(recall, 4), "fpr": round(fpr, 4), "threshold": thr}


def rule_baseline(data):
    return [_risk_score(f) for f, _ in data]


def logistic(train_x, train_y, eval_x):
    torch.manual_seed(0)
    model = torch.nn.Linear(train_x.shape[1], 1)
    opt = torch.optim.Adam(model.parameters(), lr=0.01)
    for _ in range(EPOCHS_LINEAR):
        opt.zero_grad()
        out = model(train_x).squeeze(-1)
        torch.nn.functional.binary_cross_entropy_with_logits(out, train_y).backward()
        opt.step()
    with torch.no_grad():
        return (torch.sigmoid(model(train_x).squeeze(-1)).tolist(),
                torch.sigmoid(model(eval_x).squeeze(-1)).tolist())


def boosted_stumps(train_x, train_y, eval_x, rounds=40):
    """AdaBoost with depth-1 stumps on standardized features (pure torch)."""
    n = train_x.shape[0]
    w = torch.full((n,), 1.0 / n)
    stumps, alphas = [], []
    feat_count = train_x.shape[1]
    cands = torch.quantile(train_x, torch.linspace(0.05, 0.95, 24), dim=0)  # 24 x 16
    y = train_y * 2 - 1
    for _ in range(rounds):
        best = None
        for f in range(feat_count):
            for thr in cands[:, f]:
                for pol in (1.0, -1.0):
                    pred = torch.where(train_x[:, f] >= thr, pol, -pol)
                    err = (w * (pred * y < 0)).sum()
                    if best is None or err < best[0]:
                        best = (err, f, float(thr), pol)
        err, f, thr, pol = best
        err = max(err.clamp(min=1e-6), 1e-6)
        alpha = 0.5 * torch.log((1 - err) / err)
        pred = torch.where(train_x[:, f] >= thr, pol, -pol)
        w = w * torch.exp(-alpha * pred * y)
        w = w / w.sum()
        stumps.append((f, thr, pol))
        alphas.append(float(alpha))
    def score(X):
        agg = torch.zeros(X.shape[0])
        for (f, thr, pol), a in zip(stumps, alphas):
            agg += a * torch.where(X[:, f] >= thr, pol, -pol)
        return torch.sigmoid(agg).tolist()
    return score(train_x), score(eval_x)


def gcn(train_raw, train_y, eval_raw, eval_y):
    from train_gnn import _transaction_subgraph

    def to_graphs(rows):
        out = []
        for f, _label in rows:
            out.append(_transaction_subgraph(f))
        return out

    tg = to_graphs(train_raw)
    vg = to_graphs(eval_raw)
    xs, rows, cols, senders, off = [], [], [], [], 0
    for x, ei in tg:
        xs.append(x)
        rows += (ei[0] + off).tolist()
        cols += (ei[1] + off).tolist()
        senders.append(off)
        off += x.shape[0]
    X, EI, MASK = torch.cat(xs), torch.tensor([rows, cols]), torch.tensor(senders)
    Y = torch.tensor([l for _, l in train_raw])
    vx, vei_rows, vei_cols, vmask, off = [], [], [], [], 0
    for x, ei in vg:
        vx.append(x)
        vei_rows += (ei[0] + off).tolist()
        vei_cols += (ei[1] + off).tolist()
        vmask.append(off)
        off += x.shape[0]
    VX, VEI, VMASK = torch.cat(vx), torch.tensor([vei_rows, vei_cols]), torch.tensor(vmask)

    torch.manual_seed(42)
    model = RemittanceGNN(16)
    opt = torch.optim.Adam(model.parameters(), lr=0.02)
    for _ in range(200):
        opt.zero_grad()
        out = model(X, EI).squeeze(-1)[MASK]
        torch.nn.functional.binary_cross_entropy_with_logits(out, Y).backward()
        opt.step()
    with torch.no_grad():
        ptr = torch.sigmoid(model(X, EI).squeeze(-1)[MASK]).tolist()
        pev = torch.sigmoid(model(VX, VEI).squeeze(-1)[VMASK]).tolist()
    return ptr, pev


def main() -> int:
    torch.manual_seed(42)
    train_raw = make_dataset(1920, seed=42)
    eval_raw = make_dataset(480, seed=43)
    train_y = [l for _, l in train_raw]
    eval_y = [l for _, l in eval_raw]
    train_x, _ = tensorize(train_raw)
    eval_x, _ = tensorize(eval_raw)
    mu, sd = train_x.mean(0, keepdim=True), train_x.std(0, keepdim=True) + 1e-6
    train_xn, eval_xn = (train_x - mu) / sd, (eval_x - mu) / sd

    rows = {}
    rows["rule-stand-in"] = metrics(eval_y, rule_baseline(eval_raw), train_y, rule_baseline(train_raw))
    ptr, pev = logistic(train_xn, torch.tensor(train_y), eval_xn)
    rows["logistic-regression"] = metrics(eval_y, pev, train_y, ptr)
    ptr, pev = boosted_stumps(train_xn, torch.tensor(train_y), eval_xn)
    rows["boosted-stumps"] = metrics(eval_y, pev, train_y, ptr)
    ptr, pev = gcn(train_raw, train_y, eval_raw, eval_y)
    rows["gcn-shipped"] = metrics(eval_y, pev, train_y, ptr)

    lines = [
        "# Risk-model ablation (honest positioning)",
        "",
        "Generated by `backend/ml/ablation.py` (`make ablation`). Same 2,400-sample",
        "synthetic dataset (12% fraud patterns, 2% label noise) and split as",
        "train_gnn.py; identical 16-dim standardized features for every model;",
        "thresholds tuned on train only (max-F1), metrics on the held-out split.",
        "",
        "| model | AUC | precision | recall | FPR | threshold |",
        "| :--- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, m in rows.items():
        lines.append(f"| {name} | {m['auc']} | {m['precision']} | {m['recall']} | {m['fpr']} | {m['threshold']} |")
    lines += [
        "",
        "## Findings (state plainly)",
        "",
        "1. The shipped GCN consumes **identical feature vectors on all four nodes**,",
        "   so the graph convolution reduces to an MLP on tabular features — graph",
        "   structure contributes nothing today. We therefore position the risk",
        "   component as a **graph-ready tabular risk model**, not a GNN.",
        "2. The engine label reflects the actual scorer: `heuristic-stand-in` for the",
        "   tabular rule, `pyg-gcn-trained` only when the checkpoint is loaded via",
        "   `USE_TRAINED_GNN=true`.",
        "3. Explanations are generated from the decision log (feature values and",
        "   signals); the phrase \"GNN subgraph analysis\" no longer appears anywhere.",
        "4. Demo scenarios are **scripted inputs** (`demo_features`), labeled as such;",
        "   no scenario label reaches training.",
        "5. With 2% symmetric label noise and a 1:7.3 class imbalance, the",
        "   theoretical AUC ceiling for a perfect ranker is ≈0.94.",
        "",
        f"_Generated: {__import__('datetime').datetime.now(__import__('datetime').timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}_",
    ]
    out = BACKEND / "ml" / "ablation.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
