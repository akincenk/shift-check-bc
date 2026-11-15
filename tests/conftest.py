from pathlib import Path

import pytest

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


@pytest.fixture
def examples() -> Path:
    return EXAMPLES


@pytest.fixture
def write(tmp_path):
    def _write(name: str, text: str) -> Path:
        path = tmp_path / name
        path.write_text(text, encoding="utf-8")
        return path

    return _write
