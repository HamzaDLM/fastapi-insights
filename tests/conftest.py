import pytest

from fastapi_insights import FastAPIInsights


@pytest.fixture(autouse=True)
def reset_fastapi_metrics_state():
    FastAPIInsights._initialized_apps.clear()
    FastAPIInsights._tasks.clear()
    FastAPIInsights._stores.clear()
    yield
    FastAPIInsights._initialized_apps.clear()
    FastAPIInsights._tasks.clear()
    FastAPIInsights._stores.clear()


@pytest.fixture
def anyio_backend():
    return "asyncio"
