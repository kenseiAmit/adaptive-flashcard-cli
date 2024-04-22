# Claude Code Configuration — Adaptive Flashcard Quizzer

## Project Overview
Zero-dependency Python CLI active-recall learning application implementing Strategy and Factory design patterns, bounded adaptive retry queues, progressive masked hints, fuzzy Levenshtein/SequenceMatcher typo tolerance, and persistent JSON session analytics.

## Engineering Objectives
- Strict PEP 8 compliance (`black` / `flake8` 79-character line limit, `isort` import ordering).
- Full static type safety verified via `mypy` across all modules.
- High-coverage deterministic unit and end-to-end CLI tests (`pytest`, >=95% coverage) using injectable `input_fn` / `output_fn` streams.

## Developer Verification Commands
```bash
pytest --cov=. --cov-report=term-missing
flake8 .
mypy main.py quiz_engine.py ui.py data_loader.py utils/
```
