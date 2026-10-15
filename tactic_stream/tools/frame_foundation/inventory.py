"""Inventory UI declarations and registered entry points without running the apps.

Source discovery is exhaustive within the scanned product directories. Dynamic
script/plugin UI and runtime modality require the listed entry owners to be tested.
"""

import argparse
import ast
import hashlib
import html
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
TOKENS = re.compile(
    r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`(?:\\.|[^`\\])*`|//[^\n]*|/\*.*?\*/', re.S
)
OBJECTS = re.compile(r"\b([A-Z]\w*(?:\.[A-Z]\w*)*)\s*\{")
POPUPS = {"Popup", "Menu", "Dialog", "ToolTip"}
WINDOWS = {"Window", "ApplicationWindow"}


def masked(source):
    return TOKENS.sub(lambda match: re.sub(r"[^\n]", " ", match.group()), source)


def phase(file):
    """Suggested work queue, never a readiness claim."""
    lower = file.lower()
    for name, number in [
        ("tactic_frame", 0),
        ("/frame/", 0),
        ("/controls/", 1),
        ("/shell/", 2),
        ("/administration/", 3),
        ("/configuration/", 5),
        ("/projects/", 5),
        ("/interface/", 6),
        ("/workspace/", 2),
        ("/objects/", 7),
        ("/tasks/", 8),
        ("/messages/", 9),
        ("/activity/", 9),
        ("/fileworkspace/", 10),
        ("/checkin/", 10),
        ("/scripts/", 11),
        ("/help/", 4),
        ("/debug/", 4),
        ("/connection/", 4),
        ("/users/", 4),
    ]:
        if name in lower:
            return number
    stem = Path(file).stem.lower()
    if stem in ("main", "dockhost", "dockpanel", "navigationdrawer", "sectiontabrail"):
        return 2
    for names, number in [
        (
            (
                "admin",
                "security",
                "namingeditor",
                "columnseditor",
                "layouteditor",
                "rawcell",
            ),
            3,
        ),
        (("configuration", "settings", "project", "repositoryeditor"), 5),
        (
            (
                "help",
                "error",
                "debug",
                "uiperformance",
                "userprofile",
                "serverpresets",
                "update",
            ),
            4,
        ),
        (("search", "filter", "tag", "query"), 6),
        (("task", "milestone"), 8),
        (("message", "notification", "activity", "communication"), 9),
        (
            (
                "commit",
                "dropplate",
                "file",
                "repositorysync",
                "ingest",
                "matching",
                "screenshot",
                "watchfolder",
            ),
            10,
        ),
        (("script", "database", "handler", "dcc"), 11),
    ]:
        if any(stem.startswith(name) for name in names):
            return number
    return 12


def native_inventory(handler):
    qml = handler / "thlib/ui/qml"
    sources = {
        path: path.read_text(encoding="utf-8") for path in sorted(qml.rglob("*.qml"))
    }
    clean = {path: masked(source) for path, source in sources.items()}
    root_by_path = {
        path: next(iter(OBJECTS.finditer(source)), None)
        for path, source in clean.items()
    }
    roots = {path.stem: value for path, value in root_by_path.items()}
    for index in qml.rglob("qmldir"):
        for name, target in re.findall(
            r"(?m)^(?:singleton\s+)?(\w+)\s+(?:\d+\.\d+\s+)?(\S+\.qml)\s*$",
            index.read_text(encoding="utf-8"),
        ):
            roots[name] = root_by_path.get(index.parent / target)

    def surface_type(name):
        seen = set()
        while name not in seen:
            seen.add(name)
            if name in POPUPS:
                return "menu/popover"
            if name in WINDOWS:
                return "window"
            match = roots.get(name)
            if not match:
                return None
            name = match.group(1).split(".")[-1]
        return None

    files, surfaces, dynamic = [], [], []
    for path, source in sources.items():
        file = path.relative_to(handler).as_posix()
        declarations = list(OBJECTS.finditer(clean[path]))
        files.append(
            dict(
                file=file,
                root=declarations[0].group(1) if declarations else "",
                frameView=bool(re.search(r"\b(?:Frame\.)?FrameView\s*\{", clean[path])),
                sharedRules="tactic_frame/" in source,
                phase=phase(file),
            )
        )
        for declaration in declarations:
            if declaration.group(1).split(".")[-1] == "Loader":
                dynamic.append(
                    dict(
                        file=file,
                        line=source.count("\n", 0, declaration.start()) + 1,
                        type="dynamic-loader",
                        entry="Loader",
                    )
                )
            kind = surface_type(declaration.group(1).split(".")[-1])
            if kind:
                surfaces.append(
                    dict(
                        file=file,
                        line=source.count("\n", 0, declaration.start()) + 1,
                        type=kind,
                        tag=declaration.group(1),
                    )
                )
        for match in re.finditer(
            r"\b(?:createQmlObject|createComponent|setSource)\s*\(", clean[path]
        ):
            dynamic.append(
                dict(
                    file=file,
                    line=source.count("\n", 0, match.start()) + 1,
                    type="dynamic-component",
                    entry=match.group().split("(")[0].strip(),
                )
            )

    registry = handler / "thlib/ui/workspace_models/windows.py"
    tree = ast.parse(registry.read_text(encoding="utf-8"))
    model = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "FloatingWindowModel"
    )
    assignments = {
        target.id: (node.value, node.lineno)
        for node in model.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }
    mapping, line = assignments["_content_sources"]
    windows = []
    for key, value in zip(mapping.keys, mapping.values):
        kind, target = ast.literal_eval(key), ast.literal_eval(value)
        assert (qml / target).resolve().is_relative_to(qml.resolve()), (
            f"External registered window source: {kind}"
        )
        assert (qml / target).is_file(), f"Missing registered window: {kind}: {target}"
        windows.append(
            dict(
                kind=kind,
                file="thlib/ui/qml/" + target,
                entry=registry.relative_to(handler).as_posix(),
                line=key.lineno,
                phase=phase("/" + target),
            )
        )
    pages, line = assignments["_configuration_pages"]
    assert (
        isinstance(pages, ast.Call)
        and isinstance(pages.func, ast.Name)
        and pages.func.id == "frozenset"
    )
    configuration = [
        dict(
            kind=kind,
            file="thlib/ui/qml/ConfigurationView.qml",
            entry=registry.relative_to(handler).as_posix(),
            line=line,
        )
        for kind in sorted(ast.literal_eval(pages.args[0]) if pages.args else [])
    ]
    registry = qml / "shell/docks/DockContentRegistry.qml"
    text = masked(sources[registry])
    targets = {
        match.group(1): match.group(2)
        for match in re.finditer(
            r"Component\s*\{\s*id:\s*(\w+)\s+([A-Z]\w*)\s*\{", text
        )
    }
    docks = []
    for match in re.finditer(
        r"readonly\s+property\s+Component\s+(\w+)\s*:\s*(\w+)", text
    ):
        target = targets[match.group(2)]
        docks.append(
            dict(
                kind=match.group(1),
                component=target,
                entry=registry.relative_to(handler).as_posix(),
                line=text.count("\n", 0, match.start()) + 1,
            )
        )
    python_sources = sorted((handler / "thlib/ui").rglob("*.py"))
    for path in python_sources:
        for call in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(call, ast.Call):
                continue
            name = (
                call.func.id
                if isinstance(call.func, ast.Name)
                else call.func.attr
                if isinstance(call.func, ast.Attribute)
                else ""
            )
            if name in ("QQmlApplicationEngine", "QQuickView", "QQmlComponent"):
                dynamic.append(
                    dict(
                        file=path.relative_to(handler).as_posix(),
                        line=call.lineno,
                        type="python-qml-entry",
                        entry=name,
                    )
                )
    defaults = []
    records = handler / "thlib/ui/workspace_models/docks_records.py"
    if records.is_file():
        for call in ast.walk(ast.parse(records.read_text(encoding="utf-8"))):
            if (
                isinstance(call, ast.Call)
                and isinstance(call.func, ast.Name)
                and call.func.id == "DockPanel"
                and len(call.args) >= 3
            ):
                if all(
                    isinstance(value, ast.Constant) and isinstance(value.value, str)
                    for value in call.args[:3]
                ):
                    identity, title, kind = [value.value for value in call.args[:3]]
                    defaults.append(
                        dict(
                            kind=kind,
                            name=title,
                            id=identity,
                            entry=records.relative_to(handler).as_posix(),
                            line=call.lineno,
                        )
                    )
    return dict(
        files=files,
        surfaces=surfaces,
        windows=windows,
        configuration=configuration,
        docks=docks,
        dockDefaults=defaults,
        dynamic=dynamic,
        hashes={
            path.relative_to(handler).as_posix(): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in [*sources, *qml.rglob("qmldir"), *python_sources]
        },
    )


def report(data, output):
    entries = []
    for product in ("handler", "stream"):
        part = data[product]
        for category in (
            "windows",
            "configuration",
            "docks",
            "dockDefaults",
            "surfaces",
            "dynamic",
            "files",
        ):
            for entry in part.get(category, []):
                entries.append(dict(product=product, category=category, **entry))
    rows = "".join(
        "<tr>"
        + "".join(
            "<td>" + html.escape(str(entry.get(field, ""))) + "</td>"
            for field in (
                "product",
                "category",
                "kind",
                "tag",
                "file",
                "entry",
                "line",
                "phase",
            )
        )
        + "</tr>"
        for entry in entries
    )
    output.write_text(
        """<!doctype html><meta charset="utf-8"><title>Frame UI source inventory</title>
<style>body{font:14px Segoe UI,sans-serif;background:#202426;color:#eee;margin:24px}
input{padding:12px;width:70%;background:#303638;color:inherit;border:1px solid #789}
table{border-collapse:collapse;table-layout:fixed;margin-top:20px;width:100%}
td,th{border-bottom:1px solid #495055;padding:7px;text-align:left;overflow-wrap:anywhere;vertical-align:top}
th{position:sticky;top:0;background:#303638}code,a{color:#9cd}
th:nth-child(1){width:6%}th:nth-child(2){width:9%}th:nth-child(3){width:13%}th:nth-child(4){width:11%}
th:nth-child(5){width:23%}th:nth-child(6){width:23%}th:nth-child(7){width:4%}th:nth-child(8){width:7%}</style>
<h1>Frame UI inventory · preparation gate</h1>
<p>Source declarations and registered entry points. Frame references do not mean migration or original parity is complete.</p>
<p>Dynamic script/plugin UI requires runtime verification; DCC configuration pages use the existing connector registry.
Qt declarations use a comment/string-masked source scan. Vue declarations use the installed compiler AST.</p>
<p><a href="inventory.json">Machine-readable sources and hashes</a></p>
<input id="filter" placeholder="Filter product, kind, source, category or phase"><p id="count"></p>
<table><thead><tr><th>Product</th><th>Category</th><th>Kind</th><th>Type</th><th>Source</th><th>Entry owner</th><th>Line</th><th>Suggested phase</th></tr></thead><tbody>"""
        + rows
        + """</tbody></table><script>
const rows=[...document.querySelectorAll('tbody tr')], count=document.querySelector('#count');
function filter(){const query=document.querySelector('#filter').value.toLowerCase();let visible=0;
for(const row of rows){row.hidden=!row.textContent.toLowerCase().includes(query);if(!row.hidden)visible++;}
count.textContent=visible+' / '+rows.length+' entries';}document.querySelector('#filter').addEventListener('input',filter);filter();
</script>""",
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handler-root", type=Path, required=True)
    args = parser.parse_args()
    native = native_inventory(args.handler_root.resolve())
    result = subprocess.run(
        ["node", str(HERE / "inventory_web.mjs"), str(ROOT)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    web = json.loads(result.stdout)
    for file in web["files"]:
        file["phase"] = phase("/" + file["file"])
    for surface in web["surfaces"]:
        surface["phase"] = phase("/" + surface["file"])
    web["hashes"] = {
        file: hashlib.sha256((ROOT / file).read_bytes()).hexdigest()
        for file in [
            *(entry["file"] for entry in web["files"]),
            "frontend/src/features/workspace/docks.js",
        ]
    }
    data = dict(
        handler=native,
        stream=web,
        originalHandler="fa3f594c5cd09ce565ea14acb533302e79c9308a",
        limits=[
            "Static declarations are not proof of runtime modality or feature readiness.",
            "User QML, connector-defined pages and configured/script-generated UI require runtime input.",
        ],
    )
    output = HERE / "output"
    output.mkdir(parents=True, exist_ok=True)
    (output / "inventory.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    report(data, output / "inventory.html")
    print(
        json.dumps(
            {
                product: {
                    key: len(value)
                    for key, value in part.items()
                    if isinstance(value, list)
                }
                for product, part in (("handler", native), ("stream", web))
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
