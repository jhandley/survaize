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


def test_variable_name_uniqueness() -> None:
    """Test that variable names are unique even when they would be the same after truncation."""
    writer = SurveySolutionsWriter()

    # Create names that would be identical after truncation
    long_name_1 = "a" * 35 + "xyz"  # Will be truncated to first 32 chars
    long_name_2 = "a" * 35 + "abc"  # Will be truncated to same first 32 chars

    var1 = writer.generate_variable_name(long_name_1)
    var2 = writer.generate_variable_name(long_name_2)

    # Both should be 32 characters or less
    assert len(var1) <= 32
    assert len(var2) <= 32

    # They should be different
    assert var1 != var2

    # The second one should have a suffix
    assert var2.endswith("_1")


def test_variable_name_uniqueness_with_short_names() -> None:
    """Test that short duplicate names get unique suffixes."""
    writer = SurveySolutionsWriter()

    # Generate same name multiple times
    var1 = writer.generate_variable_name("test")
    var2 = writer.generate_variable_name("test")
    var3 = writer.generate_variable_name("test")

    # All should be different
    assert var1 == "test"
    assert var2 == "test_1"
    assert var3 == "test_2"


def test_variable_name_uniqueness_reset_between_questionnaires() -> None:
    """Test that variable name tracking is reset between questionnaires."""
    writer = SurveySolutionsWriter()

    # First questionnaire
    questions1: list[Question] = [
        TextQuestion(
            number="1",
            id="test",
            text="Test question",
            type=QuestionType.TEXT,
            instructions=None,
            universe=None,
            max_length=None,
        )
    ]

    section1 = Section(
        id="section1",
        number="A",
        title="Section 1",
        description="Test section",
        questions=questions1,
        occurrences=1,
        universe=None,
    )

    questionnaire1 = Questionnaire(
        title="Test 1",
        description="First test questionnaire",
        id_fields=["test"],
        sections=[section1],
        trailing_sections=[],
    )

    # Write first questionnaire
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_file:
        temp_path = Path(temp_file.name)

    try:
        writer.write(questionnaire1, temp_path)

        # Second questionnaire with same variable name
        questions2: list[Question] = [
            TextQuestion(
                number="1",
                id="test",
                text="Test question",
                type=QuestionType.TEXT,
                instructions=None,
                universe=None,
                max_length=None,
            )
        ]

        section2 = Section(
            id="section1",
            number="A",
            title="Section 1",
            description="Test section",
            questions=questions2,
            occurrences=1,
            universe=None,
        )

        questionnaire2 = Questionnaire(
            title="Test 2",
            description="Second test questionnaire",
            id_fields=["test"],
            sections=[section2],
            trailing_sections=[],
        )

        # Write second questionnaire
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_file2:
            temp_path2 = Path(temp_file2.name)

        try:
            writer.write(questionnaire2, temp_path2)

            # Variable names should be reset, so both should use "test" without suffix
            # Read both files and verify the variable names
            with zipfile.ZipFile(temp_path, "r") as zip_file:
                content1 = json.loads(zip_file.read("document.json"))

            with zipfile.ZipFile(temp_path2, "r") as zip_file:
                content2 = json.loads(zip_file.read("document.json"))

            # Both should have the same variable name since tracking was reset
            var_name1 = content1["Children"][0]["Children"][0]["VariableName"]
            var_name2 = content2["Children"][0]["Children"][0]["VariableName"]
            assert var_name1 == "test"
            assert var_name2 == "test"

        finally:
            temp_path2.unlink(missing_ok=True)
    finally:
        temp_path.unlink(missing_ok=True)
