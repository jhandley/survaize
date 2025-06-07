import logging

import uvicorn

logger = logging.getLogger(__name__)


def run_server(host: str = "127.0.0.1", port: int = 8000, reload: bool = False) -> None:
    """
    Run the Survaize web server.

    Args:
        host: The host to bind to
        port: The port to bind to
        reload: Whether to reload the server on code changes
    """

    logger.info(f"Starting Survaize web server at http://{host}:{port}")
    uvicorn.run(app="survaize.web.backend.app:create_app", host=host, port=port, reload=reload, log_level="info")
