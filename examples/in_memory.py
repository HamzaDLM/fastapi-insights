from fastapi import FastAPI

from fastapi_insights import FastAPIInsights
from fastapi_insights.backends.in_memory import InMemoryMetricsStore

app = FastAPI()

FastAPIInsights.init(
    app,
    InMemoryMetricsStore(),
)


@app.get("/")
def index():
    return "ok"
