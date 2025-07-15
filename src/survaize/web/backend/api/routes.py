import asyncio
import logging
import shutil
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Annotated, Literal, TypedDict
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, UploadFile, WebSocket
from fastapi.responses import FileResponse
from pydantic import BaseModel
from starlette.background import BackgroundTask

from survaize.config.llm_config import LLMConfig, create_llm_config_from_env
from survaize.model.questionnaire import Questionnaire
from survaize.reader.reader_factory import ReaderFactory
from survaize.writer.writer_factory import WriterFactory

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)

# Map job_id to asyncio.Queue for streaming progress updates


class ProgressMessage(TypedDict, total=False):
    """Message sent over the progress websocket."""

    progress: int
    message: str
    questionnaire: dict[str, object]
    error: str


progress_queues: dict[str, asyncio.Queue[ProgressMessage | None]] = {}


def get_llm_config() -> LLMConfig:
    """Dependency to get LLM configuration."""
    return create_llm_config_from_env()


def get_reader_factory(llm_config: Annotated[LLMConfig, Depends(get_llm_config)]) -> ReaderFactory:
    """Dependency to get the questionnaire reader factory."""
    return ReaderFactory(llm_config)


def get_writer_factory() -> WriterFactory:
    """Dependency to get the questionnaire writer factory."""
    return WriterFactory()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """
    Health check endpoint.

    Returns:
        Status message
    """
    return {"status": "ok"}


class QuestionnaireJobResponse(BaseModel):
    """Response model containing a job identifier."""

    job_id: str


@router.post("/questionnaire/read", response_model=QuestionnaireJobResponse)
async def read_questionnaire(
    file: UploadFile,
    format: Annotated[Literal["json", "pdf"], Form()],
    reader_factory: Annotated[ReaderFactory, Depends(get_reader_factory)],
    background_tasks: BackgroundTasks,
) -> QuestionnaireJobResponse:
    """
    Read a questionnaire from a file (PDF or JSON).

    Args:
        file: The file to read (PDF or JSON)

    Returns:
        The questionnaire from the file
    """
    try:
        contents = await file.read()
        job_id = str(uuid4())
        queue: asyncio.Queue[ProgressMessage | None] = asyncio.Queue()
        progress_queues[job_id] = queue

        async def process_job() -> None:
            try:
                reader = reader_factory.get(format)

                def progress(percent: int, message: str) -> None:
                    queue.put_nowait({"progress": percent, "message": message})

                questionnaire = await asyncio.to_thread(
                    reader.read,
                    BytesIO(contents),
                    progress,
                )
                queue.put_nowait(
                    {
                        "progress": 100,
                        "questionnaire": questionnaire.model_dump(exclude_none=True),
                    }
                )
            except Exception as exc:  # noqa: BLE001
                queue.put_nowait({"error": str(exc)})
            finally:
                queue.put_nowait(None)

        background_tasks.add_task(process_job)

        return QuestionnaireJobResponse(job_id=job_id)
    except Exception as e:
        logger.error(f"Error scheduling questionnaire read: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error reading questionnaire: {str(e)}") from e


@router.websocket("/questionnaire/read/{job_id}")
async def questionnaire_progress(job_id: str, websocket: WebSocket) -> None:
    """Stream questionnaire reading progress updates."""
    logger.info(f"WebSocket connection requested for job_id: {job_id}")
    await websocket.accept()
    logger.info(f"WebSocket connection accepted for job_id: {job_id}")

    queue = progress_queues.get(job_id)
    if queue is None:
        logger.warning(f"No queue found for job_id: {job_id}")
        await websocket.close(code=1008)
        return

    try:
        while True:
            update = await queue.get()
            logger.info(f"Sending update for job_id {job_id}: {update}")
            if update is None:
                break
            await websocket.send_json(update)
            if "error" in update or "questionnaire" in update:
                break
    except Exception as e:
        logger.error(f"Error in WebSocket for job_id {job_id}: {e}")
    finally:
        logger.info(f"Closing WebSocket for job_id: {job_id}")
        await websocket.close()
        progress_queues.pop(job_id, None)


@router.post("/questionnaire/save/{format}")
async def save_questionnaire(
    format: Literal["json", "cspro", "surveysolutions", "xlsform"],
    questionnaire: Questionnaire,
    writer_factory: Annotated[WriterFactory, Depends(get_writer_factory)],
) -> FileResponse:
    """
    Save a questionnaire to a file in the specified format.

    Args:
        format: The format to save the questionnaire in (json, cspro, or surveysolutions)
        questionnaire: The questionnaire to save

    Returns:
        The saved file
    """
    # Create temporary directory for output
    try:
        temp_dir = tempfile.mkdtemp()
        temp_dir_path = Path(temp_dir)
        file_name = f"{questionnaire.title.replace(' ', '_')}"

        writer = writer_factory.get(format)

        # Determine output file path based on format
        if format == "json":
            output_path = temp_dir_path / f"{file_name}.json"
            # For JSON we can use the writer directly
            writer.write(questionnaire, output_path)

            # Set appropriate filename for download
            download_filename = f"{file_name}.json"
            media_type = "application/json"

        elif format == "surveysolutions":
            output_path = temp_dir_path / f"{file_name}.zip"
            # For Survey Solutions we create a zip file with document.json inside
            writer.write(questionnaire, output_path)

            # Set appropriate filename for download
            download_filename = f"{file_name}.zip"
            media_type = "application/zip"

        elif format == "xlsform":
            output_path = temp_dir_path / f"{file_name}.xlsx"
            writer.write(questionnaire, output_path)

            download_filename = f"{file_name}.xlsx"
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

        elif format == "cspro":
            # TODO: Better handling of CSPro files, move zipping logic to writer

            # For CSPro, we create a directory with all CSPro files
            output_path = temp_dir_path / file_name
            writer.write(questionnaire, output_path)

            # Create a zip file of the CSPro directory to return

            zip_path = temp_dir_path / f"{file_name}.zip"
            shutil.make_archive(str(zip_path).replace(".zip", ""), "zip", temp_dir_path, file_name)

            # Set output_path to the zip file for download
            output_path = zip_path
            download_filename = f"{file_name}.zip"
            media_type = "application/zip"

        # Return the file
        return FileResponse(
            path=output_path,
            filename=download_filename,
            media_type=media_type,
            background=BackgroundTask(shutil.rmtree, temp_dir, ignore_errors=True),
        )

    except Exception as e:
        # TODO: more fine-grained error handling
        logger.error(f"Error saving questionnaire: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error saving questionnaire: {str(e)}") from e
