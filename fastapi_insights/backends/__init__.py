from fastapi_insights.backends.in_memory import InMemoryMetricsStore

__all__ = ["InMemoryMetricsStore"]

try:
    from fastapi_insights.backends.redis import (
        AsyncRedisMetricsStore,
        RedisMetricsStore,
    )
except ImportError:
    pass
else:
    __all__ += ["RedisMetricsStore", "AsyncRedisMetricsStore"]

try:
    from fastapi_insights.backends.sqlite import SQLiteMetricsStore
except ImportError:
    pass
else:
    __all__ += ["SQLiteMetricsStore"]
