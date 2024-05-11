"""Unit tests for quiz mode strategies, factory pattern, and QuizEngine."""

import pytest

from data_loader import Flashcard
from quiz_engine import (
    AdaptiveMode,
    QuizEngine,
    QuizModeFactory,
    RandomMode,
    SequentialMode,
    create_quiz_mode,
)


@pytest.fixture
def sample_cards() -> list[Flashcard]:
    """Provide a fixture of sample flashcards for mode testing."""
    return [
        Flashcard(front="Q1", back="A1"),
        Flashcard(front="Q2", back="A2"),
        Flashcard(front="Q3", back="A3"),
    ]


def test_quiz_mode_factory(sample_cards: list[Flashcard]) -> None:
    """Verify factory returns the right QuizMode subclass for each mode."""
    seq_mode = QuizModeFactory.create_mode("sequential", sample_cards)
    rand_mode = QuizModeFactory.create_mode("RANDOM", sample_cards)
    adapt_mode = QuizModeFactory.create("  Adaptive ", sample_cards)
    helper_mode = create_quiz_mode("sequential", sample_cards)

    assert isinstance(seq_mode, SequentialMode)
    assert seq_mode.mode_name == "sequential"
    assert isinstance(rand_mode, RandomMode)
    assert rand_mode.mode_name == "random"
    assert isinstance(adapt_mode, AdaptiveMode)
    assert adapt_mode.mode_name == "adaptive"
    assert isinstance(helper_mode, SequentialMode)

    with pytest.raises(ValueError, match="Unknown quiz mode"):
        QuizModeFactory.create_mode("nonexistent_mode", sample_cards)

    with pytest.raises(ValueError, match="non-empty string"):
        QuizModeFactory.create_mode("   ", sample_cards)


def test_sequential_mode_order_and_reset(
    sample_cards: list[Flashcard],
) -> None:
    """Verify SequentialMode serves cards in 1..N order and resets."""
    mode = SequentialMode(sample_cards)
    served: list[str] = []

    while mode.has_more_cards():
        card = mode.get_next_card()
        assert card is not None
        served.append(card.front)

    assert served == ["Q1", "Q2", "Q3"]
    assert mode.get_next_card() is None

    mode.reset()
    first_after_reset = mode.get_next_card()
    assert first_after_reset is not None
    assert first_after_reset.front == "Q1"


def test_random_mode_shuffles_all_cards(
    sample_cards: list[Flashcard],
) -> None:
    """Verify RandomMode serves every card once without mutating input."""
    large_deck = [Flashcard(front=f"Q{i}", back=f"A{i}") for i in range(15)]
    mode = RandomMode(large_deck, seed=42)

    served: list[str] = []
    while mode.has_more_cards():
        card = mode.get_next_card()
        assert card is not None
        served.append(card.front)

    assert len(served) == 15
    assert set(served) == {f"Q{i}" for i in range(15)}
    assert served != [f"Q{i}" for i in range(15)]
    assert mode.get_next_card() is None


def test_adaptive_mode_behavior(sample_cards: list[Flashcard]) -> None:
    """Verify AdaptiveMode repeats and prioritizes missed questions."""
    mode = AdaptiveMode(sample_cards, max_repeats=2)
    presented_fronts: list[str] = []

    c1 = mode.get_next_card()
    assert c1 is not None and c1.front == "Q1"
    presented_fronts.append(c1.front)
    mode.record_result(c1, is_correct=False)
    assert mode.get_error_count(c1) == 1
    assert mode.get_error_count("Q1") == 1

    c2 = mode.get_next_card()
    assert c2 is not None and c2.front == "Q2"
    presented_fronts.append(c2.front)
    mode.record_result(c2, is_correct=True)

    c3 = mode.get_next_card()
    assert c3 is not None and c3.front == "Q1"
    presented_fronts.append(c3.front)
    mode.record_result(c3, is_correct=True)

    c4 = mode.get_next_card()
    assert c4 is not None and c4.front == "Q3"
    presented_fronts.append(c4.front)
    mode.record_result(c4, is_correct=True)

    assert not mode.has_more_cards()
    assert mode.get_next_card() is None
    assert presented_fronts.count("Q1") == 2
    assert presented_fronts == ["Q1", "Q2", "Q1", "Q3"]


def test_adaptive_mode_consecutive_misses() -> None:
    """Verify consecutive misses do not reset cooldown or delay retries."""
    cards = [
        Flashcard(front="Q1", back="A1"),
        Flashcard(front="Q2", back="A2"),
        Flashcard(front="Q3", back="A3"),
        Flashcard(front="Q4", back="A4"),
    ]
    mode = AdaptiveMode(cards, max_repeats=1)
    served: list[str] = []

    # Turn 1: Miss Q1 -> queued with cooldown=1
    c1 = mode.get_next_card()
    assert c1 is not None and c1.front == "Q1"
    served.append(c1.front)
    mode.record_result(c1, is_correct=False)

    # Turn 2: Serve Q2 (cooldown decrements to 0), miss Q2 as well
    c2 = mode.get_next_card()
    assert c2 is not None and c2.front == "Q2"
    served.append(c2.front)
    mode.record_result(c2, is_correct=False)

    # Turn 3: Q1 must be re-asked immediately (not delayed behind Q3/Q4)
    c3 = mode.get_next_card()
    assert c3 is not None and c3.front == "Q1"
    served.append(c3.front)
    mode.record_result(c3, is_correct=True)

    # Turn 4: Serve Q3 (cooldown decrements to 0)
    c4 = mode.get_next_card()
    assert c4 is not None and c4.front == "Q3"
    served.append(c4.front)
    mode.record_result(c4, is_correct=True)

    # Turn 5: Serve Q2 retry before Q4
    c5 = mode.get_next_card()
    assert c5 is not None and c5.front == "Q2"
    served.append(c5.front)
    mode.record_result(c5, is_correct=True)

    # Turn 6: Serve Q4
    c6 = mode.get_next_card()
    assert c6 is not None and c6.front == "Q4"
    served.append(c6.front)
    mode.record_result(c6, is_correct=True)

    assert not mode.has_more_cards()
    assert served == ["Q1", "Q2", "Q1", "Q3", "Q2", "Q4"]


def test_adaptive_mode_accepts_dicts_and_resets() -> None:
    """Verify AdaptiveMode works with raw card dicts and resets state."""
    raw_cards = [{"front": "Term1", "back": "Def1"}]
    mode = AdaptiveMode(raw_cards)
    card = mode.get_next_card()
    assert card is not None
    mode.record_result({"front": "Term1", "back": "Def1"}, is_correct=False)
    assert mode.get_error_count({"front": "Term1", "back": "Def1"}) == 1

    retry_card = mode.get_next_card()
    assert retry_card is not None and retry_card.front == "Term1"

    mode.reset()
    assert mode.get_error_count("Term1") == 0
    assert mode.has_more_cards()


def test_empty_or_invalid_deck_raises_value_error() -> None:
    """Verify initializing a mode with an empty/invalid list raises error."""
    with pytest.raises(ValueError, match="empty deck"):
        SequentialMode([])

    with pytest.raises(ValueError, match="Invalid card"):
        SequentialMode([123])  # type: ignore[list-item]


def test_quiz_engine_evaluation_and_close_match(
    sample_cards: list[Flashcard],
) -> None:
    """Verify QuizEngine evaluates case-insensitively and checks time."""
    mode = SequentialMode(sample_cards)
    engine = QuizEngine(mode=mode, deck_name="test_deck", time_limit=5.0)

    card1 = engine.get_next_card()
    assert card1 is not None
    eval1 = engine.evaluate_answer(card1, "  a1  ", response_time=1.2)
    assert eval1.is_correct is True
    assert eval1.timed_out is False

    long_card = Flashcard(
        front="API", back="Application Programming Interface"
    )
    eval_close = engine.evaluate_answer(
        long_card, "Application Programing Interface", response_time=2.0
    )
    assert eval_close.is_correct is False
    assert eval_close.is_close_match is True

    card2 = engine.get_next_card()
    assert card2 is not None
    eval_timeout = engine.evaluate_answer(card2, "A2", response_time=8.5)
    assert eval_timeout.is_correct is False
    assert eval_timeout.timed_out is True

    hint_str = engine.request_hint(card2)
    assert "A_" in hint_str

    stats = engine.get_stats()
    assert stats.total_questions == 3
    assert stats.correct_answers == 1
    assert stats.incorrect_answers == 2
    assert stats.hints_used == 1
    assert stats.best_streak == 1
    assert len(stats.missed_cards) == 2
