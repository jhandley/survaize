"""Module for orchestrating the questionnaire conversion process."""

import logging
from pathlib import Path

from survaize.config.llm_config import LLMConfig
from survaize.reader.reader_factory import ReaderFactory
from survaize.writer.writer_factory import WriterFactory

logger = logging.getLogger(__name__)


class QuestionnaireConverter:
    """Orchestrates the conversion of questionnaires."""

    def __init__(self, llm_config: LLMConfig):
        """Initialize the converter.
        Args:
            llm_config: Configuration for the LLM (API key, version, URL, deployment)
        """

        self.reader_factory: ReaderFactory = ReaderFactory(llm_config)
        self.writer_factory: WriterFactory = WriterFactory()

    def convert(self, input_file: Path, output_file: Path, output_format: str):
        """Convert a questionnaire to the specified format.

        Args:
            input_file: Path to the input file
            output_file: Path to file to write the output to
            output_format: Output format

        Returns:
            Path to the generated output file
        """
        output_file.parent.mkdir(parents=True, exist_ok=True)

        input_format_str = input_file.suffix.lower().replace(".", "")
        reader = self.reader_factory.get(input_format_str)

        logger.info(f"Reading questionnaire: {input_file}")
        questionnaire = reader.read(input_file)

        writer = self.writer_factory.get(output_format)

        logger.info(f"Writing converted questionnaire: {output_file}")
        writer.write(questionnaire, output_file)
