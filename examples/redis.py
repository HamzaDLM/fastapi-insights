import redis.asyncio as async_redis
from fastapi import FastAPI

from fastapi_insights import Config, FastAPIInsights
from fastapi_insights.backends.redis import AsyncRedisMetricsStore

app = FastAPI()

redis_client = async_redis.Redis(host="localhost", port=6379, db=0)

FastAPIInsights.init(
    app,
    AsyncRedisMetricsStore(redis_client),
    config=Config(),
)


@app.get("/")
def index():
    return "ok"
