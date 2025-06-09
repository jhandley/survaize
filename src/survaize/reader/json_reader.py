import json
from typing import IO

from survaize.model.questionnaire import Questionnaire


class JSONReader:
    """Read questionnaire from JSON file (Survaize JSON schema)."""

    def read(self, file: IO[bytes]) -> Questionnaire:
        """Read a document and extract its content.

        Args:
            file: File-like object containing the JSON questionnaire

        Returns:
            A Questionnaire containing the extracted content
        """
        file.seek(0)
        return Questionnaire.model_validate(json.load(file))
