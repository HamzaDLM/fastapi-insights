from fastapi import FastAPI
from fastapi_insights import Config, FastAPIInsights
from fastapi_insights.backends.sqlite import SQLiteMetricsStore


app = FastAPI()

FastAPIInsights.init(
    app,
    SQLiteMetricsStore(db_path="metrics.db"),
    config=Config(),
)


@app.get("/")
def index():
    return "ok"
