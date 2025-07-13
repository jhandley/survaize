from io import BytesIO
from unittest.mock import MagicMock, patch

from PIL import Image

from survaize.interpreter.ai_interpreter import AIQuestionnaireInterpreter
from survaize.model.questionnaire import Questionnaire
from survaize.reader.pdf_reader import PDFReader


def test_pdf_reader_without_ocr() -> None:
    interpreter = MagicMock(spec=AIQuestionnaireInterpreter)
    interpreter.interpret.return_value = Questionnaire(
        title="Survey",
        description=None,
        id_fields=[],
        sections=[],
        trailing_sections=[],
    )
    reader = PDFReader(interpreter, capture_ocr=False)
    img = Image.new("RGB", (10, 10), "white")
    with patch.object(PDFReader, "_extract_pages", return_value=[img]):
        questionnaire = reader.read(BytesIO(b"pdf"))

    scanned_doc = interpreter.interpret.call_args.args[0]
    assert scanned_doc.extracted_text == []
    assert isinstance(questionnaire, Questionnaire)
