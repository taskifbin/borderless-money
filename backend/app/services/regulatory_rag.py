"""Regulatory RAG — retrieve grounding passages for compliance/rate explanations.

Corpus: backend/rag/corpus/*.md (Bangladesh Bank circular excerpts, OFAC FAQ
excerpts, ISO 20022 reference). Retrieval is dependency-free: hashed word +
character-n-gram TF vectors with sublinear TF weighting and L2 normalization
(cosine similarity). A neural embedder (e.g. sentence-transformers MiniLM) can
be dropped in later behind the same interface; if this module fails for any
reason the orchestrator degrades to no citations.

Every returned passage carries its source so the API can expose
`regulatory_basis` with verifiable titles — no unattributed generation.
"""
import math
import re
from functools import lru_cache
from pathlib import Path

CORPUS_DIR = Path(__file__).resolve().parents[2] / "rag" / "corpus"
DIM = 512
TOP_K = 3

_WORD_RE = re.compile(r"[a-z0-9%]+")


def _hash(s: str) -> int:
    h = 2166136261
    for ch in s:
        h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    return h % DIM


def _embed(text: str) -> dict[int, float]:
    """Sublinear-TF hashed vector of words + 4-char n-grams, L2-normalized."""
    tokens = _WORD_RE.findall(text.lower())
    grams = list(tokens)
    for t in tokens:
        padded = f"^{t}$"
        grams.extend(padded[i:i + 4] for i in range(max(len(padded) - 3, 1)))
    counts: dict[int, float] = {}
    for g in grams:
        idx = _hash(g)
        counts[idx] = counts.get(idx, 0.0) + 1.0
    return {i: (1.0 + math.log(c)) for i, c in counts.items()}


def _cosine(a: dict[int, float], b: dict[int, float]) -> float:
    na, nb = math.sqrt(sum(v * v for v in a.values())), math.sqrt(sum(v * v for v in b.values()))
    if not na or not nb:
        return 0.0
    small, big = (a, b) if len(a) < len(b) else (b, a)
    dot = sum(v * big.get(i, 0.0) for i, v in small.items())
    return dot / (na * nb)


@lru_cache(maxsize=1)
def _corpus() -> list[dict]:
    docs = []
    if not CORPUS_DIR.exists():
        return docs
    for path in sorted(CORPUS_DIR.glob("*.md")):
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError:
            continue
        lines = raw.strip().splitlines()
        title = lines[0].lstrip("# ").strip() if lines else path.stem
        source = next((ln[len("Source: "):].strip() for ln in lines
                       if ln.startswith("Source: ")), path.stem)
        body = "\n".join(lines[1:])
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if len(p.strip()) > 80]
        for j, para in enumerate(paragraphs):
            docs.append({
                "id": f"{path.stem}:{j}",
                "title": title,
                "source": source,
                "text": " ".join(para.split()),
                "vector": _embed(para),
            })
    return docs


def retrieve(query: str, k: int = TOP_K) -> list[dict]:
    """Top-k corpus passages for a query: [{id, title, source, score, snippet}]."""
    try:
        qv = _embed(query)
        ranked = sorted(
            ((_cosine(qv, d["vector"]), d) for d in _corpus()),
            key=lambda pair: pair[0], reverse=True,
        )[:k]
        return [
            {
                "id": d["id"],
                "title": d["title"],
                "source": d["source"],
                "score": round(score, 4),
                "snippet": d["text"][:220],
            }
            for score, d in ranked if score > 0.05
        ]
    except Exception:  # noqa: BLE001 — citations are additive, never load-bearing
        return []
