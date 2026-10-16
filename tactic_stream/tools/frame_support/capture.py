"""Capture actual original/current Handler support views and their Frame models."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
HANDLER = Path("D:/code/th_codex")
sys.path[:0] = [str(HANDLER), str(ROOT / "tools/frame_admin")]

from PySide6.QtCore import QObject, QPointF, QRect
from tests.frame_support_fixture import Surface, SCREENS, evaluate, variant
from thlib.ui.localization import CatalogTranslator
from native_capture import snapshot, source_hashes
from original_reference import ARCHIVE, REFERENCE, extract_reference

OUT = Path(__file__).resolve().parent / "output"
CASES = {
    "debug": ["initial", "selected", "empty"],
    "performance": ["initial", "selected", "empty"],
    "profile": ["initial", "readonly", "other", "loading"],
    "editor": ["initial", "groups", "create", "uncertain"],
    "sign_in": ["initial", "busy", "error"],
    "presets": ["initial", "routing", "error"],
    "updates": ["initial", "changelog", "create", "busy", "error"],
    "error": ["initial", "expanded", "connection"],
}


def configure(surface, case, original):
    screen = surface.screen
    controller = lambda name: surface.controllers.findChild(QObject, name)
    if screen == "debug":
        surface.debug.log(
            "WARNING",
            "Fixture warning",
            group="fixture/secondary",
            module="secondary.py",
        )
        surface.debug.log(
            "ERROR",
            "Second fixture error",
            group="fixture/request",
            module="request.py",
        )
        for row in surface.debug._all_entries:
            row["timestamp"] = "2026-10-17T00:00:00.000"
        surface.debug._apply_filters()
        surface.debug._rebuild_groups()
        surface.debug.state_changed.emit()
        if case == "selected":
            surface.debug.select_entry(0)
        elif case == "empty":
            surface.debug.clear()
    elif screen == "performance":
        if case == "selected":
            sample = surface.performance.model.get(0)
            surface.view.setProperty("selectedSample", sample)
        elif case == "empty":
            surface.performance.clear()
    elif screen == "profile":
        user = controller("userController")
        if case == "readonly":
            for name in ("canEdit", "canManageUsers", "canViewWorkHours"):
                user.setProperty(name, False)
        elif case == "other":
            profile = variant(user.property("profile"))
            profile.update(login="other_artist", current=False, online=False)
            user.setProperty("profile", profile)
        elif case == "loading":
            user.setProperty("profile", {"login": "", "groups": [], "roles": []})
            user.setProperty("busy", True)
        if not original and surface.window.width() < 760:
            surface.view.setProperty("directoryExpanded", False)
    elif screen == "editor":
        if case == "groups":
            evaluate(surface.engine, surface.view, "openForGroups()")
        elif case == "create":
            evaluate(surface.engine, surface.view, "openForCreate()")
        elif case == "uncertain":
            controller("userController").setProperty(
                "editingError",
                "The request result is unknown. Reload before saving again.",
            )
            if not original:
                surface.view.setProperty("uncertain", True)
                surface.view.setProperty("confirmClose", True)
    elif screen == "sign_in":
        auth = controller("appController")
        if case == "busy":
            auth.setProperty("authentication_busy", True)
        elif case == "error":
            auth.setProperty("authentication_error", "Incorrect login or password.")
    elif screen == "presets":
        presets = controller("serverPresetsController")
        if case == "routing":
            values = variant(presets.property("selected_values"))
            values.update(
                proxyEnabled=True,
                proxyServer="https://proxy.example.test",
                proxyLogin="fixture",
                siteEnabled=True,
            )
            presets.setProperty("selected_values", values)
            presets.sessionStarted.emit()
            if not original:
                surface.view.setProperty("editing", True)
        elif case == "error":
            presets.setProperty("error", "Enter a valid TACTIC server address")
    elif screen == "updates":
        updates = controller("updateController")
        if case == "create":
            surface.view.setProperty("createMode", True)
            evaluate(surface.engine, surface.view, "syncVersion()")
        elif case == "changelog":
            surface.view.setProperty("currentPage", "changelog")
        elif case == "busy":
            for name, value in dict(
                busy=True,
                cancelable=True,
                progress=0.38,
                stage="Downloading release ZIP",
            ).items():
                updates.setProperty(name, value)
        elif case == "error":
            updates.setProperty("error", "Fixture release is unavailable")
            updates.setProperty("canInstall", False)
            updates.setProperty("portable", False)
    elif screen == "error":
        debug = surface.debug
        debug._error_title = "Application error"
        debug._error_kind = "RuntimeError"
        debug._error_type = (
            "connection_timeout" if case == "connection" else "runtime_error"
        )
        debug._error_message = "Fixture request failed. No operation has been repeated."
        debug._error_stacktrace = (
            "Traceback (most recent call last):\nRuntimeError: fixture"
        )
        debug._error_command = "print('fixture')"
        debug.error_changed.emit()
        if case == "expanded":
            evaluate(
                surface.engine,
                surface.view,
                "showStacktrace.checked = true" if original else "expanded = true",
            )
    surface.settle()


def records(surface):
    return {
        "groups": [
            dict(row)
            for row in (
                surface.debug.groups_model._records
                if surface.screen == "debug"
                else surface.groups._records
            )
        ],
        "events": [dict(row) for row in surface.debug.entries_model._records],
        "samples": [dict(row) for row in surface.performance.model._records],
        "users": [dict(row) for row in surface.users._records],
        "presets": [dict(row) for row in surface.presets._records],
        "releases": [dict(row) for row in surface.releases._records],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--screen", choices=SCREENS)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "native.json").write_text(json.dumps({"status": "capturing"}))
    original_sources = extract_reference()
    native_names = ["thlib/ui/qml/" + name + ".qml" for name in SCREENS.values()]
    native_names += [
        path.relative_to(HANDLER).as_posix()
        for path in (HANDLER / "thlib/ui/qml/features/support").rglob("*.qml")
    ]
    native_names += [
        "thlib/ui/debug_logging.py",
        "thlib/ui/ui_performance.py",
        "thlib/ui/user.py",
        "tests/frame_support_fixture.py",
        "tests/fixtures/FrameSupportControllers.qml",
        "thlib/ui/translations/ru.json",
    ]
    shared, native_sources = source_hashes(ROOT, HANDLER, native_names)
    captures = []
    screens = [args.screen] if args.screen else SCREENS
    styles = ("md3",) if args.quick else ("md3", "material5", "fluent")
    for screen in screens:
        for original in (True, False):
            for style in styles:
                for dark in (True,) if args.quick else (True, False):
                    for language in ("en",) if args.quick else ("en", "ru"):
                        for width in (
                            (1100,)
                            if args.quick
                            else ((1100, 800) if original else (1100, 800, 360))
                        ):
                            for case in ("initial",) if args.quick else CASES[screen]:
                                surface = None
                                translator = (
                                    CatalogTranslator(
                                        HANDLER / "thlib/ui/translations/ru.json"
                                    )
                                    if language == "ru"
                                    else None
                                )
                                try:
                                    surface = Surface(
                                        screen,
                                        min(width, 440)
                                        if screen == "sign_in"
                                        else width,
                                        470 if screen == "sign_in" else 740,
                                        qml=REFERENCE if original else None,
                                        language=language,
                                        dark=dark,
                                        style=style,
                                    )
                                    if translator:
                                        surface.app.installTranslator(translator)
                                        surface.engine.retranslate()
                                    configure(surface, case, original)
                                    diagnostics = list(surface.warnings)
                                    if not original:
                                        assert not diagnostics, diagnostics
                                    else:
                                        assert not any(
                                            "ReferenceError" in value
                                            or "TypeError" in value
                                            for value in diagnostics
                                        ), diagnostics
                                    measured = snapshot(
                                        surface.window, check_icons=not original
                                    )
                                    origin = surface.view_item.mapToScene(QPointF())
                                    for group in ("boxes", "interiors"):
                                        for bounds in measured[group].values():
                                            bounds["x"] -= origin.x()
                                            bounds["y"] -= origin.y()
                                    actual_width = surface.view_item.width()
                                    actual_height = surface.view_item.height()
                                    image = surface.window.grabWindow()
                                    ratio = image.devicePixelRatio()
                                    image = image.copy(
                                        QRect(
                                            round(origin.x() * ratio),
                                            round(origin.y() * ratio),
                                            round(actual_width * ratio),
                                            round(actual_height * ratio),
                                        )
                                    )
                                    filename = f"{screen}-{'original' if original else 'native'}-{style}-{int(dark)}-{language}-{width}-{case}.png"
                                    assert image.save(str(OUT / filename))
                                    row = dict(
                                        screen=screen,
                                        original=original,
                                        style=style,
                                        dark=dark,
                                        language=language,
                                        viewportWidth=width,
                                        width=actual_width,
                                        height=actual_height,
                                        case=case,
                                        image=filename,
                                        originalDiagnostics=diagnostics,
                                        activeFocusId=surface.window.activeFocusItem().objectName()
                                        if surface.window.activeFocusItem()
                                        else "",
                                        **measured,
                                    )
                                    if not original:
                                        row.update(
                                            model=surface.model(),
                                            models=records(surface),
                                            command=surface.debug.error_command,
                                            changelog=surface.controllers.findChild(
                                                QObject, "updateController"
                                            ).property("changelog"),
                                            currentVersion=surface.controllers.findChild(
                                                QObject, "updateController"
                                            ).property("currentVersion"),
                                        )
                                    captures.append(row)
                                finally:
                                    if surface:
                                        if translator:
                                            surface.app.removeTranslator(translator)
                                        surface.close()
        print(screen, "captured", flush=True)
    assert (shared, native_sources) == source_hashes(ROOT, HANDLER, native_names), (
        "Sources changed during capture"
    )
    report = dict(
        status="captured",
        quick=args.quick,
        complete=not args.screen,
        sha256=shared,
        nativeSources=native_sources,
        archive=str(ARCHIVE),
        archiveSha256=hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(),
        originalSources=original_sources,
        driverSources={
            path.relative_to(ROOT).as_posix(): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in (
                Path(__file__),
                ROOT / "tools/frame_admin/native_capture.py",
                ROOT / "tools/frame_support/support.entry.mjs",
                ROOT / "tools/frame_support/index.html",
                ROOT / "frontend/tests/frame_support.mjs",
                ROOT / "frontend/tests/frame_capture.mjs",
            )
        },
        captures=captures,
    )
    (OUT / "native.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(len(captures), "actual native captures", flush=True)


if __name__ == "__main__":
    main()
