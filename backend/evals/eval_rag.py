"""Retrieval benchmark (Step 3) — one command: `make eval-rag`.

Each labeled query must surface its expected corpus chunk in the top-2.
Prints hit@k per query plus overall hit rate; exits 1 below 0.75.
Also verifies every displayed passage carries a real source domain.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import regulatory_rag  # noqa: E402

ALLOWED_DOMAINS = {"bb.org.bd", "www.bb.org.bd", "ofac.treasury.gov", "www.iso20022.org", "iso20022.org"}


def main() -> int:
    data_file = Path(__file__).resolve().parents[1] / "data" / "rag_eval.json"
    with open(data_file, "r", encoding="utf-8") as f:
        queries = json.load(f)["queries"]

    hits = 0
    citation_failures = []
    print(f"retrieval engine: {regulatory_rag.EMBEDDING_ENGINE}\n")
    for q in queries:
        result = regulatory_rag.retrieve(q["query"], k=2)
        ids = [p["id"].split(":")[0] for p in result["passages"]]
        hit = q["expect_chunk"] in ids
        hits += hit
        print(f"{'HIT ' if hit else 'MISS'}  {q['query'][:58]:<58} -> {ids}")
        for p in result["passages"]:
            if not p.get("domain") or p["domain"] not in ALLOWED_DOMAINS:
                citation_failures.append((p["id"], p.get("domain")))

    rate = hits / len(queries) if queries else 0.0
    print(f"\nhit@2: {hits}/{len(queries)} = {rate:.0%}")
    if citation_failures:
        print("CITATION FAILURES (unknown domain):", citation_failures)
        return 1
    if rate < 0.75:
        print("Retrieval hit rate below 0.75 — failing.")
        return 1
    print("All citations resolve to allowed source domains; retrieval OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
