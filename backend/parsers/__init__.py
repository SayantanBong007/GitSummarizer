from pathlib import Path

from backend.parsers.base import BaseParser
from backend.parsers.csharp_parser import CSharpParser
from backend.parsers.go_parser import GoParser
from backend.parsers.java_parser import JavaParser
from backend.parsers.php_parser import PHPParser
from backend.parsers.python_parser import PythonParser
from backend.parsers.rust_parser import RustParser
from backend.parsers.typescript_parser import JavaScriptParser, TypeScriptParser

_PARSERS: list[type[BaseParser]] = [
    PythonParser,
    TypeScriptParser,
    JavaScriptParser,
    JavaParser,
    GoParser,
    RustParser,
    CSharpParser,
    PHPParser,
]

_INSTANCES: dict[str, BaseParser] = {}


def get_parser_for(file_path: Path) -> BaseParser | None:
    ext = file_path.suffix.lower()
    for cls in _PARSERS:
        if cls.supports(ext):
            if cls.language_name not in _INSTANCES:
                _INSTANCES[cls.language_name] = cls()
            return _INSTANCES[cls.language_name]
    return None


SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(
    ext for cls in _PARSERS for ext in cls.extensions
)
