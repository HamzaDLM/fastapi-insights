import time

from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response

from fastapi_insights.backends.base import MetricsStore, AsyncMetricsStore
from fastapi_insights.config import Config


def get_metrics_router(store: MetricsStore, config: Config) -> APIRouter:
    metrics_router = APIRouter()
    prefixed_router = APIRouter(prefix=config.custom_path)

    def dashboard_config() -> dict[str, str]:
        return {"title": config.ui_title}

    @metrics_router.get(config.ui_config_route, include_in_schema=False)
    async def get_config():
        return dashboard_config()

    @prefixed_router.get("/_dashboard_config", include_in_schema=False)
    async def get_dashboard_config():
        return dashboard_config()

    @prefixed_router.get(
        "/json",
        status_code=200,
        include_in_schema=config.include_in_openapi,
    )
    async def get_metrics(
        ts_from: int, ts_to: int | None = None, bucket_size: int | None = None
    ):
        if ts_to is None:
            ts_to = int(time.time())

        data = store.get_metrics(ts_from=ts_from, ts_to=ts_to, bucket_size=bucket_size)
        return JSONResponse(content=data)

    @prefixed_router.get(
        "/table_overview",
        status_code=200,
        include_in_schema=config.include_in_openapi,
    )
    async def get_table_overview(
        ts_from: int,
        ts_to: int | None = None,
    ):
        if ts_to is None:
            ts_to = int(time.time())

        data = store.get_table_overview(ts_from, ts_to)
        return JSONResponse(content=data)

    @prefixed_router.delete(
        "/reset",
        status_code=204,
        include_in_schema=config.include_in_openapi,
    )
    async def reset_store():
        store.reset()
        return Response(status_code=204)

    metrics_router.include_router(prefixed_router)

    return metrics_router


def get_async_metrics_router(store: AsyncMetricsStore, config: Config) -> APIRouter:
    metrics_router = APIRouter()
    prefixed_router = APIRouter(prefix=config.custom_path)

    def dashboard_config() -> dict[str, str]:
        return {"title": config.ui_title}

    @metrics_router.get(config.ui_config_route, include_in_schema=False)
    async def get_config():
        return dashboard_config()

    @prefixed_router.get("/_dashboard_config", include_in_schema=False)
    async def get_dashboard_config():
        return dashboard_config()

    @prefixed_router.get(
        "/json",
        status_code=200,
        include_in_schema=config.include_in_openapi,
    )
    async def get_metrics(
        ts_from: int, ts_to: int | None = None, bucket_size: int | None = None
    ):
        if ts_to is None:
            ts_to = int(time.time())

        data = await store.get_metrics(
            ts_from=ts_from, ts_to=ts_to, bucket_size=bucket_size
        )
        return JSONResponse(content=data)

    @prefixed_router.get(
        "/table_overview",
        status_code=200,
        include_in_schema=config.include_in_openapi,
    )
    async def get_table_overview(
        ts_from: int,
        ts_to: int | None = None,
    ):
        if ts_to is None:
            ts_to = int(time.time())

        data = await store.get_table_overview(ts_from, ts_to)
        return JSONResponse(content=data)

    @prefixed_router.delete(
        "/reset",
        status_code=204,
        include_in_schema=config.include_in_openapi,
    )
    async def reset_store():
        await store.reset()
        return Response(status_code=204)

    metrics_router.include_router(prefixed_router)

    return metrics_router
