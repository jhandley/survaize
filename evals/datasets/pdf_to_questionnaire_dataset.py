
from pathlib import Path

from pydantic_evals import Case, Dataset

from evals.datasets.case_metadata import CaseMetadata
from evals.evaluators.questionnaire_evaluators import (
    OptionExtractionEvaluator,
    QuestionPresenceEvaluator,
    QuestionTypeEvaluator,
    SectionPresenceEvaluator,
)
from survaize.config.dirs import EXAMPLES_DIR
from survaize.model.questionnaire import Questionnaire, QuestionType
from survaize.reader.json_reader import JSONReader


def _create_case(
    name: str,
    input_path: Path,
    ground_truth_json_path: Path,
    metadata: CaseMetadata,
) -> Case[Path, Questionnaire, CaseMetadata]:

    with open(ground_truth_json_path, "rb") as f:
        ground_truth_json = JSONReader().read(f)
    return Case(
        name=name,
        inputs=input_path,
        expected_output=ground_truth_json,
        metadata=metadata,
    )

def load_dataset() -> Dataset[Path, Questionnaire, CaseMetadata]:

    # Path to the example files
    # Use a more descriptive approach with a clear path reference
    
    base_path = EXAMPLES_DIR / "PopstanHouseholdSurvey"
    pdf_path = base_path / "PopstanHouseholdQuestionnaire.pdf"
    json_path = base_path / "PopstanHouseholdQuestionnaire.json"

    # Create the case
    popstan_case = _create_case(
        name="popstan_household_survey",
        input_path=pdf_path,
        ground_truth_json_path=json_path,
        metadata=CaseMetadata(
            difficulty=1,
            pages=4,
            sections=4,
            questions=24,
            question_types=[QuestionType.NUMERIC, QuestionType.TEXT, QuestionType.SINGLE_SELECT, 
                QuestionType.MULTI_SELECT, QuestionType.DATE],
        ),
    )

    return Dataset(cases=[popstan_case], 
        evaluators=[SectionPresenceEvaluator(),
        QuestionPresenceEvaluator(),
        QuestionTypeEvaluator(),
        OptionExtractionEvaluator(),
        ])
