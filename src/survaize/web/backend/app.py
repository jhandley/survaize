import logging
from importlib import resources

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from survaize.web.backend.api.routes import router as api_router

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Args:
        config: Configuration for the web application

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(title="Survaize API")

    # Include API routes
    app.include_router(api_router)

    # When installed as package mount the built frontend files from the package resources
    static_dir = resources.files("survaize.web.frontend").joinpath("dist")
    if static_dir.is_dir():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app
