import pytest

pytest.importorskip("redis")

import fastapi_insights.backends.redis as redis_backends


class FakeAsyncRedis:
    def __init__(self):
        self.hset_calls: list[tuple[str, str, str]] = []
        self.expire_calls: list[tuple[str, int]] = []

    async def hset(self, key: str, field: str, value: str) -> None:
        self.hset_calls.append((key, field, value))

    async def expire(self, key: str, ttl_seconds: int) -> None:
        self.expire_calls.append((key, ttl_seconds))


@pytest.mark.anyio
async def test_async_redis_system_metric_flush_applies_ttl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(redis_backends, "AsyncRedis", FakeAsyncRedis)
    client = FakeAsyncRedis()
    store = redis_backends.AsyncRedisMetricsStore(client, ttl_seconds=30)

    await store._flush_system_metric_to_bucket(
        "cpu_percent",
        5,
        {"timestamp": 10, "min": 1.0, "max": 2.0, "avg": 1.5},
    )

    assert client.hset_calls == [
        (
            "system-metrics:5:10",
            "cpu_percent",
            '{"timestamp": 10, "min": 1.0, "max": 2.0, "avg": 1.5}',
        )
    ]
    assert client.expire_calls == [("system-metrics:5:10", 30)]
