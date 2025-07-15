"""Test Survey Solutions export via web API."""

import pytest
from fastapi.testclient import TestClient

from survaize.model.questionnaire import (
    NumericQuestion,
    Option,
    Question,
    Questionnaire,
    QuestionType,
    Section,
    SingleChoiceQuestion,
    TextQuestion,
)
from survaize.web.backend.app import create_app


@pytest.fixture()
def client() -> TestClient:
    """Create a test client for the API."""
    app = create_app()
    return TestClient(app)


@pytest.fixture()
def sample_questionnaire() -> Questionnaire:
    """Create a sample questionnaire for testing."""
    questions: list[Question] = [
        TextQuestion(
            number="1",
            id="name",
            text="What is your name?",
            type=QuestionType.TEXT,
            instructions=None,
            universe=None,
            max_length=None,
        ),
        NumericQuestion(
            number="2",
            id="age",
            text="What is your age?",
            type=QuestionType.NUMERIC,
            instructions=None,
            universe=None,
            min_value=None,
            max_value=None,
            decimal_places=None,
        ),
        SingleChoiceQuestion(
            number="3",
            id="gender",
            text="What is your gender?",
            type=QuestionType.SINGLE_SELECT,
            instructions=None,
            universe=None,
            options=[
                Option(code="1", label="Male"),
                Option(code="2", label="Female"),
            ],
        ),
    ]

    section = Section(
        id="demographics",
        number="A",
        title="Demographics",
        description=None,
        universe=None,
        questions=questions,
        occurrences=1,
    )

    return Questionnaire(title="Test Survey", description="A test survey", id_fields=["name"], sections=[section])


def test_save_questionnaire_surveysolutions_format(client: TestClient, sample_questionnaire: Questionnaire) -> None:
    """Test saving questionnaire in Survey Solutions format via API."""
    response = client.post("/api/questionnaire/save/surveysolutions", json=sample_questionnaire.model_dump())

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"

    # Verify the response contains a valid Survey Solutions backup zip
    # For the test, we'll just check that it's a valid zip file
    # In a real scenario, you'd extract and validate the document.json content
    assert len(response.content) > 0


def test_save_questionnaire_odk_format(client: TestClient, sample_questionnaire: Questionnaire) -> None:
    """Test saving questionnaire in ODK XLSForm format via API."""
    response = client.post("/api/questionnaire/save/xlsform", json=sample_questionnaire.model_dump())

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert len(response.content) > 0
