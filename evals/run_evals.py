from pathlib import Path

from dotenv import load_dotenv

from evals.datasets.pdf_to_questionnaire_dataset import load_dataset
from survaize.config.llm_config import create_llm_config_from_env
from survaize.interpreter.ai_interpreter import AIQuestionnaireInterpreter
from survaize.model.questionnaire import Questionnaire
from survaize.reader.pdf_reader import PDFReader

load_dotenv()
config = create_llm_config_from_env()

async def convert_questionnaire(pdf_path: Path) -> Questionnaire:

    interpreter = AIQuestionnaireInterpreter(llm_config=config)
    pdf_reader = PDFReader(interpreter)
    with open(pdf_path, "rb") as f:
        questionnaire = pdf_reader.read(f)
    return questionnaire


def run_evals():

    dataset = load_dataset()

    report = dataset.evaluate_sync(task=convert_questionnaire)
    print(report)


if __name__ == "__main__":
    run_evals()