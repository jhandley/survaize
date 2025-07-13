"""Module defining the document reading layer of the pipeline."""

import logging
from collections.abc import Callable
from pathlib import Path
from typing import IO

import cv2
import logfire
import numpy as np
import pdf2image
import pytesseract
from PIL import Image

from survaize.interpreter.ai_interpreter import AIQuestionnaireInterpreter
from survaize.interpreter.scanned_questionnaire import ScannedQuestionnaire
from survaize.model.questionnaire import Questionnaire

# Configure logger
logger = logging.getLogger(__name__)


class PDFReader:
    """Reads PDF documents and optionally performs OCR extraction."""

    def __init__(
        self,
        interpreter: AIQuestionnaireInterpreter,
        capture_ocr: bool = True,
    ) -> None:
        """Initialize the PDFReader with an interpreter.

        Args:
            interpreter: An instance of AIQuestionnaireInterpreter
            capture_ocr: Flag indicating whether OCR text should be captured.
        """
        self.interpreter: AIQuestionnaireInterpreter = interpreter
        self.capture_ocr: bool = capture_ocr

    @logfire.instrument(extract_args=False)
    def read(
        self,
        file: IO[bytes],
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> Questionnaire:
        """Read a PDF document and extract its content.

        Args:
            file: File-like object containing the PDF

        Returns:
            A Questionnaire containing the extracted content. When
            ``capture_ocr`` is ``False`` no OCR text is returned.
        """

        if progress_callback:
            progress_callback(0, "Extracting pages")
        pages = self._extract_pages(file)
        if progress_callback:
            progress_callback(1, f"Extracted {len(pages)} pages")

        texts: list[str] = []
        if self.capture_ocr:
            for i, page in enumerate(pages, start=1):
                if progress_callback:
                    percent = int(10 * (i - 1) / len(pages))
                    progress_callback(percent, f"Extracting image from page {i}/{len(pages)}")
                texts.append(self._process_page(page))

        scanned_questionnaire = ScannedQuestionnaire(
            pages=pages,
            extracted_text=texts if self.capture_ocr else [],
            source_path=Path("<in-memory>"),
        )

        if progress_callback:
            progress_callback(10, "Interpreting questionnaire")

            def scaled_progress(percent: int, message: str) -> None:
                progress_callback(10 + int(percent * 0.9), message)

            questionnaire = self.interpreter.interpret(
                scanned_questionnaire,
                scaled_progress,
            )
            progress_callback(100, "Completed")
        else:
            questionnaire = self.interpreter.interpret(scanned_questionnaire)
        return questionnaire

    def _extract_pages(self, pdf_file: IO[bytes]) -> list[Image.Image]:
        """Convert PDF pages to images.

        Args:
            pdf_file: File-like object containing the PDF

        Returns:
            list of PIL Image objects, one per page
        """
        logger.info("Converting PDF to images from bytes")
        pdf_file.seek(0)
        return pdf2image.convert_from_bytes(pdf_file.read())  # type: ignore

    def _process_page(self, image: Image.Image) -> str:
        """Process a single page image with OCR.

        Args:
            image: PIL Image object of the page

        Returns:
            Extracted text from the page
        """
        # Convert PIL image to OpenCV format for preprocessing
        opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        # Basic image preprocessing
        gray = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2GRAY)
        denoised = cv2.fastNlMeansDenoising(gray)

        # Perform OCR
        return pytesseract.image_to_string(denoised)  # type: ignore
