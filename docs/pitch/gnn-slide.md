# GNN slide — the honest version

If the pitch touches the "graph neural network" risk component, this is the
slide. It says what the ablation actually shows (full table:
[docs/kpis.md](../kpis.md), produced by `make ablation` — never hand-edited).

**Slide title:** *Graph-ready risk model — we show the baseline, not a
mystique*

| Model (same benchmark, same split) | AUC |
| :--- | ---: |
| Logistic regression (linear baseline) | 0.9217 |
| Hand-crafted rule (shipped default) | 0.9185 |
| GCN shipped (`USE_TRAINED_GNN=true`) | 0.9130 |

**The one-liner:** the linear baseline matches the GCN on our synthetic
benchmark — because the shipped GCN consumes identical feature vectors on
every node, it reduces to an MLP on tabular features; graph structure adds
nothing measurable today. We position the component as a **graph-ready
tabular risk model** and ship the deterministic rule as the default; the
engine label names the actual scorer.

**Why this is the strong answer, not a weakness:** every claim in the repo is
reproducible (`make ablation`), the benchmark's ≈0.94 AUC ceiling from 2% label
noise is stated, and the learned models are enabled only behind a flag after
recalibration (raw sigmoids never reach the 0.8 production gate — recall 0.0
at that gate is documented, not hidden).

**What a real graph would buy (future work, not claimed):** sender/receiver
mule-ring detection needs real transaction history with actual edges — the
moment labeled production data exists, the same harness re-runs.
