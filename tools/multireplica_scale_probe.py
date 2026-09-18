"""Round-robin async load probe for multiple local API replicas.

The probe intentionally targets explicit replica URLs. It reports aggregate
latency/throughput plus per-replica status so regressions in one worker are visible.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import time
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(slots=True)
class Result:
    replica: str
    latency_ms: float
    status_code: int | None
    error: str | None = None


def percentile(values: list[float], p: float) -> float:
    values = sorted(values)
    if not values:
        return 0.0
    rank = (len(values) - 1) * p
    lo = int(rank)
    hi = min(lo + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (rank - lo)


def payload() -> dict[str, Any]:
    raw = os.getenv("SCALE_PAYLOAD_JSON", "").strip()
    if raw:
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError("SCALE_PAYLOAD_JSON must be a JSON object")
        return value
    return {"micro_motives": ["MED-001", "MED-002", "MED-003"], "sjt_answers": {"sjt_1": "A"}, "conjoint_choices": {"conj_1": "Q1A"}}


async def request_once(client: httpx.AsyncClient, url: str, body: dict[str, Any], semaphore: asyncio.Semaphore) -> Result:
    async with semaphore:
        started = time.perf_counter()
        try:
            response = await client.post(url, json=body)
            return Result(url, (time.perf_counter() - started) * 1000, response.status_code)
        except Exception as exc:  # pragma: no cover - network dependent
            return Result(url, (time.perf_counter() - started) * 1000, None, str(exc))


def summarize(results: list[Result], elapsed_s: float) -> dict[str, Any]:
    latencies = [r.latency_ms for r in results]
    successful = [r for r in results if r.status_code is not None and 200 <= r.status_code < 400]
    replicas: dict[str, dict[str, Any]] = {}
    for replica in sorted({r.replica for r in results}):
        subset = [r for r in results if r.replica == replica]
        subset_latencies = [r.latency_ms for r in subset]
        subset_ok = [r for r in subset if r.status_code is not None and 200 <= r.status_code < 400]
        replicas[replica] = {
            "requests": len(subset),
            "success_rate": round(len(subset_ok) / len(subset), 4),
            "p50_ms": round(percentile(subset_latencies, 0.50), 2),
            "p95_ms": round(percentile(subset_latencies, 0.95), 2),
            "p99_ms": round(percentile(subset_latencies, 0.99), 2),
        }
    return {
        "replicas": replicas,
        "requests": len(results),
        "elapsed_s": round(elapsed_s, 3),
        "rps": round(len(results) / max(elapsed_s, 0.000001), 2),
        "success_rate": round(len(successful) / len(results), 4),
        "error_rate": round((len(results) - len(successful)) / len(results), 4),
        "latency_ms": {
            "min": round(min(latencies), 2),
            "mean": round(statistics.fmean(latencies), 2),
            "p50": round(percentile(latencies, 0.50), 2),
            "p95": round(percentile(latencies, 0.95), 2),
            "p99": round(percentile(latencies, 0.99), 2),
            "max": round(max(latencies), 2),
        },
        "statuses": {str(code): sum(1 for r in results if r.status_code == code) for code in sorted({r.status_code for r in results if r.status_code is not None})},
        "network_errors": [r.error for r in results if r.error][:10],
    }


async def run(args: argparse.Namespace) -> dict[str, Any]:
    replicas = [value.strip().rstrip("/") for value in args.urls.split(",") if value.strip()]
    if not replicas:
        raise ValueError("at least one replica URL is required")
    body = payload()
    semaphore = asyncio.Semaphore(max(args.concurrency, 1))
    limits = httpx.Limits(max_connections=max(args.concurrency, 1), max_keepalive_connections=max(args.concurrency, 1))
    async with httpx.AsyncClient(timeout=httpx.Timeout(args.timeout), limits=limits) as client:
        for i in range(max(args.warmup, 0)):
            await request_once(client, replicas[i % len(replicas)], body, semaphore)
        started = time.perf_counter()
        tasks = [asyncio.create_task(request_once(client, replicas[i % len(replicas)], body, semaphore)) for i in range(max(args.requests, 1))]
        results = await asyncio.gather(*tasks)
        elapsed_s = max(time.perf_counter() - started, 0.000001)
    return summarize(results, elapsed_s)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dark Horse multi-replica PostgreSQL scale probe")
    parser.add_argument("--urls", default=os.getenv("SCALE_REPLICA_URLS", ""))
    parser.add_argument("--requests", type=int, default=int(os.getenv("SCALE_REQUESTS", "300")))
    parser.add_argument("--concurrency", type=int, default=int(os.getenv("SCALE_CONCURRENCY", "30")))
    parser.add_argument("--warmup", type=int, default=int(os.getenv("SCALE_WARMUP", "15")))
    parser.add_argument("--timeout", type=float, default=float(os.getenv("SCALE_TIMEOUT", "60")))
    args = parser.parse_args()
    if not args.urls:
        parser.error("--urls or SCALE_REPLICA_URLS is required")
    if args.requests < 1 or args.concurrency < 1 or args.warmup < 0:
        parser.error("requests and concurrency must be >= 1; warmup must be >= 0")
    return args


if __name__ == "__main__":
    print(json.dumps(asyncio.run(run(parse_args())), ensure_ascii=False, indent=2))
