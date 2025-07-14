"""Survey Solutions writer that converts Survaize questionnaires to Survey Solutions JSON format."""

import json
import logging
import re
import zipfile
from pathlib import Path

from typing_extensions import override

from ..model.questionnaire import (
    DateQuestion,
    MultipleChoiceQuestion,
    NumericQuestion,
    Question,
    Questionnaire,
    Section,
    SingleChoiceQuestion,
    TextQuestion,
)
from ..surveysolutions.models import (
    Answer,
    DateTimeQuestion,
    GpsCoordinateQuestion,
    Group,
    MultiOptionsQuestion,
    QuestionElement,
    QuestionnaireMetaInfo,
    SingleQuestion,
    SurveySolutionsQuestionnaire,
)
from ..surveysolutions.models import (
    NumericQuestion as SSNumericQuestion,
)
from ..surveysolutions.models import (
    TextQuestion as SSTextQuestion,
)
from ..writer.writer import Writer

logger = logging.getLogger(__name__)


class SurveySolutionsWriter(Writer):
    """Writer that converts Survaize questionnaires to Survey Solutions JSON format."""

    @override
    def write(self, questionnaire: Questionnaire, output_path: Path) -> None:
        """Write a questionnaire to Survey Solutions backup format (zip file).

        Args:
            questionnaire: The Survaize questionnaire to convert
            output_path: The path where the Survey Solutions backup zip will be written
        """
        logger.info(f"Converting questionnaire '{questionnaire.title}' to Survey Solutions format")

        # Convert Survaize questionnaire to Survey Solutions format
        ss_questionnaire = self._convert_questionnaire(questionnaire)

        # Create zip file with proper Survey Solutions backup structure
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # Add the main questionnaire document as document.json
            questionnaire_json = json.dumps(ss_questionnaire.model_dump(by_alias=True, exclude_none=True), indent=2)
            zip_file.writestr("document.json", questionnaire_json)

        logger.info(f"Successfully wrote Survey Solutions questionnaire backup to {output_path}")

    def _convert_questionnaire(self, questionnaire: Questionnaire) -> SurveySolutionsQuestionnaire:
        """Convert a Survaize questionnaire to Survey Solutions format.

        Args:
            questionnaire: The source questionnaire

        Returns:
            Survey Solutions questionnaire object
        """
        # Convert sections to groups
        groups: list[Group] = []
        for section in questionnaire.sections:
            group = self._convert_section_to_group(section)
            groups.append(group)

        # Create metadata
        metadata = QuestionnaireMetaInfo()

        # Create the questionnaire
        ss_questionnaire = SurveySolutionsQuestionnaire(
            Title=questionnaire.title,
            Description=questionnaire.description,
            VariableName=self.generate_variable_name(questionnaire.title),
            Children=groups,
            Metadata=metadata,
        )

        return ss_questionnaire

    def _convert_section_to_group(self, section: Section) -> Group:
        """Convert a Survaize section to a Survey Solutions group.

        Args:
            section: The source section

        Returns:
            Survey Solutions group object
        """
        # Convert questions to Survey Solutions format
        children: list[QuestionElement] = []
        for question in section.questions:
            ss_question = self._convert_question(question)
            children.append(ss_question)

        group = Group(VariableName=self.generate_variable_name(section.id), Title=section.title, Children=children)

        return group

    def _convert_question(self, question: Question) -> QuestionElement:
        """Convert a Survaize question to appropriate Survey Solutions question type.

        Args:
            question: The source question

        Returns:
            Survey Solutions question object
        """
        variable_name = self.generate_variable_name(question.id)

        if isinstance(question, TextQuestion):
            return SSTextQuestion(
                VariableName=variable_name, QuestionText=question.text, Instructions=question.instructions
            )

        elif isinstance(question, NumericQuestion):
            return SSNumericQuestion(
                VariableName=variable_name,
                QuestionText=question.text,
                Instructions=question.instructions,
                IsInteger=question.decimal_places is None or question.decimal_places == 0,
                DecimalPlaces=(
                    question.decimal_places if question.decimal_places and question.decimal_places > 0 else None
                ),
            )

        elif isinstance(question, SingleChoiceQuestion):
            single_answers: list[Answer] = []
            for i, option in enumerate(question.options):
                # Use the option code if it's numeric, otherwise use index + 1
                try:
                    code = int(option.code)
                except ValueError:
                    code = i + 1

                answer = Answer(Text=option.label, Code=code)
                single_answers.append(answer)

            return SingleQuestion(
                VariableName=variable_name,
                QuestionText=question.text,
                Instructions=question.instructions,
                Answers=single_answers,
            )

        elif isinstance(question, MultipleChoiceQuestion):
            multi_answers: list[Answer] = []
            for i, option in enumerate(question.options):
                # Use the option code if it's numeric, otherwise use index + 1
                try:
                    code = int(option.code)
                except ValueError:
                    code = i + 1

                answer = Answer(Text=option.label, Code=code)
                multi_answers.append(answer)

            return MultiOptionsQuestion(
                VariableName=variable_name,
                QuestionText=question.text,
                Instructions=question.instructions,
                Answers=multi_answers,
                MaxAllowedAnswers=question.max_selections,
            )

        elif isinstance(question, DateQuestion):
            return DateTimeQuestion(
                VariableName=variable_name, QuestionText=question.text, Instructions=question.instructions
            )

        else:  # LocationQuestion - this handles the remaining case
            return GpsCoordinateQuestion(
                VariableName=variable_name, QuestionText=question.text, Instructions=question.instructions
            )

    def generate_variable_name(self, name: str) -> str:
        """Generate a valid Survey Solutions variable name from a string.

        Survey Solutions variable names must:
        - Start with a letter
        - Contain only letters, numbers, and underscores
        - Be no longer than 32 characters

        Args:
            name: The source name

        Returns:
            A valid variable name
        """
        # Remove special characters and replace spaces with underscores
        variable_name = re.sub(r"[^a-zA-Z0-9_]", "_", name)

        # Ensure it starts with a letter
        if variable_name and not variable_name[0].isalpha():
            variable_name = "V" + variable_name

        # Ensure it's not empty
        if not variable_name:
            variable_name = "Variable"

        # Truncate to 32 characters
        if len(variable_name) > 32:
            variable_name = variable_name[:32]

        # Remove trailing underscores
        variable_name = variable_name.rstrip("_")

        return variable_name
