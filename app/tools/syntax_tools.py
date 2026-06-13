"""Syntax / lint validation for refactored code (Critic agent)."""
from __future__ import annotations

import ast
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from agno.tools import tool


def _run_ruff(file_path: Path) -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["ruff", "check", "--quiet", "--output-format=concise", str(file_path)],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "error": str(exc)}
    issues = [line for line in result.stdout.splitlines() if line.strip()]
    return {
        "available": True,
        "exit_code": result.returncode,
        "issues": issues,
        "stderr": result.stderr.strip() or None,
    }


def check_syntax(source_code: str) -> dict[str, Any]:
    try:
        ast.parse(source_code)
    except SyntaxError as exc:
        return {
            "is_valid": False,
            "error": exc.msg,
            "line": exc.lineno,
            "offset": exc.offset,
            "lint": {"available": False},
        }

    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as fh:
        fh.write(source_code)
        tmp_path = Path(fh.name)
    try:
        lint = _run_ruff(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    return {"is_valid": True, "lint": lint}


@tool(
    name="syntax_checker_tool",
    description=(
        "Valida sintaxe Python via ast.parse e roda ruff (se disponível) sobre o código informado. "
        "Retorna `is_valid` e lista de problemas encontrados."
    ),
)
def syntax_checker_tool(source_code: str) -> dict[str, Any]:
    return check_syntax(source_code)
