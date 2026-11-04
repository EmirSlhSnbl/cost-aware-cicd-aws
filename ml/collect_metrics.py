"""Downloads ECS CPU and memory utilisation from CloudWatch into a CSV.

Needs AWS credentials on your computer (the same ones the aws CLI uses) and
`pip install boto3`.

Example:
    python collect_metrics.py --cluster finops-guard-dev --service finops-guard-dev --minutes 30 --out data/metrics.csv
"""

import argparse
import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path

METRICS = {"CPUUtilization": "cpu", "MemoryUtilization": "mem"}


def fetch(
    client, cluster: str, service: str, start: datetime, end: datetime, period: int = 60
) -> list[dict]:
    """Returns one row per timestamp with cpu_avg, cpu_max, mem_avg, mem_max."""
    rows: dict[datetime, dict] = {}
    for metric, short in METRICS.items():
        response = client.get_metric_statistics(
            Namespace="AWS/ECS",
            MetricName=metric,
            Dimensions=[
                {"Name": "ClusterName", "Value": cluster},
                {"Name": "ServiceName", "Value": service},
            ],
            StartTime=start,
            EndTime=end,
            Period=period,
            Statistics=["Average", "Maximum"],
        )
        for point in response.get("Datapoints", []):
            row = rows.setdefault(
                point["Timestamp"], {"timestamp": point["Timestamp"].isoformat()}
            )
            row[f"{short}_avg"] = round(point["Average"], 2)
            row[f"{short}_max"] = round(point["Maximum"], 2)
    return [rows[t] for t in sorted(rows)]


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["timestamp", "cpu_avg", "cpu_max", "mem_avg", "mem_max"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cluster", required=True)
    parser.add_argument("--service", required=True)
    parser.add_argument("--minutes", type=int, default=30)
    parser.add_argument("--region", default="eu-central-1")
    parser.add_argument("--out", type=Path, default=Path("data/metrics.csv"))
    args = parser.parse_args()

    import boto3  # imported here so the tests do not need boto3

    client = boto3.client("cloudwatch", region_name=args.region)
    end = datetime.now(timezone.utc)
    rows = fetch(
        client, args.cluster, args.service, end - timedelta(minutes=args.minutes), end
    )
    write_csv(rows, args.out)
    print(f"wrote {len(rows)} rows to {args.out}")


if __name__ == "__main__":
    main()