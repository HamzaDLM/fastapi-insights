import asyncio
import inspect
import os
from contextlib import asynccontextmanager
from typing import ClassVar, cast

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from fastapi_insights.backends.base import AsyncMetricsStore, MetricsStore
from fastapi_insights.backends.in_memory import InMemoryMetricsStore
from fastapi_insights.config import Config
from fastapi_insights.logger import logger
from fastapi_insights.middleware import (
    AsyncMetricsMiddleware,
    MetricsMiddleware,
)
from fastapi_insights.router import (
    get_async_metrics_router,
    get_metrics_router,
)

__all__ = [
    "Config",
    "FastAPIInsights",
    "get_async_metrics_router",
    "get_metrics_router",
    "AsyncMetricsMiddleware",
    "MetricsMiddleware",
]


class FastAPIInsights:
    _initialized_apps: ClassVar[set[int]] = set()
    _tasks: ClassVar[dict[int, list[asyncio.Task]]] = {}
    _stores: ClassVar[dict[int, MetricsStore | AsyncMetricsStore]] = {}
    _sys_metrics_sampling_interval: ClassVar[int] = 5
    _cleanup_expired_rate: ClassVar[int] = 60 * 60  # seconds

    @classmethod
    def init(
        cls,
        app: FastAPI,
        store: MetricsStore | AsyncMetricsStore,
        config: Config | None = None,
    ) -> None:
        if id(app) in cls._initialized_apps:
            return

        if not hasattr(app.router, "lifespan_context"):
            raise RuntimeError(
                "fastapi app instance must be created before calling FastAPIInsights.init(app)"
            )

        resolved_store = store or InMemoryMetricsStore()
        resolved_config = cls._prepare_config(config)
        app_id = id(app)

        cls._stores[app_id] = resolved_store
        cls._setup_lifespan(app, resolved_store)

        if isinstance(resolved_store, AsyncMetricsStore):
            cls._async_register_routes(app, resolved_store, resolved_config)
        else:
            cls._register_routes(
                app, cast(MetricsStore, resolved_store), resolved_config
            )

        cls._initialized_apps.add(app_id)

    @classmethod
    def _normalize_path(cls, path: str) -> str:
        normalized = path if path.startswith("/") else f"/{path}"
        if normalized != "/":
            normalized = normalized.rstrip("/")
        return normalized or "/"

    @classmethod
    def _normalize_ignored_route(cls, route: str) -> str:
        if route.endswith("/*"):
            return f"{cls._normalize_path(route[:-2])}/*"
        return cls._normalize_path(route)

    @classmethod
    def _prepare_config(cls, config: Config | None) -> Config:
        base_config = config or Config()
        custom_path = cls._normalize_path(base_config.custom_path)
        ui_config_route = cls._normalize_path(base_config.ui_config_route)
        ignored_routes = [
            cls._normalize_ignored_route(route) for route in base_config.ignored_routes
        ]

        if base_config.exclude_library_metrics:
            ignored_routes.extend([f"{custom_path}/*", ui_config_route])

        deduped_routes = list(dict.fromkeys(ignored_routes))

        return Config(
            ignored_routes=deduped_routes,
            exclude_library_metrics=base_config.exclude_library_metrics,
            ui_config_route=ui_config_route,
            enable_dashboard_ui=base_config.enable_dashboard_ui,
            custom_path=custom_path,
            include_in_openapi=base_config.include_in_openapi,
            ui_title=base_config.ui_title,
        )

    @classmethod
    def _setup_lifespan(
        cls, app: FastAPI, store: MetricsStore | AsyncMetricsStore
    ) -> None:
        original_lifespan = getattr(app.router, "lifespan_context", None)

        @asynccontextmanager
        async def injected_lifespan(app: FastAPI):
            app_id = id(app)
            tasks = []
            tasks.append(asyncio.create_task(cls._collect_sys_metrics_loop(store)))
            tasks.append(asyncio.create_task(cls._cleanup(store)))
            cls._tasks[app_id] = tasks

            logger.debug(f"MAIN: Starting lifespan for app {app_id}")

            try:
                if original_lifespan:
                    async with original_lifespan(app):
                        logger.debug("MAIN: App is running with original lifespan...")
                        yield
                        logger.debug("MAIN: Original lifespan shutting down...")
                else:
                    yield
            finally:
                logger.debug(f"MAIN: Cleaning up lifespan for app {app_id}")
                for task in cls._tasks.pop(app_id, []):
                    logger.debug(f"MAIN: Cancelling task: {task.get_name()}")
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        logger.debug("MAIN: Task cancelled successfully")
                        pass
                cls._stores.pop(app_id, None)
                logger.debug(f"MAIN: Cleaned up tasks for app {app_id}")

        app.router.lifespan_context = injected_lifespan

    @classmethod
    def _register_routes(
        cls, app: FastAPI, store: MetricsStore, config: Config
    ) -> None:
        app.add_middleware(MetricsMiddleware, store=store, config=config)
        app.include_router(
            get_metrics_router(store, config),
            tags=["fastapi dashboard metrics"],
        )

        if config.enable_dashboard_ui:
            app.mount(
                config.custom_path,
                StaticFiles(
                    directory=os.path.join(
                        os.path.dirname(__file__), "static", "frontend"
                    ),
                    html=True,
                ),
                name="metrics",
            )

    @classmethod
    def _async_register_routes(
        cls, app: FastAPI, store: AsyncMetricsStore, config: Config
    ) -> None:
        app.add_middleware(
            AsyncMetricsMiddleware,
            store=store,
            config=config,
        )
        app.include_router(
            get_async_metrics_router(store, config),
            tags=["fastapi dashboard metrics"],
        )
        if config.enable_dashboard_ui:
            app.mount(
                config.custom_path,
                StaticFiles(
                    directory=os.path.join(
                        os.path.dirname(__file__), "static", "frontend"
                    ),
                    html=True,
                ),
                name="metrics",
            )

    @classmethod
    async def _collect_sys_metrics_loop(
        cls, store: MetricsStore | AsyncMetricsStore
    ) -> None:
        while True:
            result = store.record_system_metrics()
            if inspect.isawaitable(result):
                await result
            await asyncio.sleep(cls._sys_metrics_sampling_interval)

    @classmethod
    async def _cleanup(cls, store: MetricsStore | AsyncMetricsStore) -> None:
        while True:
            result = store._cleanup_expired_ttl()
            if inspect.isawaitable(result):
                await result
            await asyncio.sleep(cls._cleanup_expired_rate)
