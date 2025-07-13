"""Test that the AIQuestionnaireInterpreter correctly retries validation failures."""

import json
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from survaize.config.llm_config import LLMConfig, OpenAIProviderType
from survaize.interpreter.ai_interpreter import AIQuestionnaireInterpreter
from survaize.interpreter.scanned_questionnaire import ScannedQuestionnaire
from survaize.model.questionnaire import Questionnaire


@pytest.fixture
def mock_document() -> ScannedQuestionnaire:
    """Create a simple test questionnaire."""
    img = Image.new("RGB", (100, 100), color="white")
    document = ScannedQuestionnaire(pages=[img], extracted_text=["OCR text"], source_path=Path("test.pdf"))
    return document


@pytest.fixture
def mock_document_two_pages() -> ScannedQuestionnaire:
    """Create a two-page test questionnaire."""
    img = Image.new("RGB", (100, 100), color="white")
    document = ScannedQuestionnaire(
        pages=[img, img],
        extracted_text=["OCR page 1", "OCR page 2"],
        source_path=Path("test.pdf"),
    )
    return document


@pytest.fixture
def mock_llm_config() -> LLMConfig:
    """Create a mock LLM configuration."""
    return LLMConfig(
        provider=OpenAIProviderType.OPENAI,
        api_key="fake-api-key",
        api_version=None,
        api_url=None,
        model="gpt-4.1",
    )


def test_first_page_retry_validation_error(mock_document: ScannedQuestionnaire, mock_llm_config: LLMConfig):
    """Test that _process_first_page retries when Pydantic validation fails."""
    with patch("survaize.interpreter.ai_interpreter.create_openai_client") as mock_factory:
        # Set up the mock for OpenAI client
        mock_client = MagicMock()
        mock_factory.return_value = mock_client

        # Configure mock responses - first with invalid JSON, then with valid JSON
        mock_completion1 = MagicMock()
        mock_completion1.choices[0].message.content = json.dumps(
            {
                # Missing required fields to trigger validation error
                "title": "Test Survey",
                "description": "Test description",
                # Missing id_fields
                "sections": [],
            }
        )

        mock_completion2 = MagicMock()
        mock_completion2.choices[0].message.content = json.dumps(
            {
                "title": "Test Survey",
                "description": "Test description",
                "id_fields": ["test_id"],
                "sections": [
                    {"id": "section_a", "number": "A", "title": "Test Section", "questions": [], "occurrences": 1}
                ],
                "trailing_sections": [],
            }
        )

        # Configure the client.chat.completions.create method to return different responses
        mock_client.chat.completions.create.side_effect = [mock_completion1, mock_completion2]

        # Create interpreter and call the method
        interpreter = AIQuestionnaireInterpreter(mock_llm_config)
        result = interpreter.interpret(mock_document)

        # Verify the method was called twice
        assert mock_client.chat.completions.create.call_count == 2

        # Verify the result is a valid Questionnaire
        assert isinstance(result, Questionnaire)
        assert result.title == "Test Survey"
        assert result.id_fields == ["test_id"]


def test_max_retries_exceeded(mock_document: ScannedQuestionnaire, mock_llm_config: LLMConfig):
    """Test that _process_first_page raises an error after max retries."""
    with patch("survaize.interpreter.ai_interpreter.create_openai_client") as mock_factory:
        # Set up the mock for OpenAI client
        mock_client = MagicMock()
        mock_factory.return_value = mock_client

        # Configure mock response with always-invalid JSON
        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = json.dumps(
            {
                # Always missing required fields
                "title": "Test Survey",
                "description": "Test description",
                # Missing id_fields and other required fields
            }
        )

        # Configure to always return invalid response
        mock_create = MagicMock(return_value=mock_completion)
        mock_client.chat.completions.create = mock_create

        # Create interpreter with a small max_retries value
        interpreter = AIQuestionnaireInterpreter(mock_llm_config, max_retries=3)

        # Verify raises error after max retries
        with pytest.raises(ValueError) as error:
            interpreter.interpret(mock_document)

        assert "Unable to validate response after 3 attempts" in str(error)
        assert mock_create.call_count == 3


def test_interpret_reports_progress(mock_document_two_pages: ScannedQuestionnaire, mock_llm_config: LLMConfig) -> None:
    """Verify interpret emits progress updates for each page."""
    with patch("survaize.interpreter.ai_interpreter.create_openai_client") as mock_factory:
        mock_client = MagicMock()
        mock_factory.return_value = mock_client

        completion1 = MagicMock()
        completion1.choices[0].message.content = json.dumps(
            {
                "title": "Test Survey",
                "id_fields": ["id"],
                "sections": [],
                "trailing_sections": [],
            }
        )

        completion2 = MagicMock()
        completion2.choices[0].message.content = json.dumps({"sections": [], "trailing_sections": []})

        mock_client.chat.completions.create.side_effect = [completion1, completion2]

        progress: list[int] = []

        def record(percent: int, _msg: str) -> None:
            progress.append(percent)

        interpreter = AIQuestionnaireInterpreter(mock_llm_config)
        interpreter.interpret(mock_document_two_pages, record)

        assert progress[0] == 0
        assert progress[-1] == 100
        assert len(progress) == 3


def test_interpret_logs_usage(
    mock_document: ScannedQuestionnaire, mock_llm_config: LLMConfig, caplog: pytest.LogCaptureFixture
) -> None:
    """Verify interpret logs token usage when provided by the API."""
    with patch("survaize.interpreter.ai_interpreter.create_openai_client") as mock_factory:
        mock_client = MagicMock()
        mock_factory.return_value = mock_client

        completion = MagicMock()
        completion.choices[0].message.content = json.dumps(
            {"title": "Survey", "id_fields": ["id"], "sections": [], "trailing_sections": []}
        )
        usage = MagicMock()
        usage.prompt_tokens = 3
        usage.completion_tokens = 4
        completion.usage = usage

        mock_client.chat.completions.create.return_value = completion

        interpreter = AIQuestionnaireInterpreter(mock_llm_config)
        caplog.set_level(logging.INFO)
        interpreter.interpret(mock_document)

        assert any("Token usage - prompt: 3" in r.getMessage() and "total: 7" in r.getMessage() for r in caplog.records)


def test_interpret_without_ocr_text(mock_document: ScannedQuestionnaire, mock_llm_config: LLMConfig) -> None:
    """Verify interpret works when OCR text is not provided."""
    with patch("survaize.interpreter.ai_interpreter.create_openai_client") as mock_factory:
        mock_client = MagicMock()
        mock_factory.return_value = mock_client

        completion = MagicMock()
        completion.choices[0].message.content = json.dumps(
            {"title": "Test Survey", "id_fields": ["id"], "sections": [], "trailing_sections": []}
        )
        mock_client.chat.completions.create.return_value = completion

        interpreter = AIQuestionnaireInterpreter(mock_llm_config)
        doc = ScannedQuestionnaire(
            pages=mock_document.pages,
            extracted_text=[],
            source_path=mock_document.source_path,
        )

        result = interpreter.interpret(doc)

        assert isinstance(result, Questionnaire)
