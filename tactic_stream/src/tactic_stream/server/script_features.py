"""Handler script_editor_features.py (EPL-1.0), Qt-free static Python analysis."""
from __future__ import annotations

import ast
import builtins
import importlib
import inspect
import keyword
import re
import sys
from functools import lru_cache
from pathlib import Path

_STDLIB_MODULES = frozenset({
    "collections", "datetime", "functools", "itertools", "json", "math",
    "os", "pathlib", "re", "sys", "typing",
})
_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_KNOWN_EXPRESSION_TARGETS = {
    "server": ("class", "tactic_client_lib.tactic_server_stub", "TacticServerStub"),
    "Search": ("class", "pyasm.search.search", "Search"),
    "Search()": ("class", "pyasm.search.search", "Search"),
    "SearchType": ("class", "pyasm.search.search", "SearchType"),
}


def _node_signature(node):
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return ""
    if isinstance(node, ast.ClassDef):
        return "class"
    arguments = []
    positional = list(node.args.posonlyargs) + list(node.args.args)
    defaults = [None] * (len(positional) - len(node.args.defaults)) + list(node.args.defaults)
    for argument, default in zip(positional, defaults):
        label = argument.arg
        if default is not None:
            try:
                label += "=" + ast.unparse(default)
            except (AttributeError, ValueError):
                label += "=…"
        arguments.append(label)
    if node.args.vararg:
        arguments.append("*" + node.args.vararg.arg)
    arguments.extend(argument.arg for argument in node.args.kwonlyargs)
    if node.args.kwarg:
        arguments.append("**" + node.args.kwarg.arg)
    prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
    return f"{prefix}({', '.join(arguments)})"


@lru_cache(maxsize=8)
def _safe_tree(source):
    """Share read-only trees across outline, completion and highlighting.

    Recover the valid prefix at the error, not by reparsing every trailing
    line. The bounded cache retains only a few recent document revisions.
    """
    candidate = source
    while candidate:
        try:
            return ast.parse(candidate)
        except (RecursionError, ValueError):
            return None
        except SyntaxError as error:
            lines = candidate.splitlines()
            end = min(len(lines) - 1, max(0, (error.lineno or 1) - 1))
            candidate = "\n".join(lines[:end])
    return None


def _module_source_path(module_name):
    module_name = str(module_name or "")
    if not re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*", module_name):
        return None
    relative = Path(*module_name.split("."))
    roots = [_REPOSITORY_ROOT]
    roots.extend(Path(value) for value in sys.path if value)
    checked = set()
    for root in roots:
        try:
            root = root.resolve()
        except OSError:
            continue
        if root in checked:
            continue
        checked.add(root)
        for candidate in (
            root / relative.with_suffix(".py"),
            root / relative / "__init__.py",
        ):
            if candidate.is_file():
                return candidate
    return None


@lru_cache(maxsize=64)
def _module_tree_cached(path, modified_ns):
    del modified_ns
    try:
        return ast.parse(Path(path).read_text(
            encoding="utf-8", errors="replace"
        ))
    except (OSError, SyntaxError):
        return None


def _module_tree(module_name):
    path = _module_source_path(module_name)
    if path is None:
        return None
    try:
        modified_ns = path.stat().st_mtime_ns
    except OSError:
        return None
    return _module_tree_cached(str(path), modified_ns)


def _symbols_from_nodes(nodes):
    result = []
    for node in nodes:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name.startswith("_"):
                continue
            kind = "class" if isinstance(node, ast.ClassDef) else "function"
            doc = (ast.get_docstring(node) or "").strip().splitlines()
            result.append((
                node.name, kind, _node_signature(node), doc[0] if doc else "",
            ))
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and not target.id.startswith("_"):
                    result.append((target.id, "value", "", ""))
    return tuple(result)


def _source_symbols(module_name):
    tree = _module_tree(module_name)
    return _symbols_from_nodes(tree.body) if tree else ()


def _class_member_symbols(class_node):
    result = list(_symbols_from_nodes(class_node.body))
    names = {item[0] for item in result}
    for node in ast.walk(class_node):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for target in targets:
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id in {"self", "cls"}
                and not target.attr.startswith("_")
                and target.attr not in names
            ):
                result.append((target.attr, "value", "", "Instance attribute"))
                names.add(target.attr)
    return tuple(result)


def _class_symbols(module_name, class_name):
    tree = _module_tree(module_name)
    if not tree:
        return ()
    target = next((
        node for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and node.name == class_name
    ), None)
    return _class_member_symbols(target) if target else ()


def _imported_display_names(source):
    tree = _safe_tree(source)
    if not tree:
        return ()
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(
                imported.asname or imported.name.split(".", 1)[0]
                for imported in node.names
            )
        elif isinstance(node, ast.ImportFrom):
            names.update(
                imported.asname or imported.name
                for imported in node.names if imported.name != "*"
            )
    return tuple(sorted(name for name in names if name.isidentifier()))


@lru_cache(maxsize=16)
def _stdlib_symbols(module_name):
    if module_name not in _STDLIB_MODULES:
        return ()
    try:
        module = importlib.import_module(module_name)
    except ImportError:
        return ()
    result = []
    for name in dir(module):
        if name.startswith("_"):
            continue
        value = getattr(module, name)
        kind = (
            "class" if isinstance(value, type)
            else "function" if callable(value) else "value"
        )
        detail = ""
        if callable(value):
            try:
                detail = str(inspect.signature(value))
            except (TypeError, ValueError):
                pass
        result.append((name, kind, detail, "Python standard library"))
    return tuple(result)


def _module_aliases(tree):
    aliases = {}
    if not tree:
        return aliases
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for imported in node.names:
                aliases[
                    imported.asname or imported.name.split(".", 1)[0]
                ] = imported.name if imported.asname else imported.name.split(".", 1)[0]
        elif isinstance(node, ast.ImportFrom):
            module = str(node.module or "")
            for imported in node.names:
                if imported.name == "*":
                    continue
                dotted = f"{module}.{imported.name}".strip(".")
                if _module_source_path(dotted):
                    aliases[imported.asname or imported.name] = dotted
    return aliases


def _module_symbols(module_name):
    if module_name in _STDLIB_MODULES:
        return _stdlib_symbols(module_name)
    return _source_symbols(module_name)


def _target_symbols(target):
    kind, module_name, class_name = target
    if kind == "class":
        return _class_symbols(module_name, class_name)
    return _module_symbols(module_name)


def _class_node(tree, name):
    if not tree:
        return None
    return next((
        node for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and node.name == name
    ), None)


def _enclosing_class(tree, line):
    candidates = [
        node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
        and node.lineno <= line <= (getattr(node, "end_lineno", None) or line)
    ] if tree else []
    return min(candidates, key=lambda node: (
        (getattr(node, "end_lineno", node.lineno) or node.lineno) - node.lineno
    ), default=None)


def _local_expression_symbols(expression, tree, line):
    name = expression[:-2] if expression.endswith("()") else expression
    if name in {"self", "cls"}:
        owner = _enclosing_class(tree, line)
        return _class_member_symbols(owner) if owner else ()
    owner = _class_node(tree, name)
    if owner:
        return _class_member_symbols(owner)
    if not tree or "." in name:
        return ()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(isinstance(target, ast.Name) and target.id == name for target in targets):
            continue
        value = node.value
        if isinstance(value, ast.Call) and isinstance(value.func, ast.Name):
            owner = _class_node(tree, value.func.id)
            if owner:
                return _class_member_symbols(owner)
    return ()


def _expression_symbols(expression, aliases, tree, line):
    first = expression.split(".", 1)[0]
    first_name = first[:-2] if first.endswith("()") else first
    module_name = aliases.get(first_name)
    normalized = expression
    if module_name:
        normalized = module_name + expression[len(first_name):]

    target = _KNOWN_EXPRESSION_TARGETS.get(normalized)
    if target:
        return _target_symbols(target)
    if module_name:
        tail = expression[len(first_name):].lstrip(".")
        if not tail:
            return _module_symbols(module_name)
        target_name = tail[:-2] if tail.endswith("()") else tail
        if "." not in target_name:
            members = _class_symbols(module_name, target_name)
            if members:
                return members
        nested_module = f"{module_name}.{target_name}"
        if _module_source_path(nested_module):
            return _module_symbols(nested_module)
    return _local_expression_symbols(expression, tree, line)


def _completion_record(name, kind, signature, doc, start, end):
    detail = signature
    if doc:
        detail = (detail + " — " if detail else "") + doc
    callable_item = kind in {"builtin", "class", "function"}
    return {
        "label": name,
        "insertText": name + "()" if callable_item else name,
        "cursorOffset": -1 if callable_item else 0,
        "kind": kind,
        "detail": detail,
        "start": start,
        "end": end,
    }


def document_symbols(source):
    tree = _safe_tree(str(source or ""))
    if not tree:
        return []
    result = []

    def append_nodes(nodes, owner="", depth=0):
        for node in nodes:
            if not isinstance(node, (
                ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
            )):
                continue
            name = node.name
            qualified = f"{owner}.{name}" if owner else name
            kind = (
                "class" if isinstance(node, ast.ClassDef)
                else "method" if owner else "function"
            )
            result.append({
                "name": name,
                "qualifiedName": qualified,
                "kind": kind,
                "detail": _node_signature(node),
                "line": int(node.lineno),
                "endLine": int(getattr(node, "end_lineno", node.lineno)),
                "depth": depth,
            })
            append_nodes(node.body, qualified, depth + 1)

    append_nodes(tree.body)
    return result


def completion_items(source, cursor_position, manual=False):
    source = str(source or "")
    cursor_position = max(0, min(int(cursor_position), len(source)))
    before = source[:cursor_position]
    match = re.search(
        r"(?P<base>[A-Za-z_]\w*(?:\([^()\n]*\))?"
        r"(?:\.[A-Za-z_]\w*(?:\([^()\n]*\))?)*)\."
        r"(?P<prefix>[A-Za-z_]\w*)?$",
        before,
    )
    if match:
        base = match.group("base") or ""
        prefix = match.group("prefix") or ""
    else:
        match = re.search(r"(?P<prefix>[A-Za-z_]\w*)?$", before)
        base = ""
    if not match:
        return []
    prefix = match.group("prefix") or ""
    if not manual and not base and len(prefix) < 2:
        return []

    tree = _safe_tree(source)
    aliases = _module_aliases(tree)

    start = match.start("prefix")
    values = []
    if base:
        symbols = _expression_symbols(
            base, aliases, tree, before.count("\n") + 1
        )
        for name, kind, signature, doc in symbols:
            if prefix and not name.casefold().startswith(prefix.casefold()):
                continue
            values.append(_completion_record(
                name, kind, signature, doc, start, cursor_position
            ))
    else:
        candidates = {}
        for name in keyword.kwlist:
            candidates[name] = ("keyword", "Python keyword")
        for name in dir(builtins):
            if not name.startswith("_"):
                value = getattr(builtins, name)
                candidates[name] = (
                    "class" if isinstance(value, type) else "builtin",
                    "Python built-in",
                )
        for alias, module_name in aliases.items():
            candidates[alias] = (
                "module",
                "Python standard library" if module_name in _STDLIB_MODULES
                else module_name,
            )
        if tree:
            for node in ast.walk(tree):
                name = getattr(node, "name", "")
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and name:
                    candidates[name] = (
                        "class" if isinstance(node, ast.ClassDef) else "function",
                        _node_signature(node),
                    )
                elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                    candidates[node.id] = ("variable", "Local name")
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    for imported in node.names:
                        candidates[imported.asname or imported.name.split(".")[0]] = (
                            "module", "Imported name"
                        )
        for name, (kind, detail) in candidates.items():
            if prefix and not name.casefold().startswith(prefix.casefold()):
                continue
            values.append(_completion_record(
                name, kind, detail, "", start, cursor_position
            ))
    values.sort(key=lambda item: (
        not item["label"].casefold().startswith(prefix.casefold()),
        item["label"].casefold(),
    ))
    return values[:200]


