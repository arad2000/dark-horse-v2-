"""Lightweight async load probe for staging capacity baselines.

The probe measures application latency and throughput; it does not attempt to
model two million simultaneous users. Use a representative concurrency level
and request mix, then extrapolate only from measured infrastructure behavior.
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
    latency_ms: float
    status_code: int | None
    error: str | None = None


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    rank = (len(values) - 1) * p
    lo = int(rank)
    hi = min(lo + 1, len(values) - 1)
    frac = rank - lo
    return values[lo] + (values[hi] - values[lo]) * frac


def build_payload() -> dict[str, Any]:
    raw = os.getenv("SCALE_PAYLOAD_JSON", "").strip()
    if raw:
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError("SCALE_PAYLOAD_JSON must be a JSON object")
        return value
    return {
        "micro_motives": [],
        "sjt_answers": {},
        "conjoint_choices": {},
    }


async def request_once(
    client: httpx.AsyncClient,
    url: str,
    method: str,
    payload: dict[str, Any],
    semaphore: asyncio.Semaphore,
) -> Result:
    async with semaphore:
        started = time.perf_counter()
        try:
            if method == "GET":
                response = await client.get(url)
            else:
                response = await client.post(url, json=payload)
            elapsed = (time.perf_counter() - started) * 1000
            return Result(elapsed, response.status_code)
        except Exception as exc:  # pragma: no cover - network dependent
            elapsed = (time.perf_counter() - started) * 1000
            return Result(elapsed, None, str(exc))


async def run(args: argparse.Namespace) -> dict[str, Any]:
    method = args.method.upper()
    payload = build_payload() if method != "GET" else {}
    headers = {}
    if args.bearer:
        headers["Authorization"] = f"Bearer {args.bearer}"

    timeout = httpx.Timeout(args.timeout)
    limits = httpx.Limits(
        max_connections=max(args.concurrency, 1),
        max_keepalive_connections=max(args.concurrency, 1),
    )
    semaphore = asyncio.Semaphore(max(args.concurrency, 1))

    async with httpx.AsyncClient(
        headers=headers,
        timeout=timeout,
        limits=limits,
        follow_redirects=False,
    ) as client:
        for _ in range(max(args.warmup, 0)):
            result = await request_once(client, args.url, method, payload, semaphore)
            if result.status_code is None or result.status_code >= 500:
                break

        started = time.perf_counter()
        tasks = [
            asyncio.create_task(request_once(client, args.url, method, payload, semaphore))
            for _ in range(max(args.requests, 1))
        ]
        results = await asyncio.gather(*tasks)
        elapsed_s = max(time.perf_counter() - started, 0.000001)

    latencies = [r.latency_ms for r in results]
    ok = [r for r in results if r.status_code is not None and 200 <= r.status_code < 400]
    errors = [r for r in results if r.error]
    statuses: dict[str, int] = {}
    for result in results:
        key = str(result.status_code) if result.status_code is not None else "network_error"
        statuses[key] = statuses.get(key, 0) + 1

    return {
        "url": args.url,
        "method": method,
        "requests": len(results),
        "concurrency": args.concurrency,
        "warmup": args.warmup,
        "elapsed_s": round(elapsed_s, 3),
        "rps": round(len(results) / elapsed_s, 2),
        "success_rate": round(len(ok) / len(results), 4),
        "error_rate": round((len(results) - len(ok)) / len(results), 4),
        "latency_ms": {
            "min": round(min(latencies), 2),
            "mean": round(statistics.fmean(latencies), 2),
            "p50": round(percentile(latencies, 0.50), 2),
            "p95": round(percentile(latencies, 0.95), 2),
            "p99": round(percentile(latencies, 0.99), 2),
            "max": round(max(latencies), 2),
        },
        "statuses": statuses,
        "network_errors": errors[:10],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dark Horse staging scale baseline probe")
    parser.add_argument("--url", default=os.getenv("SCALE_BASE_URL", ""), help="Full endpoint URL")
    parser.add_argument("--method", default=os.getenv("SCALE_METHOD", "POST"), choices=["GET", "POST"])
    parser.add_argument("--requests", type=int, default=int(os.getenv("SCALE_REQUESTS", "200")))
    parser.add_argument("--concurrency", type=int, default=int(os.getenv("SCALE_CONCURRENCY", "20")))
    parser.add_argument("--warmup", type=int, default=int(os.getenv("SCALE_WARMUP", "10")))
    parser.add_argument("--timeout", type=float, default=float(os.getenv("SCALE_TIMEOUT", "30")))
    parser.add_argument("--bearer", default=os.getenv("SCALE_BEARER_TOKEN", ""))
    args = parser.parse_args()
    if not args.url:
        parser.error("--url or SCALE_BASE_URL is required")
    if args.requests < 1 or args.concurrency < 1 or args.warmup < 0:
        parser.error("requests and concurrency must be >= 1; warmup must be >= 0")
    return args


if __name__ == "__main__":
    print(json.dumps(asyncio.run(run(parse_args())), ensure_ascii=False, indent=2))
