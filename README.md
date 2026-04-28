# fastapi-insights

![Dashboard Screenshot](https://github.com/HamzaDLM/fastapi-insights/blob/main/fastapi_insights/static/bg.png?raw=true)

## Introduction

`fastapi-insights` is a FastAPI extension for application performance monitoring.
It tracks request and system metrics using lightweight middleware.
Metrics can be stored in in-memory, SQLite, or Redis backends and visualized in a built-in dashboard UI.

## Who is it for?

- Developers who want a metrics dashboard without running a full Prometheus + Grafana stack.
- Indie devs or small teams running single-instance FastAPI backends who just need lightweight insights.

## Features

- 🚀 Zero-config FastAPI middleware
- 🗄 Multiple storage backends: in-memory, SQLite, Redis
- 💻 Built-in dashboard UI with charts
- ⚡ Lightweight & async-first design
- 🔌 Configurable retention, bucket sizes, and cleanup

## Installation

```shell
> pip install fastapi-insights
```

Optional dependencies:

```shell
> pip install "fastapi-insights[redis]"
```

Supported Python versions: `3.10+`

## Development

Install dev dependencies and set up pre-commit hooks:

```shell
> uv sync --dev
> uv run pre-commit install
```

Run the checks manually at any time with:

```shell
> uv run pre-commit run --all-files
```

## Quick Start

Check the `examples` folder for more.

```python
from fastapi import FastAPI
from fastapi_insights import FastAPIInsights, Config
from fastapi_insights.backends.in_memory import InMemoryMetricsStore

app = FastAPI()

FastAPIInsights.init(
    app,
    InMemoryMetricsStore(),
    config=Config(),
)

@app.get("/")
def index():
    return "ok"
```

Visit `/metrics` to view the UI.

## Backends

#### In-Memory (default)

```python
from fastapi_insights.backends.in_memory import InMemoryMetricsStore
store = InMemoryMetricsStore()
```

#### Redis

```python
from fastapi_insights.backends.redis import AsyncRedisMetricsStore, RedisMetricsStore

# sync
import redis

redis_client = redis.Redis(host="localhost", port=6379, db=0)
store = RedisMetricsStore(redis_client)

# async
import redis.asyncio as async_redis

async_redis_client = async_redis.Redis(host="localhost", port=6379, db=0)
async_store = AsyncRedisMetricsStore(async_redis_client)
```

#### SQLite

```python
from fastapi_insights.backends.sqlite import SQLiteMetricsStore
store = SQLiteMetricsStore("metrics.db")
```

The SQLite backend uses the standard library `sqlite3` module, so no extra dependency is required.

### Configuration

You can customize the behavior by adjusting the `Config` options at initialization.

#### Example

```python
from fastapi_insights import Config

config = Config(
    ignored_routes=["/health", "/internal/*"],
    exclude_library_metrics=True,
    ui_config_route="/config-b887e852-bd12-41f2-b057-1bd31eb5443e",
    enable_dashboard_ui=True,
    custom_path="/metrics",
    include_in_openapi=False,
    ui_title="FastAPI Metrics"
)
```

#### Available Options

| Option                        | Type        | Default                                          | Description                                                                                                                        |
| ----------------------------- | ----------- | ------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------- |
| **`ignored_routes`**          | `list[str]` | `[]`                                             | Routes to be ignored by the metrics middleware. Use exact matches like `/route`, or wildcard matches like `/route/*` for prefixes. |
| **`exclude_library_metrics`** | `bool`      | `True`                                           | If `True`, excludes internal fastapi-insights endpoints from being tracked.                                                        |
| **`ui_config_route`**         | `str`       | `"/config-b887e852-bd12-41f2-b057-1bd31eb5443e"` | Internal route used to serve the dashboard’s configuration JSON. Should generally be left unchanged.                               |
| **`enable_dashboard_ui`**     | `bool`      | `True`                                           | Enables or disables the built-in dashboard UI. When disabled, only raw metrics endpoints remain active.                            |
| **`custom_path`**             | `str`       | `"/metrics"`                                     | The URL path under which metrics are exposed (e.g., `/metrics` or `/stats`).                                                       |
| **`include_in_openapi`**      | `bool`      | `False`                                          | Whether to include the metrics endpoints in your FastAPI OpenAPI schema (Swagger UI).                                              |
| **`ui_title`**                | `str`       | `"FastAPI Metrics"`                              | The title displayed in the dashboard UI.                                                                                           |

## Development

```shell
git clone https://github.com/HamzaDLM/fastapi-insights
cd fastapi-insights
uv sync
uv run pytest
```

## Releasing

Releases are published with GitHub Actions using Trusted Publishing.

- Publish to TestPyPI first
- Verify the built wheel and install path
- Then publish the exact same ref to PyPI

The full release procedure is documented in [RELEASE.md](RELEASE.md).

## Limitations

- Best suited for single-instance FastAPI deployments or small teams that want an embedded dashboard.
- Not a replacement for a full metrics pipeline such as Prometheus + Grafana in larger distributed systems.
- The in-memory backend is process-local and not durable across restarts.

## License

This project is licensed under the Apache-2.0 License.
