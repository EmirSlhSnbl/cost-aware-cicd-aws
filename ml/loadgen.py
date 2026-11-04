"""Tiny load generator for the /work endpoint (standard library only).

Example:
    python loadgen.py --url http://localhost:8080 --stages 1:30,4:30,8:30 --work-ms 100 --out data/load.csv

--stages is a list of CONCURRENCY:SECONDS pairs run one after another, so a
single run produces low, medium and high load phases.
"""

import argparse
import csv
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path


def percentile(sorted_values: list[float], q: float) -> float:
    """Nearest-rank percentile, q in 0..100."""
    if not sorted_values:
        return float("nan")
    rank = max(1, -(-len(sorted_values) * q // 100))  # ceil
    return sorted_values[int(rank) - 1]


def parse_stages(text: str) -> list[tuple[int, float]]:
    stages = []
    for part in text.split(","):
        concurrency, seconds = part.split(":")
        stages.append((int(concurrency), float(seconds)))
    if not stages or any(c < 1 or s <= 0 for c, s in stages):
        raise ValueError("stages must look like 2:30,8:30 with positive numbers")
    return stages


def _worker(
    url: str, deadline: float, stage: int, results: list, lock: threading.Lock
) -> None:
    while time.monotonic() < deadline:
        started = time.monotonic()
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                response.read()
                status = response.status
        except urllib.error.HTTPError as exc:
            status = exc.code
        except (urllib.error.URLError, OSError):
            status = 0  # connection error or timeout
        latency_ms = (time.monotonic() - started) * 1000
        with lock:
            results.append((time.time(), stage, status, round(latency_ms, 2)))


def run(base_url: str, stages: list[tuple[int, float]], work_ms: int) -> list[tuple]:
    url = f"{base_url.rstrip('/')}/work?ms={work_ms}"
    results: list[tuple] = []
    lock = threading.Lock()
    for index, (concurrency, seconds) in enumerate(stages, start=1):
        deadline = time.monotonic() + seconds
        threads = [
            threading.Thread(target=_worker, args=(url, deadline, index, results, lock))
            for _ in range(concurrency)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    return results


def summarize(results: list[tuple]) -> dict:
    latencies = sorted(r[3] for r in results if r[2] == 200)
    total = len(results)
    errors = sum(1 for r in results if r[2] != 200)
    duration = (
        (max(r[0] for r in results) - min(r[0] for r in results)) if total > 1 else 0.0
    )
    return {
        "requests": total,
        "errors": errors,
        "error_rate_pct": 100 * errors / total if total else 0.0,
        "rps": total / duration if duration > 0 else float(total),
        "p50_ms": percentile(latencies, 50),
        "p90_ms": percentile(latencies, 90),
        "p99_ms": percentile(latencies, 99),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--url", required=True, help="base URL, e.g. http://localhost:8080"
    )
    parser.add_argument("--stages", default="1:10,4:10", help="CONCURRENCY:SECONDS,...")
    parser.add_argument("--work-ms", type=int, default=100)
    parser.add_argument(
        "--out", type=Path, default=None, help="optional CSV with every request"
    )
    args = parser.parse_args()

    results = run(args.url, parse_stages(args.stages), args.work_ms)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "stage", "status", "latency_ms"])
            writer.writerows(results)
    for key, value in summarize(results).items():
        print(f"{key}: {value:.1f}" if isinstance(value, float) else f"{key}: {value}")


if __name__ == "__main__":
    main()