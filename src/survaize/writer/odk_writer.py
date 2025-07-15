import logging
import re
from pathlib import Path

import logfire
from openpyxl import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from survaize.model.questionnaire import (
    DateQuestion,
    MultipleChoiceQuestion,
    NumericQuestion,
    Question,
    Questionnaire,
    SingleChoiceQuestion,
    TextQuestion,
)
from survaize.writer.writer import Writer

logger = logging.getLogger(__name__)


class ODKWriter(Writer):
    """Generate XLSForm workbooks for use with ODK."""

    @logfire.instrument()
    def write(self, questionnaire: Questionnaire, output_path: Path) -> None:
        """Write a questionnaire to an XLSForm workbook.

        Args:
            questionnaire: The questionnaire to convert.
            output_path: Path where the XLSForm workbook should be written.
        """
        logger.info("Writing XLSForm to %s", output_path)

        workbook = Workbook()
        survey_ws: Worksheet = workbook.active  # type: ignore[assignment]
        survey_ws.title = "survey"
        survey_ws.append(["type", "name", "label"])

        choices_ws: Worksheet = workbook.create_sheet("choices")
        choices_ws.append(["list_name", "name", "label"])

        for section in questionnaire.sections:
            survey_ws.append(["begin group", self._to_variable(section.id), section.title])
            for question in section.questions:
                self._add_question(question, survey_ws, choices_ws)
            survey_ws.append(["end group", "", ""])

        workbook.save(output_path)

    def _add_question(self, question: Question, survey_ws: Worksheet, choices_ws: Worksheet) -> None:
        name = self._to_variable(question.id)
        if isinstance(question, TextQuestion):
            survey_ws.append(["text", name, question.text])
        elif isinstance(question, NumericQuestion):
            q_type = "decimal" if question.decimal_places else "integer"
            survey_ws.append([q_type, name, question.text])
        elif isinstance(question, SingleChoiceQuestion):
            list_name = f"{name}_list"
            survey_ws.append([f"select_one {list_name}", name, question.text])
            for option in question.options:
                choices_ws.append([list_name, option.code, option.label])
        elif isinstance(question, MultipleChoiceQuestion):
            list_name = f"{name}_list"
            survey_ws.append([f"select_multiple {list_name}", name, question.text])
            for option in question.options:
                choices_ws.append([list_name, option.code, option.label])
        elif isinstance(question, DateQuestion):
            survey_ws.append(["date", name, question.text])
        else:  # LocationQuestion handled here
            survey_ws.append(["geopoint", name, question.text])

    def _to_variable(self, name: str) -> str:
        variable = re.sub(r"[^a-zA-Z0-9_]", "_", name)
        if variable and not variable[0].isalpha():
            variable = "v" + variable
        if not variable:
            variable = "var"
        variable = variable[:32]
        return variable.rstrip("_")
