import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from soco.exceptions import SoCoException

from sonos_api.config import settings
from sonos_api.discovery.manager import SpeakerManager
from sonos_api.routers import equalizer, events, favorites, groups, playback, queue, state, system, tts, volume
from sonos_api.routers import settings as settings_router


def setup_logging() -> None:
    """Configure structlog for structured logging."""
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if settings.log_json:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.log_level.upper())

    # Quiet noisy loggers
    logging.getLogger("soco").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger = structlog.get_logger()
    logger.info("Starting Sonos API", port=settings.api_port)

    manager = SpeakerManager(discovery_interval=settings.discovery_interval)
    app.state.speaker_manager = manager
    await manager.start()

    yield

    logger.info("Shutting down Sonos API")
    await manager.stop()


app = FastAPI(
    title="Sonos API",
    description="Stable HTTP API for Sonos speakers",
    version="0.1.0",
    lifespan=lifespan,
)

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")


# Serve TTS audio files
import os
os.makedirs(settings.tts_cache_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=settings.tts_cache_dir), name="static")

# Register routers
app.include_router(system.router, tags=["system"])
app.include_router(state.router, tags=["state"])
app.include_router(playback.router, tags=["playback"])
app.include_router(volume.router, tags=["volume"])
app.include_router(queue.router, tags=["queue"])
app.include_router(favorites.router, tags=["favorites"])
app.include_router(settings_router.router, tags=["settings"])
app.include_router(tts.router, tags=["tts"])
app.include_router(groups.router, tags=["groups"])
app.include_router(equalizer.router, tags=["equalizer"])
app.include_router(events.router, tags=["events"])


# Global exception handlers
@app.exception_handler(SoCoException)
async def soco_exception_handler(request: Request, exc: SoCoException):
    logger = structlog.get_logger()
    logger.error("SoCo error", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=502,
        content={"error": "Speaker communication error", "detail": str(exc)},
    )


@app.exception_handler(ConnectionError)
async def connection_error_handler(request: Request, exc: ConnectionError):
    logger = structlog.get_logger()
    logger.error("Connection error", error=str(exc), path=request.url.path)
    # Trigger re-discovery in background
    if hasattr(request.app.state, "speaker_manager"):
        import asyncio

        asyncio.create_task(request.app.state.speaker_manager.trigger_rediscovery())
    return JSONResponse(
        status_code=503,
        content={"error": "Speaker unreachable", "detail": str(exc)},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger = structlog.get_logger()
    logger.exception("Unhandled error", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )
