import json
from typing import Any

import redis
from flask import current_app


_fallback_store: dict[str, str] = {}


def redis_client() -> redis.Redis:
    return redis.from_url(current_app.config["REDIS_URL"], decode_responses=True)


def set_json(key: str, value: dict[str, Any], ex_seconds: int):
    serialized = json.dumps(value)
    try:
        redis_client().setex(key, ex_seconds, serialized)
    except redis.RedisError:
        _fallback_store[key] = serialized


def get_json(key: str) -> dict[str, Any] | None:
    try:
        raw = redis_client().get(key)
    except redis.RedisError:
        raw = _fallback_store.get(key)
    if not raw:
        return None
    return json.loads(raw)


def delete_key(key: str):
    try:
        redis_client().delete(key)
    except redis.RedisError:
        _fallback_store.pop(key, None)
