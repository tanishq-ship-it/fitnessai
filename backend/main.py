from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import create_pool, ensure_schema
from routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create DB connection pool
    app.state.db_pool = await create_pool()
    await ensure_schema(app.state.db_pool)
    yield
    # Shutdown: close pool
    await app.state.db_pool.close()


app = FastAPI(title="FitnessAI API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:19006", "http://localhost:8081"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
