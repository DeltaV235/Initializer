# Repository Guidelines

## Project Structure & Module Organization
Core Python sources live in `src/initializer/`, split into `modules/` for backend logic, `ui/` for Textual screens and components, and `utils/` for helpers. Configuration YAML sits under `config/` (app, modules, themes, presets). Executable entry points are `main.py` for local runs and `run.sh` for virtualenv bootstrapping. Legacy Bash scripts remain in `legacy/` for reference only; do not modify them without a migration plan.

## Build, Test, and Development Commands
Bootstrap dependencies with `./install.sh` (creates `.venv` and installs extras). Launch the TUI via `./run.sh` or `python -m initializer.main --preset server` for preset validation. Install editable dev tooling using `pip install -e .[dev]`. Run static checks with `flake8 src` and `black --check src`. Execute fast smoke tests using `pytest -q`. Use `tools/sync-to-remote.sh -n` to dry-run remote sync before deployments.

## Coding Style & Naming Conventions
Follow PEP 8 with 4-space indentation and an 88-character line width (enforced by Black). Modules and packages use lowercase underscores (`system_info.py`), classes use PascalCase (`HomebrewScreen`), and functions plus variables use snake_case. Keep Rich/Textual view code declarative and move heavy logic into `modules/`. Run `black src` and `flake8` before submitting changes.

## Testing Guidelines
Adopt `pytest` for unit and integration coverage; place new suites under `tests/` mirroring the `src/initializer/` structure. Name files `test_<feature>.py` and functions `test_<case>()`. Aim to exercise new module logic plus UI screen controller methods and include fixtures for configuration samples in `config/`. Run `pytest --maxfail=1 --disable-warnings -q` locally and add regression tests whenever fixing bugs.

## Commit & Pull Request Guidelines
Match existing history by prefixing commits with an emoji plus Conventional-style type, e.g. `✨ feat: add progress overlay screen`. Keep messages in imperative mood and reference issues with `refs #123` when available. Pull requests should describe scope, call out configuration changes, list validation commands, and include screenshots or terminal recordings for UI tweaks. Request review once CI (formatters, lint, pytest) passes and ensure remote sync instructions are updated when deployment behavior changes.

## Configuration & Safety Notes
Keep sensitive values out of YAML presets; use environment variables when needed. Validate new configuration keys in `config/modules.yaml` and update `ConfigManager` defaults. When touching installer logic, test both `.venv` workflows (`install.sh`, `run.sh`) and `python main.py` entry points. For remote automation, prefer the provided sync script and confirm the target host before running destructive operations.
