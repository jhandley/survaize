from dataclasses import dataclass

from survaize.model.questionnaire import QuestionType


@dataclass
class CaseMetadata:
    """Metadata for a case."""

    difficulty: int  # scale of 1 to 5
    pages: int
    sections: int
    questions: int
    question_types: list[QuestionType]
