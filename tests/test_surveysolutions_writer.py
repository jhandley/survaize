"""Tests for the Survey Solutions writer."""

import json
import tempfile
import zipfile
from pathlib import Path

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
from survaize.writer.surveysolutions_writer import SurveySolutionsWriter


def test_surveysolutions_writer_basic_questionnaire() -> None:
    """Test that the Survey Solutions writer can convert a basic questionnaire."""
    # Create a simple questionnaire
    questions: list[Question] = [
        TextQuestion(
            number="1",
            id="name",
            text="What is your name?",
            type=QuestionType.TEXT,
            instructions="Enter your full name",
            universe=None,
            max_length=None,
        ),
        NumericQuestion(
            number="2",
            id="age",
            text="What is your age?",
            type=QuestionType.NUMERIC,
            min_value=0,
            max_value=120,
            instructions=None,
            universe=None,
            decimal_places=None,
        ),
        SingleChoiceQuestion(
            number="3",
            id="gender",
            text="What is your gender?",
            type=QuestionType.SINGLE_SELECT,
            options=[
                Option(code="1", label="Male"),
                Option(code="2", label="Female"),
                Option(code="3", label="Other"),
            ],
            instructions=None,
            universe=None,
        ),
    ]

    section = Section(
        id="demographics",
        number="A",
        title="Demographics",
        description="Basic demographic information",
        questions=questions,
        occurrences=1,
        universe=None,
    )

    questionnaire = Questionnaire(
        title="Test Survey",
        description="A test survey for Survey Solutions export",
        id_fields=["name"],
        sections=[section],
        trailing_sections=[],
    )

    # Create writer and convert
    writer = SurveySolutionsWriter()

    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = Path(temp_dir) / "test_survey.zip"
        writer.write(questionnaire, output_path)

        # Verify zip file was created
        assert output_path.exists()

        # Verify zip file contains document.json
        with zipfile.ZipFile(output_path, "r") as zip_file:
            zip_contents = zip_file.namelist()
            assert "document.json" in zip_contents

            # Read and verify the JSON content
            with zip_file.open("document.json") as json_file:
                content = json.load(json_file)

        # Basic structure checks
        assert content["Title"] == "Test Survey"
        assert content["Description"] == "A test survey for Survey Solutions export"
        assert len(content["Children"]) == 1

        # Check the section/group
        group = content["Children"][0]
        assert group["Type"] == "Group"
        assert group["Title"] == "Demographics"
        assert len(group["Children"]) == 3

        # Check text question
        text_q = group["Children"][0]
        assert text_q["Type"] == "TextQuestion"
        assert text_q["QuestionText"] == "What is your name?"
        assert text_q["VariableName"] == "name"

        # Check numeric question
        numeric_q = group["Children"][1]
        assert numeric_q["Type"] == "NumericQuestion"
        assert numeric_q["QuestionText"] == "What is your age?"
        assert numeric_q["VariableName"] == "age"

        # Check single choice question
        single_q = group["Children"][2]
        assert single_q["Type"] == "SingleQuestion"
        assert single_q["QuestionText"] == "What is your gender?"
        assert single_q["VariableName"] == "gender"
        assert len(single_q["Answers"]) == 3
        assert single_q["Answers"][0]["Text"] == "Male"
        assert single_q["Answers"][0]["Code"] == 1


def test_variable_name_generation() -> None:
    """Test variable name generation for Survey Solutions compliance."""
    writer = SurveySolutionsWriter()  # Test basic cases
    assert writer.generate_variable_name("simple") == "simple"
    assert writer.generate_variable_name("with spaces") == "with_spaces"
    assert writer.generate_variable_name("with-dashes") == "with_dashes"
    assert writer.generate_variable_name("with.dots") == "with_dots"

    # Test starting with number
    assert writer.generate_variable_name("1name").startswith("V")

    # Test empty string
    assert writer.generate_variable_name("") == "Variable"

    # Test long name (should be truncated to 32 chars)
    long_name = "a" * 40
    assert len(writer.generate_variable_name(long_name)) == 32
