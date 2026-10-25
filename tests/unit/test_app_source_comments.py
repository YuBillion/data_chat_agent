from __future__ import annotations

import ast
import io
import tokenize
from pathlib import Path

APP_ROOT = Path(__file__).parents[2] / "app"


def _excluded_source_lines(source: str) -> set[int]:
    excluded: set[int] = set()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(
            node,
            (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            continue
        if not node.body:
            continue
        first = node.body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
            if isinstance(first.value.value, str):
                excluded.update(
                    range(
                        first.value.lineno,
                        getattr(first.value, "end_lineno", first.value.lineno) + 1,
                    )
                )

    tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    fstring_depth = 0
    fstring_start = 0
    fstring_start_kind = getattr(tokenize, "FSTRING_START", -1)
    fstring_end_kind = getattr(tokenize, "FSTRING_END", -1)
    for token in tokens:
        if token.type == tokenize.STRING and token.end[0] > token.start[0]:
            excluded.update(range(token.start[0], token.end[0] + 1))
        if token.type == fstring_start_kind:
            if fstring_depth == 0:
                fstring_start = token.start[0]
            fstring_depth += 1
        elif token.type == fstring_end_kind:
            fstring_depth = max(fstring_depth - 1, 0)
            if fstring_depth == 0 and token.end[0] > fstring_start:
                excluded.update(range(fstring_start, token.end[0] + 1))
    return excluded


def test_all_app_code_lines_have_comments() -> None:
    missing: list[str] = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        if not source.strip():
            missing.append(f"{path.relative_to(APP_ROOT)}: empty module")
            continue
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
        excluded = _excluded_source_lines(source)
        code_lines = {
            token.start[0]
            for token in tokens
            if token.type
            not in {
                tokenize.ENCODING,
                tokenize.ENDMARKER,
                tokenize.INDENT,
                tokenize.DEDENT,
                tokenize.NEWLINE,
                tokenize.NL,
                tokenize.COMMENT,
                getattr(tokenize, "FSTRING_START", -1),
                getattr(tokenize, "FSTRING_MIDDLE", -1),
                getattr(tokenize, "FSTRING_END", -1),
            }
        }
        comment_lines = {
            token.start[0]
            for token in tokens
            if token.type == tokenize.COMMENT
        }
        for line_number in sorted(code_lines - excluded - comment_lines):
            missing.append(
                f"{path.relative_to(APP_ROOT)}:{line_number}: "
                f"{source.splitlines()[line_number - 1].strip()}"
            )
    assert not missing, "Missing line comments:\n" + "\n".join(missing)
