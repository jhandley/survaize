from survaize.config.llm_config import LLMConfig
from survaize.interpreter.ai_interpreter import AIQuestionnaireInterpreter
from survaize.reader.json_reader import JSONReader
from survaize.reader.pdf_reader import PDFReader
from survaize.reader.reader import Reader


class ReaderFactory:
    """Factory for creating reader instances."""

    def __init__(self, llm_config: LLMConfig) -> None:
        """Initialize the ReaderFactory.

        Args:
            llm_config: Configuration for the LLM, required for PDFReader.
        """
        interpreter = AIQuestionnaireInterpreter(llm_config)
        self._readers: dict[str, Reader] = {
            "pdf": PDFReader(interpreter),
            "json": JSONReader(),
        }

    def get(self, input_format: str) -> Reader:
        """Get a reader instance based on the input format.

        Args:
            input_format: The type of reader to create (e.g., "pdf", "json").

        Returns:
            A reader instance.

        Raises:
            ValueError: If an unsupported input format is provided.
        """
        reader = self._readers.get(input_format)
        if not reader:
            supported_formats_str = ", ".join(self.get_supported_formats())
            raise ValueError(
                f"Unsupported input format: {input_format}. Supported formats are: {supported_formats_str}"
            )
        return reader

    def get_supported_formats(self) -> list[str]:
        """Get a list of supported input formats.

        Returns:
            A list of strings representing the supported input formats.
        """
        return list(self._readers.keys())
