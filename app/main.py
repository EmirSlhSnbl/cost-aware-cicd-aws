"""FinOps Guard sample service.

The service is small on purpose: the project is about the pipeline around it.
The endpoints exist to make a deployment observable (/version), health-checkable
(/health) and load-testable (/work) for the cost-prediction experiments.
"""

import json
import logging
import os
import sys
import time

from flask import Flask, g, jsonify, request

APP_VERSION = os.getenv("APP_VERSION", "dev")
MAX_WORK_MS = 500  # upper bound for /work so it cannot be used to burn CPU for long
STARTED_AT = time.time()
QUIET_PATHS = {"/health"}  # health probes run every few seconds: do not log them


class JsonFormatter(logging.Formatter):
    """One JSON object per line, easy to query in CloudWatch Logs."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "message": record.getMessage(),
            "version": APP_VERSION,
        }
        extra = getattr(record, "fields", None)
        if extra:
            payload.update(extra)
        return json.dumps(payload)


def _build_logger() -> logging.Logger:
    log = logging.getLogger("finops")
    if not log.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        log.addHandler(handler)
        log.setLevel(logging.INFO)
        log.propagate = False
    return log


logger = _build_logger()
app = Flask(__name__)


@app.before_request
def _start_timer():
    g.started = time.perf_counter()


@app.after_request
def _finish(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    if request.path not in QUIET_PATHS:
        duration_ms = round((time.perf_counter() - g.started) * 1000, 2)
        logger.info(
            "request",
            extra={
                "fields": {
                    "method": request.method,
                    "path": request.path,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                }
            },
        )
    return response


@app.get("/")
def index():
    return jsonify(message="Merhaba, FinOps Guard!", version=APP_VERSION)


@app.get("/health")
def health():
    # CHAOS_UNHEALTHY lets us rehearse a failed deployment on purpose (rollback demo).
    if os.getenv("CHAOS_UNHEALTHY") == "1":
        return jsonify(status="unhealthy"), 503
    return jsonify(status="ok"), 200


@app.get("/version")
def version():
    return jsonify(
        version=APP_VERSION, uptime_seconds=round(time.time() - STARTED_AT, 1)
    )


@app.get("/work")
def work():
    """Burn CPU for `ms` milliseconds. Used by load tests to generate usage data."""
    raw = request.args.get("ms", "100")
    try:
        ms = int(raw)
    except ValueError:
        return jsonify(error="ms must be an integer"), 400
    if ms < 1 or ms > MAX_WORK_MS:
        return jsonify(error=f"ms must be between 1 and {MAX_WORK_MS}"), 400

    deadline = time.perf_counter() + ms / 1000
    iterations = 0
    while time.perf_counter() < deadline:
        iterations += 1
    return jsonify(worked_ms=ms, iterations=iterations)


@app.errorhandler(404)
def not_found(_error):
    return jsonify(error="not found"), 404


@app.errorhandler(405)
def method_not_allowed(_error):
    return jsonify(error="method not allowed"), 405


@app.errorhandler(500)
def server_error(_error):
    return jsonify(error="internal server error"), 500