"""Section matching utilities for questionnaire evaluation."""

from dataclasses import dataclass

from survaize.model.questionnaire import Questionnaire, Section


@dataclass
class SectionMatch:
    """Represents a matched section pair."""

    expected_idx: int
    actual_idx: int
    expected_section: Section
    actual_section: Section
    match_type: str
    confidence: float


class SectionMatcher:
    """Simple matcher for sections using number, title, and position."""

    def match_sections(self, expected: Questionnaire, actual: Questionnaire) -> dict[int, int]:
        """
        Match sections between questionnaires.
        Returns a mapping from expected section index to actual section index.
        """
        expected_sections = expected.sections
        actual_sections = actual.sections

        section_matches: dict[int, int] = {}
        used_actual: set[int] = set()

        # Level 1: Exact number and title match
        for exp_idx, exp_section in enumerate(expected_sections):
            for act_idx, act_section in enumerate(actual_sections):
                if (
                    act_idx not in used_actual
                    and exp_section.number == act_section.number
                    and exp_section.title == act_section.title
                ):
                    section_matches[exp_idx] = act_idx
                    used_actual.add(act_idx)
                    break

        # Level 2: Number match only (if unique)
        for exp_idx, exp_section in enumerate(expected_sections):
            if (
                exp_idx not in section_matches
                and sum(1 for s in expected_sections if s.number == exp_section.number) == 1
            ):
                for act_idx, act_section in enumerate(actual_sections):
                    if (
                        act_idx not in used_actual
                        and act_section.number == exp_section.number
                        and sum(1 for s in actual_sections if s.number == act_section.number) == 1
                    ):
                        section_matches[exp_idx] = act_idx
                        used_actual.add(act_idx)
                        break

        # Level 3: Title match only (if reasonably unique)
        for exp_idx, exp_section in enumerate(expected_sections):
            if exp_idx not in section_matches:
                for act_idx, act_section in enumerate(actual_sections):
                    if (
                        act_idx not in used_actual
                        and exp_section.title.strip().lower() == act_section.title.strip().lower()
                    ):
                        section_matches[exp_idx] = act_idx
                        used_actual.add(act_idx)
                        break

        # Level 4: Position-based fallback
        for exp_idx, _ in enumerate(expected_sections):
            if exp_idx not in section_matches and exp_idx < len(actual_sections) and exp_idx not in used_actual:
                section_matches[exp_idx] = exp_idx
                used_actual.add(exp_idx)

        return section_matches
