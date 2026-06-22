"""
AI Job Search Agent – FastAPI Application Entry Point.

Configures CORS, registers routers, initialises the database, and
exposes health-check / root endpoints.
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database.database import init_db

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup tasks before the app begins serving requests."""
    # Create uploads directory
    uploads = Path(settings.UPLOAD_DIR)
    uploads.mkdir(parents=True, exist_ok=True)
    logger.info("Uploads directory ready: %s", uploads.resolve())

    # Create chroma directory
    chroma = Path(settings.CHROMA_PERSIST_DIR)
    chroma.mkdir(parents=True, exist_ok=True)
    logger.info("ChromaDB directory ready: %s", chroma.resolve())

    # Initialise database tables
    await init_db()
    logger.info("Database initialised successfully.")

    yield  # application is running

    # Shutdown tasks (if any) go here
    logger.info("Application shutting down.")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="AI Job Search Agent",
    description=(
        "Intelligent job search assistant powered by AI. "
        "Upload your CV, find matching jobs, generate cover letters, "
        "practice interviews, and track applications."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS (allow all origins for development)
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Register routers (wrapped in try/except so the app starts even if
# individual router modules haven't been created yet)
# ---------------------------------------------------------------------------
_router_modules = [
    ("routers.auth", "auth", "/api"),
    ("routers.cv", "cv", "/api"),
    ("routers.jobs", "jobs", "/api"),
    ("routers.applications", "applications", "/api"),
    ("routers.cover_letters", "cover_letters", "/api"),
    ("routers.emails", "emails", "/api"),
    ("routers.interviews", "interviews", "/api"),
]

for module_path, attr_hint, prefix in _router_modules:
    try:
        import importlib

        mod = importlib.import_module(module_path)
        # Convention: each router module exposes a `router` attribute
        router = getattr(mod, "router", None)
        if router is not None:
            app.include_router(router, prefix=prefix)
            logger.info("Registered router: %s", module_path)
        else:
            logger.warning(
                "Module %s loaded but has no 'router' attribute – skipping.",
                module_path,
            )
    except ModuleNotFoundError:
        logger.warning(
            "Router module %s not found – skipping (create the file to enable).",
            module_path,
        )
    except Exception as exc:
        logger.warning(
            "Failed to load router %s: %s – skipping.",
            module_path,
            exc,
        )


# ---------------------------------------------------------------------------
# Root & health-check endpoints
# ---------------------------------------------------------------------------
@app.get("/", tags=["Root"])
async def root():
    """Welcome message for the API root."""
    return {
        "message": "Welcome to the AI Job Search Agent API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/api/health", tags=["Health"])
async def health_check():
    """Simple health-check endpoint."""
    return {
        "status": "healthy",
        "service": "AI Job Search Agent",
        "version": "1.0.0",
    }
