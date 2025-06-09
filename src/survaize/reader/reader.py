from typing import IO, Protocol

from survaize.model.questionnaire import Questionnaire


class Reader(Protocol):
    """Protocol defining the interface for questionnaire readers."""

    def read(self, file: IO[bytes]) -> Questionnaire:
        """Read a document and extract its content.

        Args:
            file: File-like object positioned at the beginning of the document

        Returns:
            A Questionnaire containing the extracted content
        """
        ...
