# Load test — end-to-end HTTP p95 for the quote pipeline
"""Measures what the KPI docs cite: not the in-process engine time, but the full
HTTP round trip against a running uvicorn (parse -> score -> screen ->
persist -> serialize).

Prereq: backend running on :8000 (make run-backend, or docker compose up).

Run:  backend/.venv/bin/python scripts/load_test_p95.py [n_requests]
Default n=300 sequential keep-alive requests to POST /api/agent/quote.

NOTE: this is a single-client latency measurement from the same host — it is
NOT a capacity/load benchmark (no concurrency ramp, no cross-region network).
Results land in reports/load_test.txt; the README KPI table cites that file
instead of a hand-copied number.
"""
import json
import os
import statistics
import sys
import time
import urllib.request

BASE = os.environ.get("XPAY_BASE_URL", "http://localhost:8000")
BODY = json.dumps({"amount": 1000, "payout_method": "BKASH",
                   "text": "Send 1,000 dirhams to my mother's bKash in Dhaka"}).encode()


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    timings = []
    codes = {}
    for _ in range(n):
        req = urllib.request.Request(f"{BASE}/api/agent/quote", data=BODY,
                                     headers={"Content-Type": "application/json"})
        t0 = time.perf_counter()
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
            code = resp.status
        timings.append((time.perf_counter() - t0) * 1000.0)
        codes[code] = codes.get(code, 0) + 1
    timings.sort()
    p50 = timings[int(0.50 * (len(timings) - 1))]
    p95 = timings[int(0.95 * (len(timings) - 1))]
    p99 = timings[min(len(timings) - 1, int(0.99 * (len(timings) - 1)))]
    print(f"requests={n} statuses={codes}")
    print(f"end-to-end HTTP POST /api/agent/quote vs localhost uvicorn:")
    print(f"  p50={p50:.1f}ms p95={p95:.1f}ms p99={p99:.1f}ms "
          f"mean={statistics.mean(timings):.1f}ms max={max(timings):.1f}ms")


if __name__ == "__main__":
    main()
