"""Entry point for the Flashcard Quizzer CLI application."""

import argparse
import sys
from pathlib import Path
from typing import Callable, List, Optional, Sequence

from data_loader import (
    Flashcard,
    FlashcardLoadError,
    add_flashcard_to_file,
    load_flashcards,
    load_session_history,
    save_flashcards,
    save_session_record,
    search_flashcards,
)
from quiz_engine import QuizEngine, QuizModeFactory
from ui import (
    GREEN,
    RED,
    YELLOW,
    colorize,
    format_card_list,
    format_historical_stats,
    run_interactive_quiz,
)


def build_parser() -> argparse.ArgumentParser:
    """Construct and configure the CLI argument parser.

    Returns:
        Configured argparse.ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        prog="flashcard-quizzer",
        description=(
            "Flashcard Quizzer: An AI-assisted CLI learning application "
            "supporting sequential, random, and adaptive quiz modes."
        ),
    )
    parser.add_argument(
        "-f",
        "--file",
        dest="file",
        default="data/glossary.json",
        help="Path to the flashcard JSON file (default: data/glossary.json).",
    )
    parser.add_argument(
        "-m",
        "--mode",
        dest="mode",
        type=str.lower,
        choices=["sequential", "random", "adaptive"],
        default="sequential",
        help="Quiz mode: sequential, random, or adaptive.",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Display cumulative historical session statistics.",
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Display historical session statistics and exit.",
    )
    parser.add_argument(
        "--search",
        metavar="QUERY",
        default=None,
        help="Search flashcards in the deck by keyword and exit.",
    )
    parser.add_argument(
        "--filter",
        dest="filter_query",
        metavar="KEYWORD",
        default=None,
        help="Filter flashcards by category or keyword before quizzing.",
    )
    parser.add_argument(
        "-n",
        "--limit",
        type=int,
        default=None,
        help="Limit the number of flashcards included in the quiz session.",
    )
    parser.add_argument(
        "--time-limit",
        type=float,
        default=None,
        help="Optional time limit in seconds per question.",
    )
    parser.add_argument(
        "--export-missed",
        metavar="OUTPUT_FILE",
        default=None,
        help="Export flashcards missed during the session to a JSON file.",
    )
    parser.add_argument(
        "--add-card",
        nargs=2,
        metavar=("FRONT", "BACK"),
        default=None,
        help="Add a new flashcard (FRONT BACK) to the deck file and exit.",
    )
    parser.add_argument(
        "--hint-text",
        default=None,
        help="Optional hint text when adding a new card with --add-card.",
    )
    parser.add_argument(
        "--category",
        default=None,
        help="Optional category tag when adding a new card with --add-card.",
    )
    parser.add_argument(
        "--history-file",
        default="data/.session_history.json",
        help="Path to the JSON file storing session history.",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI color codes in terminal output.",
    )
    return parser


def run_cli(
    argv: Optional[Sequence[str]] = None,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> int:
    """Parse CLI arguments and execute the requested workflow.

    Args:
        argv: Command-line argument list (defaults to sys.argv[1:]).
        input_fn: Callable for reading user input.
        output_fn: Callable for printing output.

    Returns:
        Process exit code (0 for success, 1 for recoverable error).
    """
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    args = parser.parse_args(raw_argv)
    use_color = not args.no_color

    try:
        if args.stats_only or raw_argv == ["--stats"]:
            history = load_session_history(args.history_file)
            output_fn(format_historical_stats(history, use_color=use_color))
            return 0

        if args.add_card is not None:
            front_text, back_text = args.add_card
            added = add_flashcard_to_file(
                args.file,
                front=front_text,
                back=back_text,
                hint=args.hint_text,
                category=args.category,
            )
            output_fn(
                colorize(
                    f"Added flashcard '{added.front}' -> '{added.back}' "
                    f"to '{args.file}'.",
                    GREEN,
                    use_color=use_color,
                )
            )
            return 0

        cards: List[Flashcard] = load_flashcards(args.file)

        if args.search is not None:
            matches = search_flashcards(cards, query=args.search)
            output_fn(
                format_card_list(
                    matches,
                    title=f"Search Results for '{args.search}'",
                    use_color=use_color,
                )
            )
            return 0

        if args.filter_query is not None:
            cards = search_flashcards(cards, query=args.filter_query)
            if not cards:
                msg = (
                    f"Error: No flashcards matched filter "
                    f"'{args.filter_query}'."
                )
                output_fn(colorize(msg, RED, use_color=use_color))
                return 1

        if args.limit is not None:
            if args.limit <= 0:
                output_fn(
                    colorize(
                        "Error: --limit must be a positive integer.",
                        RED,
                        use_color=use_color,
                    )
                )
                return 1
            cards = cards[: args.limit]

        quiz_mode = QuizModeFactory.create_mode(args.mode, cards)
        deck_name = Path(args.file).stem
        engine = QuizEngine(
            mode=quiz_mode,
            deck_name=deck_name,
            time_limit=args.time_limit,
        )

        stats = run_interactive_quiz(
            engine,
            input_fn=input_fn,
            output_fn=output_fn,
            use_color=use_color,
        )

        if stats.total_questions > 0:
            save_session_record(args.history_file, stats.to_dict())

        if args.export_missed:
            if stats.missed_cards:
                save_flashcards(args.export_missed, stats.missed_cards)
                output_fn(
                    colorize(
                        f"Exported {len(stats.missed_cards)} missed card(s) "
                        f"to '{args.export_missed}'.",
                        YELLOW,
                        use_color=use_color,
                    )
                )
            else:
                output_fn(
                    colorize(
                        "No missed cards to export!",
                        GREEN,
                        use_color=use_color,
                    )
                )

        if args.stats:
            history = load_session_history(args.history_file)
            output_fn(format_historical_stats(history, use_color=use_color))

        return 0

    except (FlashcardLoadError, ValueError) as exc:
        output_fn(colorize(f"Error: {exc}", RED, use_color=use_color))
        return 1
    except (KeyboardInterrupt, EOFError):
        output_fn(
            colorize(
                "\nExiting Flashcard Quizzer. Goodbye!",
                YELLOW,
                use_color=use_color,
            )
        )
        return 0


def main() -> None:
    """CLI entry point."""
    sys.exit(run_cli())


if __name__ == "__main__":
    main()
