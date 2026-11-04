import json
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

import collect_metrics
import evaluate
import loadgen
import pricing
import simulate


# ---------- pricing ----------
def test_always_on_smallest_task_costs_about_14_dollars():
    cost = pricing.static_estimate(0.25, 0.5, 1)
    assert 13.5 < cost < 14.5


def test_cost_scales_linearly_with_tasks_and_hours():
    one = pricing.monthly_cost(0.5, 1, 1, 100)
    assert pricing.monthly_cost(0.5, 1, 2, 100) == pytest.approx(2 * one, rel=1e-6)
    assert pricing.monthly_cost(0.5, 1, 1, 200) == pytest.approx(2 * one, rel=1e-6)


def test_public_ip_adds_cost():
    with_ip = pricing.monthly_cost(0.25, 0.5, 1, 730, public_ip=True)
    without = pricing.monthly_cost(0.25, 0.5, 1, 730, public_ip=False)
    assert with_ip - without == pytest.approx(730 * pricing.PUBLIC_IPV4_HOUR, abs=1e-3)


def test_egress_is_free_below_allowance_and_paid_above():
    base = pricing.monthly_cost(0.25, 0.5, 1, 10)
    assert pricing.monthly_cost(0.25, 0.5, 1, 10, egress_gb=100) == base
    extra = pricing.monthly_cost(0.25, 0.5, 1, 10, egress_gb=200) - base
    assert extra == pytest.approx(100 * pricing.EGRESS_GB_PRICE, abs=1e-3)


@pytest.mark.parametrize("vcpu,mem", [(0.25, 8), (3, 4), (1, 1)])
def test_invalid_fargate_sizes_are_rejected(vcpu, mem):
    with pytest.raises(ValueError):
        pricing.monthly_cost(vcpu, mem, 1, 1)


def test_negative_values_are_rejected():
    with pytest.raises(ValueError):
        pricing.monthly_cost(0.25, 0.5, -1, 1)


# ---------- simulate ----------
def test_simulation_is_deterministic_for_a_seed():
    assert simulate.generate(50, seed=1) == simulate.generate(50, seed=1)
    assert simulate.generate(50, seed=1) != simulate.generate(50, seed=2)


def test_simulated_rows_are_valid_and_positive():
    for row in simulate.generate(300, seed=3):
        assert set(row) == set(simulate.FIELDS)
        assert row["actual_cost"] > 0
        assert row["memory_gb"] in pricing.VALID_SIZES[row["vcpu"]]
        assert 0 < row["duty_cycle"] <= 1


def test_csv_round_trip(tmp_path):
    rows = simulate.generate(20, seed=4)
    path = tmp_path / "d.csv"
    simulate.write_csv(rows, path)
    back = evaluate.read_rows(path)
    assert len(back) == 20
    assert back[0]["actual_cost"] == pytest.approx(rows[0]["actual_cost"])


# ---------- evaluate ----------
def test_score_of_a_perfect_prediction():
    s = evaluate.score([1.0, 2.0], [1.0, 2.0])
    assert s["mae"] == 0 and s["mape"] == 0 and s["under_pct"] == 0


def test_score_counts_underestimates():
    s = evaluate.score([10.0, 10.0], [5.0, 20.0])
    assert s["under_pct"] == 50.0 and s["p90_coverage"] == 50.0


def test_score_rejects_bad_input():
    with pytest.raises(ValueError):
        evaluate.score([], [])
    with pytest.raises(ValueError):
        evaluate.score([1.0], [1.0, 2.0])


def test_static_estimate_overshoots_dev_and_misses_prod():
    result = evaluate.report(simulate.generate(3000, seed=42))
    assert result["dev"]["p90_coverage"] > 95  # dev is mostly switched off
    assert (
        result["prod"]["under_pct"] > 50
    )  # autoscaling and traffic are not in the estimate
    assert result["dev"]["mape"] > 1.0  # more than 100% off on average
    assert "all" in evaluate.format_report(result)


# ---------- loadgen ----------
def test_percentile_nearest_rank():
    values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    assert loadgen.percentile(values, 50) == 5.0
    assert loadgen.percentile(values, 90) == 9.0
    assert loadgen.percentile(values, 100) == 10.0
    assert loadgen.percentile([], 50) != loadgen.percentile([], 50)  # NaN


def test_parse_stages():
    assert loadgen.parse_stages("2:30,8:15") == [(2, 30.0), (8, 15.0)]
    with pytest.raises(ValueError):
        loadgen.parse_stages("0:10")


def _serve(status):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            body = json.dumps({"ok": True}).encode()
            self.send_response(status)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


@pytest.mark.parametrize("status,expected_errors", [(200, False), (500, True)])
def test_loadgen_against_a_stub_server(status, expected_errors):
    server = _serve(status)
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}"
        results = loadgen.run(url, [(2, 0.5)], work_ms=10)
    finally:
        server.shutdown()
    summary = loadgen.summarize(results)
    assert summary["requests"] > 0
    assert (summary["errors"] > 0) == expected_errors


def test_loadgen_counts_connection_errors_as_status_zero():
    results = loadgen.run("http://127.0.0.1:1", [(1, 0.3)], work_ms=10)
    assert results and all(r[2] == 0 for r in results)


# ---------- collect_metrics ----------
class FakeCloudWatch:
    def __init__(self):
        self.calls = []

    def get_metric_statistics(self, **kwargs):
        self.calls.append(kwargs)
        t1 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 1, 1, 12, 1, tzinfo=timezone.utc)
        base = 10.0 if kwargs["MetricName"] == "CPUUtilization" else 20.0
        return {
            "Datapoints": [
                {"Timestamp": t2, "Average": base + 1, "Maximum": base + 2},
                {"Timestamp": t1, "Average": base, "Maximum": base + 1},
            ]
        }


def test_fetch_merges_metrics_by_timestamp_and_sorts(tmp_path):
    client = FakeCloudWatch()
    start = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    rows = collect_metrics.fetch(client, "c", "s", start, start)
    assert [r["cpu_avg"] for r in rows] == [10.0, 11.0]
    assert [r["mem_max"] for r in rows] == [21.0, 22.0]
    assert {c["MetricName"] for c in client.calls} == {
        "CPUUtilization",
        "MemoryUtilization",
    }
    out = tmp_path / "m.csv"
    collect_metrics.write_csv(rows, out)
    assert (
        out.read_text().splitlines()[0] == "timestamp,cpu_avg,cpu_max,mem_avg,mem_max"
    )
