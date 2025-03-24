# Contributing to langchain-document-pipeline

Thank you for your interest in contributing. This document covers development setup,
coding standards, and the pull request process.

## Development Setup

```bash
# Clone and enter the repo
git clone https://github.com/ivanpodgurskiy/langchain-document-pipeline.git
cd langchain-document-pipeline

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Copy and configure environment variables
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Start the database
docker compose up -d

# Run tests
pytest tests/ -v
```

## Code Standards

### Style
- **Formatter**: `ruff format` (line length 100)
- **Linter**: `ruff check` — E, F, I rules
- **Type checker**: `mypy` — run before committing

```bash
ruff check src/ scripts/ tests/
mypy src/
```

### Python Guidelines
- Use type hints on all function signatures
- Write docstrings for all public functions and classes
- No star imports (`from module import *`)
- Each module should be 50–200 lines of real, functional code
- Prefer `async`/`await` for all I/O-bound operations

### Commits
- Use imperative mood: "Add X", "Fix Y", "Remove Z"
- Keep commits focused — one logical change per commit
- Reference issues in commit messages where applicable

## Adding New Extraction Chains

1. Create `src/extraction/your_chain.py` (follow the pattern in `hcpcs_chain.py`)
2. Include a system prompt, at least 3 few-shot examples, and a Pydantic model
3. Integrate with `tracker.record()` for token usage tracking
4. Add tests in `tests/test_extraction.py`

## Adding API Endpoints

1. Create `src/api/your_router.py` with an `APIRouter`
2. Register it in `src/main.py` with `app.include_router()`
3. Add integration tests in `tests/test_api.py`

## Pull Request Process

1. Fork the repository and create a feature branch from `main`
2. Ensure all CI checks pass (`ruff`, `mypy`, `pytest`)
3. Update the README if your change adds or modifies user-facing behavior
4. Open a pull request with a clear description of the change and its motivation
5. Maintainer review required before merge

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
