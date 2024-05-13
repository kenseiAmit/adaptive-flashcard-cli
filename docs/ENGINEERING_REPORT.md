# AI-Assisted Development Project Report

**Author:** Amit Kumar Koshta  
**Project Title:** Flashcard Quizzer: AI-Assisted CLI Learning Application  
**Date:** November 6, 2026

## Executive Summary

**Flashcard Quizzer** is a modular Python CLI application for mastering technical terminology through active recall. It ingests JSON flashcard decks, validates schemas defensively, and runs quizzes in **Sequential**, **Random**, and **Adaptive** modes with five extra study features.

AI assistants generated code while architecture, prompt design, and checklist-driven reviews stayed human-directed. Using a **Decompose -> Prompt -> Review -> Refine -> Verify** workflow, the project reached **97% test coverage** across 26 `pytest` tests and passed `flake8`, `black`, `isort`, and `mypy` with zero errors.

## Project Overview

### Problem Statement
Learners need a terminal tool to review terminology, yet simple scripts often crash on malformed or non-UTF-8 JSON files, lack adaptive retry logic, and mix CLI I/O with business logic.

### Solution Approach
- **Key Design Decisions:** Decoupled file I/O from quiz state and UI using `@dataclass(frozen=True)` models (`Flashcard`, `AnswerEvaluation`) and `FlashcardLoadError`.
- **Architecture Choices:** Used the **Strategy Pattern** (`SequentialMode`, `RandomMode`, `AdaptiveMode`) and **Factory Pattern** (`QuizModeFactory`) for runtime mode selection.
- **Technology Stack:** Python 3 standard library (`abc`, `argparse`, `dataclasses`, `difflib`, `json`, `pathlib`, `random`, `time`, `typing`) plus `pytest`, `pytest-cov`, `black`, `isort`, `flake8`, and `mypy`.

### Final Features
- [x] **Core Functionality #1:** Dual-format JSON loading (Array and Object Wrapper) with `FlashcardLoadError` validation.
- [x] **Core Functionality #2:** Interactive CLI loop supporting Sequential, Random, and Adaptive modes, ANSI colors, graceful exit, and summary tables.
- [x] **Additional Feature #1 (Hints & Close-Match):** `hint`/`?` clue display and `difflib.SequenceMatcher` (`>=75%`) typo detection.
- [x] **Additional Feature #2 (Analytics & Timers):** Response times, streaks, `--time-limit`, and persistent JSON session history (`--stats`).
- [x] **Additional Feature #3 (Search, Filter, Add & Export):** `--search`, `--filter`, `--limit`, `--add-card`, and `--export-missed`.

## AI Collaboration Experience

### AI Tools Used
- [x] Claude (Claude Code CLI / Assistant)
- [ ] GitHub Copilot
- [ ] ChatGPT
- [x] Other: Gemini Coding Assistant

### Collaboration Workflow
1. **Structuring Prompts:** Wrote *Context + Requirements + Constraints + Verification* prompts defining types and failure modes.
2. **Task Delegation:** Delegated boilerplate, dataclasses, `argparse` setup, ANSI tables, and initial `pytest` suites to AI.
3. **Review and Validation:** Audited every output against `ai_guidance/code_review_checklist.md` and logged a `Checklist findings` line in each entry of `docs/ai_edit_log.md`.
4. **Refinement Process:** Corrected defects via targeted follow-up prompts and verified with `pytest`, `flake8`, and `mypy`.

### Most Valuable AI Interactions

#### Example 1: Dual-Format Data Loader and Validation
- **Context:** Building `utils/file_handler.py` for `glossary.json` and `python_basics.json`.
- **AI Prompt:** Requested `load_flashcards()` and `FlashcardLoadError` supporting array and wrapper formats.
- **AI Response:** Used broad `except Exception:`, missed `UnicodeDecodeError`, and allowed blank strings.
- **Your Changes:** Added explicit `FileNotFoundError`, `IsADirectoryError`, `PermissionError`, `UnicodeDecodeError`, `OSError`, and `json.JSONDecodeError` handlers in `read_json_file()`, caught `UnicodeDecodeError` in `load_session_history()`, and validated stripped strings with card indices.
- **Outcome:** Malformed or non-UTF-8 files fail gracefully.

#### Example 2: Bounded Priority Scheduling in AdaptiveMode
- **Context:** Repeating missed cards in `AdaptiveMode` (`quiz_engine.py`).
- **AI Prompt:** Requested `AdaptiveMode.record_result()` and `get_next_card()` to re-queue missed cards.
- **AI Response:** Draft 1 inserted missed cards at index `0` (infinite loop risk); Draft 2 reset `self._cooldown = 1` on every miss, delaying retries on consecutive misses.
- **Your Changes:** Used `_primary_queue` and `_retry_queue` with `max_repeats`, and guarded `self._cooldown = 1` with `if was_empty:` so consecutive misses never delay queued retries.
- **Outcome:** Missed cards repeat after 1 spacing card even on consecutive misses (`test_adaptive_mode_consecutive_misses`).

#### Example 3: Injectable CLI I/O for Integration Testing
- **Context:** Building `ui.py` and `main.py` with `argparse`, ANSI colors, and `exit`/`Ctrl+C` handling.
- **AI Prompt:** Requested `run_interactive_quiz()` and `run_cli()` with colored feedback and graceful exit.
- **AI Response:** Hardcoded `input()`/`print()`, omitted `EOFError`, and left `--stats-only` outside `try:`.
- **Your Changes:** Injected `input_fn`/`output_fn`, moved `--stats-only` inside `try:`, and caught `(KeyboardInterrupt, EOFError)`.
- **Outcome:** Deterministic integration tests (`test_full_session`).

### Challenges with AI Collaboration
- **Happy-Path Bias:** AI missed empty files, non-UTF-8 inputs, blank strings, and consecutive misses in `AdaptiveMode`.
- **Unintended Side Effects:** Initial code mutated input lists in `RandomMode` and wrote test files to `data/` until refactored to copies and `tmp_path`.
- **Unnecessary Dependencies:** Replaced AI's suggested `fuzzywuzzy` with `difflib.SequenceMatcher`.

## Software Engineering Practices

### Code Quality Measures
- [x] Code formatting (`black`, `isort` at 79 chars)
- [x] Linting (`flake8` — 0 errors)
- [x] Type hints (`mypy` — 0 errors)
- [x] Documentation/comments (Docstrings on all functions/classes)
- [x] Error handling (`FlashcardLoadError`, `ValueError`, `UnicodeDecodeError`, `KeyboardInterrupt`/`EOFError`)

### Testing Strategy
A 26-test `pytest` suite across `test_flashcard_loader.py`, `test_quiz_modes.py`, and `test_integration.py` reaches **97% coverage**, testing valid decks, non-UTF-8 files, missing fields, and consecutive-miss adaptive behavior via `tmp_path`.

### Design Patterns Used
- **Strategy Pattern (`QuizMode`, `SequentialMode`, `RandomMode`, `AdaptiveMode`):** Encapsulates card-selection algorithms behind one interface so modes can be added without modifying `QuizEngine`.
- **Factory Pattern (`QuizModeFactory`):** Instantiates strategies from `--mode`.

### Code Structure and Organization
- `main.py`: `argparse` CLI parsing and top-level error boundary.
- `data_loader.py` & `utils/file_handler.py`: `Flashcard` model, validation, search, and JSON persistence.
- `quiz_engine.py`: Strategy/Factory classes, `QuizEngine`, `AnswerEvaluation`, and `SessionStats`.
- `ui.py`: ANSI formatting, summary tables, and interactive quiz loop.

## Technical Challenges and Solutions

### Challenge 1: Consecutive Misses and Cooldown Resets in AdaptiveMode
- **Problem:** Resetting `_cooldown = 1` on every miss delayed queued retries during consecutive misses.
- **Solution:** Used `_primary_queue` and `_retry_queue` with `max_repeats` and only set `_cooldown = 1` when `_retry_queue` was previously empty.
- **AI Involvement:** AI generated the dual-queue skeleton; checklist review caught the consecutive-miss bug and added `test_adaptive_mode_consecutive_misses`.
- **Lessons Learned:** Stateful schedulers need sequence tests for consecutive failures.

### Challenge 2: Defensive File I/O and Encoding Error Boundaries
- **Problem:** Non-UTF-8 binary files passed to `load_session_history` or `read_json_file` risked `UnicodeDecodeError` tracebacks.
- **Solution:** Added explicit `FileNotFoundError`, `IsADirectoryError`, `PermissionError`, `UnicodeDecodeError`, and `OSError` handlers in `read_json_file`, caught `UnicodeDecodeError` in `load_session_history`, and moved `--stats-only` inside `try:`.
- **AI Involvement:** AI wrote initial handlers; checklist review caught the missing `UnicodeDecodeError` catch.
- **Lessons Learned:** Every file reader must handle `UnicodeDecodeError` alongside `OSError` and `JSONDecodeError`.

### Challenge 3: Testable Terminal Interactions
- **Problem:** Testing interactive loops reading from `stdin` is brittle with global patches.
- **Solution:** Parameterized `run_interactive_quiz` and `run_cli` with `input_fn` and `output_fn`.
- **AI Involvement:** AI refactored signatures and generated iterator-based integration tests.
- **Lessons Learned:** Dependency injection at I/O boundaries makes CLI tests fast and reliable.

## Code Quality Analysis

### Metrics
- **Lines of code:** 577 statements across source modules
- **Test coverage:** 97% (26 passed, 0 failed)
- **Number of functions/classes:** 10 classes and 28 functions/methods
- **Linting score:** 100% clean (0 `flake8` errors, 0 `mypy` errors)

### Self-Assessment
- **Code Readability: 5/5** — Clear naming and 79-char PEP 8 formatting.
- **Code Maintainability: 5/5** — Modular separation and Strategy/Factory patterns.
- **Test Quality: 5/5** — 97% coverage across unit, consecutive-miss, non-UTF-8, and CLI tests.
- **Documentation: 5/5** — Complete docstrings, `README.md`, and 7 checklist-audited log entries.

## Learning Outcomes

### Technical Skills Developed
Instead of relying on LBYL (`exists()`/`is_dir()`) checks or broad catches, I now write explicit EAFP exception hierarchies (`FileNotFoundError`, `IsADirectoryError`, `UnicodeDecodeError`) and design stateful schedulers with explicit queue invariants.

### AI Collaboration Skills
I shifted from treating the review checklist as a post-project summary to applying it per interaction—recording specific `Checklist findings` on every prompt output before accepting code.

### Software Engineering Insights
Combining Strategy and Factory patterns with injectable I/O callables showed how clean boundaries let complex behaviors like adaptive retry scheduling be tested without touching the terminal.

## Reflection

### What Worked Well
Decomposing the application into four phases (Data Layer, Core Engine, CLI/UI, Testing/QA) and injecting `input_fn`/`output_fn` made writing deterministic integration tests effortless.

### What Could Be Improved
In my initial pass, I applied the code review checklist once as a project-wide summary rather than auditing each AI interaction individually. Because of that, I initially missed two subtle bugs: `AdaptiveMode.record_result` resetting `_cooldown = 1` on consecutive misses, and `load_session_history` not catching `UnicodeDecodeError` when `--stats-only` sat outside the `try` block. I also wrote in the log that `read_json_file` had `FileNotFoundError`/`IsADirectoryError` handlers when it was still using `exists()`/`is_dir()` checks. Going forward, I will run the checklist immediately after each prompt, verify that every logged claim matches the exact code, and write tests for consecutive failures and binary inputs upfront.

### Future Enhancements
1. **SM-2 Spaced Repetition Strategy:** Add a `SpacedRepetitionMode(QuizMode)` persisting per-card easiness factors and review intervals across sessions.
2. **Interactive Terminal UI (TUI):** Add an optional `rich` or `curses` interface with progress bars and live timers.
3. **Multi-Format Deck Import/Export:** Extend `ExporterFactory` to import and export CSV and Markdown decks.

## Conclusion

This project reshaped how I collaborate with AI coding tools: AI accelerates scaffolding, but human engineering judgment—enforced through per-interaction checklist audits, explicit error boundaries, and adversarial edge-case testing—is what turns generated code into reliable software.

## Appendices

### Appendix A: AI Interaction Log
See [`docs/ai_edit_log.md`](ai_edit_log.md) for 7 detailed AI interaction logs with per-entry `Checklist findings`.

### Appendix B: Code Statistics
- `pytest --cov=.`: 26 passed, 97% coverage; `flake8`, `black`, `isort`, `mypy`: 0 errors.

### Appendix C: Additional Resources
- [`docs/design_patterns.md`](design_patterns.md), [`ai_guidance/code_review_checklist.md`](../ai_guidance/code_review_checklist.md), [`ai_guidance/prompting_best_practices.md`](../ai_guidance/prompting_best_practices.md)
