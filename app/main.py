from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import init_db
from app.routers import evaluate, report


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="STT API 선정 벤치마크", lifespan=lifespan)
app.include_router(evaluate.router)
app.include_router(report.router)


@app.get("/health")
def health():
    return {"status": "ok"}
