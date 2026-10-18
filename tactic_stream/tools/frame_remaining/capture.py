"""Fresh B14 production reference captures and corresponding shared compositions."""

import argparse
import hashlib
import json
import os
import sys
import zipfile
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "output"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handler-root", type=Path, required=True)
    parser.add_argument("--reference-archive", type=Path, required=True)
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()
    handler = args.handler_root.resolve()
    reference = ROOT / ".tmp/b14/reference"
    with zipfile.ZipFile(args.reference_archive) as archive:
        for name in archive.namelist():
            if not name.startswith("thlib/ui/qml/") or name.endswith("/"):
                continue
            target = (reference / name).resolve()
            assert target.is_relative_to(reference.resolve())
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(name))
    os.environ.update(
        QT_QPA_PLATFORM="offscreen",
        QT_QUICK_BACKEND="software",
        QT_QUICK_CONTROLS_STYLE="Basic",
    )
    sys.path[:0] = [str(handler), str(ROOT / "tools/frame_admin")]
    from native_capture import assert_icons, snapshot, source_hashes
    from tests.frame_remaining_fixture import PANELS, PRODUCTION, Surface
    from tests.profile_ui_responsiveness import frame
    from tests.test_sidebar_editor_qml import SidebarEditorQmlTests
    from thlib.ui.localization import CatalogTranslator

    OUT.mkdir(parents=True, exist_ok=True)
    names = [
        path.relative_to(handler).as_posix()
        for path in (handler / "thlib/ui/qml").glob("Knowledge*.qml")
    ]
    names += [
        "thlib/ui/qml/" + name + ".qml"
        for name in (
            "TimesheetView",
            "WorkReportsView",
            "CostReportsView",
            "WorkHourEditorDialog",
        )
    ]
    names += [
        path.relative_to(handler).as_posix()
        for domain in ("knowledge", "workhours", "collaboration")
        for path in (handler / "thlib/ui/qml/features" / domain).glob("*.qml")
    ]
    names += [
        "thlib/ui/qml/CollaborationInitializationState.qml",
        "tests/frame_remaining_fixture.py",
        "tests/fixtures/FrameRemainingHarness.qml",
        "tests/test_frame_remaining.py",
        "tests/test_knowledge_base.py",
        "tests/test_work_hours.py",
        "thlib/ui/knowledge.py",
        "thlib/ui/rich_text_document.py",
        "thlib/ui/work_hours.py",
        "thlib/ui/translations/ru.json",
    ]
    shared, sources = source_hashes(ROOT, handler, names)
    drivers = [
        "tools/frame_remaining/capture.py",
        "tools/frame_remaining/RemainingFixture.vue",
        "tools/frame_remaining/remaining.entry.mjs",
        "tools/frame_remaining/index.html",
        "tools/frame_admin/native_capture.py",
        "frontend/tests/frame_remaining_capture.mjs",
        "frontend/tests/frame_capture.mjs",
    ]
    result = {
        "status": "running",
        "quick": args.quick,
        "sha256": shared,
        "nativeSources": sources,
        "driverSources": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in drivers
        },
        "archiveSha256": hashlib.sha256(
            args.reference_archive.read_bytes()
        ).hexdigest(),
        "captures": [],
    }
    tasks = []
    for screen, style, dark, language, width, locked in product(
        PANELS,
        ["md3"] if args.quick else ["md3", "material5", "fluent"],
        [True] if args.quick else [True, False],
        ["en"] if args.quick else ["en", "ru"],
        [900] if args.quick else [430, 900, 1200],
        [False] if args.quick else [False, True],
    ):
        tasks.append(
            {
                "screen": screen,
                "style": style,
                "dark": dark,
                "language": language,
                "width": width,
                "height": 420,
                "locked": locked,
                "original": False,
                "panel": True,
            }
        )
    for screen, original, language, width in product(
        PRODUCTION,
        [True, False],
        ["en"] if args.quick else ["en", "ru"],
        [900] if args.quick else [430, 1100],
    ):
        tasks.append(
            {
                "screen": screen,
                "style": "md3",
                "dark": True,
                "language": language,
                "width": width,
                "height": 700,
                "locked": False,
                "original": original,
                "panel": False,
            }
        )
    try:
        for index, record in enumerate(tasks):
            surface = Surface.__new__(Surface)
            translator = None
            try:
                Surface.__init__(
                    surface,
                    record["screen"],
                    record["width"],
                    record["height"],
                    qml=reference / "thlib/ui/qml" if record["original"] else None,
                    style=record["style"],
                    dark=record["dark"],
                    language=record["language"],
                    locked=record["locked"],
                )
                if record["language"] == "ru":
                    translator = CatalogTranslator(
                        handler / "thlib/ui/translations/ru.json"
                    )
                    surface.app.installTranslator(translator)
                    surface.engine.retranslate()
                    surface.app.processEvents()
                assert not surface.warnings, surface.warnings
                if index == 0:
                    glyph = next(
                        item
                        for item in SidebarEditorQmlTests.descendants(
                            surface.window.contentItem()
                        )
                        if item.objectName() == "materialIconGlyph" and item.isVisible()
                    )
                    icon = glyph.parentItem()
                    original_name = icon.property("name")
                    try:
                        icon.setProperty(
                            "name", "fontawesome-solid:frame-nonexistent-icon"
                        )
                        frame(surface.window)
                        try:
                            assert_icons(surface.window)
                        except AssertionError:
                            pass
                        else:
                            raise AssertionError(
                                "Unknown-icon validator accepted a missing qualified glyph"
                            )
                    finally:
                        icon.setProperty("name", original_name)
                        frame(surface.window)
                measured = snapshot(surface.window, check_icons=not record["original"])
                name = f"{index:04d}-{record['screen']}-{'original' if record['original'] else 'native'}.png"
                assert surface.window.grabWindow().save(str(OUT / name))
                result["captures"].append(
                    dict(record, file=name, model=surface.model, measured=measured)
                )
                if index % 24 == 0:
                    print(index + 1, "/", len(tasks), record["screen"], flush=True)
            finally:
                if translator:
                    surface.app.removeTranslator(translator)
                surface.close()
        assert (shared, sources) == source_hashes(ROOT, handler, names), (
            "Sources changed during capture"
        )
        for name, digest in result["driverSources"].items():
            assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, (
                name
            )
        result["status"] = "captured"
    finally:
        (OUT / "native.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    print("Captured", len(result["captures"]), "native surfaces")


if __name__ == "__main__":
    main()
