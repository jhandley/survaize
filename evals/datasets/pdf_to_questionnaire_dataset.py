from pathlib import Path

from pydantic_evals import Case, Dataset

from evals.datasets.case_metadata import CaseMetadata
from evals.evaluators.questionnaire_evaluators import (
    OptionExtractionEvaluator,
    QuestionPresenceEvaluator,
    QuestionSectionGroupingEvaluator,
    QuestionTextEvaluator,
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
    # Create cases for all questionnaires
    cases: list[Case[Path, Questionnaire, CaseMetadata]] = []

    # Popstan Household Survey
    base_path = EXAMPLES_DIR / "PopstanHouseholdSurvey"
    pdf_path = base_path / "PopstanHouseholdQuestionnaire.pdf"
    json_path = base_path / "PopstanHouseholdQuestionnaire.json"

    popstan_case = _create_case(
        name="popstan_household_survey",
        input_path=pdf_path,
        ground_truth_json_path=json_path,
        metadata=CaseMetadata(
            difficulty=1,
            pages=4,
            sections=4,
            questions=24,
            question_types=[
                QuestionType.NUMERIC,
                QuestionType.TEXT,
                QuestionType.SINGLE_SELECT,
                QuestionType.MULTI_SELECT,
                QuestionType.DATE,
            ],
        ),
    )
    cases.append(popstan_case)

    # Japan National Survey of Family Income 2019
    base_path = EXAMPLES_DIR / "Japan National Survey of Family Income 2019"
    pdf_path = base_path / "JapanNationalSurveyFamilyIncome2019.pdf"
    json_path = base_path / "JapanNationalSurveyFamilyIncome2019.json"

    japan_case = _create_case(
        name="japan_national_survey_family_income_2019",
        input_path=pdf_path,
        ground_truth_json_path=json_path,
        metadata=CaseMetadata(
            difficulty=3,
            pages=2,
            sections=10,
            questions=47,
            question_types=[
                QuestionType.MULTI_SELECT,
                QuestionType.NUMERIC,
                QuestionType.SINGLE_SELECT,
                QuestionType.TEXT,
            ],
        ),
    )
    cases.append(japan_case)

    # Slovenia Census Questionnaire for Dwellings 2002
    base_path = EXAMPLES_DIR / "Slovenia Census Questionnaire for Dwellings 2002"
    pdf_path = base_path / "SloveniaCensusQuestionnaireDwellings2002.pdf"
    json_path = base_path / "SloveniaCensusQuestionnaireDwellings2002.json"

    slovenia_case = _create_case(
        name="slovenia_census_questionnaire_dwellings_2002",
        input_path=pdf_path,
        ground_truth_json_path=json_path,
        metadata=CaseMetadata(
            difficulty=2,
            pages=2,
            sections=2,
            questions=41,
            question_types=[
                QuestionType.MULTI_SELECT,
                QuestionType.NUMERIC,
                QuestionType.SINGLE_SELECT,
                QuestionType.TEXT,
            ],
        ),
    )
    cases.append(slovenia_case)

    # Rwanda Population and Housing Census 2022
    base_path = EXAMPLES_DIR / "Rwanda Population and Housing Census 2022"
    pdf_path = base_path / "RwandaPHC2022_HH_Questionnaire.pdf"
    json_path = base_path / "RwandaPHC2022_HH_Questionnaire.json"

    rwanda_case = _create_case(
        name="rwanda_phc_2022_hh_questionnaire",
        input_path=pdf_path,
        ground_truth_json_path=json_path,
        metadata=CaseMetadata(
            difficulty=5,
            pages=10,
            sections=5,
            questions=155,
            question_types=[
                QuestionType.LOCATION,
                QuestionType.MULTI_SELECT,
                QuestionType.NUMERIC,
                QuestionType.SINGLE_SELECT,
                QuestionType.TEXT,
            ],
        ),
    )
    cases.append(rwanda_case)

    # World Bank COVID-19 Impact on Firms
    base_path = EXAMPLES_DIR / "World Bank COVID-19 Impact on Firms"
    pdf_path = base_path / "WorldBankCOVID19ImpactFirms.pdf"
    json_path = base_path / "WorldBankCOVID19ImpactFirms.json"

    world_bank_case = _create_case(
        name="world_bank_covid19_impact_firms",
        input_path=pdf_path,
        ground_truth_json_path=json_path,
        metadata=CaseMetadata(
            difficulty=4,
            pages=17,
            sections=10,
            questions=81,
            question_types=[QuestionType.DATE, QuestionType.NUMERIC, QuestionType.SINGLE_SELECT, QuestionType.TEXT],
        ),
    )
    cases.append(world_bank_case)

    return Dataset(
        cases=cases,
        evaluators=[
            SectionPresenceEvaluator(),
            QuestionPresenceEvaluator(),
            QuestionTypeEvaluator(),
            QuestionTextEvaluator(),
            QuestionSectionGroupingEvaluator(),
            OptionExtractionEvaluator(),
        ],
    )
