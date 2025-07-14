from pathlib import Path

import logfire
from dotenv import load_dotenv

from evals.datasets.pdf_to_questionnaire_dataset import load_dataset
from survaize.config.llm_config import create_llm_config_from_env
from survaize.interpreter.ai_interpreter import AIQuestionnaireInterpreter
from survaize.model.questionnaire import Questionnaire
from survaize.reader.pdf_reader import PDFReader

load_dotenv()
config = create_llm_config_from_env()

logfire.configure(
    send_to_logfire="if-token-present",
    environment="development",
    service_name="evals",
)
logfire.instrument_openai()


async def convert_questionnaire(pdf_path: Path) -> Questionnaire:
    interpreter = AIQuestionnaireInterpreter(llm_config=config, sleep_between_pages_seconds=10)
    pdf_reader = PDFReader(interpreter)
    with open(pdf_path, "rb") as f:
        questionnaire = pdf_reader.read(f)
    return questionnaire


def run_evals():
    dataset = load_dataset()

    report = dataset.evaluate_sync(task=convert_questionnaire, max_concurrency=1)
    print(report)


if __name__ == "__main__":
    run_evals()
