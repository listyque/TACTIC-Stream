"""Read every table-widget reference without executing configured scripts."""

import argparse
import ast
import html
import json
import re
import sqlite3
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from tactic_stream.server.table_cells import WIDGETS

OUT = Path(__file__).parent / "output"
LEGACY = ROOT / "reports/table-view-2026-10-13/source_inventory.json"


def sources():
    for path in sorted(
        (ROOT / "src/tactic_stream/config/search_type/widget").rglob("*.xml")
    ):
        yield path.relative_to(ROOT).as_posix(), path.read_text(encoding="utf-8-sig")
    for block in (
        (ROOT.parent / "cg/config_widget_config.spt")
        .read_text(encoding="utf-8-sig")
        .split("#-- Start Entry --#")
    ):
        if not block.strip():
            continue
        fields = {}
        for node in ast.walk(ast.parse(block)):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "set_value"
                and len(node.args) == 2
            ):
                fields[ast.literal_eval(node.args[0])] = ast.literal_eval(node.args[1])
        if fields.get("config"):
            yield (
                "cg:" + str(fields.get("search_type")) + "/" + str(fields.get("view")),
                fields["config"],
            )


def database_sources(path):
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        if not db.execute(
            "SELECT name FROM sqlite_master WHERE name='spt_widget_config'"
        ).fetchone():
            return
        for code, kind, view, status, xml in db.execute(
            "SELECT code,search_type,view,s_status,config FROM spt_widget_config"
        ):
            if xml:
                yield (
                    path.name
                    + ":"
                    + str(kind)
                    + "/"
                    + str(view)
                    + "/"
                    + str(code)
                    + (" [retired]" if status == "retired" else ""),
                    xml,
                )


def inventory(databases=()):
    catalog = json.loads(LEGACY.read_text(encoding="utf-8"))
    aliases = {row["alias"]: row["handler"] for row in catalog["catalog"]}
    names = {row["class"] for row in catalog["classes"]} | {
        cls.__name__ for cls in WIDGETS.values()
    }
    definitions = catalog["classes"]

    def canonical(handler):
        name = handler.rsplit(".", 1)[-1]
        for prefix in (
            [handler.rsplit(".", 1)[0]]
            if "." in handler
            else ["pyasm.widget", "tactic.ui.table", "tactic.ui.common"]
        ):
            candidates = [
                row["qualified_class"]
                for row in definitions
                if row["class"] == name
                and (row["module"] == prefix or row["module"].startswith(prefix + "."))
            ]
            if len(candidates) == 1:
                return candidates[0]
        return handler

    unfinished = {
        "SnapshotServerElementWdg": "The original class is an empty placeholder.",
        "PublishElementWdg": "The original CG application class only returns an unbound text area.",
        "WikiElementWdg": "The original explicitly describes its wiki implementation as unfinished.",
    }
    rows, issues, count = {}, [], 0
    all_sources = list(sources())
    for path in databases:
        all_sources.extend(database_sources(path))
    for source, xml in all_sources:
        count += 1
        try:
            tree = ET.fromstring(xml)
        except (ET.ParseError, TypeError) as error:
            issues.append(dict(source=source, reason=str(error)))
            continue
        parents = {child: parent for parent in tree.iter() for child in parent}
        for node in tree.iter():
            refs = []
            if node.get("class"):
                refs.append(node.get("class"))
            if node.get("widget") in aliases:
                refs.append(aliases[node.get("widget")])
            if node.tag in ("dynamic_class", "class_name") and node.text:
                refs.append(node.text.strip())
            for text in (node.text, node.tail):
                if text:
                    refs.extend(
                        re.findall(
                            r"\b(?:tactic\.ui|pyasm\.(?:widget|prod))\.[\w.]+(?:Wdg|TableElement)\b",
                            text,
                        )
                    )
            for handler in refs:
                name = handler.rsplit(".", 1)[-1]
                if name not in names and handler not in WIDGETS:
                    continue
                widget = WIDGETS.get(handler)
                key = (
                    widget.__module__ + "." + widget.__name__
                    if widget
                    else canonical(handler)
                )
                status = "adapted" if widget else "pending"
                reason = (
                    "A typed adapter exists; this does not certify every legacy option."
                    if widget
                    else "A native portable implementation and its workflow examples are still required."
                )
                if handler.startswith("pyasm.prod."):
                    status, reason = (
                        "excluded-production",
                        "Previously excluded obsolete pyasm.prod subsystem.",
                    )
                elif name in unfinished:
                    status, reason = "excluded-unfinished", unfinished[name]
                parts, current = [], node
                while current is not None:
                    parts.append(
                        current.tag
                        + (
                            "[" + current.get("name") + "]"
                            if current.get("name")
                            else ""
                        )
                    )
                    current = parents.get(current)
                use = dict(
                    source=source,
                    location="/".join(reversed(parts)),
                    options=sorted(child.tag for child in node),
                )
                row = rows.setdefault(
                    key,
                    dict(
                        widget=key, handlers=[], status=status, reason=reason, uses=[]
                    ),
                )
                if handler not in row["handlers"]:
                    row["handlers"].append(handler)
                if use not in row["uses"]:
                    row["uses"].append(use)
    return dict(
        sources=count,
        issues=issues,
        widgets=sorted(rows.values(), key=lambda row: row["widget"]),
        rule="Every mention counts. An adapter is not proof of complete option support. Local databases are read-only.",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", action="append", type=Path, default=[])
    args = parser.parse_args()
    result = inventory(args.database)
    result["counts"] = dict(Counter(row["status"] for row in result["widgets"]))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "inventory.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    rows = []
    for row in result["widgets"]:
        uses = "".join(
            "<li>" + html.escape(use["source"] + " → " + use["location"]) + "</li>"
            for use in row["uses"]
        )
        rows.append(
            "<tr><td><code>"
            + html.escape(row["widget"])
            + "</code></td><td>"
            + html.escape(row["status"])
            + "</td><td>"
            + html.escape(row["reason"])
            + "<details><summary>References: "
            + str(len(row["uses"]))
            + "</summary><ul>"
            + uses
            + "</ul></details></td></tr>"
        )
    page = (
        '<!doctype html><meta charset="utf-8"><title>Frame table inventory</title><style>body{font:15px/1.5 system-ui;margin:24px;background:#24292e;color:#e5e9ed}td,th{padding:10px;border-bottom:1px solid #667077;text-align:left;vertical-align:top}code{overflow-wrap:anywhere}</style><h1>Table widget references</h1><p>'
        + html.escape(result["rule"])
        + "</p><p>"
        + html.escape(json.dumps(result["counts"]))
        + "</p><table><tr><th>Widget</th><th>Status</th><th>Evidence / remaining work</th></tr>"
        + "".join(rows)
        + "</table>"
    )
    (OUT / "inventory.html").write_text(page, encoding="utf-8")
    print(
        json.dumps(
            dict(sources=result["sources"], counts=result["counts"]), ensure_ascii=False
        )
    )


if __name__ == "__main__":
    main()
