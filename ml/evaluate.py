"""Scores the static (Infracost-style) estimate against the simulated actual cost.

Metrics (computed per environment and overall):
    MAE            mean absolute error in USD
    MAPE           mean absolute percentage error
    under%         share of rows where actual > estimate (the budget would be exceeded)
    P90 coverage   share of rows where actual <= estimate. A good P90 forecast
                   should land close to 90%.
"""

import argparse
import csv
from pathlib import Path


def read_rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return [
            {k: (v if k == "env" else float(v)) for k, v in row.items()}
            for row in csv.DictReader(f)
        ]


def score(actuals: list[float], predictions: list[float]) -> dict:
    n = len(actuals)
    if n == 0 or n != len(predictions):
        raise ValueError("need two non-empty lists of the same length")
    errors = [abs(a - p) for a, p in zip(actuals, predictions)]
    pct = [abs(a - p) / a for a, p in zip(actuals, predictions) if a > 0]
    covered = sum(1 for a, p in zip(actuals, predictions) if a <= p)
    return {
        "n": n,
        "mae": sum(errors) / n,
        "mape": sum(pct) / len(pct) if pct else float("nan"),
        "under_pct": 100 * (n - covered) / n,
        "p90_coverage": 100 * covered / n,
    }


def report(rows: list[dict], pred_key: str = "static_estimate") -> dict[str, dict]:
    groups = {"all": rows}
    for env in sorted({r["env"] for r in rows}):
        groups[env] = [r for r in rows if r["env"] == env]
    return {
        name: score([r["actual_cost"] for r in g], [r[pred_key] for r in g])
        for name, g in groups.items()
    }


def format_report(result: dict[str, dict]) -> str:
    lines = [
        f"{'group':<8}{'n':>6}{'MAE $':>10}{'MAPE':>9}{'under %':>10}{'P90 cov %':>11}"
    ]
    for name, s in result.items():
        lines.append(
            f"{name:<8}{s['n']:>6}{s['mae']:>10.2f}{s['mape'] * 100:>8.0f}%{s['under_pct']:>10.1f}{s['p90_coverage']:>11.1f}"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data", type=Path, default=Path("data/simulated_costs.csv"))
    args = parser.parse_args()
    print(format_report(report(read_rows(args.data))))


if __name__ == "__main__":
    main()
