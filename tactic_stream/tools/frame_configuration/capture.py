"""Fresh original/current QML Configuration and projects, with source fingerprints."""

import argparse
import hashlib
import json
from pathlib import Path
import sys
import subprocess
import io
import zipfile
import base64

ROOT = Path(__file__).resolve().parents[2]
HANDLER = Path("D:/grav/Tactic Stream/TH")
sys.path[:0] = [str(HANDLER), str(ROOT / "tools/frame_admin")]

from tests.frame_configuration_fixture import Surface, SCREENS
from tests.test_sidebar_editor_qml import SidebarEditorQmlTests
from tests.frame_support_fixture import evaluate
from PySide6.QtCore import QObject, QPointF, QRect
from PySide6.QtGui import QImage, QColor
from native_capture import snapshot, source_hashes
from original_reference import extract_reference, REFERENCE, ARCHIVE

OUT = Path(__file__).resolve().parent / "output"
PREVIEW = OUT / "fixture-preview.png"
TEMPLATE_REFERENCE = ROOT / "tools/frame_foundation/reference-b05/thlib/ui/qml"
CASES = {name: ["initial"] for name in SCREENS}
CASES.update(
    wizard=[
        "initial",
        "image",
        "image_selected",
        "template",
        "review",
        "review_selected",
        "error",
        "busy",
    ],
    editor=["initial", "dirty", "image", "error"],
    templates=["initial", "selected"],
    repository_editor=["initial", "custom"],
    configuration=["initial", "dirty"],
)


def configure(surface, case, original):
    if surface.screen == "wizard":
        controller = surface.creator
        if case != "initial":
            controller._draft.update(
                title="Studio Project",
                code="studio_project",
                category="Studio",
                description="Project configuration example.",
                namespace="studio",
            )
            controller._step = {
                "image": 1,
                "image_selected": 1,
                "template": 2,
                "review": 3,
                "review_selected": 3,
                "error": 3,
                "busy": 3,
            }[case]
        if case in ("image_selected", "review_selected"):
            controller._draft["previewPath"] = str(PREVIEW)
        if case == "error":
            controller._error = (
                "Project title is required and cannot exceed 100 characters"
            )
        if case == "busy":
            controller._busy = True
        controller.stateChanged.emit()
    elif surface.screen == "editor":
        if case == "image":
            surface.editor.set_preview_path(str(PREVIEW))
        if case == "dirty":
            surface.editor.set_title("Edited project")
        if case == "error":
            surface.editor._set_error("Project name is required")
    elif surface.screen == "templates":
        if case == "selected":
            surface.view.setProperty("selectedCode", "cg_template")
    elif surface.screen == "repository_editor" and case == "custom":
        surface.view.setProperty("selectedRow", 1)
        if not original:
            surface.view.setProperty("editing", True)
    elif surface.screen == "configuration" and case == "dirty":
        values = surface.case.config.page_values("appearance")
        values["popupAnimations"] = False
        surface.case.config.update_page("appearance", values)
        surface.case.config.select_page("appearance")
    surface.settle()


def model(surface):
    screen = surface.screen
    if screen in ("server", "checkin", "global", "appearance", "cache", "tasks", "dcc"):
        result = surface.evaluate("formModel")
        result["fields"] = surface.evaluate("fields")
        return dict(module="settings", describe="describe", model=result)
    if screen == "configuration":
        # Actual body projection, independently composed again by the browser.
        body = next(
            item
            for item in surface.view.childItems()
            if item.metaObject().className().startswith("ConfigurationPage")
        )
        loader = body.childItems()[0]
        content = loader.property("item")
        result = evaluate(surface.engine, content, "formModel")
        result["fields"] = evaluate(surface.engine, content, "fields")
        return dict(
            module="configuration",
            model=surface.evaluate("frameModel"),
            child=dict(module="settings", model=result),
        )
    if screen == "wizard":
        return dict(module="wizard", describe="wizard", model=surface.evaluate("model"))
    if screen == "editor":
        return dict(module="editor", model=surface.evaluate("model"))
    if screen == "templates":
        return dict(
            module="templates",
            model=dict(
                packages=surface.creator.catalog.get("installedTemplates", []),
                selected=surface.view.property("selectedCode"),
                deletion=surface.view.property("deletion"),
                busy=surface.creator.busy,
                error=surface.creator.error,
            ),
        )
    if screen == "projects":
        rows = [
            dict(projectCode=row["code"], projectDetails=row)
            for group in surface.projects.groups
            for row in group["projects"]
        ]
        return dict(
            module="projects",
            model=surface.evaluate("model"),
            models=dict(projects=rows),
        )
    if screen in ("repositories", "repository_editor"):
        return dict(
            module="repository",
            describe="summary" if screen == "repositories" else "editor",
            model=surface.evaluate("model"),
            models=dict(repositories=surface.repositories.model._records),
        )
    raise ValueError(screen)


def capture_confirmation(surface, original, metadata, kind):
    if kind == "template":
        if original:
            evaluate(surface.engine, surface.view, "deleteConfirmation.open()")
        else:
            surface.view.setProperty("deletion", "cg_template")
        dialog = evaluate(surface.engine, surface.view, "deleteConfirmation")
        name, case = "template_confirmation", "delete"
    elif kind == "close":
        surface.case.config.request_close()
        dialog = evaluate(surface.engine, surface.view, "unsavedDialog")
        name, case = "configuration_confirmation", "close"
    else:
        if original:
            evaluate(surface.engine, surface.view, "clearConfirmation.open()")
            dialog = evaluate(surface.engine, surface.view, "clearConfirmation")
        else:
            surface.evaluate('dispatch({type:"clearData"})')
            dialog = surface.view.findChild(
                QObject, "configurationCacheClearConfirmation"
            )
        name, case = "cache_confirmation", "clear"
    surface.settle()
    content = dialog.property("contentItem")
    target = dialog.property("background").parentItem() if original else content
    window = target.window()
    origin = target.mapToScene(QPointF())
    image = window.grabWindow()
    ratio = image.devicePixelRatio()
    image = image.copy(
        QRect(
            round(origin.x() * ratio),
            round(origin.y() * ratio),
            round(target.width() * ratio),
            round(target.height() * ratio),
        )
    )
    record = dict(
        metadata,
        screen=name,
        case=case,
        width=target.width(),
        height=target.height(),
    )
    record["image"] = metadata["image"].replace(metadata["screen"] + "-", name + "-")
    record.pop("child", None)
    record.pop("models", None)
    assert image.save(str(OUT / record["image"]))
    if not original:
        record.update(
            module="templates" if kind == "template" else "configuration",
            describe="confirmation",
            model=dict(code="cg_template", busy=False)
            if kind == "template"
            else dict(kind=kind, busy=False),
            backgroundColor=surface.theme.property("surfaceContainerHighest").name(),
        )
        measured = snapshot(window)
        descendants = [content]
        for item in descendants:
            descendants.extend(item.childItems())
        names = {item.objectName() for item in descendants}
        for group in ("boxes", "styles", "fills", "interiors"):
            measured[group] = {
                key: value for key, value in measured[group].items() if key in names
            }
        measured["frameIds"] = [name for name in measured["frameIds"] if name in names]
        for group in ("boxes", "interiors"):
            for bounds in measured[group].values():
                bounds["x"] -= origin.x()
                bounds["y"] -= origin.y()
        record.update(measured)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    preview = QImage(32, 32, QImage.Format_RGB32)
    preview.fill(QColor("#78a6c4"))
    assert preview.save(str(PREVIEW))
    (OUT / "native.json").write_text(json.dumps(dict(status="capturing")))
    original_sources = extract_reference()
    # This manager was introduced after the archived pre-Frame reference.
    template_archive = subprocess.check_output(
        [
            "git",
            "-C",
            str(HANDLER),
            "archive",
            "--format=zip",
            "dfd985c040a258d6fa793324f4e985542a4397a8",
            "thlib/ui/qml",
        ]
    )
    with zipfile.ZipFile(io.BytesIO(template_archive)) as archive:
        for name in archive.namelist():
            if name.endswith("/"):
                continue
            relative = Path(name).relative_to("thlib/ui/qml")
            assert ".." not in relative.parts
            target = TEMPLATE_REFERENCE / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            data = archive.read(name)
            target.write_bytes(data)
            original_sources["pre-b05/" + name] = hashlib.sha256(data).hexdigest()
    names = ["thlib/ui/qml/" + name + ".qml" for name in SCREENS.values()]
    names += [
        "thlib/ui/qml/ConfigurationPage.qml",
        "thlib/ui/qml/features/configuration/SettingsPage.qml",
        "thlib/ui/qml/controls/ImagePicker.qml",
        "thlib/ui/configuration.py",
        "thlib/ui/project_creation.py",
        "thlib/ui/project_editor.py",
        "thlib/ui/repository_editor.py",
        "tests/frame_configuration_fixture.py",
        "tests/test_configuration_layout.py",
        "thlib/ui/translations/ru.json",
    ]
    shared, native_sources = source_hashes(ROOT, HANDLER, names)
    drivers = {
        path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in Path(__file__).parent.glob("*.*")
        if path.suffix in (".py", ".vue", ".mjs", ".html")
    }
    captures = []
    for screen in SCREENS:
        for original in (True, False):
            for style in ["md3"] if args.quick else ["md3", "material5", "fluent"]:
                for dark in [True] if args.quick else [True, False]:
                    for language in ["en"] if args.quick else ["en", "ru"]:
                        widths = [1100] if args.quick else [1100, 800]
                        if not original and (
                            not args.quick or screen in ("wizard", "editor")
                        ):
                            widths.append(360)
                        for width in widths:
                            for case in (
                                ["initial"]
                                if args.quick
                                and screen
                                not in (
                                    "templates",
                                    "configuration",
                                    "wizard",
                                    "editor",
                                )
                                else CASES[screen]
                            ):
                                surface = None
                                try:
                                    reference = (
                                        TEMPLATE_REFERENCE
                                        if screen == "templates"
                                        else REFERENCE
                                    )
                                    surface = Surface(
                                        screen,
                                        width,
                                        740,
                                        qml=reference if original else None,
                                        language=language,
                                        dark=dark,
                                        style=style,
                                    )
                                    configure(surface, case, original)
                                    assert not surface.warnings, surface.warnings
                                    if not original:
                                        for item in SidebarEditorQmlTests.descendants(
                                            surface.window.contentItem()
                                        ):
                                            if (
                                                item.objectName() == "buttonLabel"
                                                and item.isVisible()
                                                and item.width() > 0
                                            ):
                                                assert not item.property("truncated"), (
                                                    screen, language, width, case,
                                                    item.property("text"),
                                                )
                                    name = f"{screen}-{'original' if original else 'native'}-{style}-{'dark' if dark else 'light'}-{language}-{width}-{case}.png"
                                    assert surface.window.grabWindow().save(
                                        str(OUT / name)
                                    )
                                    capture = dict(
                                        screen=screen,
                                        original=original,
                                        style=style,
                                        dark=dark,
                                        language=language,
                                        width=width,
                                        viewportWidth=width,
                                        height=740,
                                        case=case,
                                        image=name,
                                    )
                                    if not original:
                                        capture.update(model(surface))
                                        if capture["model"].get("image") or capture[
                                            "model"
                                        ].get("stagedImage"):
                                            capture["imageData"] = (
                                                "data:image/png;base64,"
                                                + base64.b64encode(
                                                    PREVIEW.read_bytes()
                                                ).decode()
                                            )
                                        capture.update(snapshot(surface.window))
                                    captures.append(capture)
                                    if screen == "templates" and case == "selected":
                                        captures.append(
                                            capture_confirmation(
                                                surface, original, capture, "template"
                                            )
                                        )
                                    elif screen == "configuration" and case == "dirty":
                                        captures.append(
                                            capture_confirmation(
                                                surface, original, capture, "close"
                                            )
                                        )
                                    elif screen == "cache":
                                        captures.append(
                                            capture_confirmation(
                                                surface, original, capture, "clear"
                                            )
                                        )
                                finally:
                                    if surface:
                                        surface.close()
        print(screen, len(captures), flush=True)
    assert (shared, native_sources) == source_hashes(ROOT, HANDLER, names), (
        "Sources changed during capture"
    )
    (OUT / "native.json").write_text(
        json.dumps(
            dict(
                status="captured",
                quick=args.quick,
                sha256=shared,
                nativeSources=native_sources,
                driverSources=drivers,
                originalSources=original_sources,
                archive=str(ARCHIVE),
                archiveSha256=hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(),
                captures=captures,
            ),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print("Captured", len(captures), "actual original/native surfaces")


if __name__ == "__main__":
    main()
