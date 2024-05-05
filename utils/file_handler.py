"""File handling, JSON validation, and persistence utilities."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union


class FlashcardLoadError(Exception):
    """Exception raised when flashcard data cannot be loaded or validated."""


@dataclass(frozen=True)
class Flashcard:
    """Immutable representation of a single flashcard.

    Attributes:
        front: The question, term, or prompt displayed to the user.
        back: The expected answer or definition.
        hint: Optional clue displayed when the user requests a hint.
        category: Optional topic or category tag for filtering.
        difficulty: Optional difficulty label (default: 'medium').
    """

    front: str
    back: str
    hint: Optional[str] = None
    category: Optional[str] = None
    difficulty: str = "medium"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the flashcard to a dictionary for JSON export."""
        result: Dict[str, Any] = {
            "front": self.front,
            "back": self.back,
        }
        if self.hint is not None:
            result["hint"] = self.hint
        if self.category is not None:
            result["category"] = self.category
        if self.difficulty and self.difficulty != "medium":
            result["difficulty"] = self.difficulty
        return result

    def get_hint(self) -> str:
        """Return an explicit hint if present, or generate a masked clue."""
        if self.hint and self.hint.strip():
            return self.hint.strip()

        words = self.back.strip().split()
        if not words:
            return "No hint available."

        masked_words: List[str] = []
        for word in words:
            if len(word) <= 1:
                masked_words.append(word)
            else:
                masked_words.append(word[0] + "_" * (len(word) - 1))

        word_count = len(words)
        char_count = len(self.back.strip())
        word_label = "word" if word_count == 1 else "words"
        masked_str = " ".join(masked_words)
        return f"{masked_str} ({word_count} {word_label}, {char_count} chars)"

    @classmethod
    def from_dict(
        cls, data: Dict[str, Any], index: Optional[int] = None
    ) -> "Flashcard":
        """Validate a dictionary and construct a Flashcard instance.

        Args:
            data: Raw dictionary representing a flashcard.
            index: Optional 1-based position in the deck for error reporting.

        Returns:
            Validated Flashcard object.

        Raises:
            FlashcardLoadError: If required fields are missing or invalid.
        """
        loc = f" at card #{index}" if index is not None else ""
        if not isinstance(data, dict):
            raise FlashcardLoadError(
                f"Invalid flashcard entry{loc}: expected a JSON object, "
                f"got {type(data).__name__}."
            )

        if "front" not in data:
            raise FlashcardLoadError(
                f"Missing required field 'front'{loc}. "
                "Every flashcard must include both 'front' and 'back' fields."
            )
        if "back" not in data:
            raise FlashcardLoadError(
                f"Missing required field 'back'{loc}. "
                "Every flashcard must include both 'front' and 'back' fields."
            )

        front_val = data["front"]
        back_val = data["back"]

        if not isinstance(front_val, str) or not front_val.strip():
            raise FlashcardLoadError(
                f"Invalid 'front' value{loc}: must be a non-empty string."
            )
        if not isinstance(back_val, str) or not back_val.strip():
            raise FlashcardLoadError(
                f"Invalid 'back' value{loc}: must be a non-empty string."
            )

        hint_val = data.get("hint")
        if hint_val is not None and not isinstance(hint_val, str):
            raise FlashcardLoadError(
                f"Invalid 'hint' value{loc}: must be a string if provided."
            )

        category_val = data.get("category")
        if category_val is not None and not isinstance(category_val, str):
            raise FlashcardLoadError(
                f"Invalid 'category' value{loc}: must be a string if provided."
            )

        difficulty_val = data.get("difficulty", "medium")
        if not isinstance(difficulty_val, str) or not difficulty_val.strip():
            difficulty_val = "medium"

        cleaned_hint = (
            hint_val.strip()
            if isinstance(hint_val, str) and hint_val.strip()
            else None
        )
        cleaned_cat = (
            category_val.strip()
            if isinstance(category_val, str) and category_val.strip()
            else None
        )

        return cls(
            front=front_val.strip(),
            back=back_val.strip(),
            hint=cleaned_hint,
            category=cleaned_cat,
            difficulty=difficulty_val.strip().lower(),
        )


def read_json_file(file_path: Union[str, Path]) -> Any:
    """Read and parse a JSON file safely with friendly error messages.

    Args:
        file_path: Path to the JSON file.

    Returns:
        Parsed JSON content.

    Raises:
        FlashcardLoadError: If file is missing, unreadable, or malformed JSON.
    """
    path = Path(file_path)
    try:
        raw_text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise FlashcardLoadError(
            f"Flashcard file not found: '{path}'. Please check the file path."
        ) from exc
    except IsADirectoryError as exc:
        raise FlashcardLoadError(
            f"Invalid file path: '{path}' is a directory, not a JSON file."
        ) from exc
    except PermissionError as exc:
        raise FlashcardLoadError(
            f"Permission denied when reading file: '{path}'."
        ) from exc
    except UnicodeDecodeError as exc:
        raise FlashcardLoadError(
            f"File '{path}' is not valid UTF-8 text."
        ) from exc
    except OSError as exc:
        raise FlashcardLoadError(
            f"Could not read file '{path}': {exc}."
        ) from exc

    if not raw_text.strip():
        raise FlashcardLoadError(
            f"Flashcard file '{path}' is empty. Expected valid JSON data."
        )

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise FlashcardLoadError(
            f"Malformed JSON in '{path}' "
            f"(line {exc.lineno}, column {exc.colno}): {exc.msg}."
        ) from exc


def validate_flashcards_data(
    raw_data: Any, source: str = "<memory>"
) -> List[Flashcard]:
    """Validate parsed JSON data in either array or object wrapper format.

    Supports:
        1. Array format: [{"front": "...", "back": "..."}, ...]
        2. Object format: {"cards": [{"front": "...", "back": "..."}, ...]}

    Args:
        raw_data: Parsed JSON structure.
        source: Source identifier for error messages.

    Returns:
        A non-empty list of validated Flashcard instances.

    Raises:
        FlashcardLoadError: If structure is invalid or has no valid cards.
    """
    if isinstance(raw_data, list):
        card_items = raw_data
    elif isinstance(raw_data, dict):
        if "cards" not in raw_data:
            raise FlashcardLoadError(
                f"Invalid JSON object in '{source}': "
                "missing required 'cards' key."
            )
        if not isinstance(raw_data["cards"], list):
            raise FlashcardLoadError(
                f"Invalid JSON structure in '{source}': "
                "'cards' must be a list."
            )
        card_items = raw_data["cards"]
    else:
        raise FlashcardLoadError(
            f"Invalid JSON root type in '{source}': expected a JSON array "
            f"or an object with a 'cards' key, got {type(raw_data).__name__}."
        )

    if not card_items:
        raise FlashcardLoadError(
            f"No flashcards found in '{source}': the deck cannot be empty."
        )

    cards: List[Flashcard] = []
    for idx, item in enumerate(card_items, start=1):
        cards.append(Flashcard.from_dict(item, index=idx))

    return cards


def load_flashcards(file_path: Union[str, Path]) -> List[Flashcard]:
    """Load and validate flashcards from a JSON file.

    Args:
        file_path: Path to the JSON deck file.

    Returns:
        List of validated Flashcard objects.

    Raises:
        FlashcardLoadError: If the file cannot be read or has invalid data.
    """
    raw_data = read_json_file(file_path)
    return validate_flashcards_data(raw_data, source=str(file_path))


def save_flashcards(
    file_path: Union[str, Path],
    cards: Sequence[Union[Flashcard, Dict[str, Any]]],
    wrapper_format: bool = False,
) -> None:
    """Save flashcards to a JSON file in either array or object format.

    Args:
        file_path: Destination JSON file path.
        cards: Sequence of Flashcard instances or dictionaries.
        wrapper_format: If True, writes {"cards": [...]}; else writes [...].

    Raises:
        FlashcardLoadError: If cards are invalid or file cannot be written.
    """
    serialized: List[Dict[str, Any]] = []
    for idx, card in enumerate(cards, start=1):
        if isinstance(card, Flashcard):
            serialized.append(card.to_dict())
        elif isinstance(card, dict):
            validated = Flashcard.from_dict(card, index=idx)
            serialized.append(validated.to_dict())
        else:
            raise FlashcardLoadError(
                f"Cannot serialize card #{idx}: "
                f"unsupported type {type(card).__name__}."
            )

    payload: Any = {"cards": serialized} if wrapper_format else serialized
    path = Path(file_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        raise FlashcardLoadError(
            f"Failed to write flashcards to '{path}': {exc}."
        ) from exc


def add_flashcard_to_file(
    file_path: Union[str, Path],
    front: str,
    back: str,
    hint: Optional[str] = None,
    category: Optional[str] = None,
) -> Flashcard:
    """Add a new flashcard to an existing or new JSON deck file.

    Preserves the existing format (array vs. object wrapper) if file exists.

    Args:
        file_path: Path to the target JSON deck file.
        front: Front text of the new card.
        back: Back text of the new card.
        hint: Optional hint text.
        category: Optional category tag.

    Returns:
        The newly created Flashcard instance.

    Raises:
        FlashcardLoadError: If the new card is invalid or file I/O fails.
    """
    new_card = Flashcard.from_dict(
        {"front": front, "back": back, "hint": hint, "category": category}
    )
    path = Path(file_path)
    wrapper_format = False
    existing_cards: List[Flashcard] = []

    if path.exists():
        raw_data = read_json_file(path)
        wrapper_format = isinstance(raw_data, dict)
        existing_cards = validate_flashcards_data(raw_data, source=str(path))

    existing_cards.append(new_card)
    save_flashcards(path, existing_cards, wrapper_format=wrapper_format)
    return new_card


def search_flashcards(
    cards: Sequence[Flashcard],
    query: Optional[str] = None,
    category: Optional[str] = None,
) -> List[Flashcard]:
    """Filter flashcards by case-insensitive keyword query and/or category.

    Args:
        cards: Sequence of Flashcard instances to search.
        query: Optional substring matched against front, back, or category.
        category: Optional category name matched case-insensitively.

    Returns:
        List of matching Flashcard instances.
    """
    results = list(cards)

    if category and category.strip():
        target_cat = category.strip().lower()
        results = [
            c
            for c in results
            if (c.category and target_cat in c.category.lower())
            or target_cat in c.front.lower()
            or target_cat in c.back.lower()
        ]

    if query and query.strip():
        target_q = query.strip().lower()
        results = [
            c
            for c in results
            if target_q in c.front.lower()
            or target_q in c.back.lower()
            or (c.category is not None and target_q in c.category.lower())
        ]

    return results


def load_session_history(
    history_path: Union[str, Path],
) -> List[Dict[str, Any]]:
    """Load persisted quiz session history records from a JSON file.

    Args:
        history_path: Path to the session history JSON file.

    Returns:
        List of historical session dictionaries (empty if file is missing
        or unreadable/corrupt).
    """
    path = Path(history_path)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        return []
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return []


def save_session_record(
    history_path: Union[str, Path], record: Dict[str, Any]
) -> None:
    """Append a completed quiz session record to the history JSON file.

    Args:
        history_path: Path to the session history JSON file.
        record: Session summary dictionary to append.
    """
    path = Path(history_path)
    history = load_session_history(path)
    history.append(record)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass
