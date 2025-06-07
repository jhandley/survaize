from fastapi import APIRouter

router = APIRouter(prefix="/api")


@router.get("/health")
async def health_check() -> dict[str, str]:
    """
    Health check endpoint.

    Returns:
        Status message
    """
    return {"status": "ok"}


@router.get("/hello")
async def hello_world() -> dict[str, str]:
    """
    Simple hello world endpoint for testing.

    Returns:
        Greeting message
    """
    return {"message": "Hello from Survaize API!"}
