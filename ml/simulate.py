"""Simulated history of monthly Fargate bills.

Why simulate? A student project does not have hundreds of real bills. The
simulator creates them from stated assumptions so the data pipeline and the
evaluation code can be built and tested now. Real measurements (Week 6, step 6)
are used to sanity-check the assumptions. Results on simulated data prove that
the code works, not that a model is good in the real world.

Known at pull-request time (usable as model features):
    env, vcpu, memory_gb, desired_count, public_ip
Only known after the month is over (latent, never use as features):
    duty_cycle, task_multiplier, egress_gb
Target:
    actual_cost
"""

import argparse
import csv
import random
from pathlib import Path

from pricing import HOURS_PER_MONTH, VALID_SIZES, monthly_cost, static_estimate

FIELDS = [
    "env",
    "vcpu",
    "memory_gb",
    "desired_count",
    "public_ip",
    "duty_cycle",
    "task_multiplier",
    "egress_gb",
    "static_estimate",
    "actual_cost",
]

# Assumptions per environment (documented so they can be challenged and calibrated)
PROFILES = {
    # dev: switched on for demos, mostly off
    "dev": {
        "sizes": [0.25, 0.5],
        "count": [1, 1, 1, 2],
        "duty": (2, 6),
        "scale": (0.0, 0.0),
        "egress": (1.0, 0.8),
    },
    # staging: on during working days
    "staging": {
        "sizes": [0.25, 0.5, 1],
        "count": [1, 2],
        "duty": (5, 2),
        "scale": (0.05, 0.05),
        "egress": (2.5, 0.8),
    },
    # prod: always on, autoscaling adds tasks, real traffic
    "prod": {
        "sizes": [0.5, 1, 2],
        "count": [2, 2, 3, 4],
        "duty": (60, 1),
        "scale": (0.25, 0.15),
        "egress": (4.2, 0.8),
    },
}
ENV_WEIGHTS = {"dev": 0.5, "staging": 0.3, "prod": 0.2}


def sample_row(rng: random.Random) -> dict:
    env = rng.choices(list(ENV_WEIGHTS), weights=list(ENV_WEIGHTS.values()))[0]
    p = PROFILES[env]
    vcpu = rng.choice(p["sizes"])
    memory_gb = rng.choice(VALID_SIZES[vcpu])
    desired_count = rng.choice(p["count"])
    public_ip = rng.random() < 0.8

    duty_cycle = min(1.0, rng.betavariate(*p["duty"]))
    mean, sd = p["scale"]
    task_multiplier = 1.0 + max(0.0, rng.gauss(mean, sd))
    egress_gb = rng.lognormvariate(*p["egress"])  # median e^mu GB

    actual = monthly_cost(
        vcpu,
        memory_gb,
        desired_count * task_multiplier,
        HOURS_PER_MONTH * duty_cycle,
        public_ip,
        egress_gb,
    )
    actual = round(
        actual * rng.lognormvariate(0, 0.03), 4
    )  # billing rounding, minor extras

    return {
        "env": env,
        "vcpu": vcpu,
        "memory_gb": memory_gb,
        "desired_count": desired_count,
        "public_ip": int(public_ip),
        "duty_cycle": round(duty_cycle, 4),
        "task_multiplier": round(task_multiplier, 4),
        "egress_gb": round(egress_gb, 2),
        "static_estimate": static_estimate(vcpu, memory_gb, desired_count, public_ip),
        "actual_cost": actual,
    }


def generate(n: int, seed: int = 42) -> list[dict]:
    rng = random.Random(seed)
    return [sample_row(rng) for _ in range(n)]


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--rows", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=Path("data/simulated_costs.csv"))
    args = parser.parse_args()
    rows = generate(args.rows, args.seed)
    write_csv(rows, args.out)
    print(f"wrote {len(rows)} rows to {args.out}")


if __name__ == "__main__":
    main()