import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .database import Base, SessionLocal, engine
from .deps import today
from .routers import auth, budgets, categories, expenses, insights, me
from .services.seed import ensure_demo_user

settings = get_settings()
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    if settings.seed_demo:
        with SessionLocal() as db:
            ensure_demo_user(db, today())
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Backend for Apna Hisab Kitaab — Har Kharchay Ka Apna Hisab.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    # Give the frontend one readable message in `detail`, plus the field errors.
    first = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(p) for p in first.get("loc", [])[1:])
    msg = first.get("msg", "Invalid input").replace("Value error, ", "")
    return JSONResponse(status_code=422, content={"detail": f"{field}: {msg}" if field else msg, "errors": exc.errors()})


API = "/api/v1"
for r in (auth.router, me.router, expenses.router, categories.router, budgets.router, insights.router):
    app.include_router(r, prefix=API)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
