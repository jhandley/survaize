import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from starlette.background import BackgroundTask

from survaize.config.llm_config import LLMConfig, create_llm_config_from_env
from survaize.model.questionnaire import Questionnaire
from survaize.reader.reader_factory import ReaderFactory
from survaize.writer.writer_factory import WriterFactory

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)


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


@router.get("/hello")
async def hello_world() -> dict[str, str]:
    """
    Simple hello world endpoint for testing.

    Returns:
        Greeting message
    """
    return {"message": "Hello from Survaize API!"}


class QuestionnaireResponse(BaseModel):
    """Response model for a questionnaire."""

    questionnaire: Questionnaire


@router.post("/questionnaire/read", response_model=QuestionnaireResponse)
async def read_questionnaire(
    file: UploadFile,
    format: Annotated[Literal["json", "pdf"], Form()],
    reader_factory: Annotated[ReaderFactory, Depends(get_reader_factory)],
) -> QuestionnaireResponse:
    """
    Read a questionnaire from a file (PDF or JSON).

    Args:
        file: The file to read (PDF or JSON)

    Returns:
        The questionnaire from the file
    """
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=format) as temp_file:
            temp_file.write(await file.read())
            temp_path = Path(temp_file.name)

        reader = reader_factory.get(format)

        # Read the questionnaire
        questionnaire = reader.read(temp_path)
        return QuestionnaireResponse(questionnaire=questionnaire)
    except Exception as e:
        # TODO: More fine-grained error handling (consistent exceptions from readers)
        logger.error(f"Error reading questionnaire: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error reading questionnaire: {str(e)}") from e
    finally:
        # Clean up the temporary file
        if temp_path and temp_path.exists():
            os.unlink(temp_path)


@router.post("/questionnaire/save/{format}")
async def save_questionnaire(
    format: Literal["json", "cspro"],
    questionnaire: Questionnaire,
    writer_factory: Annotated[WriterFactory, Depends(get_writer_factory)],
) -> FileResponse:
    """
    Save a questionnaire to a file in the specified format.

    Args:
        format: The format to save the questionnaire in (json or cspro)
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
