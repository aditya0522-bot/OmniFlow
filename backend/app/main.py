import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import models  # noqa: F401  (registers tables on Base)
from .config import settings
from .database import SessionLocal, get_db, run_migrations
from .routers import (
    auth,
    bot,
    conversations,
    customers,
    dashboard,
    demo,
    orders,
    settings as settings_router,
    team,
    templates,
    webhooks,
)
from .seed import seed
from .services.retry import retry_failed

logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("omniflow")

if settings.sentry_dsn:
    import sentry_sdk

    sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.environment, traces_sample_rate=0.1)


async def retry_loop() -> None:
    while True:
        await asyncio.sleep(settings.retry_interval_seconds)
        try:
            await run_in_threadpool(retry_failed)
        except Exception:
            logger.exception("retry worker failed")


@asynccontextmanager
async def lifespan(_: FastAPI):
    run_migrations()
    if settings.seed_demo_data and (settings.environment != "production" or settings.demo_mode):
        with SessionLocal() as db:
            seed(db)
    worker = asyncio.create_task(retry_loop()) if settings.worker_enabled else None
    yield
    if worker:
        worker.cancel()


app = FastAPI(title="OmniFlow API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_log_and_headers(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("unhandled error id=%s %s %s", request_id, request.method, request.url.path)
        return JSONResponse({"detail": "Something went wrong on our side"}, status_code=500)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    logger.info(
        "%s %s %s %.0fms id=%s",
        request.method,
        request.url.path,
        response.status_code,
        (time.perf_counter() - started) * 1000,
        request_id,
    )
    return response


for module in (auth, team, dashboard, customers, conversations, orders, bot, templates, demo, settings_router):
    app.include_router(module.router, prefix="/api/v1")
app.include_router(webhooks.router, prefix="/webhooks")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    db.execute(text("select 1"))
    return {"status": "ready"}
