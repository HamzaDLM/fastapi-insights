from collections import defaultdict
from typing import Any

import pytest

from fastapi_insights.backends.base import MetricsStore
from fastapi_insights.backends.in_memory import InMemoryMetricsStore


class MockStore(MetricsStore):
    def __init__(
        self,
        fake_data: dict[int, dict[str, dict[str, Any]]],
        system_data: dict[str, Any],
    ):
        super().__init__()
        self._fake_data = fake_data
        self._system_data = system_data
        self.reset_calls = 0

    @property
    def bucket_sizes(self) -> list[int]:
        return [60, 300]

    def record_request_metrics(
        self, path: str, duration: float, status_code: int, method: str
    ) -> None:
        raise NotImplementedError

    async def _flush_system_metric_to_bucket(
        self, key: str, bucket_size: int, data: dict
    ) -> None:
        raise NotImplementedError

    def get_request_metrics_series(
        self, bucket_size: int, ts_from: int, ts_to: int
    ) -> dict[int, dict[str, dict[str, Any]]]:
        return self._fake_data

    def get_system_metrics_series(
        self, bucket_size: int, ts_from: int, ts_to: int
    ) -> dict[str, Any]:
        return self._system_data

    def reset(self) -> None:
        self.reset_calls += 1
        self._fake_data.clear()

    def _cleanup_expired_ttl(self) -> None:
        return None


@pytest.fixture
def mock_store() -> MockStore:
    return MockStore(
        fake_data={
            60: {
                "/": {
                    "latencies": [0.11, 0.15, 0.18],
                    "count": 3,
                    "errors": 0,
                    "status_codes": {"2XX": 3},
                    "methods": {"GET": 3},
                    "rw_count": {"read": 3, "write": 0},
                },
                "/items": {
                    "latencies": [0.40, 0.42, 0.44],
                    "count": 3,
                    "errors": 2,
                    "status_codes": {"2XX": 1, "4XX": 1, "5XX": 1},
                    "methods": {"GET": 1, "POST": 2},
                    "rw_count": {"read": 1, "write": 2},
                },
            },
            120: {
                "/": {
                    "latencies": [0.09, 0.10, 0.12],
                    "count": 3,
                    "errors": 0,
                    "status_codes": {"2XX": 3},
                    "methods": {"GET": 3},
                    "rw_count": {"read": 3, "write": 0},
                }
            },
        },
        system_data={
            "cpu_percent": [{"timestamp": 60, "min": 5.0, "max": 10.0, "avg": 7.5}]
        },
    )


def test_top_routes_and_method_breakdown(mock_store: MockStore) -> None:
    assert list(mock_store._get_top_routes(60, 0, 300, limit=2).keys()) == [
        "/",
        "/items",
    ]
    assert mock_store._get_requests_per_method(60, 0, 300) == {
        "GET": 7,
        "POST": 2,
    }


def test_latency_and_status_series(mock_store: MockStore) -> None:
    latencies = {
        item["name"]: item["data"]
        for item in mock_store._get_latency_series(60, 0, 300)
    }
    assert set(latencies) == {"/", "/items"}
    assert latencies["/"][0][0] == 60

    status_codes = {
        item["name"]: item["data"]
        for item in mock_store._get_status_code_series(60, 0, 300)
    }
    assert status_codes["2XX"] == [[60, 4], [120, 3]]
    assert status_codes["4XX"] == [[60, 1]]
    assert status_codes["5XX"] == [[60, 1]]


def test_get_metrics_and_table_overview(mock_store: MockStore) -> None:
    metrics = mock_store.get_metrics(0, 300, bucket_size=60)
    assert metrics["meta"]["bucket_size_secs"] == 60
    assert metrics["top_error_prone_requests"] == {"/items": 2, "/": 0}
    assert metrics["system_metrics"]["num_threads"] >= 1

    overview = mock_store.get_table_overview(0, 300)
    assert overview["total"] == 2
    assert overview["rows"]["/"]["total_call_count"] == 6
    assert overview["rows"]["/items"]["total_errors_count"] == 2
    assert overview["max_values"]["p99_latency"] >= overview["rows"]["/"]["p99_latency"]


def test_in_memory_store_records_expected_counts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = InMemoryMetricsStore()
    monkeypatch.setattr("fastapi_insights.backends.in_memory.time.time", lambda: 125.0)

    store.record_request_metrics("/users", 0.25, 201, "POST")

    bucket = store.get_request_metrics_series(bucket_size=5, ts_from=125, ts_to=125)[
        125
    ]["/users"]
    assert bucket["latencies"] == [0.25]
    assert bucket["count"] == 1
    assert bucket["errors"] == 0
    assert bucket["status_codes"] == {"2XX": 1}
    assert bucket["methods"] == {"POST": 1}
    assert bucket["rw_count"] == {"write": 1}


def test_in_memory_cleanup_removes_request_and_system_buckets() -> None:
    store = InMemoryMetricsStore(ttl_seconds=0)
    store._request_buckets[5][0]["/users"] = {
        "latencies": [0.1],
        "count": 1,
        "errors": 0,
        "status_codes": defaultdict(int, {"2XX": 1}),
        "methods": defaultdict(int, {"GET": 1}),
        "rw_count": defaultdict(int, {"read": 1}),
    }
    store._system_buckets[5][0]["cpu_percent"] = {
        "timestamp": 0,
        "min": 1.0,
        "max": 1.0,
        "avg": 1.0,
    }

    store._cleanup_expired_ttl()

    assert 0 not in store._request_buckets[5]
    assert 0 not in store._system_buckets[5]
