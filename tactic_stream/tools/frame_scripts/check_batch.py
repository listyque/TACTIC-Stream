"""Verify an existing private Batch script's native entry point without executing jobs."""

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handler-root", type=Path, required=True)
    parser.add_argument("--script", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    handler = args.handler_root.resolve()
    script = args.script.resolve()
    original = hashlib.sha256(script.read_bytes()).hexdigest()
    os.environ.update(
        QT_QPA_PLATFORM="offscreen",
        QT_QUICK_BACKEND="software",
        QT_QUICK_CONTROLS_STYLE="Basic",
    )
    sys.path.insert(0, str(handler))
    from PySide6.QtCore import QUrl
    from PySide6.QtQml import QQmlComponent, QQmlEngine
    from PySide6.QtQuick import QQuickWindow
    from tests.profile_ui_responsiveness import frame
    from tests.qt_application import gui_test_application
    from thlib.environment import env_mode
    from thlib.ui.icon_font import qml_icon_bindings

    app = gui_test_application()
    engine = QQmlEngine()
    warnings = []
    engine.warnings.connect(
        lambda values: warnings.extend(value.toString() for value in values)
    )
    icons = qml_icon_bindings(handler, engine)
    for name, value in icons.items():
        engine.rootContext().setContextProperty(name, value)
    parent_component = QQmlComponent(engine)
    parent_component.setData(
        b"""import QtQuick.Window
Window { property bool dark: true; property string applicationThemeStyleName: "md3";
property color applicationThemeBaseColor: "#292d30"; property color applicationThemeAccentColor: "#78a6c4" }""",
        QUrl(),
    )
    parent = parent_component.create()
    assert isinstance(parent, QQuickWindow), [
        value.toString() for value in parent_component.errors()
    ]
    spec = importlib.util.spec_from_file_location("_frame_batch_verification", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert (
        module._ui_text("Queue paused\nCustom status")
        == module._UI_TEXT["Queue paused"] + "\nCustom status"
    )
    previous_path = env_mode.current_path
    controller = window = component = None
    try:
        with tempfile.TemporaryDirectory(prefix="frame-batch-") as directory:
            env_mode.current_path = directory
            # Offline initialization must not use any API/filesystem job operation.
            controller = module.BatchDispatcherController(
                object(), "fixture", offline=True
            )
            component, window = module._create_window(
                engine, handler, parent, controller
            )
            controller.attach_window(window)
            controller.initialize()
            window.show()
            frame(window)
            assert window.isVisible()
            closed = []
            controller.windowCloseRequested.connect(lambda: closed.append(True))
            controller.closeWindow()
            assert (
                closed
                and not controller._clock.isActive()
                and not controller._poll_timer.isActive()
            )
            window.hide()
            assert not warnings, warnings
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(
                    {
                        "status": "passed",
                        "sha256": original,
                        "nativeWindow": True,
                        "offline": True,
                        "schedulerExecuted": False,
                        "closed": True,
                        "warnings": warnings,
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
    finally:
        if controller is not None:
            controller.shutdown()
        if window is not None:
            window.deleteLater()
        if component is not None:
            component.deleteLater()
        parent.deleteLater()
        app.processEvents()
        env_mode.current_path = previous_path
    assert hashlib.sha256(script.read_bytes()).hexdigest() == original
    print(
        "PASS unchanged private Batch: native QML creation, offline initialization and owned timer shutdown"
    )


if __name__ == "__main__":
    main()
