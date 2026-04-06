# Contributing to Jack The Shadow

Thanks for your interest in contributing! 🗡️

## Getting Started

1. Fork the repo and clone your fork
2. Create a virtual environment: `python3 -m venv .venv && source .venv/bin/activate`
3. Install in dev mode: `pip install -e ".[dev]"`
4. Create a branch: `git checkout -b feature/your-feature`

## Code Style

- **Type hints** on all function signatures
- **Docstrings** for public classes and functions
- Follow existing patterns — one tool per file in `tools/builtin/`
- Keep UI logic in `ui/`, business logic in `core/`, tool logic in `tools/`

## Adding a New Tool

1. Create `src/jack_the_shadow/tools/builtin/your_tool.py`
2. Define a `BaseTool` subclass with `name`, `description`, `parameters_schema()`
3. Add handler method in the same file
4. Register in `tools/registry.py` → `build_default_registry()`
5. Register handler in `tools/executor.py` → `ToolExecutor.__init__`
6. Update i18n if needed

## Pull Requests

- One feature per PR
- Include tests for new tools
- Update README.md if adding user-facing features
- Ensure `pytest` passes before submitting

## Reporting Issues

- Use GitHub Issues
- Include: Python version, OS, steps to reproduce, expected vs actual behaviour

## License

By contributing, you agree your contributions will be licensed under MIT.
