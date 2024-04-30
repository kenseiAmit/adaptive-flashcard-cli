"""Data loader module for loading, validating, and managing flashcard decks."""

from utils.file_handler import (
    Flashcard,
    FlashcardLoadError,
    add_flashcard_to_file,
    load_flashcards,
    load_session_history,
    read_json_file,
    save_flashcards,
    save_session_record,
    search_flashcards,
    validate_flashcards_data,
)

__all__ = [
    "Flashcard",
    "FlashcardLoadError",
    "add_flashcard_to_file",
    "load_flashcards",
    "load_session_history",
    "read_json_file",
    "save_flashcards",
    "save_session_record",
    "search_flashcards",
    "validate_flashcards_data",
]
