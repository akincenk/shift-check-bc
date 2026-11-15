# Contributing

Thanks for looking at shift-check-bc. Issues and pull requests are welcome.

## Set up

```sh
python3 -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'
```

## Before you open a pull request

```sh
ruff check .
ruff format --check .
pytest -q
gitleaks dir .
```

CI runs the same checks on Python 3.11 and 3.14, plus a gitleaks scan of the history.

## Guidelines

- One change per pull request, with tests. Bug fixes start with a test that fails.
- Keep the runtime free of third-party dependencies unless an issue agrees otherwise.
- Sample data must be made up. Do not commit real names, phone numbers, addresses or company data.
- The planned work is in [ROADMAP.md](ROADMAP.md); each item has a GitHub issue. Comment on the issue before starting a large item.
