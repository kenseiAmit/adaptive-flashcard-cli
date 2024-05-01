"""Core quiz engine implementing Strategy and Factory patterns."""

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Sequence, Type, Union

from utils.file_handler import Flashcard


def _normalize_cards(
    cards: Sequence[Union[Flashcard, Dict[str, Any]]],
) -> List[Flashcard]:
    """Convert Flashcard objects or dicts into a validated Flashcard list.

    Args:
        cards: Non-empty sequence of Flashcard objects or dictionaries.

    Returns:
        List of Flashcard instances.

    Raises:
        ValueError: If the card sequence is empty or has invalid elements.
    """
    if not cards:
        raise ValueError(
            "Cannot initialize quiz mode with an empty deck of cards."
        )

    normalized: List[Flashcard] = []
    for idx, item in enumerate(cards, start=1):
        if isinstance(item, Flashcard):
            normalized.append(item)
        elif isinstance(item, dict):
            normalized.append(Flashcard.from_dict(item, index=idx))
        else:
            raise ValueError(
                f"Invalid card at index {idx}: expected Flashcard or dict, "
                f"got {type(item).__name__}."
            )
    return normalized


class QuizMode(ABC):
    """Abstract base class (Strategy interface) for card selection."""

    def __init__(
        self, cards: Sequence[Union[Flashcard, Dict[str, Any]]]
    ) -> None:
        """Initialize the quiz mode with a deck of flashcards.

        Args:
            cards: Sequence of Flashcard instances or dictionaries.
        """
        self._original_cards: List[Flashcard] = _normalize_cards(cards)

    @property
    @abstractmethod
    def mode_name(self) -> str:
        """Return the canonical lowercase name of the quiz mode."""

    @abstractmethod
    def has_more_cards(self) -> bool:
        """Return True if there are remaining cards to serve in the session."""

    @abstractmethod
    def get_next_card(self) -> Optional[Flashcard]:
        """Return the next flashcard according to the strategy, or None."""

    def record_result(
        self, card: Union[Flashcard, Dict[str, Any]], is_correct: bool
    ) -> None:
        """Record whether the user answered the given card correctly.

        Default implementation is a no-op; adaptive strategies override this.

        Args:
            card: The flashcard that was answered.
            is_correct: True if the user's answer was correct, False otherwise.
        """

    @abstractmethod
    def reset(self) -> None:
        """Reset the strategy to its initial state for a fresh session."""


class SequentialMode(QuizMode):
    """Strategy that presents flashcards in sequential order from 1 to N."""

    def __init__(
        self, cards: Sequence[Union[Flashcard, Dict[str, Any]]]
    ) -> None:
        """Initialize sequential mode."""
        super().__init__(cards)
        self._index: int = 0

    @property
    def mode_name(self) -> str:
        """Return canonical mode name."""
        return "sequential"

    def has_more_cards(self) -> bool:
        """Return True if current index is within the deck bounds."""
        return self._index < len(self._original_cards)

    def get_next_card(self) -> Optional[Flashcard]:
        """Return the next sequential card, or None if deck is exhausted."""
        if not self.has_more_cards():
            return None
        card = self._original_cards[self._index]
        self._index += 1
        return card

    def reset(self) -> None:
        """Reset pointer back to the first card."""
        self._index = 0


class RandomMode(QuizMode):
    """Strategy that shuffles the deck and serves cards in random order."""

    def __init__(
        self,
        cards: Sequence[Union[Flashcard, Dict[str, Any]]],
        seed: Optional[int] = None,
    ) -> None:
        """Initialize random mode with an optional seed for reproducibility."""
        super().__init__(cards)
        self._seed: Optional[int] = seed
        self._rng = random.Random(seed)
        self._shuffled_cards: List[Flashcard] = []
        self._index: int = 0
        self.reset()

    @property
    def mode_name(self) -> str:
        """Return canonical mode name."""
        return "random"

    def has_more_cards(self) -> bool:
        """Return True if more shuffled cards remain."""
        return self._index < len(self._shuffled_cards)

    def get_next_card(self) -> Optional[Flashcard]:
        """Return the next card from the shuffled deck, or None if finished."""
        if not self.has_more_cards():
            return None
        card = self._shuffled_cards[self._index]
        self._index += 1
        return card

    def reset(self) -> None:
        """Reshuffle a fresh copy of the original deck and reset the index."""
        self._shuffled_cards = list(self._original_cards)
        self._rng.shuffle(self._shuffled_cards)
        self._index = 0


class AdaptiveMode(QuizMode):
    """Strategy that prioritizes and repeats cards answered incorrectly.

    Cards missed during the session are assigned higher priority weights based
    on their cumulative error counts and re-inserted into a priority retry
    queue so the learner reinforces difficult concepts.
    """

    def __init__(
        self,
        cards: Sequence[Union[Flashcard, Dict[str, Any]]],
        max_repeats: int = 1,
    ) -> None:
        """Initialize adaptive mode.

        Args:
            cards: Sequence of Flashcard instances or dictionaries.
            max_repeats: Maximum number of retry attempts queued per missed
                card within a single session (default: 1, minimum: 1).
        """
        super().__init__(cards)
        self._max_repeats: int = max(1, max_repeats)
        self._primary_queue: List[Flashcard] = []
        self._retry_queue: List[Flashcard] = []
        self._error_counts: Dict[str, int] = {}
        self._repeat_counts: Dict[str, int] = {}
        self._cooldown: int = 0
        self.reset()

    @property
    def mode_name(self) -> str:
        """Return canonical mode name."""
        return "adaptive"

    def has_more_cards(self) -> bool:
        """Return True if either the primary queue or retry queue has cards."""
        return bool(self._primary_queue or self._retry_queue)

    def get_next_card(self) -> Optional[Flashcard]:
        """Select the next flashcard, prioritizing missed cards when ready."""
        if not self.has_more_cards():
            return None

        if self._retry_queue and (
            not self._primary_queue or self._cooldown <= 0
        ):
            self._retry_queue.sort(
                key=lambda c: self._error_counts.get(c.front, 0),
                reverse=True,
            )
            self._cooldown = 1
            return self._retry_queue.pop(0)

        if self._primary_queue:
            if self._cooldown > 0:
                self._cooldown -= 1
            return self._primary_queue.pop(0)

        return self._retry_queue.pop(0)

    def record_result(
        self, card: Union[Flashcard, Dict[str, Any]], is_correct: bool
    ) -> None:
        """Update card priority and schedule retries for incorrect answers.

        Args:
            card: The flashcard that was answered.
            is_correct: True if answered correctly, False if missed.
        """
        normalized = (
            card if isinstance(card, Flashcard) else Flashcard.from_dict(card)
        )
        key = normalized.front

        if not is_correct:
            self._error_counts[key] = self._error_counts.get(key, 0) + 1
            repeats_used = self._repeat_counts.get(key, 0)
            if (
                repeats_used < self._max_repeats
                and normalized not in self._retry_queue
            ):
                was_empty = len(self._retry_queue) == 0
                self._repeat_counts[key] = repeats_used + 1
                self._retry_queue.append(normalized)
                if was_empty:
                    self._cooldown = 1 if self._primary_queue else 0

    def get_error_count(
        self, card: Union[Flashcard, Dict[str, Any], str]
    ) -> int:
        """Return the recorded error count for a card or front string."""
        if isinstance(card, str):
            key = card
        elif isinstance(card, Flashcard):
            key = card.front
        else:
            key = str(card.get("front", ""))
        return self._error_counts.get(key, 0)

    def reset(self) -> None:
        """Reset queues and error tracking for a new adaptive session."""
        self._primary_queue = list(self._original_cards)
        self._retry_queue = []
        self._error_counts = {}
        self._repeat_counts = {}
        self._cooldown = 0


class QuizModeFactory:
    """Factory class for instantiating QuizMode strategies by name."""

    _MODES: Dict[str, Type[QuizMode]] = {
        "sequential": SequentialMode,
        "random": RandomMode,
        "adaptive": AdaptiveMode,
    }

    @classmethod
    def create_mode(
        cls,
        mode_name: str,
        cards: Sequence[Union[Flashcard, Dict[str, Any]]],
        **kwargs: Any,
    ) -> QuizMode:
        """Create and return a QuizMode strategy instance by mode name.

        Args:
            mode_name: Name of the mode ('sequential', 'random', 'adaptive').
            cards: Non-empty sequence of Flashcard objects or dicts.
            **kwargs: Optional keyword arguments for the mode constructor.

        Returns:
            An initialized QuizMode subclass instance.

        Raises:
            ValueError: If mode_name is not recognized or cards is empty.
        """
        if not isinstance(mode_name, str) or not mode_name.strip():
            valid_list = ", ".join(sorted(cls._MODES.keys()))
            raise ValueError(
                "Quiz mode name must be a non-empty string. "
                f"Available modes: {valid_list}."
            )

        cleaned = mode_name.strip().lower()
        mode_cls = cls._MODES.get(cleaned)
        if mode_cls is None:
            valid = ", ".join(sorted(cls._MODES.keys()))
            raise ValueError(
                f"Unknown quiz mode '{mode_name}'. Supported modes: {valid}."
            )

        instance: QuizMode = mode_cls(cards, **kwargs)
        return instance

    @classmethod
    def create(
        cls,
        mode_name: str,
        cards: Sequence[Union[Flashcard, Dict[str, Any]]],
        **kwargs: Any,
    ) -> QuizMode:
        """Alias for create_mode."""
        return cls.create_mode(mode_name, cards, **kwargs)


def create_quiz_mode(
    mode_name: str,
    cards: Sequence[Union[Flashcard, Dict[str, Any]]],
    **kwargs: Any,
) -> QuizMode:
    """Module-level factory helper to create a QuizMode instance."""
    return QuizModeFactory.create_mode(mode_name, cards, **kwargs)


@dataclass(frozen=True)
class AnswerEvaluation:
    """Result of evaluating a single user response against a flashcard."""

    card: Flashcard
    user_answer: str
    expected_answer: str
    is_correct: bool
    is_close_match: bool
    similarity: float
    response_time: float = 0.0
    timed_out: bool = False


@dataclass
class SessionStats:
    """Summary statistics for a completed or interrupted quiz session."""

    total_questions: int = 0
    correct_answers: int = 0
    incorrect_answers: int = 0
    accuracy: float = 0.0
    missed_cards: List[Flashcard] = field(default_factory=list)
    best_streak: int = 0
    hints_used: int = 0
    total_time_seconds: float = 0.0
    average_time_seconds: float = 0.0
    mode_name: str = "sequential"
    deck_name: str = "deck"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize session stats to a dictionary for JSON persistence."""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "deck_name": self.deck_name,
            "mode_name": self.mode_name,
            "total_questions": self.total_questions,
            "correct_answers": self.correct_answers,
            "incorrect_answers": self.incorrect_answers,
            "accuracy": round(self.accuracy, 2),
            "best_streak": self.best_streak,
            "hints_used": self.hints_used,
            "total_time_seconds": round(self.total_time_seconds, 2),
            "average_time_seconds": round(self.average_time_seconds, 2),
            "missed_terms": [c.front for c in self.missed_cards],
        }


class QuizEngine:
    """Context class that executes a quiz session using a QuizMode strategy."""

    CLOSE_MATCH_THRESHOLD: float = 0.75

    def __init__(
        self,
        mode: QuizMode,
        deck_name: str = "deck",
        time_limit: Optional[float] = None,
    ) -> None:
        """Initialize the quiz engine with a chosen QuizMode strategy.

        Args:
            mode: The QuizMode strategy governing card selection.
            deck_name: Display name of the loaded flashcard deck.
            time_limit: Optional maximum allowed seconds per question.
        """
        self.mode: QuizMode = mode
        self.deck_name: str = deck_name
        self.time_limit: Optional[float] = (
            time_limit if time_limit is not None and time_limit > 0 else None
        )
        self._total_questions: int = 0
        self._correct_answers: int = 0
        self._incorrect_answers: int = 0
        self._current_streak: int = 0
        self._best_streak: int = 0
        self._hints_used: int = 0
        self._total_time: float = 0.0
        self._missed_cards: List[Flashcard] = []
        self._missed_fronts: set[str] = set()

    def has_more_cards(self) -> bool:
        """Return True if the strategy has more cards to present."""
        return self.mode.has_more_cards()

    def get_next_card(self) -> Optional[Flashcard]:
        """Retrieve the next flashcard from the active strategy."""
        return self.mode.get_next_card()

    def request_hint(self, card: Flashcard) -> str:
        """Increment the hints counter and return a hint for the given card."""
        self._hints_used += 1
        return card.get_hint()

    def evaluate_answer(
        self,
        card: Union[Flashcard, Dict[str, Any]],
        user_input: str,
        response_time: float = 0.0,
    ) -> AnswerEvaluation:
        """Compare user input to card's back (case-insensitive) & record stats.

        Args:
            card: Flashcard being answered.
            user_input: Raw text answer entered by the user.
            response_time: Time taken to answer in seconds.

        Returns:
            AnswerEvaluation containing correctness, similarity, and timing.
        """
        normalized_card = (
            card if isinstance(card, Flashcard) else Flashcard.from_dict(card)
        )
        cleaned_input = " ".join(user_input.strip().split())
        cleaned_expected = " ".join(normalized_card.back.strip().split())

        raw_match = cleaned_input.lower() == cleaned_expected.lower()
        timed_out = (
            self.time_limit is not None and response_time > self.time_limit
        )
        is_correct = raw_match and not timed_out

        similarity = SequenceMatcher(
            None, cleaned_input.lower(), cleaned_expected.lower()
        ).ratio()
        is_close_match = (
            not is_correct and similarity >= self.CLOSE_MATCH_THRESHOLD
        )

        self._total_questions += 1
        self._total_time += max(0.0, response_time)

        if is_correct:
            self._correct_answers += 1
            self._current_streak += 1
            if self._current_streak > self._best_streak:
                self._best_streak = self._current_streak
        else:
            self._incorrect_answers += 1
            self._current_streak = 0
            if normalized_card.front not in self._missed_fronts:
                self._missed_fronts.add(normalized_card.front)
                self._missed_cards.append(normalized_card)

        self.mode.record_result(normalized_card, is_correct)

        return AnswerEvaluation(
            card=normalized_card,
            user_answer=user_input.strip(),
            expected_answer=normalized_card.back,
            is_correct=is_correct,
            is_close_match=is_close_match,
            similarity=similarity,
            response_time=max(0.0, response_time),
            timed_out=timed_out,
        )

    def get_stats(self) -> SessionStats:
        """Compute and return the current session statistics."""
        accuracy = (
            (self._correct_answers / self._total_questions) * 100.0
            if self._total_questions > 0
            else 0.0
        )
        avg_time = (
            self._total_time / self._total_questions
            if self._total_questions > 0
            else 0.0
        )
        return SessionStats(
            total_questions=self._total_questions,
            correct_answers=self._correct_answers,
            incorrect_answers=self._incorrect_answers,
            accuracy=accuracy,
            missed_cards=list(self._missed_cards),
            best_streak=self._best_streak,
            hints_used=self._hints_used,
            total_time_seconds=self._total_time,
            average_time_seconds=avg_time,
            mode_name=self.mode.mode_name,
            deck_name=self.deck_name,
        )
