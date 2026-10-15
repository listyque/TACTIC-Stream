"""Handler filename filter/pattern preparation; upload IO is validated by the command."""
import os, re

def _split_patterns(value: str) -> list[str]:
    return [
        part.strip() for part in str(value or "").split(",")
        if part.strip()
    ]

def _path_allowed(path: str, options: dict) -> bool:
    name = os.path.basename(path)
    if any(
        name.casefold().endswith(value.casefold())
        for value in _split_patterns(options.get("ignore", ""))
    ):
        return False
    filters = _split_patterns(options.get("filter", ""))
    if not filters:
        return True
    for value in filters:
        if value.startswith("/") and value.endswith("/"):
            try:
                if re.search(value[1:-1], name):
                    return True
            except re.error:
                continue
        elif value.casefold() in name.casefold():
            return True
    return False

def _rule_tags(path: str, pattern: str) -> tuple[dict, dict] | None:
    pattern = str(pattern or "").replace("\\", "/")
    if not pattern:
        return {}, {}
    token_re = re.compile(r"\{(?:(sobject|snapshot)\.)?([A-Za-z_]\w*)\}")
    parts = []
    tokens = []
    cursor = 0
    for index, match in enumerate(token_re.finditer(pattern)):
        parts.append(re.escape(pattern[cursor:match.start()]))
        group = f"ingest_{index}"
        parts.append(f"(?P<{group}>.+)")
        tokens.append((group, match.group(1) or "sobject", match.group(2)))
        cursor = match.end()
    if not tokens:
        normalized = path.replace("\\", "/")
        return ({}, {}) if pattern in {
            normalized, os.path.basename(normalized),
        } else None
    parts.append(re.escape(pattern[cursor:]))
    expression = re.compile("^" + "".join(parts) + "$", re.IGNORECASE)
    normalized = path.replace("\\", "/")
    candidates = (
        (normalized, os.path.basename(normalized))
        if "/" in pattern
        else (os.path.basename(normalized), normalized)
    )
    match = expression.match(candidates[0]) or expression.match(candidates[1])
    if not match:
        return None
    sobject_values = {}
    snapshot_values = {}
    for group, owner, name in tokens:
        target = snapshot_values if owner == "snapshot" else sobject_values
        target[name] = match.group(group)
    return sobject_values, snapshot_values

def prepare_ingest_path(path: str, options: dict) -> dict:
    if not _path_allowed(path, options):
        return {"accepted": False, "reason": "Filtered by ingest rule"}
    extra_data = dict(options.get("extraData") or {})
    context = str(options.get("context") or "publish")
    if options.get("usePattern") and options.get("pattern"):
        tags = _rule_tags(path, str(options["pattern"]))
        if tags is None:
            return {
                "accepted": False,
                "reason": "Does not match ingest rule",
            }
        sobject_values, snapshot_values = tags
        extra_data.update(sobject_values)
        context = str(snapshot_values.get("context") or context)
    return {
        "accepted": True,
        "extraData": extra_data,
        "context": context,
    }
