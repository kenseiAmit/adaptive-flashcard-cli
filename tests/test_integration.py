"""Integration tests covering full quiz sessions, UI formatting, and CLI."""

import json
from pathlib import Path
from typing import Iterator

from data_loader import Flashcard, load_flashcards
from main import run_cli
from quiz_engine import QuizEngine, QuizModeFactory
from ui import (
    format_card_list,
    format_feedback,
    format_historical_stats,
    format_summary_table,
    run_interactive_quiz,
)


def test_full_session() -> None:
    """Simulate answering 3 questions and verify final stats calculation."""
    cards = [
        Flashcard(front="API", back="Application Programming Interface"),
        Flashcard(front="CPU", back="Central Processing Unit"),
        Flashcard(front="DNS", back="Domain Name System"),
    ]
    mode = QuizModeFactory.create_mode("sequential", cards)
    engine = QuizEngine(mode=mode, deck_name="glossary")

    simulated_answers: Iterator[str] = iter(
        [
            "application programming interface",
            "wrong answer",
            "Domain Name System",
        ]
    )
    outputs: list[str] = []

    stats = run_interactive_quiz(
        engine,
        input_fn=lambda _prompt: next(simulated_answers),
        output_fn=outputs.append,
        use_color=False,
    )

    assert stats.total_questions == 3
    assert stats.correct_answers == 2
    assert stats.incorrect_answers == 1
    assert abs(stats.accuracy - (200.0 / 3.0)) < 1e-5
    assert stats.best_streak == 1
    assert [c.front for c in stats.missed_cards] == ["CPU"]

    joined_output = "\n".join(outputs)
    assert "SESSION SUMMARY" in joined_output
    assert "Total Questions" in joined_output
    assert "66.7%" in joined_output
    assert "CPU -> Central Processing Unit" in joined_output


def test_interactive_quiz_hint_and_exit_gracefully() -> None:
    """Verify typing 'hint' shows a clue and typing 'exit' quits cleanly."""
    cards = [
        Flashcard(
            front="RAM",
            back="Random Access Memory",
            hint="Volatile memory",
        ),
        Flashcard(front="SSH", back="Secure Shell"),
    ]
    mode = QuizModeFactory.create_mode("sequential", cards)
    engine = QuizEngine(mode=mode, deck_name="glossary")

    responses = iter(["hint", "Random Access Memory", "exit"])
    outputs: list[str] = []

    stats = run_interactive_quiz(
        engine,
        input_fn=lambda _prompt: next(responses),
        output_fn=outputs.append,
        use_color=True,
    )

    assert stats.total_questions == 1
    assert stats.correct_answers == 1
    assert stats.hints_used == 1
    assert stats.accuracy == 100.0
    joined = "\n".join(outputs)
    assert "Hint: Volatile memory" in joined
    assert "Exiting quiz early" in joined


def test_interactive_quiz_keyboard_interrupt() -> None:
    """Verify pressing Ctrl+C exits gracefully with session stats."""
    cards = [Flashcard(front="TLS", back="Transport Layer Security")]
    mode = QuizModeFactory.create_mode("sequential", cards)
    engine = QuizEngine(mode=mode, deck_name="glossary")
    outputs: list[str] = []

    def raise_interrupt(_prompt: str) -> str:
        raise KeyboardInterrupt

    stats = run_interactive_quiz(
        engine,
        input_fn=raise_interrupt,
        output_fn=outputs.append,
        use_color=False,
    )

    assert stats.total_questions == 0
    assert any("Session interrupted by user" in line for line in outputs)


def test_cli_end_to_end_adaptive_and_export(tmp_path: Path) -> None:
    """Verify CLI workflow with adaptive mode, history, and export-missed."""
    deck_file = tmp_path / "deck.json"
    deck_file.write_text(
        json.dumps(
            {
                "cards": [
                    {"front": "Keyword for function?", "back": "def"},
                    {"front": "Boolean type?", "back": "bool"},
                ]
            }
        ),
        encoding="utf-8",
    )
    history_file = tmp_path / "history.json"
    export_file = tmp_path / "missed.json"

    answers = iter(["fn", "bool", "def"])
    outputs: list[str] = []

    exit_code = run_cli(
        argv=[
            "-m",
            "adaptive",
            "-f",
            str(deck_file),
            "--stats",
            "--export-missed",
            str(export_file),
            "--history-file",
            str(history_file),
            "--no-color",
        ],
        input_fn=lambda _p: next(answers),
        output_fn=outputs.append,
    )

    assert exit_code == 0
    assert export_file.exists()
    exported_cards = load_flashcards(export_file)
    assert len(exported_cards) == 1
    assert exported_cards[0].front == "Keyword for function?"

    joined = "\n".join(outputs)
    assert "HISTORICAL PERFORMANCE ANALYTICS" in joined
    assert "Exported 1 missed card(s)" in joined


def test_cli_auxiliary_commands_and_error_handling(tmp_path: Path) -> None:
    """Verify CLI flags for add-card, search, filter, limit, and errors."""
    deck_file = tmp_path / "cards.json"
    history_file = tmp_path / "history.json"
    outputs: list[str] = []

    code1 = run_cli(
        argv=[
            "-f",
            str(deck_file),
            "--add-card",
            "HTTP",
            "Hypertext Transfer Protocol",
            "--category",
            "Network",
        ],
        output_fn=outputs.append,
    )
    assert code1 == 0

    code2 = run_cli(
        argv=[
            "-f",
            str(deck_file),
            "--add-card",
            "RAM",
            "Random Access Memory",
            "--category",
            "Hardware",
        ],
        output_fn=outputs.append,
    )
    assert code2 == 0

    search_out: list[str] = []
    code_search = run_cli(
        argv=["-f", str(deck_file), "--search", "Hypertext", "--no-color"],
        output_fn=search_out.append,
    )
    assert code_search == 0
    assert "HTTP" in "\n".join(search_out)

    quiz_out: list[str] = []
    code_quiz = run_cli(
        argv=[
            "-f",
            str(deck_file),
            "--filter",
            "Hardware",
            "--limit",
            "1",
            "--export-missed",
            str(tmp_path / "none_missed.json"),
            "--history-file",
            str(history_file),
        ],
        input_fn=lambda _p: "Random Access Memory",
        output_fn=quiz_out.append,
    )
    assert code_quiz == 0
    assert "No missed cards to export!" in "\n".join(quiz_out)

    stats_out: list[str] = []
    code_stats = run_cli(
        argv=[
            "--stats-only",
            "--history-file",
            str(history_file),
            "--no-color",
        ],
        output_fn=stats_out.append,
    )
    assert code_stats == 0
    assert "Total Sessions Completed" in "\n".join(stats_out)

    # Verify non-UTF-8 history file with --stats-only does not traceback
    bad_hist = tmp_path / "bad_utf8_hist.json"
    bad_hist.write_bytes(b"\xff\xfe\x80not_utf8")
    bad_stats_out: list[str] = []
    code_bad_stats = run_cli(
        argv=[
            "--stats-only",
            "--history-file",
            str(bad_hist),
            "--no-color",
        ],
        output_fn=bad_stats_out.append,
    )
    assert code_bad_stats == 0
    assert "No recorded quiz sessions found yet." in "\n".join(bad_stats_out)

    assert (
        run_cli(
            argv=["-f", str(deck_file), "--filter", "NonExistentCategory"],
            output_fn=outputs.append,
        )
        == 1
    )
    assert (
        run_cli(
            argv=["-f", str(deck_file), "--limit", "0"],
            output_fn=outputs.append,
        )
        == 1
    )
    assert (
        run_cli(
            argv=["-f", str(tmp_path / "missing.json")],
            output_fn=outputs.append,
        )
        == 1
    )


def test_ui_formatting_helpers() -> None:
    """Verify UI formatting helpers for empty history, lists, and feedback."""
    empty_hist = format_historical_stats([], use_color=False)
    assert "No recorded quiz sessions found yet." in empty_hist

    empty_list = format_card_list([], title="Empty", use_color=False)
    assert "No matching flashcards found." in empty_list

    mode = QuizModeFactory.create_mode(
        "sequential", [Flashcard(front="Q", back="Answer")]
    )
    engine = QuizEngine(mode=mode, time_limit=1.0)
    card = engine.get_next_card()
    assert card is not None

    eval_timeout = engine.evaluate_answer(card, "Answer", response_time=2.5)
    msg_timeout = format_feedback(eval_timeout, use_color=False)
    assert "Time limit exceeded" in msg_timeout

    eval_close = engine.evaluate_answer(card, "Answe", response_time=0.5)
    msg_close = format_feedback(eval_close, use_color=False)
    assert "Close!" in msg_close

    summary = format_summary_table(engine.get_stats(), use_color=False)
    assert "Terms Missed" in summary
