from __future__ import annotations

from collections import defaultdict
from time import time as monotonic_time

import redis
from redis.exceptions import RedisError

from app.core.config import settings


fallback_rate_limit_store: dict[str, list[float]] = defaultdict(list)
_redis_client: redis.Redis | None = None
_redis_disabled_until = 0.0


class RateLimitExceeded(Exception):
    pass


def _client() -> redis.Redis | None:
    global _redis_client, _redis_disabled_until

    now = monotonic_time()
    if now < _redis_disabled_until:
        return None
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=0.2,
            socket_timeout=0.2,
        )
    return _redis_client


def _disable_redis_temporarily() -> None:
    global _redis_disabled_until
    _redis_disabled_until = monotonic_time() + 30


def _check_fallback(key: str, *, max_requests: int, window_seconds: int) -> None:
    now = monotonic_time()
    fallback_rate_limit_store[key] = [
        ts for ts in fallback_rate_limit_store[key] if now - ts < window_seconds
    ]
    if len(fallback_rate_limit_store[key]) >= max_requests:
        raise RateLimitExceeded
    fallback_rate_limit_store[key].append(now)


def check_rate_limit(key: str, *, max_requests: int, window_seconds: int) -> None:
    client = _client()
    if client is None:
        _check_fallback(key, max_requests=max_requests, window_seconds=window_seconds)
        return

    redis_key = f"blocktest:rate-limit:{key}"
    try:
        count = client.incr(redis_key)
        if count == 1:
            client.expire(redis_key, window_seconds)
        if count > max_requests:
            raise RateLimitExceeded
    except RedisError:
        _disable_redis_temporarily()
        _check_fallback(key, max_requests=max_requests, window_seconds=window_seconds)


def clear_rate_limit_state() -> None:
    fallback_rate_limit_store.clear()
    client = _client()
    if client is None:
        return

    try:
        cursor = 0
        while True:
            cursor, keys = client.scan(
                cursor=cursor,
                match="blocktest:rate-limit:*",
                count=100,
            )
            if keys:
                client.delete(*keys)
            if cursor == 0:
                break
    except RedisError:
        _disable_redis_temporarily()
