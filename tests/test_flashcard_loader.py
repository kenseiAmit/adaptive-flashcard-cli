"""Unit tests for flashcard loading, validation, search, and persistence."""

import json
from pathlib import Path

import pytest

from data_loader import (
    Flashcard,
    FlashcardLoadError,
    add_flashcard_to_file,
    load_flashcards,
    load_session_history,
    save_flashcards,
    save_session_record,
    search_flashcards,
    validate_flashcards_data,
)


def test_load_valid_flashcards_array(tmp_path: Path) -> None:
    """Verify loading a valid JSON array of flashcards works correctly."""
    deck_file = tmp_path / "array_deck.json"
    sample_data = [
        {"front": "API", "back": "Application Programming Interface"},
        {"front": "CPU", "back": "Central Processing Unit"},
    ]
    deck_file.write_text(json.dumps(sample_data), encoding="utf-8")

    cards = load_flashcards(deck_file)

    assert len(cards) == 2
    assert isinstance(cards[0], Flashcard)
    assert cards[0].front == "API"
    assert cards[0].back == "Application Programming Interface"
    assert cards[1].front == "CPU"
    assert cards[1].back == "Central Processing Unit"


def test_load_valid_flashcards_object_wrapper(tmp_path: Path) -> None:
    """Verify loading a valid JSON object wrapper {'cards': [...]}."""
    deck_file = tmp_path / "object_deck.json"
    sample_data = {
        "cards": [
            {
                "front": "Which keyword defines a function?",
                "back": "def",
                "hint": "Three-letter keyword",
                "category": "Syntax",
                "difficulty": "easy",
            }
        ]
    }
    deck_file.write_text(json.dumps(sample_data), encoding="utf-8")

    cards = load_flashcards(deck_file)

    assert len(cards) == 1
    assert cards[0].front == "Which keyword defines a function?"
    assert cards[0].back == "def"
    assert cards[0].hint == "Three-letter keyword"
    assert cards[0].category == "Syntax"
    assert cards[0].difficulty == "easy"
    assert cards[0].get_hint() == "Three-letter keyword"


def test_load_invalid_json(tmp_path: Path) -> None:
    """Verify malformed JSON syntax raises FlashcardLoadError gracefully."""
    bad_file = tmp_path / "broken.json"
    bad_file.write_text(
        '[{"front": "API", "back": "Unclosed}', encoding="utf-8"
    )

    with pytest.raises(FlashcardLoadError, match="Malformed JSON"):
        load_flashcards(bad_file)


def test_load_missing_required_field(tmp_path: Path) -> None:
    """Verify cards missing required 'back' or 'front' fields are rejected."""
    missing_back_file = tmp_path / "missing_back.json"
    missing_back_file.write_text(
        json.dumps([{"front": "Question without a back"}]),
        encoding="utf-8",
    )

    with pytest.raises(
        FlashcardLoadError, match="Missing required field 'back'"
    ):
        load_flashcards(missing_back_file)

    missing_front_file = tmp_path / "missing_front.json"
    missing_front_file.write_text(
        json.dumps([{"back": "Answer without a front"}]),
        encoding="utf-8",
    )

    with pytest.raises(
        FlashcardLoadError, match="Missing required field 'front'"
    ):
        load_flashcards(missing_front_file)


def test_load_missing_file_raises_helpful_error(tmp_path: Path) -> None:
    """Verify loading a non-existent file raises FlashcardLoadError."""
    non_existent = tmp_path / "does_not_exist.json"

    with pytest.raises(FlashcardLoadError, match="not found"):
        load_flashcards(non_existent)


def test_load_directory_path_raises_error(tmp_path: Path) -> None:
    """Verify passing a directory instead of a file raises error."""
    with pytest.raises(FlashcardLoadError, match="is a directory"):
        load_flashcards(tmp_path)


def test_load_empty_and_non_utf8_file_raises_error(tmp_path: Path) -> None:
    """Verify empty or non-UTF-8 files raise FlashcardLoadError."""
    empty_file = tmp_path / "empty.json"
    empty_file.write_text("   \n  ", encoding="utf-8")

    with pytest.raises(FlashcardLoadError, match="is empty"):
        load_flashcards(empty_file)

    binary_file = tmp_path / "non_utf8.json"
    binary_file.write_bytes(b"\xff\xfe\x00\x00invalid")

    with pytest.raises(FlashcardLoadError, match="not valid UTF-8"):
        load_flashcards(binary_file)


def test_validate_invalid_structures_and_values() -> None:
    """Verify validation rejects empty decks, bad types, and blank strings."""
    with pytest.raises(FlashcardLoadError, match="cannot be empty"):
        validate_flashcards_data([])

    with pytest.raises(
        FlashcardLoadError, match="missing required 'cards' key"
    ):
        validate_flashcards_data({"items": []})

    with pytest.raises(FlashcardLoadError, match="'cards' must be a list"):
        validate_flashcards_data({"cards": "not a list"})

    with pytest.raises(FlashcardLoadError, match="Invalid JSON root type"):
        validate_flashcards_data(42)

    with pytest.raises(FlashcardLoadError, match="expected a JSON object"):
        validate_flashcards_data(["not a dict"])

    with pytest.raises(FlashcardLoadError, match="Invalid 'front' value"):
        validate_flashcards_data([{"front": "   ", "back": "valid"}])

    with pytest.raises(FlashcardLoadError, match="Invalid 'back' value"):
        validate_flashcards_data([{"front": "valid", "back": ""}])

    with pytest.raises(FlashcardLoadError, match="Invalid 'hint' value"):
        validate_flashcards_data([{"front": "Q", "back": "A", "hint": 123}])

    with pytest.raises(FlashcardLoadError, match="Invalid 'category' value"):
        validate_flashcards_data(
            [{"front": "Q", "back": "A", "category": 999}]
        )


def test_flashcard_generated_hint_and_serialization() -> None:
    """Verify automatic masked hint generation and dict serialization."""
    card = Flashcard(front="API", back="Application Programming Interface")
    hint = card.get_hint()
    assert "A__________ P__________ I________" in hint
    assert "3 words" in hint

    short_card = Flashcard(
        front="Single char",
        back="A",
        hint="First letter",
        category="Alphabet",
        difficulty="hard",
    )
    assert short_card.get_hint() == "First letter"
    serialized = short_card.to_dict()
    assert serialized == {
        "front": "Single char",
        "back": "A",
        "hint": "First letter",
        "category": "Alphabet",
        "difficulty": "hard",
    }

    single_char_auto = Flashcard(front="Single", back="X")
    assert "X (1 word, 1 chars)" in single_char_auto.get_hint()


def test_save_and_add_flashcard_to_file(tmp_path: Path) -> None:
    """Verify saving decks and appending cards preserves deck format."""
    deck_path = tmp_path / "custom.json"
    card1 = add_flashcard_to_file(
        deck_path,
        front="HTTP",
        back="Hypertext Transfer Protocol",
        category="Web",
    )
    assert card1.front == "HTTP"

    loaded = load_flashcards(deck_path)
    assert len(loaded) == 1
    assert loaded[0].category == "Web"

    save_flashcards(
        deck_path,
        [{"front": "DNS", "back": "Domain Name System"}],
        wrapper_format=True,
    )
    add_flashcard_to_file(deck_path, front="SSH", back="Secure Shell")
    raw = json.loads(deck_path.read_text(encoding="utf-8"))
    assert "cards" in raw
    assert len(raw["cards"]) == 2

    with pytest.raises(FlashcardLoadError, match="unsupported type"):
        save_flashcards(deck_path, ["invalid_item"])  # type: ignore[list-item]


def test_search_flashcards() -> None:
    """Verify searching flashcards by query and category."""
    cards = [
        Flashcard(
            front="API",
            back="Application Programming Interface",
            category="Dev",
        ),
        Flashcard(
            front="CPU",
            back="Central Processing Unit",
            category="Hardware",
        ),
        Flashcard(
            front="RAM",
            back="Random Access Memory",
            category="Hardware",
        ),
    ]

    hardware_cards = search_flashcards(cards, category="hardware")
    assert len(hardware_cards) == 2

    memory_cards = search_flashcards(cards, query="memory")
    assert len(memory_cards) == 1
    assert memory_cards[0].front == "RAM"


def test_session_history_persistence(tmp_path: Path) -> None:
    """Verify loading and saving session history, including non-UTF-8."""
    history_file = tmp_path / "history.json"
    assert load_session_history(history_file) == []

    record = {
        "deck_name": "glossary",
        "mode_name": "sequential",
        "total_questions": 5,
        "correct_answers": 4,
        "accuracy": 80.0,
        "missed_terms": ["TLS"],
    }
    save_session_record(history_file, record)

    history = load_session_history(history_file)
    assert len(history) == 1
    assert history[0]["deck_name"] == "glossary"

    history_file.write_text("{corrupt json", encoding="utf-8")
    assert load_session_history(history_file) == []

    history_file.write_bytes(b"\xff\xfe\x80invalid_utf8")
    assert load_session_history(history_file) == []
