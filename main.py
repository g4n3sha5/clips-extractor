from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from config import load_settings
from services.session import load_session_from_disk
from routers import cache as cache_router
from routers import clips as clips_router
from routers import config as config_router
from routers import download as download_router
from routers import instructional as instructional_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_session_from_disk()
    settings = load_settings()
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="Drill Clip Extractor", lifespan=lifespan)

# Include API routers before mounting StaticFiles.
app.include_router(config_router.router, prefix="/api")
app.include_router(instructional_router.router, prefix="/api")
app.include_router(cache_router.router, prefix="/api")
app.include_router(download_router.router, prefix="/api")
app.include_router(clips_router.router, prefix="/api")

# StaticFiles acts as a catch-all and should be mounted last.
app.mount("/", StaticFiles(directory="static", html=True), name="static")
