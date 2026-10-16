"""Run the focused Frame platform gate in both independent products.

This composes existing drivers; full Administration/original-reference suites
remain separate release checks. Every child, including browser descendants, is
terminated on interruption or timeout.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "tools/frame_foundation/output/platform"


def stop(process):
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            check=False,
        )
    else:
        os.killpg(process.pid, signal.SIGKILL)
    process.wait()


def run(name, command, directory, environment):
    log = OUTPUT / (name + ".log")
    with log.open("w", encoding="utf-8") as stream:
        process = subprocess.Popen(
            command,
            cwd=directory,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=stream,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            start_new_session=os.name != "nt",
        )
        try:
            status = process.wait(timeout=120)
        finally:
            stop(process)
    print(name, status, flush=True)
    if status:
        raise RuntimeError(f"{name} failed; see {log}")
    text = log.read_text(encoding="utf-8")
    count = re.search(r"Ran (\d+) tests?", text)
    return dict(
        name=name, status=status, log=log.name, tests=int(count[1]) if count else None
    )


def fingerprints(handler):
    roots = [
        ("stream", ROOT / "frontend/src"),
        ("shared", ROOT / "src/tactic_stream/shared_ui"),
        ("handler", handler / "thlib/ui"),
    ]
    result = {}
    for product, directory in roots:
        for path in sorted(directory.rglob("*")):
            if path.is_file() and (
                path.suffix in (".qml", ".mjs", ".json", ".vue", ".js", ".css", ".py")
                or path.name == "qmldir"
            ):
                result[product + "/" + path.relative_to(directory).as_posix()] = (
                    hashlib.sha256(path.read_bytes()).hexdigest()
                )
    checks = [
        ROOT / "frontend/tests" / name
        for name in (
            "frame_contract.mjs",
            "frame_renderer_contract.mjs",
            "frame_resize.mjs",
            "frame_platform.mjs",
            "frame_controls_contract.mjs",
            "frame_controls.mjs",
            "frame_controls_input.mjs",
            "icons.mjs",
            "frame_help_state.mjs",
            "frame_help.mjs",
            "frame_navigation.mjs",
            "frame_menus.mjs",
            "frame_dock_placement.mjs",
            "frame_dock_layout.mjs",
            "frame_dock_interaction.mjs",
            "frame_window_lifecycle.mjs",
            "window_types.mjs",
            "shared_help.mjs",
        )
    ]
    checks += [
        handler / "tests/test_frame_platform.py",
        handler / "tests/test_frame_controls.py",
        handler / "tests/fixtures/FrameControlsHarness.qml",
        handler / "tests/test_user_combo_box.py",
        handler / "tests/test_frame_help.py",
        handler / "tests/test_frame_navigation.py",
        handler / "tests/test_frame_dock_input.py",
        handler / "tests/test_frame_menus.py",
        handler / "tests/test_frame_dock_layout.py",
        handler / "tests/fixtures/DockWorkspaceHarness.qml",
        handler / "tests/test_dock_resizing.py",
        handler / "tests/test_dock_layout_tree.py",
        handler / "tests/test_retained_ui.py",
        handler / "tests/test_qml_smoke_harness.py",
        ROOT / "tests/test_frame_inventory.py",
        ROOT / "tests/test_tactic_frame_sync.py",
        ROOT / "tools/frame_foundation/check_platform.py",
        ROOT / "tools/frame_foundation/inventory.py",
        ROOT / "tools/frame_foundation/inventory_web.mjs",
        ROOT / "tools/sync_tactic_frame.py",
        ROOT / "tools/check_frame_package.py",
        ROOT / "tools/format_tactic_frame.py",
        ROOT / "pyproject.toml",
        handler / "thlib/version.json",
        ROOT / "src/tactic_stream/shared_ui/README.md",
        handler / "thlib/ui/qml/tactic_frame/README.md",
        ROOT / "tools/frame_foundation/PlatformHarness.vue",
        ROOT / "tools/frame_foundation/platform.entry.js",
        ROOT / "tools/frame_foundation/platform.html",
    ]
    checks += [
        path
        for path in (ROOT / "tools/frame_controls").iterdir()
        if path.is_file() and path.suffix in (".vue", ".js", ".html", ".py")
    ]
    checks += [
        path
        for path in (ROOT / "tools/frame_menus").iterdir()
        if path.is_file() and path.suffix in (".vue", ".js", ".html", ".py")
    ]
    for index, path in enumerate(checks):
        result[f"check/{index}/{path.name}"] = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handler-root", type=Path, required=True)
    args = parser.parse_args()
    handler = args.handler_root.resolve()
    assert (handler / "tests/test_frame_platform.py").is_file(), (
        "Handler platform tests are required"
    )
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (ROOT / ".tmp/frame-tests").mkdir(parents=True, exist_ok=True)
    environment = dict(
        os.environ,
        PYTHONDONTWRITEBYTECODE="1",
        QT_QPA_PLATFORM="offscreen",
        QT_QUICK_BACKEND="software",
        QSG_RENDER_LOOP="basic",
        TMP=str(ROOT / ".tmp/frame-tests"),
        TEMP=str(ROOT / ".tmp/frame-tests"),
    )
    python = [sys.executable, "-B", "-X", "utf8"]
    version = json.loads((handler / "thlib/version.json").read_text(encoding="utf-8"))
    stream_version = tomllib.loads(
        (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )["project"]["version"]
    report = dict(
        status="running",
        steps=[],
        sources=fingerprints(handler),
        versions={
            "handler": ".".join(
                version[key] for key in ("major", "minor", "build", "revision")
            ),
            "stream": stream_version,
        },
    )
    path = OUTPUT / "gate.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    steps = [
        (
            "format",
            python
            + [
                "tools/format_tactic_frame.py",
                "--check",
                "--handler-root",
                str(handler),
            ],
            ROOT,
            {},
        ),
        (
            "sync",
            python
            + ["tools/sync_tactic_frame.py", "--handler-root", str(handler), "--check"],
            ROOT,
            {},
        ),
        ("contract", ["node", "frontend/tests/frame_contract.mjs"], ROOT, {}),
        (
            "icons-contract",
            ["node", "frontend/tests/icons.mjs", str(handler)],
            ROOT,
            {},
        ),
        (
            "controls-contract",
            ["node", "frontend/tests/frame_controls_contract.mjs"],
            ROOT,
            {},
        ),
        (
            "renderers",
            ["node", "frontend/tests/frame_renderer_contract.mjs", str(handler)],
            ROOT,
            {},
        ),
        ("resize", ["node", "frontend/tests/frame_resize.mjs"], ROOT, {}),
        ("help-state", ["node", "frontend/tests/frame_help_state.mjs"], ROOT, {}),
        (
            "dock-placement",
            ["node", "frontend/tests/frame_dock_placement.mjs"],
            ROOT,
            {},
        ),
        ("dock-layout", ["node", "frontend/tests/frame_dock_layout.mjs"], ROOT, {}),
        (
            "inventory-tests",
            python
            + [
                "-m",
                "unittest",
                "-q",
                "tests.test_frame_inventory",
                "tests.test_tactic_frame_sync",
            ],
            ROOT,
            {},
        ),
        *[
            (
                f"native-{scale}",
                python
                + [
                    "-m",
                    "unittest",
                    "-q",
                    "tests.test_frame_platform.FramePlatformTests",
                    "tests.test_frame_controls.FrameControlsTests",
                    "tests.test_user_combo_box.UserPickerTests",
                    "tests.test_frame_help.FrameHelpTests",
                    "tests.test_frame_navigation.FrameNavigationTests",
                    "tests.test_frame_dock_input.FrameDockInputTests",
                    "tests.test_frame_menus.FrameMenuTests",
                    "tests.test_frame_dock_layout.FrameDockLayoutTests",
                ],
                handler,
                {"QT_SCALE_FACTOR": scale},
            )
            for scale in ("1", "1.5", "2")
        ],
        ("browser", ["node", "tests/frame_platform.mjs"], ROOT / "frontend", {}),
        (
            "browser-controls",
            ["node", "frontend/tests/frame_controls.mjs", "--input-only"],
            ROOT,
            {},
        ),
        (
            "smoke",
            python + ["-m", "unittest", "-q", "tests.test_qml_smoke_harness"],
            handler,
            {},
        ),
        *[
            (name, ["node", "frontend/tests/" + script + ".mjs"], ROOT, {})
            for name, script in [
                ("help-input", "frame_help"),
                ("help-launchers", "shared_help"),
                ("navigation-input", "frame_navigation"),
                ("menus-input", "frame_menus"),
                ("dock-input", "frame_dock_interaction"),
                ("window-input", "frame_window_lifecycle"),
                ("window-kinds", "window_types"),
            ]
        ],
        (
            "dock-rollback",
            python
            + [
                "-m",
                "unittest",
                "-q",
                "tests.test_dock_resizing",
                "tests.test_dock_layout_tree",
            ],
            handler,
            {},
        ),
        (
            "dock-retention",
            python
            + ["-m", "unittest", "-q"]
            + [
                "tests.test_retained_ui.RetainedUiTests." + name
                for name in [
                    "test_unsnapped_dock_title_drag_keeps_the_dock_in_its_layout",
                    "test_dock_layout_switch_keeps_delegate_and_loaded_content",
                    "test_stacked_search_dock_keeps_move_grip_at_fixed_position",
                    "test_dock_content_reflows_live_during_resize",
                    "test_shared_dock_resize_grip_starts_on_first_press",
                ]
            ],
            handler,
            {},
        ),
        ("package", python + ["tools/check_frame_package.py"], ROOT, {}),
        (
            "inventory",
            python
            + ["tools/frame_foundation/inventory.py", "--handler-root", str(handler)],
            ROOT,
            {},
        ),
    ]
    try:
        with tempfile.TemporaryDirectory(
            prefix="frame-platform-", dir=ROOT / ".tmp"
        ) as settings:
            assert Path(settings).resolve().is_relative_to((ROOT / ".tmp").resolve())
            environment.update(
                LOCALAPPDATA=settings,
                APPDATA=settings,
                XDG_CONFIG_HOME=settings,
                XDG_CACHE_HOME=settings,
            )
            for name, command, directory, extra in steps:
                report["steps"].append(
                    run(name, command, directory, dict(environment, **extra))
                )
            assert report["sources"] == fingerprints(handler), (
                "UI source changed during the gate"
            )
            report["status"] = "passed"
    except BaseException:
        report["status"] = "failed"
        raise
    finally:
        path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Frame platform gate passed; full release scenarios remain separate.")


if __name__ == "__main__":
    main()
