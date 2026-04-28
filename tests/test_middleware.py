import pytest
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from httpx import ASGITransport, AsyncClient

from fastapi_insights.config import Config
from fastapi_insights.middleware import AsyncMetricsMiddleware, MetricsMiddleware


class DummyStore:
    def __init__(self):
        self.records: list[tuple[str, int, str]] = []

    def record_request_metrics(
        self, path: str, duration: float, status_code: int, method: str
    ) -> None:
        self.records.append((path, status_code, method))


class AsyncDummyStore:
    def __init__(self):
        self.records: list[tuple[str, int, str]] = []

    async def record_request_metrics(
        self, path: str, duration: float, status_code: int, method: str
    ) -> None:
        self.records.append((path, status_code, method))


def build_sync_app() -> tuple[FastAPI, DummyStore]:
    app = FastAPI()
    store = DummyStore()
    config = Config(ignored_routes=["/metrics", "/metrics/*"])

    @app.get("/metrics")
    async def metrics_root():
        return PlainTextResponse("metrics ok")

    @app.get("/metrics/ui")
    async def metrics_ui():
        return PlainTextResponse("metrics ui ok")

    @app.get("/api/data")
    async def api_data():
        return PlainTextResponse("data ok")

    @app.get("/error")
    async def error():
        raise ValueError("boom")

    app.add_middleware(MetricsMiddleware, store=store, config=config)
    return app, store


def build_async_app() -> tuple[FastAPI, AsyncDummyStore]:
    app = FastAPI()
    store = AsyncDummyStore()
    config = Config(ignored_routes=["/skip", "/skip/*"])

    @app.get("/skip")
    async def skip_root():
        return PlainTextResponse("skip")

    @app.get("/skip/child")
    async def skip_child():
        return PlainTextResponse("skip child")

    @app.post("/api/items")
    async def create_item():
        return PlainTextResponse("created", status_code=201)

    app.add_middleware(AsyncMetricsMiddleware, store=store, config=config)
    return app, store


@pytest.mark.anyio
async def test_sync_middleware_skips_ignored_routes() -> None:
    app, store = build_sync_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.get("/metrics")
        await client.get("/metrics/ui")

    assert store.records == []


@pytest.mark.anyio
async def test_sync_middleware_records_success_and_errors() -> None:
    app, store = build_sync_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/data")
        assert response.status_code == 200
        with pytest.raises(ValueError):
            await client.get("/error")

    assert store.records[0] == ("/api/data", 200, "GET")
    assert store.records[1] == ("/error", 500, "GET")


@pytest.mark.anyio
async def test_async_middleware_skips_and_records() -> None:
    app, store = build_async_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.get("/skip")
        await client.get("/skip/child")
        response = await client.post("/api/items")

    assert response.status_code == 201
    assert store.records == [("/api/items", 201, "POST")]
