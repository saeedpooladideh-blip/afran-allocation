from __future__ import annotations

import ast
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
IGNORED_PARTS = {".git", ".pytest_cache", ".ruff_cache", ".venv", "__pycache__"}
LEGACY_PROJECT_IMPORTS = {"app.crawlers.types", "app.utils.logging"}


def project_python_files() -> list[Path]:
    return [
        path
        for path in BACKEND_ROOT.rglob("*.py")
        if not IGNORED_PARTS.intersection(path.parts)
    ]


def test_project_modules_do_not_shadow_python_standard_library() -> None:
    conflicts = [
        str(path.relative_to(BACKEND_ROOT))
        for path in project_python_files()
        if path.stem in sys.stdlib_module_names
    ]
    assert conflicts == [], f"Python standard-library module names are shadowed: {conflicts}"


def test_legacy_project_imports_are_not_reintroduced() -> None:
    broken_imports: list[str] = []
    for path in project_python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported = {alias.name for alias in node.names}
                if imported.intersection(LEGACY_PROJECT_IMPORTS):
                    broken_imports.append(str(path.relative_to(BACKEND_ROOT)))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module in LEGACY_PROJECT_IMPORTS or (
                    node.level > 0 and module in {"types", "logging"}
                ):
                    broken_imports.append(str(path.relative_to(BACKEND_ROOT)))
    assert broken_imports == [], f"Legacy project imports remain: {sorted(set(broken_imports))}"
