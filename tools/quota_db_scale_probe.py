"""Async PostgreSQL-backed auth/quota scale probe for disposable CI only."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import uuid
from dataclasses import dataclass
from pathlib import Path
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


def load_users(path: str) -> list[dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise ValueError("scale auth file must contain a non-empty JSON list")
    for row in data:
        if not isinstance(row, dict) or not row.get("token"):
            raise ValueError("each scale auth row must contain a token")
    return data


async def request_once(client: httpx.AsyncClient, replica: str, mode: str, user: dict[str, Any], semaphore: asyncio.Semaphore) -> Result:
    async with semaphore:
        started = asyncio.get_running_loop().time()
        headers = {"Authorization": f"Bearer {user['token']}"}
        try:
            if mode == "quota":
                response = await client.get(f"{replica}/api/v1/me/quota", headers=headers)
            else:
                response = await client.post(
                    f"{replica}/api/v1/me/consume-test",
                    headers=headers,
                    json={"session_uuid": str(uuid.uuid4())},
                )
            elapsed = (asyncio.get_running_loop().time() - started) * 1000
            return Result(replica, elapsed, response.status_code)
        except Exception as exc:
            elapsed = (asyncio.get_running_loop().time() - started) * 1000
            return Result(replica, elapsed, None, str(exc))


def summarize(results: list[Result], mode: str, elapsed_s: float) -> dict[str, Any]:
    latencies = [r.latency_ms for r in results]
    successful = [r for r in results if r.status_code is not None and 200 <= r.status_code < 400]
    per_replica: dict[str, dict[str, Any]] = {}
    for replica in sorted({r.replica for r in results}):
        subset = [r for r in results if r.replica == replica]
        vals = [r.latency_ms for r in subset]
        ok = [r for r in subset if r.status_code is not None and 200 <= r.status_code < 400]
        per_replica[replica] = {
            "requests": len(subset),
            "success_rate": round(len(ok) / len(subset), 4),
            "p50_ms": round(percentile(vals, 0.50), 2),
            "p95_ms": round(percentile(vals, 0.95), 2),
            "p99_ms": round(percentile(vals, 0.99), 2),
        }
    statuses: dict[str, int] = {}
    for result in results:
        key = str(result.status_code) if result.status_code is not None else "network_error"
        statuses[key] = statuses.get(key, 0) + 1
    return {
        "mode": mode,
        "users_in_pool": int(os.getenv("SCALE_USER_COUNT", "0")),
        "requests": len(results),
        "concurrency": int(os.getenv("SCALE_CONCURRENCY", "0")),
        "warmup": int(os.getenv("SCALE_WARMUP", "0")),
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
        "statuses": statuses,
        "network_errors": [r.error for r in results if r.error][:10],
        "replicas": per_replica,
    }


async def run(args: argparse.Namespace) -> dict[str, Any]:
    replicas = [value.strip().rstrip("/") for value in args.replicas.split(",") if value.strip()]
    if not replicas:
        raise ValueError("at least one replica URL is required")
    users = load_users(args.auth_file)
    semaphore = asyncio.Semaphore(max(args.concurrency, 1))
    limits = httpx.Limits(max_connections=max(args.concurrency, 1), max_keepalive_connections=max(args.concurrency, 1))
    async with httpx.AsyncClient(timeout=httpx.Timeout(args.timeout), limits=limits) as client:
        for i in range(max(args.warmup, 0)):
            await request_once(client, replicas[i % len(replicas)], args.mode, users[i % len(users)], semaphore)
        started = asyncio.get_running_loop().time()
        tasks = [
            asyncio.create_task(request_once(client, replicas[i % len(replicas)], args.mode, users[i % len(users)], semaphore))
            for i in range(max(args.requests, 1))
        ]
        results = await asyncio.gather(*tasks)
        elapsed_s = max(asyncio.get_running_loop().time() - started, 0.000001)
    return summarize(results, args.mode, elapsed_s)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replicas", default=os.getenv("SCALE_REPLICA_URLS", ""))
    parser.add_argument("--mode", choices=["quota", "consume"], default=os.getenv("SCALE_MODE", "quota"))
    parser.add_argument("--auth-file", default=os.getenv("SCALE_AUTH_FILE", "/tmp/darkhorse-scale-users.json"))
    parser.add_argument("--requests", type=int, default=int(os.getenv("SCALE_REQUESTS", "300")))
    parser.add_argument("--concurrency", type=int, default=int(os.getenv("SCALE_CONCURRENCY", "30")))
    parser.add_argument("--warmup", type=int, default=int(os.getenv("SCALE_WARMUP", "15")))
    parser.add_argument("--timeout", type=float, default=float(os.getenv("SCALE_TIMEOUT", "60")))
    args = parser.parse_args()
    if not args.replicas:
        parser.error("--replicas or SCALE_REPLICA_URLS is required")
    if args.requests < 1 or args.concurrency < 1 or args.warmup < 0:
        parser.error("requests and concurrency must be >= 1; warmup must be >= 0")
    return args


if __name__ == "__main__":
    print(json.dumps(asyncio.run(run(parse_args())), ensure_ascii=False, indent=2))
