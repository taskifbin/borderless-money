"""Review-volume measurement — operational load of the sanctions gate.

Generates 500 synthetic transfers with common Bangladeshi sender/recipient
names (combinatorial name pools, seeded) and screens every party with the real
matcher. Reports how many transfers trigger a human review (any party
FUZZY_MATCH_REVIEW or BLOCKED) -> reviews per 1,000 transfers.

This is the honest operational-cost number that pairs with the recall/FPR
metrics: a gate with perfect recall but a 20% review rate would be unusable.

NOTE on data: the name POOLS are common Bangladeshi first/last names typed in
by hand; the combinations are synthetic (seeded). No real customer data exists
in this repo. The sanctions list is the 10-entry local sample — review volume
against the full OFAC SDN file will be HIGHER and must be re-measured before
any production claim.

Run:  backend/.venv/bin/python scripts/review_volume.py
Writes reports/review_volume.json.
"""
import json
import random
import sys
from collections import Counter
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from app.services import compliance  # noqa: E402

FIRST_NAMES = [
    "Mohammad", "Abdul", "Rahim", "Shahidul", "Tanvir", "Mizanur", "Jahid", "Rakib",
    "Sohel", "Nayeem", "Imran", "Habibur", "Rezaul", "Kamal", "Rubel", "Jashim",
    "Alamin", "Shafiqul", "Nur", "Mostofa", "Fahim", "Wasik", "Taskif", "Arif",
    "Sumon", "Jewel", "Babul", "Rasel", "Shamim", "Jahangir",
    "Ayesha", "Salma", "Nusrat", "Shirin", "Alisha", "Sukonya", "Nasrin", "Sabina",
    "Rahima", "Fatema", "Jahanara", "Rokeya", "Marjina", "Shefali", "Parul", "Nazma",
]
LAST_NAMES = [
    "Islam", "Mia", "Hossain", "Rahman", "Uddin", "Akter", "Khatun", "Begum",
    "Hasan", "Alam", "Sheikh", "Molla", "Sardar", "Chowdhury", "Talukder", "Munshi",
    "Fakir", "Gazi", "Bayen", "Mondol", "Sarker", "Biswas", "Das", "Pal",
    "Howlader", "Sana", "Pramanik", "Dos", "Barmon", "Roy",
]
N = 500
SEED = 7


def main() -> None:
    rng = random.Random(SEED)
    decisions = Counter()
    review_transfers = 0
    flagged_examples = []

    for i in range(N):
        sender = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        recipient = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        result = compliance.screen_transaction(sender, recipient)
        overall = result["ofac_match_status"]
        decisions[overall] += 1
        if overall != "CLEAR":
            review_transfers += 1
            if len(flagged_examples) < 10:
                flagged = next(p for p in result["screened_parties"] if p["status"] != "CLEAR")
                flagged_examples.append({
                    "transfer": i, "sender": sender, "recipient": recipient,
                    "party": flagged["role"], "status": flagged["status"],
                    "matched": flagged["best_match"]["name"] if flagged["best_match"] else None,
                    "score": flagged["best_match"]["similarity"] if flagged["best_match"] else None,
                })

    report = {
        "suite": "xpay-review-volume",
        "n_transfers": N,
        "seed": SEED,
        "data_note": "synthetic name combinations from common Bangladeshi name pools; "
                     "sanctions list is the 10-entry local sample — re-measure against the "
                     "official SDN file before any production claim",
        "decisions": dict(decisions),
        "reviews_per_1000_transfers": round(review_transfers / N * 1000, 1),
        "review_share_pct": round(review_transfers / N * 100, 2),
        "flagged_examples": flagged_examples,
    }
    out = Path(__file__).resolve().parents[1] / "reports" / "review_volume.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nwritten: {out}")


if __name__ == "__main__":
    main()
