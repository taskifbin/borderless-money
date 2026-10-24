"""Regulatory RAG — retrieve grounding passages for compliance/rate explanations.

Corpus: backend/rag/corpus/*.md — Bangladesh Bank circular excerpts, OFAC FAQ
excerpts, ISO 20022 reference. Every chunk carries its source line verbatim
(organization + domain) so the API can expose `regulatory_basis` with checkable
citations. Invented citations are fatal for a compliance product, so the source
string is taken from the corpus file, never generated.

Embeddings: when `sentence-transformers` is installed the chunks are embedded
with all-MiniLM-L6-v2 (small, local, offline); otherwise a lexical hashed
n-gram TF retriever serves as the documented fallback. `engine` in retrieve()
always reports which one answered.
"""
import math
import re
from functools import lru_cache
from pathlib import Path

CORPUS_DIR = Path(__file__).resolve().parents[2] / "rag" / "corpus"
DIM = 512
TOP_K = 3
_URL_RE = re.compile(r"https?://[^\s)]+|\((?:www\.)?([a-z0-9.\-]+\.[a-z]{2,})\)")

try:  # optional: real embeddings when available
    from sentence_transformers import SentenceTransformer

    _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    EMBEDDING_ENGINE = "all-MiniLM-L6-v2"
except Exception:  # noqa: BLE001 — lexical fallback is the documented default
    _MODEL = None
    EMBEDDING_ENGINE = "lexical-ngram-tf"

_WORD_RE = re.compile(r"[a-z0-9%]+")


def _hash(s: str) -> int:
    h = 2166136261
    for ch in s:
        h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    return h % DIM


def _lexical_embed(text: str) -> list[float]:
    tokens = _WORD_RE.findall(text.lower())
    grams = list(tokens)
    for t in tokens:
        padded = f"^{t}$"
        grams.extend(padded[i:i + 4] for i in range(max(len(padded) - 3, 1)))
    vec = [0.0] * DIM
    for g in grams:
        vec[_hash(g)] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _embed_texts(texts: list[str]) -> list:
    if _MODEL is not None:
        return _MODEL.encode(texts, normalize_embeddings=True).tolist()
    return [_lexical_embed(t) for t in texts]


def _dense_cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _sparse_cosine(a: dict[int, float], b: dict[int, float]) -> float:
    na = math.sqrt(sum(v * v for v in a.values())) or 1.0
    nb = math.sqrt(sum(v * v for v in b.values())) or 1.0
    small, big = (a, b) if len(a) < len(b) else (b, a)
    return sum(v * big.get(i, 0.0) for i, v in small.items()) / (na * nb)


def _first_domain(source: str) -> str | None:
    m = re.search(r"\((?:www\.)?([a-z0-9.\-]+\.[a-z]{2,})\)", source)
    return m.group(1) if m else None


@lru_cache(maxsize=1)
def _corpus() -> tuple:
    docs = []
    if not CORPUS_DIR.exists():
        return ()
    for path in sorted(CORPUS_DIR.glob("*.md")):
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError:
            continue
        lines = raw.strip().splitlines()
        title = lines[0].lstrip("# ").strip() if lines else path.stem
        source = next((ln[len("Source: "):].strip() for ln in lines
                       if ln.startswith("Source: ")), path.stem)
        body = "\n".join(ln for ln in lines if not ln.startswith(("Source:", "Status:")))
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if len(p.strip()) > 80]
        for j, para in enumerate(paragraphs):
            docs.append({
                "id": f"{path.stem}:{j}",
                "title": title,
                "source": source,
                "domain": _first_domain(source),
                "text": " ".join(para.split()),
            })
    embeddings = _embed_texts([d["text"] for d in docs])
    for d, emb in zip(docs, embeddings):
        if _MODEL is not None:
            d["vector"] = emb
        else:
            d["vector"] = {i: v for i, v in enumerate(emb) if v}
    return tuple(docs)


def retrieve(query: str, k: int = TOP_K) -> dict:
    """Top-k corpus passages: {engine, passages: [{id, title, source, domain,
    score, snippet}]}. Never raises — citations are additive, never load-bearing."""
    try:
        docs = _corpus()
        if not docs:
            return {"engine": EMBEDDING_ENGINE, "passages": []}
        qv = _embed_texts([query])[0]
        scored = []
        for d in docs:
            if _MODEL is not None:
                score = _dense_cosine(qv, d["vector"])
            else:
                score = _sparse_cosine(
                    {i: v for i, v in enumerate(qv) if v}, d["vector"])
            scored.append((score, d))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        passages = [
            {
                "id": d["id"],
                "title": d["title"],
                "source": d["source"],
                "domain": d["domain"],
                "score": round(score, 4),
                "snippet": d["text"][:220],
            }
            for score, d in scored[:k] if score > 0.02
        ]
        return {"engine": EMBEDDING_ENGINE, "passages": passages}
    except Exception:  # noqa: BLE001
        return {"engine": EMBEDDING_ENGINE, "passages": []}
