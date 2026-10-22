"""Build a source-linked UI atlas; source presence is never a readiness claim."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent / "frame_foundation"))
from inventory import OBJECTS, masked  # noqa: E402
from report import verify_sources  # noqa: E402
from report_variants import verify_sources as verify_variants  # noqa: E402

QT_TYPES = {
    "Button",
    "ToolButton",
    "RoundButton",
    "RadioButton",
    "CheckBox",
    "Switch",
    "TextField",
    "TextArea",
    "TextInput",
    "TextEdit",
    "ComboBox",
    "SpinBox",
    "Slider",
    "RangeSlider",
    "Dial",
    "Menu",
    "MenuItem",
    "Popup",
    "Dialog",
    "ToolTip",
    "TabButton",
    "TabBar",
    "ProgressBar",
    "BusyIndicator",
}
INFRA_NAMES = {
    "PopupAction",
    "PopupCoordinator",
    "HoverReleaseCoordinator",
    "ActivationHandler",
    "MaterialRipple",
    "TreeExpansionMotion",
    "DockDragGrip",
    "ResizeGripVisual",
    "DockGrip",
    "WindowControls",
    "MobilePage",
    "UserFilter",
    "NavigationDrawer",
    "TaskEditorReleaseCoordinator",
    "WorkspaceTabInput",
    "DccSettingField",
}


def native_sources(handler):
    base = handler / "thlib/ui/qml"
    files, uses = [], []
    for path in sorted(base.rglob("*.qml")):
        source = path.read_text(encoding="utf-8")
        clean = masked(source)
        file = path.relative_to(handler).as_posix()
        imports = {}
        for match in re.finditer(
            r'^\s*import\s+"([^"]+)"(?:\s+as\s+(\w+))?', source, re.M
        ):
            directory = (path.parent / match[1]).resolve()
            if directory.is_relative_to(handler):
                imports[match[2] or ""] = directory
        modules = dict(
            re.findall(r"^\s*import\s+(Qt\S+)(?:\s+[\d.]+)?\s+as\s+(\w+)", source, re.M)
        )
        qt_aliases = {alias: module for module, alias in modules.items()}

        def resolve(tag):
            alias, _, name = tag.rpartition(".")
            if alias in qt_aliases:
                return qt_aliases[alias], "qt"
            directories = [imports[alias]] if alias in imports else []
            if not alias:
                directories = [path.parent, *([imports[""]] if "" in imports else [])]
            for directory in directories:
                target = directory / (name + ".qml")
                index = directory / "qmldir"
                if index.exists():
                    mapping = re.search(
                        r"(?m)^(?:singleton\s+)?"
                        + re.escape(name)
                        + r"\s+(?:\d+\.\d+\s+)?(\S+\.qml)\s*$",
                        index.read_text(encoding="utf-8"),
                    )
                    if mapping:
                        target = directory / mapping[1]
                if target.is_file():
                    return target.resolve().relative_to(handler).as_posix(), "house"
            return (
                ("Qt / context import", "qt")
                if name in QT_TYPES
                else ("unresolved / Qt primitive", "unresolved")
            )

        declarations = {match.end() - 1: match for match in OBJECTS.finditer(clean)}
        root_match = next(iter(declarations.values()), None)
        stack = []
        for index, char in enumerate(clean):
            if char == "{":
                match = declarations.get(index)
                parent = next((entry for entry in reversed(stack) if entry), None)
                if match:
                    tag = match[1]
                    resolved, origin = resolve(tag)
                    row = dict(
                        file=file,
                        line=source.count("\n", 0, match.start()) + 1,
                        tag=tag,
                        parent=parent["tag"] if parent else "",
                        resolved=resolved,
                        origin=origin,
                        props={},
                    )
                    uses.append(row)
                    stack.append(row)
                else:
                    stack.append(None)
            elif char == "}" and stack:
                stack.pop()
            elif char == ":" and stack and stack[-1]:
                start = clean.rfind("\n", 0, index) + 1
                key = clean[start:index].strip()
                if re.fullmatch(r"[\w.]+", key) and re.search(
                    r"id$|text$|icon|size|height|width|padding|spacing|radius|font|color|checked|enabled|compact|prominent|highlight|value|stepSize|orientation|title",
                    key,
                    re.I,
                ):
                    end = source.find("\n", index)
                    stack[-1]["props"][key] = source[
                        index + 1 : end if end >= 0 else len(source)
                    ].strip()[:220]
        files.append(
            dict(
                file=file,
                name=path.stem,
                kind="component",
                root=root_match[1] if root_match else "",
            )
        )
    for path in sorted((base / "controls").glob("*.js")):
        files.append(
            dict(
                file=path.relative_to(handler).as_posix(), name=path.name, kind="helper"
            )
        )
    return dict(files=files, uses=uses, styles=[], frames=[])


def family_for(tag, props, registry):
    stem = tag.rsplit(".", 1)[-1]
    exact = [
        family["id"] for family in registry if stem in family["native"] + family["vue"]
    ]
    if exact:
        return exact
    aliases = {
        "button": "buttons",
        "ToolButton": "buttons",
        "RoundButton": "buttons",
        "RadioButton": "toggles",
        "input": "text-fields",
        "textarea": "text-fields",
        "TextInput": "text-fields",
        "TextEdit": "text-fields",
        "select": "choices",
        "TabBar": "tabs",
        "header": "headers",
        "ProgressBar": "feedback",
        "progress": "feedback",
        "ListView": "lists",
        "TreeView": "lists",
        "TableView": "tables",
        "table": "tables",
        "ScrollView": "scroll-layout",
        "Flickable": "scroll-layout",
        "Text": "typography",
        "Label": "typography",
        "Image": "previews",
        "img": "previews",
        "MenuItem": "menus",
        "dialog": "popups",
        "details": "menus",
        "summary": "menus",
    }
    if stem == "input":
        kind = props.get("type", "text")
        if kind in ("checkbox", "radio"):
            return ["toggles"]
        if kind in ("number", "range"):
            return ["numbers"]
        if kind in ("date", "time", "datetime-local"):
            return ["dates"]
        if kind == "file":
            return ["drag-files"]
    if stem in aliases:
        return [aliases[stem]]
    # Hints locate inline fragments; they never establish a new base component.
    text = " ".join([tag, props.get("class", ""), props.get("id", "")]).lower()
    return [
        family["id"]
        for family in registry
        if any(token in text for token in family["tokens"])
    ]


def classify(row, engine, registry, feature_roots):
    families = [family for family in registry if row["name"] in family[engine]]
    if row["kind"] in ("helper", "style"):
        return (
            "infrastructure",
            "Implementation helper / stylesheet",
            [f["id"] for f in families],
        )
    if row["kind"] == "frame-module":
        level = "feature" if "/features/" in row["file"] else "infrastructure"
        return (
            level,
            "Shared declaration or state module, not an extra native control",
            [],
        )
    if any(f["level"] == "feature" for f in families):
        return (
            "feature",
            "Reviewed domain fragment: owns scenario semantics",
            [f["id"] for f in families],
        )
    if (
        row["name"] in INFRA_NAMES
        or "/frame/" in row["file"]
        or "/tactic_frame/" in row["file"]
    ):
        return (
            "infrastructure",
            "Renderer / input / host mechanism",
            [f["id"] for f in families],
        )
    if families:
        return (
            families[0]["level"],
            "Reviewed reusable family; membership is not a 1:1 counterpart claim",
            [f["id"] for f in families],
        )
    if row["name"] in feature_roots.get(engine, []):
        return (
            "feature",
            "Reviewed scenario / domain data contract, not a neutral control",
            [],
        )
    if "/controls/" in row["file"]:
        raise AssertionError(
            "House component missing from reviewed registry: " + row["file"]
        )
    if "/shell/" in row["file"] or row["name"] in ("Main", "App", "Theme"):
        return "infrastructure", "Application shell or window host", []
    if "/features/" in row["file"]:
        return (
            "feature",
            "Feature-owned implementation; extraction candidates remain visible",
            [],
        )
    return (
        "review",
        "Outside the reviewed kit; responsibility needs inspection, not inference from its filename",
        [],
    )


def baseline_samples(handler):
    result = {}
    paths = [HERE / "output" / name for name in ("qml.json", "vue.json")]
    if not all(path.is_file() for path in paths):
        return {}, "Парные снимки ещё не сняты."
    native, browser = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    try:
        verify_sources(native, browser, handler)
    except (AssertionError, FileNotFoundError) as error:
        return (
            {},
            "Снимки пропущены: исходники изменились после парной проверки. "
            + str(error),
        )
    for product, name in (("native", "qml.json"), ("vue", "vue.json")):
        path = HERE / "output" / name
        if not path.exists():
            continue
        for capture in json.loads(path.read_text(encoding="utf-8"))["captures"]:
            if not (
                capture["style"] == "md3"
                and capture["mode"] == "dark"
                and capture["language"] == "en"
                and capture["width"] == 900
                and capture["state"] == "idle"
            ):
                continue
            for key, box in capture["boxes"].items():
                if (
                    box["width"] > 0
                    and box["height"] > 0
                    and box["y"] >= 0
                    and box["y"] + box["height"] <= 900
                ):
                    result.setdefault(key, {}).setdefault(
                        product, dict(image=capture["image"], **box)
                    )
    return (
        result,
        "Показанные вырезки соответствуют текущим отпечаткам парной проверки.",
    )


def samples(handler):
    result, note = baseline_samples(handler)
    paths = [
        HERE / "output/variants" / name for name in ("native.json", "browser.json")
    ]
    if not all(path.is_file() for path in paths):
        return result, note
    native, browser = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    try:
        verify_variants(native, browser, handler)
    except (AssertionError, FileNotFoundError) as error:
        return result, note + " Расширенные снимки устарели: " + str(error)
    for product, data in (("native", native), ("vue", browser)):
        for capture in data["captures"]:
            if (
                capture["style"],
                capture["mode"],
                capture["language"],
                capture["width"],
            ) != ("md3", "dark", "en", 900):
                continue
            result.setdefault(capture["id"], {})[product] = dict(
                image="variants/" + capture["image"], **capture["boxes"]["sample"]
            )
    return (
        result,
        note + " Расширенные примеры сверены с текущими отпечатками исходников.",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handler-root", type=Path, default=Path("D:/grav/Tactic Stream/TH"))
    args = parser.parse_args()
    registry = json.loads((HERE / "element_catalog.json").read_text(encoding="utf-8"))
    families = registry["families"]
    assert len({f["id"] for f in families}) == len(families)
    fixture = 'Button { text: "} Fake {" // X {\n}'
    assert [match[1] for match in OBJECTS.finditer(masked(fixture))] == ["Button"]
    assert len(masked(fixture)) == len(fixture)
    native = native_sources(args.handler_root.resolve())
    web = json.loads(
        subprocess.run(
            ["node", str(HERE / "element_sources.mjs"), str(ROOT)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        ).stdout
    )
    for engine, data in (("native", native), ("vue", web)):
        names = {row["name"] for row in data["files"] if row["kind"] == "component"}
        reviewed = {name for family in families for name in family[engine]}
        assert reviewed <= names, (engine, "Missing registry sources", reviewed - names)
        assert set(registry.get("reviewedFeatureRoots", {}).get(engine, [])) <= names
    entries = []
    hashes = {}
    for engine, data, base in (
        ("native", native, args.handler_root),
        ("vue", web, ROOT),
    ):
        by_file = {}
        for row in data["files"]:
            level, reason, family = classify(
                row, engine, families, registry.get("reviewedFeatureRoots", {})
            )
            if row["kind"] == "component" and row["name"] in registry.get(
                "levelOverrides", {}
            ):
                level = registry["levelOverrides"][row["name"]]
                reason = "Reviewed component responsibility; a family may contain different control levels"
            entry = dict(
                engine=engine,
                category="source",
                level=level,
                reason=reason,
                families=family,
                tag=row["name"],
                line=1,
                uri=(base / row["file"]).resolve().as_uri(),
                **row,
            )
            by_file[row["file"]] = entry
            entries.append(entry)
            hashes[engine + ":" + row["file"]] = hashlib.sha256(
                (base / row["file"]).read_bytes()
            ).hexdigest()
        for category in ("uses", "styles", "frames"):
            for row in data[category]:
                owner = by_file[row["file"]]
                families_for_use = family_for(row["tag"], row["props"], families)
                resolved = by_file.get(row.get("resolved", ""))
                level = (
                    resolved["level"]
                    if resolved
                    else "infrastructure"
                    if category == "styles"
                    else "review"
                )
                candidate = owner["level"] in ("feature", "review") and (
                    row.get("origin") == "qt"
                    or row["tag"] in {"button", "input", "select", "textarea"}
                )
                entries.append(
                    dict(
                        engine=engine,
                        category=category,
                        level=level,
                        ownerLevel=owner["level"],
                        families=families_for_use,
                        candidate=candidate,
                        uri=owner["uri"],
                        **row,
                    )
                )
    counts = {
        engine: {
            kind: sum(row["kind"] == kind for row in data["files"])
            for kind in ("component", "helper", "style", "frame-module")
        }
        for engine, data in (("native", native), ("vue", web))
    }
    for engine, data, prefix in (
        ("native", native, "thlib/ui/qml/controls/"),
        ("vue", web, "frontend/src/controls/"),
    ):
        counts[engine]["houseComponents"] = sum(
            row["kind"] == "component" and row["file"].startswith(prefix)
            for row in data["files"]
        )
    counts["levels"] = dict(
        Counter(
            row["level"]
            for row in entries
            if row["category"] == "source" and row["kind"] == "component"
        )
    )
    counts["declarations"] = dict(Counter(row["category"] for row in entries))
    assert any(row.get("origin") == "house" for row in entries)
    assert any(row.get("origin") == "qt" for row in entries)
    for name, expected in (
        ("ProjectFilterToggles", "feature"),
        ("SettingRow", "composite"),
        ("UserFilter", "infrastructure"),
    ):
        assert all(
            row["level"] == expected
            for row in entries
            if row["category"] == "source" and row["tag"] == name
        )
    previews, evidence = samples(args.handler_root)
    result = dict(
        **registry,
        entries=entries,
        counts=counts,
        samples=previews,
        evidence=evidence,
        sha256=hashes,
    )
    out = HERE / "output"
    out.mkdir(exist_ok=True)
    (out / "ui-elements.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    payload = json.dumps(result, ensure_ascii=False).replace("<", "\\u003c")
    page = (
        (HERE / "elements.html")
        .read_text(encoding="utf-8")
        .replace("__DATA__", payload)
    )
    (out / "ui-elements.html").write_text(page, encoding="utf-8")
    print(json.dumps(counts, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
