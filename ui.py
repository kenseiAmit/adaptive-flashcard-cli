"""Terminal UI formatting, ANSI color helpers, and interactive quiz loop."""

import time
from collections import Counter
from typing import Any, Callable, Dict, List, Sequence

from quiz_engine import AnswerEvaluation, QuizEngine, SessionStats
from utils.file_handler import Flashcard

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def colorize(text: str, color_code: str, use_color: bool = True) -> str:
    """Wrap text in ANSI color escape sequences when color output is enabled.

    Args:
        text: The text string to format.
        color_code: ANSI escape code prefix.
        use_color: Whether to apply ANSI codes (default: True).

    Returns:
        Formatted string.
    """
    if not use_color:
        return text
    return f"{color_code}{text}{RESET}"


def format_feedback(
    evaluation: AnswerEvaluation, use_color: bool = True
) -> str:
    """Format immediate feedback for user's answer (Green=Correct, Red=Wrong).

    Args:
        evaluation: AnswerEvaluation returned by QuizEngine.
        use_color: Whether to include ANSI colors.

    Returns:
        Formatted feedback string.
    """
    if evaluation.is_correct:
        msg = "Correct!"
        if evaluation.response_time > 0:
            msg += f" ({evaluation.response_time:.1f}s)"
        return colorize(msg, GREEN, use_color=use_color)

    if evaluation.timed_out:
        elapsed_str = f"{evaluation.response_time:.1f}s"
        reason = (
            f"Incorrect (Time limit exceeded: {elapsed_str})! "
            f"Expected: {evaluation.expected_answer}"
        )
    elif evaluation.is_close_match:
        pct = int(round(evaluation.similarity * 100))
        reason = (
            f"Incorrect (Close! {pct}% match). "
            f"Expected: {evaluation.expected_answer}"
        )
    else:
        reason = f"Incorrect! Expected: {evaluation.expected_answer}"

    return colorize(reason, RED, use_color=use_color)


def format_summary_table(stats: SessionStats, use_color: bool = True) -> str:
    """Format the end-of-session statistics summary table.

    Includes Total Questions, Correct/Incorrect counts, Accuracy %,
    Best Streak, Hints Used, and a list of terms the user missed.

    Args:
        stats: SessionStats instance from the quiz session.
        use_color: Whether to include ANSI colors.

    Returns:
        Multi-line formatted summary table string.
    """
    border = "=" * 56
    divider = "-" * 56
    header = colorize("SESSION SUMMARY", BOLD + CYAN, use_color=use_color)

    lines: List[str] = [
        "",
        border,
        f"  {header}",
        border,
        f"  {'Deck':<24} | {stats.deck_name}",
        f"  {'Mode':<24} | {stats.mode_name.capitalize()}",
        divider,
        f"  {'Total Questions':<24} | {stats.total_questions}",
        f"  {'Correct Answers':<24} | {stats.correct_answers}",
        f"  {'Incorrect Answers':<24} | {stats.incorrect_answers}",
        f"  {'Accuracy %':<24} | {stats.accuracy:.1f}%",
        f"  {'Best Streak':<24} | {stats.best_streak}",
        f"  {'Hints Used':<24} | {stats.hints_used}",
        f"  {'Average Time / Card':<24} | {stats.average_time_seconds:.2f}s",
        border,
    ]

    if stats.missed_cards:
        missed_header = colorize(
            "Terms Missed (Review List):", BOLD + RED, use_color=use_color
        )
        lines.append(f"  {missed_header}")
        for card in stats.missed_cards:
            lines.append(f"    - {card.front} -> {card.back}")
    else:
        perfect_msg = colorize(
            "Terms Missed: None! Perfect session!", GREEN, use_color=use_color
        )
        lines.append(f"  {perfect_msg}")

    lines.append(border)
    return "\n".join(lines)


def format_historical_stats(
    history: Sequence[Dict[str, Any]], use_color: bool = True
) -> str:
    """Format cumulative analytics across all recorded quiz sessions.

    Args:
        history: Sequence of persisted session dictionaries.
        use_color: Whether to include ANSI colors.

    Returns:
        Formatted multi-line analytics report.
    """
    border = "=" * 56
    divider = "-" * 56
    title = colorize(
        "HISTORICAL PERFORMANCE ANALYTICS", BOLD + CYAN, use_color=use_color
    )

    if not history:
        return "\n".join(
            [
                "",
                border,
                f"  {title}",
                border,
                "  No recorded quiz sessions found yet.",
                border,
            ]
        )

    total_sessions = len(history)
    total_questions = sum(int(s.get("total_questions", 0)) for s in history)
    total_correct = sum(int(s.get("correct_answers", 0)) for s in history)
    overall_accuracy = (
        (total_correct / total_questions) * 100.0
        if total_questions > 0
        else 0.0
    )
    best_streak = max(
        (int(s.get("best_streak", 0)) for s in history), default=0
    )

    missed_counter: Counter[str] = Counter()
    for session in history:
        terms = session.get("missed_terms", [])
        if isinstance(terms, list):
            for term in terms:
                if isinstance(term, str):
                    missed_counter[term] += 1

    lines: List[str] = [
        "",
        border,
        f"  {title}",
        border,
        f"  {'Total Sessions Completed':<26} | {total_sessions}",
        f"  {'Total Questions Answered':<26} | {total_questions}",
        f"  {'Overall Accuracy %':<26} | {overall_accuracy:.1f}%",
        f"  {'All-Time Best Streak':<26} | {best_streak}",
    ]

    if missed_counter:
        lines.append(divider)
        lines.append("  Most Frequently Missed Terms:")
        for term, count in missed_counter.most_common(5):
            lines.append(f"    - {term} (missed in {count} session(s))")

    lines.append(border)
    return "\n".join(lines)


def format_card_list(
    cards: Sequence[Flashcard],
    title: str = "Flashcards",
    use_color: bool = True,
) -> str:
    """Format a list of flashcards for search or deck inspection.

    Args:
        cards: Sequence of Flashcard objects to display.
        title: Header title.
        use_color: Whether to apply ANSI color formatting.

    Returns:
        Formatted string table of flashcards.
    """
    border = "=" * 56
    header = colorize(
        f"{title} ({len(cards)} card(s))", BOLD + CYAN, use_color=use_color
    )
    lines: List[str] = [border, f"  {header}", border]
    if not cards:
        lines.append("  No matching flashcards found.")
    else:
        for idx, card in enumerate(cards, start=1):
            cat_badge = f" [{card.category}]" if card.category else ""
            lines.append(f"  {idx}. {card.front}{cat_badge} -> {card.back}")
    lines.append(border)
    return "\n".join(lines)


def run_interactive_quiz(
    engine: QuizEngine,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
    use_color: bool = True,
) -> SessionStats:
    """Run the interactive CLI quiz loop until completion or user exit.

    Supports:
        - Typing 'hint' or '?' to view a clue before answering
        - Typing 'exit' or 'quit' to end the session gracefully
        - Pressing Ctrl+C (KeyboardInterrupt) or Ctrl+D (EOFError)

    Args:
        engine: Configured QuizEngine instance.
        input_fn: Input callable (defaults to built-in input).
        output_fn: Output callable (defaults to built-in print).
        use_color: Whether to display ANSI colors.

    Returns:
        Completed SessionStats for the quiz run.
    """
    mode_title = engine.mode.mode_name.capitalize()
    banner = colorize(
        f"Starting Flashcard Quizzer | Deck: {engine.deck_name} | "
        f"Mode: {mode_title}",
        BOLD + CYAN,
        use_color=use_color,
    )
    output_fn(banner)
    output_fn(
        "Type your answer and press Enter. "
        "Type 'hint' for a clue, or 'exit' (or press Ctrl+C) to quit.\n"
    )

    question_num = 1
    try:
        while engine.has_more_cards():
            card = engine.get_next_card()
            if card is None:
                break

            cat_tag = f" [{card.category}]" if card.category else ""
            prompt_header = colorize(
                f"Question #{question_num}{cat_tag}: {card.front}",
                BOLD,
                use_color=use_color,
            )
            output_fn(prompt_header)

            start_time = time.monotonic()
            while True:
                raw_answer = input_fn("Your answer: ")
                stripped = raw_answer.strip()

                if stripped.lower() in {"exit", "quit"}:
                    output_fn(
                        colorize(
                            "\nExiting quiz early. "
                            "Calculating session stats...",
                            YELLOW,
                            use_color=use_color,
                        )
                    )
                    stats = engine.get_stats()
                    output_fn(format_summary_table(stats, use_color=use_color))
                    return stats

                if stripped.lower() in {"hint", "?"}:
                    hint_text = engine.request_hint(card)
                    output_fn(
                        colorize(
                            f"Hint: {hint_text}", YELLOW, use_color=use_color
                        )
                    )
                    continue

                elapsed = time.monotonic() - start_time
                evaluation = engine.evaluate_answer(
                    card, raw_answer, response_time=elapsed
                )
                output_fn(format_feedback(evaluation, use_color=use_color))
                output_fn("")
                question_num += 1
                break

    except (KeyboardInterrupt, EOFError):
        output_fn(
            colorize(
                "\n\nSession interrupted by user. Exiting gracefully...",
                YELLOW,
                use_color=use_color,
            )
        )

    stats = engine.get_stats()
    output_fn(format_summary_table(stats, use_color=use_color))
    return stats
