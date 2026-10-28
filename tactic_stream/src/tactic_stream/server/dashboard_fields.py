"""Record bindings and compact native EditWdg forms for configured pages."""

import hashlib
import json
import re

from pyasm.search import SearchType
from pyasm.common.errors import SecurityException
from pyasm.widget import WidgetConfigView
from .interface import _require_table_access, read_form


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, default=str).encode()
    ).hexdigest()


def form(block, source):
    names = block.fields
    if not names:
        return dict(
            readOnly=True,
            fields=[],
            hint="Select fields from the existing native edit view.",
        )
    if len(set(names)) != len(names) or any(
        not re.fullmatch(r"[A-Za-z_][\w.-]{0,127}", name) for name in names
    ):
        raise ValueError("Choose distinct fields from the native edit view")
    search_type = source.get_base_search_type()
    _require_table_access(search_type)
    from .api import check_record_access

    check_record_access(search_type)
    try:
        _require_table_access(search_type, "edit")
    except SecurityException:
        columns = SearchType.get_column_info(search_type)
        if any(name not in columns for name in names):
            raise ValueError("Choose existing record fields") from None
        return dict(
            readOnly=True,
            fields=[
                dict(
                    name=name,
                    title=columns[name].get("title") or name,
                    type="text",
                    value=source.get_value(name, auto_convert=False),
                    readOnly=True,
                )
                for name in names
            ],
        )
    definition = read_form(
        search_type, block.edit_view, source.get_search_key(), element_names=names
    )
    config = WidgetConfigView.get_by_search_type(
        search_type, block.edit_view, use_cache=False
    )
    revision = digest(
        [
            block.model_dump(),
            [item.get_xml().to_string() for item in config.get_configs()],
        ]
    )
    fields = []
    for item in definition["fields"]:
        handler = item["action"]["handler"] or ""
        if handler.rsplit(".", 1)[-1] not in ("", "DatabaseAction"):
            raise ValueError("This field needs the full native record editor")
        kind = item["class_name"].rsplit(".", 1)[-1]
        control = item.get("input", {})
        mode = (
            "bool"
            if kind == "CheckboxWdg"
            else "multiline"
            if kind == "TextAreaWdg"
            else "select"
            if "choices" in item
            else control.get("type", "text")
        )
        if mode not in (
            "text",
            "multiline",
            "select",
            "bool",
            "date",
            "datetime-local",
        ):
            raise ValueError("This field needs the full native record editor")
        options = item.get("options", {})
        value = (item.get("values") or [None])[0]
        if mode == "bool":
            value = value in (True, 1, "1", "true", "on", "yes")
        if mode in ("date", "datetime-local"):
            value = control.get("value", "")
        read_only = options.get("read_only") in (True, "true") or control.get(
            "read_only", False
        )
        target = (
            item["action"]["options"].get("column")
            or options.get("column")
            or item["name"]
        )
        read_only = read_only or target in (
            "id",
            "code",
            "project_code",
            "timestamp",
            "login",
        )
        fields.append(
            dict(
                name=item["name"],
                title=item["title"],
                type=mode,
                value=value,
                readOnly=bool(read_only),
                required=options.get("required") in (True, "true"),
                options=[
                    dict(value="" if value is None else str(value), label=str(label))
                    for value, label in zip(
                        item.get("choices", []), item.get("labels", [])
                    )
                ],
                suffix=control.get("value_suffix", ""),
                unchanged=control.get("unchanged_value"),
            )
        )
    for item, field in zip(definition["fields"], fields):
        if "empty_label" in item.get("input", {}) and not any(
            option["value"] == "" for option in field["options"]
        ):
            field["options"].insert(
                0, dict(value="", label=item["input"]["empty_label"])
            )
    by_name = {item["name"]: item for item in fields}
    if set(by_name) != set(names):
        raise ValueError("Choose existing fields from the native edit view")
    return dict(
        searchKey=source.get_search_key(),
        searchType=search_type,
        view=block.edit_view,
        expectedRevision=definition["expected_revision"],
        configRevision=revision,
        readOnly=all(item["readOnly"] for item in fields),
        fields=[by_name[name] for name in names],
    )
