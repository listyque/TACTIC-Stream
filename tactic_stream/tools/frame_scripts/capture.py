"""Capture immutable original and current native B13 production surfaces."""

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
    reference = ROOT / ".tmp/b13/reference"
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
    from native_capture import snapshot, source_hashes
    from PySide6.QtCore import QCoreApplication
    from tests.frame_scripts_fixture import SCREENS, Surface
    from thlib.ui.localization import CatalogTranslator

    OUT.mkdir(parents=True, exist_ok=True)
    names = ["thlib/ui/qml/" + name + ".qml" for name in SCREENS.values()]
    names += [
        p.relative_to(handler).as_posix()
        for domain in ("scripts", "tools")
        for p in (handler / "thlib/ui/qml/features" / domain).glob("*.qml")
    ]
    names += [
        "tests/frame_scripts_fixture.py",
        "tests/test_frame_script_tools.py",
        "thlib/ui/translations/ru.json",
    ]
    names += [
        "thlib/ui/" + name + ".py"
        for name in (
            "script_editor",
            "script_editor_features",
            "script_shelf",
            "script_triggers",
            "handler_server_controller",
            "dcc_options",
        )
    ]
    shared, sources = source_hashes(ROOT, handler, names)
    result = {
        "status": "capturing",
        "quick": args.quick,
        "sha256": shared,
        "nativeSources": sources,
        "archiveSha256": hashlib.sha256(
            args.reference_archive.read_bytes()
        ).hexdigest(),
        "captures": [],
        "driverSources": {
            path.relative_to(ROOT).as_posix(): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in (
                Path(__file__),
                ROOT / "tools/frame_scripts/report.py",
                ROOT / "tools/frame_scripts/ScriptFixture.vue",
                ROOT / "tools/frame_scripts/index.html",
                ROOT / "tools/frame_scripts/scripts.entry.mjs",
                ROOT / "tools/frame_admin/native_capture.py",
                ROOT / "frontend/tests/frame_scripts.mjs",
                ROOT / "frontend/tests/frame_capture.mjs",
            )
        },
    }
    path = OUT / "native.json"
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    try:
        variants = product(
            SCREENS,
            (True, False),
            ["md3"] if args.quick else ["md3", "material5", "fluent"],
            [(True, "en")]
            if args.quick
            else [
                (dark, language) for dark in (True, False) for language in ("en", "ru")
            ],
            [900] if args.quick else [900, 720],
            ["initial"] if args.quick else ["initial", "locked"],
        )
        for screen, original, style, (dark, language), width, case in variants:
            surface = None
            translator = (
                CatalogTranslator(handler / "thlib/ui/translations/ru.json")
                if language == "ru"
                else None
            )
            try:
                surface = Surface(
                    screen,
                    width,
                    48 if screen == "bar" else 650,
                    qml=reference / "thlib/ui/qml" if original else None,
                    dark=dark,
                    style=style,
                    language=language,
                    case=case,
                )
                if translator:
                    surface.app.installTranslator(translator)
                    surface.engine.retranslate()
                    surface.app.processEvents()
                assert not surface.warnings, surface.warnings
                measured = snapshot(surface.window, check_icons=not original)
                name = f"{screen}-{'original' if original else 'native'}-{style}-{'dark' if dark else 'light'}-{language}-{width}-{case}.png"
                assert surface.window.grabWindow().save(str(OUT / name))
                record = dict(
                    screen=screen,
                    original=original,
                    style=style,
                    dark=dark,
                    language=language,
                    width=width,
                    height=48 if screen == "bar" else 650,
                    case=case,
                    file=name,
                    measured=measured,
                )
                if not original and screen in ("editor", "shelf", "bar"):
                    model = surface.view.property(
                        "projection" if screen != "editor" else "presentation"
                    )
                    if hasattr(model, "toVariant"):
                        model = model.toVariant()
                    record["model"] = model
                    if screen == "shelf":
                        record["model"] = surface.view.property(
                            "projection"
                        ).toVariant()
                        record["buttons"] = surface.controller.editor_buttons.records()
                        presets = surface.view.property("presets")
                        record["presets"] = (
                            presets.toVariant()
                            if hasattr(presets, "toVariant")
                            else presets
                        )
                        record["scripts"] = [
                            dict(
                                path=row["value"],
                                title=row["value"].rsplit("/", 1)[-1],
                                language="python",
                                runnable=True,
                            )
                            for row in surface.controller.scriptOptions
                        ]
                    elif screen == "bar":
                        record["buttons"] = surface.controller.buttons.records()
                result["captures"].append(record)
                print(name, flush=True)
            finally:
                if surface:
                    if translator:
                        surface.app.removeTranslator(translator)
                    surface.dispose()
                QCoreApplication.processEvents()
        assert (shared, sources) == source_hashes(ROOT, handler, names), (
            "Sources changed during capture"
        )
        result["status"] = "captured"
        for name, digest in result["driverSources"].items():
            assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, (
                name
            )
    finally:
        path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
