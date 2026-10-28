import pytest
from pathlib import Path


def test_python_parser_functions(tmp_path):
    from backend.parsers.python_parser import PythonParser

    code = b"""
def greet(name: str) -> str:
    return f"Hello {name}"

class Greeter:
    def hello(self) -> None:
        pass
"""
    f = tmp_path / "test.py"
    f.write_bytes(code)
    parser = PythonParser()
    result = parser.parse_file(f)
    assert result is not None
    assert result["language"] == "python"
    names = [s["name"] for s in result["symbols"]]
    assert "greet" in names
    assert "Greeter" in names
    assert "hello" in names


def test_python_parser_imports(tmp_path):
    from backend.parsers.python_parser import PythonParser

    code = b"import os\nfrom pathlib import Path\n"
    f = tmp_path / "imports.py"
    f.write_bytes(code)
    parser = PythonParser()
    result = parser.parse_file(f)
    assert result is not None
    assert any("import os" in imp for imp in result["imports"])


def test_parser_registry():
    from backend.parsers import get_parser_for, SUPPORTED_EXTENSIONS
    from pathlib import Path

    assert ".py" in SUPPORTED_EXTENSIONS
    assert ".ts" in SUPPORTED_EXTENSIONS
    assert ".java" in SUPPORTED_EXTENSIONS

    py_parser = get_parser_for(Path("test.py"))
    assert py_parser is not None
    assert py_parser.language_name == "python"

    ts_parser = get_parser_for(Path("test.ts"))
    assert ts_parser is not None
    assert ts_parser.language_name == "typescript"

    unknown = get_parser_for(Path("test.xyz"))
    assert unknown is None


def test_parser_skips_large_files(tmp_path):
    from backend.parsers.python_parser import PythonParser
    from backend.parsers.base import SNIPPET_LINES

    lines = ["x = 1\n"] * (SNIPPET_LINES + 100)
    f = tmp_path / "big.py"
    f.write_bytes("".join(lines).encode())
    parser = PythonParser()
    result = parser.parse_file(f)
    assert result is not None
    snippet_lines = result["raw_snippet"].splitlines()
    assert len(snippet_lines) <= SNIPPET_LINES
