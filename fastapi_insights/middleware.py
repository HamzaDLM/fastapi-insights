import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from fastapi_insights.backends.base import AsyncMetricsStore, MetricsStore
from fastapi_insights.config import Config


class MetricsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, store: MetricsStore, config: Config):
        super().__init__(app)
        self.store = store
        self.config = config

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        for ignored_route in self.config.ignored_routes:
            if ignored_route.endswith("/*"):
                prefix = ignored_route[:-1]
                if path.startswith(prefix):
                    return await call_next(request)
            elif path == ignored_route:
                return await call_next(request)

        start_time = time.perf_counter()
        status_code = 500

        try:
            response: Response = await call_next(request)
            status_code = response.status_code
        except Exception:
            status_code = 500
            raise
        finally:
            duration = time.perf_counter() - start_time
            method = request.method
            self.store.record_request_metrics(path, duration, status_code, method)

        return response


class AsyncMetricsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, store: AsyncMetricsStore, config: Config):
        super().__init__(app)
        self.store = store
        self.config = config

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        for ignored_route in self.config.ignored_routes:
            if ignored_route.endswith("/*"):
                prefix = ignored_route[:-1]
                if path.startswith(prefix):
                    return await call_next(request)
            elif path == ignored_route:
                return await call_next(request)

        start_time = time.perf_counter()
        status_code = 500

        try:
            response: Response = await call_next(request)
            status_code = response.status_code
        except Exception:
            status_code = 500
            raise
        finally:
            duration = time.perf_counter() - start_time
            method = request.method
            await self.store.record_request_metrics(path, duration, status_code, method)

        return response
