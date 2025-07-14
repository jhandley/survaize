"""Questionnaire-specific evaluators for Survaize."""

import logging
from pathlib import Path

from pydantic_evals.evaluators import Evaluator, EvaluatorContext
from typing_extensions import override

from evals.datasets.case_metadata import CaseMetadata
from evals.evaluators.question_matcher import QuestionMatcher
from evals.evaluators.section_matcher import SectionMatcher
from survaize.model.questionnaire import MultipleChoiceQuestion, Question, Questionnaire, SingleChoiceQuestion

logger = logging.getLogger(__name__)


class SectionPresenceEvaluator(Evaluator[Path, Questionnaire, CaseMetadata]):
    """Evaluator for checking that all expected sections are present."""

    def __init__(self) -> None:
        super().__init__()
        self.section_matcher: SectionMatcher = SectionMatcher()

    @override
    def evaluate(self, ctx: EvaluatorContext[Path, Questionnaire, CaseMetadata]) -> dict[str, float]:
        """Compute precision, recall, and F1 for section presence using robust matching."""
        expected = ctx.expected_output
        assert expected is not None, "Expected output must not be None"
        actual: Questionnaire = ctx.output

        # Use the section matcher to find section correspondences
        section_matches = self.section_matcher.match_sections(expected, actual)

        true_positives = len(section_matches)
        total_expected = len(expected.sections)
        total_actual = len(actual.sections)

        precision = true_positives / total_actual if total_actual else 0.0
        recall = true_positives / total_expected if total_expected else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall > 0 else 0.0

        # Log mismatches for debugging
        matched_expected_indices = set(section_matches.keys())
        matched_actual_indices = set(section_matches.values())

        missing_sections = [
            f"Section {i}: ({expected.sections[i].number}, '{expected.sections[i].title}')"
            for i in range(len(expected.sections))
            if i not in matched_expected_indices
        ]

        extra_sections = [
            f"Section {i}: ({actual.sections[i].number}, '{actual.sections[i].title}')"
            for i in range(len(actual.sections))
            if i not in matched_actual_indices
        ]

        if missing_sections:
            logger.warning(f"Missing sections ({len(missing_sections)}): {missing_sections}")
        if extra_sections:
            logger.warning(f"Unexpected sections ({len(extra_sections)}): {extra_sections}")

        return {
            "section_presence_precision": precision,
            "section_presence_recall": recall,
            "section_presence_f1": f1,
        }


class QuestionPresenceEvaluator(Evaluator[Path, Questionnaire, CaseMetadata]):
    """Evaluator for checking that all expected questions are present."""

    def __init__(self) -> None:
        super().__init__()
        self.matcher: QuestionMatcher = QuestionMatcher()

    @override
    def evaluate(self, ctx: EvaluatorContext[Path, Questionnaire, CaseMetadata]) -> dict[str, float]:
        """Compute precision, recall, and F1 for question presence using robust matching."""
        expected = ctx.expected_output
        assert expected is not None, "Expected output must not be None"
        actual: Questionnaire = ctx.output

        # Get all questions flattened across sections
        expected_questions: list[Question] = []
        for section in expected.sections:
            expected_questions.extend(section.questions)

        actual_questions: list[Question] = []
        for section in actual.sections:
            actual_questions.extend(section.questions)

        # Use the matcher to find question correspondences
        matches = self.matcher.match_questions(expected, actual)

        true_positives = len(matches)
        total_expected = len(expected_questions)
        total_actual = len(actual_questions)

        precision = true_positives / total_actual if total_actual else 0.0
        recall = true_positives / total_expected if total_expected else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall > 0 else 0.0

        # Log mismatches for debugging
        matched_expected_indices = {m.expected_idx for m in matches}
        matched_actual_indices = {m.actual_idx for m in matches}

        missing_questions = [
            f"Q{i}: {expected_questions[i].number or 'no_num'} - {expected_questions[i].text[:50]}..."
            for i in range(len(expected_questions))
            if i not in matched_expected_indices
        ]

        extra_questions = [
            f"Q{i}: {actual_questions[i].number or 'no_num'} - {actual_questions[i].text[:50]}..."
            for i in range(len(actual_questions))
            if i not in matched_actual_indices
        ]

        if missing_questions:
            logger.warning(f"Missing questions ({len(missing_questions)}): {missing_questions[:5]}...")
        if extra_questions:
            logger.warning(f"Unexpected questions ({len(extra_questions)}): {extra_questions[:5]}...")

        # Log match statistics
        match_types: dict[str, int] = {}
        for match in matches:
            match_type_str = match.match_type.value
            match_types[match_type_str] = match_types.get(match_type_str, 0) + 1
        logger.info(f"Question match statistics: {match_types}")

        return {
            "question_presence_precision": precision,
            "question_presence_recall": recall,
            "question_presence_f1": f1,
        }


class QuestionTypeEvaluator(Evaluator[Path, Questionnaire, CaseMetadata]):
    """Evaluator for checking that question types match the expected types."""

    def __init__(self) -> None:
        super().__init__()
        self.matcher: QuestionMatcher = QuestionMatcher()

    @override
    def evaluate(self, ctx: EvaluatorContext[Path, Questionnaire, CaseMetadata]) -> dict[str, float]:
        expected = ctx.expected_output
        assert expected is not None, "Expected output must not be None"
        actual: Questionnaire = ctx.output

        # Get all questions flattened across sections
        expected_questions: list[Question] = []
        for section in expected.sections:
            expected_questions.extend(section.questions)

        actual_questions: list[Question] = []
        for section in actual.sections:
            actual_questions.extend(section.questions)

        # Use the matcher to find question correspondences
        matches = self.matcher.match_questions(expected, actual)

        # Count type matches among successfully matched questions
        type_matches = 0
        total_matches = len(matches)

        for match in matches:
            if match.expected_question.type == match.actual_question.type:
                type_matches += 1
            else:
                logger.warning(
                    f"Type mismatch: {match.expected_question.number or match.expected_question.id} "
                    + f"expected {match.expected_question.type}, got {match.actual_question.type}"
                )

        # For precision: how many of the actual questions that were matched have correct types
        precision = type_matches / total_matches if total_matches else 0.0

        # For recall: how many of the expected questions were matched with correct types
        total_expected = len(expected_questions)
        recall = type_matches / total_expected if total_expected else 0.0

        f1 = 2 * precision * recall / (precision + recall) if precision + recall > 0 else 0.0

        return {
            "question_type_precision": precision,
            "question_type_recall": recall,
            "question_type_f1": f1,
        }


class OptionExtractionEvaluator(Evaluator[Path, Questionnaire, CaseMetadata]):
    """Evaluator for checking that select‐question options are correctly extracted."""

    def __init__(self) -> None:
        super().__init__()
        self.matcher: QuestionMatcher = QuestionMatcher()

    @override
    def evaluate(self, ctx: EvaluatorContext[Path, Questionnaire, CaseMetadata]) -> dict[str, float]:
        expected = ctx.expected_output
        assert expected is not None, "Expected output must not be None"
        actual: Questionnaire = ctx.output

        # Use the matcher to find question correspondences
        matches = self.matcher.match_questions(expected, actual)

        # Filter matches to only include select questions and count option matches
        option_matches = 0
        total_select_matches = 0

        for match in matches:
            exp_q = match.expected_question
            act_q = match.actual_question

            # Only evaluate option extraction for select questions
            if isinstance(exp_q, SingleChoiceQuestion | MultipleChoiceQuestion):
                total_select_matches += 1

                # Check if actual question is also a select question
                if isinstance(act_q, SingleChoiceQuestion | MultipleChoiceQuestion):
                    # Compare options lists
                    if exp_q.options == act_q.options:
                        option_matches += 1
                    else:
                        # Format options more readably
                        exp_opts = (
                            "\n    - " + "\n    - ".join(str(opt) for opt in exp_q.options) if exp_q.options else "[]"
                        )
                        act_opts = (
                            "\n    - " + "\n    - ".join(str(opt) for opt in act_q.options) if act_q.options else "[]"
                        )

                        logger.warning(
                            f"Option mismatch for {exp_q.number or exp_q.id}:\n"
                            + f"Expected options:{exp_opts}\n"
                            + f"Actual options:{act_opts}"
                        )
                else:
                    logger.warning(
                        f"Type mismatch for select question {exp_q.number or exp_q.id}: "
                        + f"expected select question, got {act_q.type}"
                    )

        # Calculate metrics based on successfully matched select questions
        precision = option_matches / total_select_matches if total_select_matches else 0.0

        # For recall, count all expected select questions
        total_expected_select = sum(
            1
            for section in expected.sections
            for question in section.questions
            if isinstance(question, SingleChoiceQuestion | MultipleChoiceQuestion)
        )

        recall = option_matches / total_expected_select if total_expected_select else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall > 0 else 0.0

        return {
            "option_extraction_precision": precision,
            "option_extraction_recall": recall,
            "option_extraction_f1": f1,
        }


class QuestionTextEvaluator(Evaluator[Path, Questionnaire, CaseMetadata]):
    """Evaluator for checking that question text fields are an exact match."""

    def __init__(self) -> None:
        super().__init__()
        self.matcher: QuestionMatcher = QuestionMatcher()

    @override
    def evaluate(self, ctx: EvaluatorContext[Path, Questionnaire, CaseMetadata]) -> dict[str, float]:
        """Compute precision, recall, and F1 for exact question text matches."""
        expected = ctx.expected_output
        assert expected is not None, "Expected output must not be None"
        actual: Questionnaire = ctx.output

        # Get all questions flattened across sections
        expected_questions: list[Question] = []
        for section in expected.sections:
            expected_questions.extend(section.questions)

        actual_questions: list[Question] = []
        for section in actual.sections:
            actual_questions.extend(section.questions)

        # Use the matcher to find question correspondences
        matches = self.matcher.match_questions(expected, actual)

        # Count exact text matches among successfully matched questions
        text_matches = 0
        total_matches = len(matches)

        for match in matches:
            if match.expected_question.text == match.actual_question.text:
                text_matches += 1
            else:
                logger.warning(
                    f"Text mismatch for {match.expected_question.number or match.expected_question.id}: "
                    + f"expected '{match.expected_question.text}', "
                    + f"got '{match.actual_question.text}'"
                )

        # For precision: how many of the actual questions that were matched have exact text
        precision = text_matches / total_matches if total_matches else 0.0

        # For recall: how many of the expected questions were matched with exact text
        total_expected = len(expected_questions)
        recall = text_matches / total_expected if total_expected else 0.0

        f1 = 2 * precision * recall / (precision + recall) if precision + recall > 0 else 0.0

        return {
            "question_text_precision": precision,
            "question_text_recall": recall,
            "question_text_f1": f1,
        }


class QuestionSectionGroupingEvaluator(Evaluator[Path, Questionnaire, CaseMetadata]):
    """Evaluator for checking that questions are correctly grouped into their expected sections."""

    def __init__(self) -> None:
        super().__init__()
        self.matcher: QuestionMatcher = QuestionMatcher()
        self.section_matcher: SectionMatcher = SectionMatcher()

    @override
    def evaluate(self, ctx: EvaluatorContext[Path, Questionnaire, CaseMetadata]) -> dict[str, float]:
        """Compute precision, recall, and F1 for correct question section grouping."""
        expected = ctx.expected_output
        assert expected is not None, "Expected output must not be None"
        actual: Questionnaire = ctx.output

        # First, match sections between expected and actual questionnaires
        section_matches = self.section_matcher.match_sections(expected, actual)

        # Build mappings from question flat index to matched section index
        expected_question_to_section_idx: dict[int, int] = {}
        flat_idx = 0
        for section_idx, section in enumerate(expected.sections):
            for _ in section.questions:
                expected_question_to_section_idx[flat_idx] = section_idx
                flat_idx += 1

        actual_question_to_section_idx: dict[int, int] = {}
        flat_idx = 0
        for section_idx, section in enumerate(actual.sections):
            for _ in section.questions:
                actual_question_to_section_idx[flat_idx] = section_idx
                flat_idx += 1

        # Use the question matcher to find question correspondences
        matches = self.matcher.match_questions(expected, actual)

        # Count correct section groupings among successfully matched questions
        correct_groupings = 0
        total_matches = len(matches)

        for match in matches:
            # Get section indices for both questions
            expected_section_idx = expected_question_to_section_idx.get(match.expected_idx)
            actual_section_idx = actual_question_to_section_idx.get(match.actual_idx)

            if expected_section_idx is not None and actual_section_idx is not None:
                # Check if the actual section matches the expected section
                expected_matched_section_idx = section_matches.get(expected_section_idx)

                if expected_matched_section_idx == actual_section_idx:
                    correct_groupings += 1
                else:
                    # Log the mismatch with section details
                    question_id = match.expected_question.number or match.expected_question.id
                    exp_section = expected.sections[expected_section_idx]
                    act_section = actual.sections[actual_section_idx]

                    if expected_matched_section_idx is not None:
                        expected_matched_section = actual.sections[expected_matched_section_idx]
                        logger.warning(
                            f"Section grouping mismatch for question {question_id}: "
                            + f"expected in section ({exp_section.number}, '{exp_section.title}') "
                            + f"which matches actual section ({expected_matched_section.number}, "
                            + f"'{expected_matched_section.title}'), "
                            + f"but found in section ({act_section.number}, '{act_section.title}')"
                        )
                    else:
                        logger.warning(
                            f"Section grouping mismatch for question {question_id}: "
                            + f"expected section ({exp_section.number}, '{exp_section.title}') has no match, "
                            + f"but question found in section ({act_section.number}, '{act_section.title}')"
                        )
            else:
                question_id = match.expected_question.number or match.expected_question.id
                logger.warning(f"Could not determine section for question {question_id}")

        # For precision: how many of the matched questions are in the correct section
        precision = correct_groupings / total_matches if total_matches else 0.0

        # For recall: how many of the expected questions were matched and placed in correct sections
        total_expected_questions = sum(len(section.questions) for section in expected.sections)
        recall = correct_groupings / total_expected_questions if total_expected_questions else 0.0

        f1 = 2 * precision * recall / (precision + recall) if precision + recall > 0 else 0.0

        return {
            "question_section_grouping_precision": precision,
            "question_section_grouping_recall": recall,
            "question_section_grouping_f1": f1,
        }
