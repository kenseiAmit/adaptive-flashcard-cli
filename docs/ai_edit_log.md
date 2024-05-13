# AI Edit Log

**Instructions:** Use this document to track all your interactions with AI assistants during the project. This log will help you reflect on your AI collaboration process and demonstrate your learning journey.

## How to Use This Log

For each AI interaction, create a new entry with the following structure:

### Entry Template
```
## [Date] - [Brief Description]

**Context:** What were you trying to accomplish?
**AI Tool Used:** Claude/ChatGPT/Copilot/etc.
**Prompt/Request:** What exactly did you ask the AI?
**AI Response:** Summary of what the AI generated (don't copy entire code blocks)
**Checklist findings:** Sections of ai_guidance/code_review_checklist.md checked and what each caught
**Changes Made:** What modifications did you make to the AI's suggestions?
**Reasoning:** Why did you make those changes?
**Outcome:** What was the final result?
```

---

## Your Log Entries

### 2026-11-05 - Interaction 1: Flashcard Data Loader and Dual-Format JSON Validation

**Context:** Phase 1 required building `utils/file_handler.py` and `data_loader.py` to load flashcard decks from JSON files in two formats—an array format (`[{"front": "...", "back": "..."}]` used by `data/glossary.json`) and an object wrapper format (`{"cards": [...]}` used by `data/python_basics.json`)—while failing gracefully with a clear message on missing files, malformed JSON, or missing required fields.

**AI Tool Used:** Claude Code / Gemini AI Coding Assistant

**Prompt/Request:** "Create `utils/file_handler.py` and `data_loader.py` to load and validate flashcards from a JSON file. Support both array format `[{"front": "...", "back": "..."}]` and object wrapper format `{"cards": [...]}`. Define a `Flashcard` dataclass and a custom `FlashcardLoadError` exception. Raise `FlashcardLoadError` with a descriptive message if the file is missing, empty, malformed JSON, or if any card is missing `'front'` or `'back'`. Include full Python type hints and docstrings."

**AI Response:** The AI generated a `Flashcard` dataclass, a `FlashcardLoadError` exception, and a `load_flashcards(filepath: str)` function. While it supported both list and dict root structures, it had four flaws:
1. It used a broad `except Exception as e:` block around `open()` and `json.load()`, swallowing specific failure causes and omitting line/column details on malformed JSON.
2. In `load_session_history()`, it caught `(OSError, json.JSONDecodeError)` but did not catch `UnicodeDecodeError`, causing non-UTF-8 files to raise an unhandled traceback.
3. It checked `if "front" not in card or "back" not in card:` without validating whether the values were strings or whether they were empty/whitespace-only (`{"front": "   ", "back": ""}`).
4. It did not include the 1-based card index in validation error messages.

**Checklist findings:** 1. Correctness and Functionality (Input/Output) - whitespace-only strings and non-string values for `front`/`back` were not rejected, and card position was missing from error messages (fixed). 2. Code Quality - `Flashcard` was mutable instead of `frozen=True` (fixed). 3. Security Considerations - no unsafe deserialization found (`json.loads` used safely). 5. Error Handling and Robustness - broad `except Exception:` used in `read_json_file()` and `UnicodeDecodeError` not caught in `read_json_file()` or `load_session_history()` (fixed by adding explicit `FileNotFoundError`, `IsADirectoryError`, `PermissionError`, `UnicodeDecodeError`, `OSError`, and `json.JSONDecodeError` handlers).

**Changes Made:**
- Replaced the broad `except Exception:` block in `read_json_file()` with explicit `try...except` handlers for `FileNotFoundError`, `IsADirectoryError`, `PermissionError`, `UnicodeDecodeError`, `OSError`, and `json.JSONDecodeError` (including `exc.lineno` and `exc.colno`).
- Updated `load_session_history()` to catch `(OSError, UnicodeDecodeError, json.JSONDecodeError)` so corrupt or non-UTF-8 history files gracefully return `[]`.
- Made `Flashcard` a frozen dataclass (`@dataclass(frozen=True)`) with optional metadata fields (`hint`, `category`, `difficulty`) and a `from_dict(data, index)` factory method that verifies `front` and `back` are non-empty strings after `.strip()`.
- Added explicit checks for empty files (`not raw_text.strip()`) and empty card arrays (`if not card_items:`), raising `FlashcardLoadError` with the 1-based card position (`at card #N`).

**Reasoning:**
- Catching bare or overly broad exceptions hides real defects, while missing `UnicodeDecodeError` leaks raw tracebacks when a binary or non-UTF-8 file is passed.
- Including line numbers for JSON syntax errors and card indices for schema errors gives the user actionable CLI feedback without exposing raw Python tracebacks.

**Outcome:** `load_flashcards()` and `validate_flashcards_data()` cleanly load both `data/glossary.json` and `data/python_basics.json`, reject non-UTF-8 or malformed files cleanly, and pass `test_load_valid_flashcards_array`, `test_load_invalid_json`, and `test_load_missing_required_field`.

**Lessons Learned:**
- AI assistants handle the happy path quickly but often under-specify input validation and encoding exceptions (`UnicodeDecodeError`) unless checked systematically against the review checklist.

---

### 2026-11-05 - Interaction 2: Strategy and Factory Patterns for Quiz Modes

**Context:** Phase 2 required implementing the core quiz engine in `quiz_engine.py` using the Strategy Pattern (`QuizMode` abstract base class with `SequentialMode`, `RandomMode`, and `AdaptiveMode` subclasses) and the Factory Pattern (`QuizModeFactory`) to instantiate the appropriate strategy based on user CLI input.

**AI Tool Used:** Claude Code / Gemini AI Coding Assistant

**Prompt/Request:** "Implement the Strategy Pattern and Factory Pattern in `quiz_engine.py`. Create an abstract base class `QuizMode` using `abc.ABC` with abstract methods `get_next_card()`, `has_more_cards()`, `reset()`, and a `record_result(card, is_correct)` hook. Implement `SequentialMode`, `RandomMode`, and `AdaptiveMode` subclasses, plus a `QuizModeFactory` class with `create_mode(mode_name, cards)` that selects the strategy at runtime."

**AI Response:** The AI created the `QuizMode` ABC and the three concrete strategy classes, but it had three issues:
1. In `RandomMode.__init__`, it called `random.shuffle(self.cards)` directly on the list reference passed into the constructor, mutating the caller's original deck list in-place.
2. `RandomMode` had no way to pass a deterministic seed, making unit tests potentially flaky on small decks.
3. The base constructor only accepted `List[Flashcard]` and crashed with `AttributeError` when a unit test passed raw dictionaries `[{"front": "Q", "back": "A"}]`.

**Checklist findings:** 1. Correctness and Functionality - `RandomMode` mutated the caller's input list in-place via `random.shuffle()` (fixed by copying into `self._shuffled_cards`). 5. Error Handling and Robustness (Defensive Programming) - empty decks were not rejected at initialization and raw dicts caused `AttributeError` (fixed via `_normalize_cards()`). 7. Testing and Testability - `RandomMode` used global `random.shuffle` without an injectable seed (fixed by using `random.Random(seed)`). 8. Maintainability (Extensibility) - Strategy and Factory interfaces cleanly separated, no issues found.

**Changes Made:**
- Modified `RandomMode.reset()` to copy the deck (`self._shuffled_cards = list(self._original_cards)`) and shuffle using a dedicated `random.Random(seed)` instance (`self._rng.shuffle(self._shuffled_cards)`), leaving the caller's list untouched and enabling deterministic unit tests.
- Added a `_normalize_cards()` helper in `quiz_engine.py` that accepts either `Flashcard` instances or raw dictionaries `{"front": "...", "back": "..."}` and raises `ValueError` on empty decks.
- Normalized `mode_name` in `QuizModeFactory.create_mode()` using `.strip().lower()` and added clear `ValueError` messages listing the valid modes (`adaptive, random, sequential`).

**Reasoning:**
- Mutating caller arguments violates defensive programming principles and causes subtle bugs across test runs.
- Supporting an optional `seed` parameter in `RandomMode` and accepting both `Flashcard` objects and dicts makes the Strategy classes deterministic and easy to test in isolation.

**Outcome:** `QuizModeFactory`, `SequentialMode`, and `RandomMode` are completely decoupled from `QuizEngine` and pass `test_quiz_mode_factory` and all mode unit tests cleanly.

**Lessons Learned:**
- Always inspect AI-generated collection operations (like `random.shuffle` or `.sort()`) for unintended in-place mutation of shared state.

---

### 2026-11-05 - Interaction 3: Fixing Infinite Retry Loops and Cooldown Resets in AdaptiveMode

**Context:** Implementing the challenge feature (`AdaptiveMode`), which must prioritize and repeat flashcards that the user previously answered incorrectly.

**AI Tool Used:** Claude Code / Gemini AI Coding Assistant

**Prompt/Request:** "Implement `AdaptiveMode(QuizMode)` in `quiz_engine.py` so that when `record_result(card, is_correct=False)` is called, the card's error count increases and the card is prioritized to be asked again during the session."

**AI Response:** The AI's first draft inserted any missed card at index `0` of the main queue (`self.queue.insert(0, card)`) every time `is_correct` was `False`, with no repeat limit and no spacing cooldown. In the second draft with a spacing cooldown (`self._cooldown = 1`), `record_result()` unconditionally reset `self._cooldown = 1` on every miss—meaning that if a user missed multiple cards consecutively (e.g., Q1 then Q2), Q2's miss reset `_cooldown` back to `1` and delayed Q1's retry until the end of the primary queue.

**Checklist findings:** 1. Correctness and Functionality (Logic and Algorithm) - initial draft had an unbounded retry loop (`Red Flags: Infinite loops without proper termination`, fixed with `max_repeats`), and the second draft unconditionally reset `self._cooldown = 1` on consecutive misses so queued retries were delayed while misses were consecutive (fixed by only setting `self._cooldown = 1` when `self._retry_queue` was previously empty). 4. Performance and Efficiency - sorting the small retry queue by `_error_counts` is fast and appropriate, no issues found. 7. Testing and Testability - added `get_error_count()` inspection helper and `test_adaptive_mode_consecutive_misses` to verify consecutive-miss behavior.

**Changes Made:**
- Rejected the naive `self.queue.insert(0, card)` approach and designed `AdaptiveMode` with two queues: `self._primary_queue` (unseen cards) and `self._retry_queue` (missed cards awaiting review), plus `self._error_counts` and `self._repeat_counts`.
- Fixed the cooldown logic in `record_result()` so `self._cooldown = 1 if self._primary_queue else 0` is only set when `self._retry_queue` was empty prior to appending (`was_empty = len(self._retry_queue) == 0`). When a user misses Q1 and then also misses Q2 consecutively, Q1's cooldown has already expired (`_cooldown == 0`), so Q1 is immediately re-asked on Turn 3 before Q3 and Q4.
- Added a configurable `max_repeats` bound (defaulting to `1` retry per missed card per session, configurable for multi-repeat drills) so that a user who does not know an answer is never trapped in an infinite loop.

**Reasoning:**
- Asking the exact same question on the very next prompt tests only immediate 1-second echo memory rather than retrieval, while resetting `_cooldown` on consecutive misses prevented earlier missed cards from repeating promptly.
- Guarding `self._cooldown` with `if was_empty:` ensures every missed card waits at most 1 turn before being prioritized from `_retry_queue`, even during a streak of consecutive misses.

**Outcome:** `AdaptiveMode` repeats missed cards after a 1-card spacing interval even when misses are consecutive, prioritizes cards with higher error counts, and terminates reliably. Both `test_adaptive_mode_behavior` and `test_adaptive_mode_consecutive_misses` pass.

**Lessons Learned:**
- Stateful scheduling algorithms require tracing multi-step edge cases (such as consecutive misses vs. alternating hits and misses) rather than only testing a single miss in isolation.

---

### 2026-11-05 - Interaction 4: Adding Features Beyond Basic CRUD (Hints, Close-Match Detection, Timed Mode, and Analytics)

**Context:** The product specification requires implementing at least 3 extended features beyond basic CRUD operations to make the application genuinely useful for learners.

**AI Tool Used:** Claude Code / Gemini AI Coding Assistant

**Prompt/Request:** "Extend the Flashcard Quizzer with features beyond basic CRUD: (1) an interactive hint system (`hint` or `?`) that displays a custom hint or generates a masked word clue, (2) close-answer typo detection that tells the user when their answer is close to the expected answer, (3) per-question response timing with an optional `--time-limit` flag and streak tracking, (4) deck search/filtering (`--search`, `--filter`, `--limit`) and exporting missed cards (`--export-missed`), and (5) persistent session history analytics (`--stats`)."

**AI Response:** For close-answer detection, the AI initially suggested importing `fuzzywuzzy` / `thefuzz` and `python-Levenshtein`. For hint generation, it revealed the first half of the string, which leaked almost the entire answer for short keywords like `"def"` or `"int"`. Also, in `QuizEngine.evaluate_answer()`, it appended missed cards to `self._missed_cards` without checking if the card had already been missed on an earlier adaptive attempt.

**Checklist findings:** 1. Correctness and Functionality (Edge Cases) - reveals of `back[:len(back)//2]` in `get_hint()` leaked 1-character and 3-character answers, and `self._missed_cards` recorded duplicate entries when a card was missed twice in `AdaptiveMode` (fixed). 4. Performance and Efficiency - replaced O(N) list scan with O(1) `self._missed_fronts` set lookup for deduplication (fixed). 6. Integration and Compatibility (Dependencies) - rejected external `fuzzywuzzy` dependency not present in `requirements.txt` in favor of standard library `difflib.SequenceMatcher` (fixed). 3. Security Considerations - no issues found.

**Changes Made:**
- Rejected adding third-party `fuzzywuzzy` dependencies and replaced it with Python's standard library `difflib.SequenceMatcher(None, cleaned_input.lower(), cleaned_expected.lower()).ratio()` using `CLOSE_MATCH_THRESHOLD = 0.75`.
- Refined `Flashcard.get_hint()` in `utils/file_handler.py` to mask every word after its first character (`A__________ P__________ I________ (3 words, 33 chars)`), and handled 1-character answers safely.
- Added `self._missed_fronts: set[str]` in `QuizEngine` to deduplicate `self._missed_cards` while preserving order.

**Reasoning:**
- Standard library `difflib.SequenceMatcher` is zero-dependency, fast, deterministic, and available in every Python 3 environment.
- Deduplicating `missed_cards` ensures the end-of-session review list and `--export-missed` JSON deck never contain duplicate flashcards.

**Outcome:** All five extended features work seamlessly together, require zero extra external packages, and are fully covered by unit and integration tests.

**Lessons Learned:**
- Checking Section 6 (Dependencies) and Section 1 (Edge Cases) of the review checklist prevented unnecessary third-party package bloat and caught duplicate missed-card entries in adaptive sessions.

---

### 2026-11-05 - Interaction 5: CLI Architecture, ANSI Colors, and Testable I/O Injection

**Context:** Phase 3 required building `ui.py` and `main.py` with `argparse` flags (`-f`/`--file`, `-m`/`--mode`, `--stats`), ANSI color feedback (Green for correct, Red for incorrect), and graceful termination on `"exit"` or `Ctrl+C` (`KeyboardInterrupt`).

**AI Tool Used:** Claude Code / Gemini AI Coding Assistant

**Prompt/Request:** "Create `ui.py` and `main.py` using `argparse` to support `-f`/`--file`, `-m`/`--mode`, and `--stats`. Format correct answers in green and incorrect answers in red, display a session summary table at the end, and allow the user to type `'exit'` or press `Ctrl+C` to quit gracefully without a traceback."

**AI Response:** The AI wrote an interactive loop in `ui.py` that directly called `input()` and `print()`, did not handle `EOFError` (when stdin closes or a user presses `Ctrl+D`), and placed the `--stats-only` branch in `main.py` before the `try...except` block.

**Checklist findings:** 1. Correctness and Functionality - multi-word answers with extra internal spaces were marked wrong (fixed by normalizing whitespace with `" ".join(user_input.strip().split())`). 3. Security and Error Exposure - `--stats-only` branch in `main.py` sat outside the `try...except` block (fixed by moving it inside `try:`). 5. Error Handling and Robustness - `EOFError` was not caught alongside `KeyboardInterrupt` (fixed). 7. Testing and Testability - `input()` and `print()` were hardcoded, making CLI testing brittle (fixed by injecting `input_fn` and `output_fn` callables).

**Changes Made:**
- Refactored `run_interactive_quiz()` in `ui.py` and `run_cli()` in `main.py` to accept injectable `input_fn: Callable[[str], str] = input` and `output_fn: Callable[[str], None] = print` parameters.
- Moved the `--stats-only` / `raw_argv == ["--stats"]` branch inside the `try...except` block in `main.py` and caught `(KeyboardInterrupt, EOFError)` in both `ui.py` and `main.py`.
- Added whitespace normalization (`" ".join(user_input.strip().split())`) in `QuizEngine.evaluate_answer()`.

**Reasoning:**
- Dependency injection for `input_fn` and `output_fn` aligns directly with `ai_guidance/code_review_checklist.md` (Section 7: "Are dependencies injectable for mocking?") and makes integration tests fast and deterministic.
- Ensuring all CLI subcommands execute inside the `try...except` block guarantees no unhandled exceptions leak to the terminal.

**Outcome:** Both interactive terminal sessions and automated integration tests (`test_full_session`, `test_interactive_quiz_keyboard_interrupt`, `test_cli_auxiliary_commands_and_error_handling`) run cleanly without tracebacks.

**Lessons Learned:**
- Every CLI execution branch—even early-exit flags like `--stats-only`—should reside inside the top-level error boundary.

---

### 2026-11-05 - Interaction 6: Unit and Integration Test Suite Design with Pytest

**Context:** Phase 3 Testing Requirements specified six mandatory tests across `tests/test_flashcard_loader.py`, `tests/test_quiz_modes.py`, and `tests/test_integration.py`, with a target of >80% code coverage.

**AI Tool Used:** Claude Code / Gemini AI Coding Assistant

**Prompt/Request:** "Generate comprehensive pytest test suites in `tests/test_flashcard_loader.py`, `tests/test_quiz_modes.py`, and `tests/test_integration.py`. Include all required test functions (`test_load_valid_flashcards_array`, `test_load_invalid_json`, `test_load_missing_required_field`, `test_quiz_mode_factory`, `test_adaptive_mode_behavior`, `test_full_session`) plus edge cases and error conditions to achieve >90% test coverage."

**AI Response:** The AI generated the test files, but in `test_flashcard_loader.py` it initially created temporary JSON files inside the live `data/` folder using `open("data/test_temp.json", "w")` and manual `os.remove()` calls, and it only tested a single miss in `AdaptiveMode` rather than consecutive misses or non-UTF-8 files.

**Checklist findings:** 1. Correctness and Functionality (Testing Boundary Conditions) - missing test cases for consecutive misses in `AdaptiveMode` and non-UTF-8 binary files in loader/history (fixed by adding `test_adaptive_mode_consecutive_misses` and non-UTF-8 test assertions). 2. Code Quality (Style and Conventions) - test names were clear and descriptive, no issues found. 4. Performance and Resource Cleanup - tests wrote temporary files into `data/` where a failed assertion would leave orphan files behind (fixed by refactoring to pytest's `tmp_path` fixture). 7. Testing and Testability - side effects in filesystem tests eliminated via `tmp_path`.

**Changes Made:**
- Replaced all manual file creation in `tests/test_flashcard_loader.py` and `tests/test_integration.py` with pytest's built-in `tmp_path: Path` fixture.
- Added `test_adaptive_mode_consecutive_misses` in `tests/test_quiz_modes.py` to verify that missing Q1 and Q2 back-to-back still re-asks Q1 on Turn 3 before Q3 and Q4.
- Added tests for non-UTF-8 files in `test_load_empty_and_non_utf8_file_raises_error`, `test_session_history_persistence`, and `test_cli_auxiliary_commands_and_error_handling`.

**Reasoning:**
- Writing temporary test artifacts into `data/` risks polluting the repository if a test fails before `os.remove()` runs. Using pytest's `tmp_path` guarantees isolated, automatically cleaned temporary directories.

**Outcome:** All 26 unit and integration tests pass in ~0.5 seconds, achieving **97% code coverage** across the application modules (well above the 80% requirement).

**Lessons Learned:**
- Reviewing AI-generated test suites with the same rigor as production code catches missing boundary conditions (such as consecutive failures and binary file inputs) early.

---

### 2026-11-05 - Interaction 7: Linting (`flake8`), Formatting (`black`), and Static Type Checking (`mypy`)

**Context:** Verifying the Definition of Done by running `black`, `isort`, `flake8`, and `mypy` across the entire codebase.

**AI Tool Used:** Claude Code / Gemini AI Coding Assistant

**Prompt/Request:** "Review the codebase against `flake8`, `black`, `isort`, and `mypy`. Fix any line-length violations, import ordering issues, or static type checking warnings."

**AI Response:** Running `flake8` after default `black` (which defaults to 88 characters) flagged `E501 line too long (> 79 characters)` on several lines, and `mypy` flagged `Returning Any from function declared to return "QuizMode" [no-any-return]` on `QuizModeFactory.create_mode()` because ` QuizModeFactory._MODES` was inferred as `Dict[str, Any]`.

**Checklist findings:** 1. Correctness and Functionality - `QuizModeFactory._MODES` lacked an explicit `Dict[str, Type[QuizMode]]` annotation, causing `mypy` `[no-any-return]` error (fixed). 2. Code Quality (Style and Conventions) - 26 lines exceeded 79 characters under default `black` formatting, violating strict PEP 8 `flake8` checks (fixed by configuring `line-length = 79` in `pyproject.toml` and `setup.cfg` and wrapping long docstrings). 6. Integration and Compatibility - `skip_gitignore = true` in `isort` emitted git warnings when run outside a git repository (fixed by replacing with `extend_skip`).

**Changes Made:**
- Annotated `QuizModeFactory._MODES: Dict[str, Type[QuizMode]]` in `quiz_engine.py` so `mypy` statically verifies the factory return type without `Any`.
- Wrapped all docstrings, error message literals, and test strings to stay within 79 characters and configured `line-length = 79` in `pyproject.toml` and `max-line-length = 79` in `setup.cfg`.
- Configured `extend_skip = [".venv", "venv", "env", "htmlcov", ".claude"]` in `pyproject.toml` so `isort --check .` runs cleanly in any directory.

**Reasoning:**
- Aligning `black`, `isort`, and `flake8` to 79 characters ensures zero linting warnings regardless of whether `flake8` is invoked with or without custom flags.

**Outcome:** Zero `flake8` errors, zero `mypy` errors, 100% `black` and `isort` compliance, and 26/26 passing tests.

**Lessons Learned:**
- Running automated quality gates (`pytest`, `flake8`, `black`, `isort`, `mypy`) after every AI code generation step catches subtle typing and formatting discrepancies immediately.

---

## Summary Statistics

At the end of your project, fill out these statistics:

- **Total AI interactions:** 7 documented core engineering interactions (across 4 development phases)
- **Lines of AI-generated code used:** ~790 lines across source and test modules
- **Lines of AI-generated code modified:** ~230 lines refined for specific exception handling (`FileNotFoundError`, `IsADirectoryError`, `UnicodeDecodeError`), immutable dataclasses, consecutive-miss adaptive retry scheduling, injectable I/O, and PEP 8 compliance
- **Most helpful AI interaction:** Interactions 2 & 5 — Scaffolding the Strategy/Factory class hierarchy in `quiz_engine.py` and the `argparse` CLI + ANSI terminal table formatting in `main.py` and `ui.py`.
- **Most challenging AI interaction:** Interaction 3 — Designing `AdaptiveMode` so that missed questions are prioritized and repeated with spacing cooldowns even across consecutive misses without causing immediate back-to-back repetition or infinite loops.
- **Biggest lesson learned:** Treating the AI as a pair programmer requires reviewing every single generated snippet against a structured checklist (`code_review_checklist.md`) and testing multi-step boundary conditions (`pytest`, `flake8`, `mypy`, `black`).

---

**Note:** This log is a required component of your final project report. Be thorough and honest in your documentation to demonstrate your learning process and AI collaboration skills.
