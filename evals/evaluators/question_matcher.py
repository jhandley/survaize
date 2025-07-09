"""Question matching utilities for robust questionnaire comparison."""

import logging
from dataclasses import dataclass
from enum import Enum

from survaize.model.questionnaire import Question, Questionnaire

logger = logging.getLogger(__name__)


class MatchType(Enum):
    """Types of question matches."""
    NUMBER = "number"
    ID = "id"
    TEXT = "text"
    FUZZY = "fuzzy"
    POSITION = "position"


@dataclass
class QuestionMatch:
    """Represents a matched question pair with confidence score."""
    expected_idx: int
    actual_idx: int
    expected_question: Question
    actual_question: Question
    match_type: MatchType
    confidence: float


class QuestionMatcher:
    """Matches questions between questionnaires using multiple strategies, ignoring section boundaries."""
    
    def __init__(self, similarity_threshold: float = 0.8) -> None:
        self.similarity_threshold: float = similarity_threshold
    
    def match_questions(self, expected: Questionnaire, actual: Questionnaire) -> list[QuestionMatch]:
        """Match questions globally across questionnaires, ignoring section boundaries."""
        # Flatten all questions with global indices
        expected_questions: list[Question] = []
        for section in expected.sections:
            expected_questions.extend(section.questions)
        
        actual_questions: list[Question] = []
        for section in actual.sections:
            actual_questions.extend(section.questions)
        
        matches: list[QuestionMatch] = []
        used_actual: set[int] = set()
        
        # Level 1: Question number match (if both exist and are unique)
        for exp_idx, exp_q in enumerate(expected_questions):
            if exp_q.number and self._is_unique_number(exp_q.number, expected_questions):
                for act_idx, act_q in enumerate(actual_questions):
                    if (act_idx not in used_actual and 
                        act_q.number == exp_q.number and 
                        self._is_unique_number(act_q.number, actual_questions)):
                        matches.append(QuestionMatch(
                            exp_idx, act_idx, exp_q, act_q, MatchType.NUMBER, 1.0
                        ))
                        used_actual.add(act_idx)
                        break
        
        # Level 2: Question ID match (if both exist and are unique)
        matched_expected = {m.expected_idx for m in matches}
        for exp_idx, exp_q in enumerate(expected_questions):
            if (exp_idx not in matched_expected and 
                exp_q.id and self._is_unique_id(exp_q.id, expected_questions)):
                for act_idx, act_q in enumerate(actual_questions):
                    if (act_idx not in used_actual and 
                        act_q.id == exp_q.id and 
                        self._is_unique_id(act_q.id, actual_questions)):
                        matches.append(QuestionMatch(
                            exp_idx, act_idx, exp_q, act_q, MatchType.ID, 0.9
                        ))
                        used_actual.add(act_idx)
                        break
        
        # Level 3: Exact text match
        matched_expected = {m.expected_idx for m in matches}
        for exp_idx, exp_q in enumerate(expected_questions):
            if exp_idx not in matched_expected:
                for act_idx, act_q in enumerate(actual_questions):
                    if (act_idx not in used_actual and 
                        exp_q.text.strip() == act_q.text.strip()):
                        matches.append(QuestionMatch(
                            exp_idx, act_idx, exp_q, act_q, MatchType.TEXT, 0.8
                        ))
                        used_actual.add(act_idx)
                        break
        
        # Level 4: Fuzzy text match
        matched_expected = {m.expected_idx for m in matches}
        for exp_idx, exp_q in enumerate(expected_questions):
            if exp_idx not in matched_expected:
                best_match = None
                best_similarity = 0.0
                
                for act_idx, act_q in enumerate(actual_questions):
                    if act_idx not in used_actual:
                        similarity = self._text_similarity(exp_q.text, act_q.text)
                        if similarity >= self.similarity_threshold and similarity > best_similarity:
                            best_similarity = similarity
                            best_match = (act_idx, act_q)
                
                if best_match:
                    act_idx, act_q = best_match
                    matches.append(QuestionMatch(
                        exp_idx, act_idx, exp_q, act_q, MatchType.FUZZY, best_similarity * 0.7
                    ))
                    used_actual.add(act_idx)
        
        # Level 5: Position-based mapping for remaining questions
        matched_expected = {m.expected_idx for m in matches}
        unmatched_expected = [
            (i, q) for i, q in enumerate(expected_questions) 
            if i not in matched_expected
        ]
        unmatched_actual = [
            (i, q) for i, q in enumerate(actual_questions) 
            if i not in used_actual
        ]
        
        # Match by relative position if we have similar numbers of unmatched questions
        if unmatched_expected and unmatched_actual:
            position_matches = self._position_based_matching(
                unmatched_expected, unmatched_actual
            )
            
            for exp_idx, act_idx, confidence in position_matches:
                matches.append(QuestionMatch(
                    exp_idx, act_idx, expected_questions[exp_idx], 
                    actual_questions[act_idx], MatchType.POSITION, confidence
                ))
                used_actual.add(act_idx)

        return matches
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity using a simple approach based on common words."""
        # Normalize texts
        words1 = set(text1.lower().strip().split())
        words2 = set(text2.lower().strip().split())
        
        # Remove common stop words that don't add meaning
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", 
            "with", "by", "is", "are", "was", "were", "what", "how", "when", "where", "why", "which"
        }
        words1 = words1 - stop_words
        words2 = words2 - stop_words
        
        if not words1 or not words2:
            return 0.0
        
        # Calculate Jaccard similarity
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def _position_based_matching(
        self, 
        unmatched_expected: list[tuple[int, Question]], 
        unmatched_actual: list[tuple[int, Question]]
    ) -> list[tuple[int, int, float]]:
        """Match questions based on their relative positions."""
        matches: list[tuple[int, int, float]] = []
        
        # Simple greedy approach: match questions in order of their positions
        min_len = min(len(unmatched_expected), len(unmatched_actual))
        
        for i in range(min_len):
            exp_idx, exp_q = unmatched_expected[i]
            act_idx, act_q = unmatched_actual[i]
            
            # Calculate confidence based on position alignment and question type similarity
            confidence = 0.4  # Base confidence for position matching
            
            # Bonus if question types match
            if exp_q.type == act_q.type:
                confidence += 0.2
            
            # Small bonus for text similarity even if below threshold
            text_sim = self._text_similarity(exp_q.text, act_q.text)
            confidence += text_sim * 0.2
            
            # Cap confidence at reasonable level for position-based matching
            confidence = min(confidence, 0.6)
            
            matches.append((exp_idx, act_idx, confidence))
        
        return matches
    
    def _is_unique_number(self, number: str, questions: list[Question]) -> bool:
        """Check if a question number is unique within the question list."""
        if not number or number.isspace():
            return False
        count = sum(1 for q in questions if q.number == number)
        return count == 1
    
    def _is_unique_id(self, id_val: str, questions: list[Question]) -> bool:
        """Check if a question ID is unique within the question list."""
        if not id_val or id_val.isspace():
            return False
        count = sum(1 for q in questions if q.id == id_val)
        return count == 1
    
