import time
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fastapi_insights import Config, FastAPIInsights
from fastapi_insights.backends.base import MetricsStore
from fastapi_insights.backends.in_memory import InMemoryMetricsStore


class CountingStore(MetricsStore):
    def __init__(self):
        super().__init__()
        self.system_metrics_calls = 0
        self.cleanup_calls = 0

    @property
    def bucket_sizes(self) -> list[int]:
        return [5]

    async def record_system_metrics(self) -> None:
        self.system_metrics_calls += 1

    def record_request_metrics(
        self, path: str, duration: float, status_code: int, method: str
    ) -> None:
        return None

    async def _flush_system_metric_to_bucket(
        self, key: str, bucket_size: int, data: dict
    ) -> None:
        return None

    def get_request_metrics_series(
        self, bucket_size: int, ts_from: int, ts_to: int
    ) -> dict[int, dict[str, dict[str, Any]]]:
        return {}

    def get_system_metrics_series(
        self, bucket_size: int, ts_from: int, ts_to: int
    ) -> dict[str, list[dict[str, Any]]]:
        return {}

    def reset(self) -> None:
        return None

    def _cleanup_expired_ttl(self) -> None:
        self.cleanup_calls += 1


def wait_for(predicate, timeout: float = 1.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("condition was not met before timeout")


def build_app(
    store: MetricsStore | None = None, config: Config | None = None
) -> tuple[FastAPI, InMemoryMetricsStore | MetricsStore]:
    app = FastAPI()
    metrics_store = store or InMemoryMetricsStore()

    @app.get("/ok")
    async def ok():
        return {"ok": True}

    FastAPIInsights.init(app, metrics_store, config=config or Config())
    return app, metrics_store


def test_metrics_routes_respect_custom_path_and_reset_contract() -> None:
    app, _ = build_app(
        config=Config(
            custom_path="/stats",
            ui_config_route="/custom-dashboard-config",
            ui_title="Custom Metrics",
        )
    )

    with TestClient(app) as client:
        response = client.get("/ok")
        assert response.status_code == 200

        config_response = client.get("/stats/_dashboard_config")
        assert config_response.status_code == 200
        assert config_response.json() == {"title": "Custom Metrics"}

        legacy_config_response = client.get("/custom-dashboard-config")
        assert legacy_config_response.status_code == 200
        assert legacy_config_response.json() == {"title": "Custom Metrics"}

        metrics_response = client.get("/stats/json", params={"ts_from": 0})
        assert metrics_response.status_code == 200
        metrics_payload = metrics_response.json()
        assert metrics_payload["meta"]["bucket_size_secs"] >= 5
        assert metrics_payload["top_routes"]["/ok"] >= 1

        overview_response = client.get("/stats/table_overview", params={"ts_from": 0})
        assert overview_response.status_code == 200
        overview_payload = overview_response.json()
        assert overview_payload["rows"]["/ok"]["total_call_count"] >= 1

        reset_response = client.delete("/stats/reset")
        assert reset_response.status_code == 204
        assert reset_response.content == b""

        html_response = client.get("/stats/")
        assert html_response.status_code == 200

        js_response = client.get("/stats/main.js")
        assert js_response.status_code == 200
        assert "/metrics/json" not in js_response.text
        assert "/config-b887e852-bd12-41f2-b057-1bd31eb5443e" not in js_response.text
        assert "/_dashboard_config" in js_response.text


def test_duplicate_init_is_idempotent() -> None:
    app = FastAPI()

    @app.get("/ok")
    async def ok():
        return {"ok": True}

    store = InMemoryMetricsStore()
    config = Config(custom_path="/stats")
    FastAPIInsights.init(app, store, config=config)
    FastAPIInsights.init(app, store, config=config)

    route_paths = [route.path for route in app.routes if hasattr(route, "path")]
    assert route_paths.count("/stats/json") == 1
    assert len(app.user_middleware) == 1


def test_multiple_apps_keep_background_tasks_bound_to_their_own_store() -> None:
    app_one, store_one = build_app(
        store=CountingStore(), config=Config(enable_dashboard_ui=False)
    )
    app_two, store_two = build_app(
        store=CountingStore(), config=Config(enable_dashboard_ui=False)
    )

    with TestClient(app_one):
        wait_for(lambda: store_one.system_metrics_calls >= 1)
        wait_for(lambda: store_one.cleanup_calls >= 1)
        assert store_two.system_metrics_calls == 0

    assert FastAPIInsights._tasks == {}

    with TestClient(app_two):
        wait_for(lambda: store_two.system_metrics_calls >= 1)
        wait_for(lambda: store_two.cleanup_calls >= 1)
