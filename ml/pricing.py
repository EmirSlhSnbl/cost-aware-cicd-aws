"""Fargate cost formulas (eu-central-1, Linux/x86).

The constants below are the only place where prices live. Check them against
https://aws.amazon.com/fargate/pricing/ and the AWS Pricing Calculator before
quoting numbers in the thesis. Not modelled on purpose: CloudWatch Logs
ingestion, ECR storage and S3 (a few cents per month in this project).
"""

HOURS_PER_MONTH = 730
VCPU_HOUR = 0.04656  # USD per vCPU-hour
GB_HOUR = 0.00511  # USD per GB-hour of memory
PUBLIC_IPV4_HOUR = 0.005  # USD per public IPv4 address-hour
EGRESS_GB_PRICE = 0.09  # USD per GB sent to the internet
EGRESS_FREE_GB = 100  # free monthly allowance (shared by the whole account)

# Valid Fargate sizes: vCPU -> allowed memory (GB)
VALID_SIZES = {
    0.25: [0.5, 1, 2],
    0.5: [1, 2, 3, 4],
    1: list(range(2, 9)),
    2: list(range(4, 17)),
    4: list(range(8, 31)),
}


def check_size(vcpu: float, memory_gb: float) -> None:
    if vcpu not in VALID_SIZES or memory_gb not in VALID_SIZES[vcpu]:
        raise ValueError(f"invalid Fargate size: {vcpu} vCPU / {memory_gb} GB")


def monthly_cost(
    vcpu: float,
    memory_gb: float,
    avg_tasks: float,
    hours_on: float,
    public_ip: bool = True,
    egress_gb: float = 0.0,
) -> float:
    """Cost in USD for one month.

    avg_tasks: average number of running tasks while the service is on
    hours_on:  hours per month the service is on (730 = always on)
    """
    check_size(vcpu, memory_gb)
    if avg_tasks < 0 or hours_on < 0 or egress_gb < 0:
        raise ValueError("avg_tasks, hours_on and egress_gb must be >= 0")
    task_hours = avg_tasks * hours_on
    compute = task_hours * (vcpu * VCPU_HOUR + memory_gb * GB_HOUR)
    ip = task_hours * PUBLIC_IPV4_HOUR if public_ip else 0.0
    egress = max(0.0, egress_gb - EGRESS_FREE_GB) * EGRESS_GB_PRICE
    return round(compute + ip + egress, 4)


def static_estimate(
    vcpu: float, memory_gb: float, desired_count: int, public_ip: bool = True
) -> float:
    """What a static tool assumes: always on, exactly `desired_count` tasks, no traffic."""
    return monthly_cost(vcpu, memory_gb, desired_count, HOURS_PER_MONTH, public_ip, 0.0)