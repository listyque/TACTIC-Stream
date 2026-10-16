"""Keep Frame source readable: Prettier for JS/Vue, Qt for native QML."""

import argparse
from pathlib import Path
import subprocess
import shutil

import PySide6

ROOT = Path(__file__).resolve().parents[1]
FORMATTER = Path(PySide6.__file__).parent / "qmlformat.exe"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--handler-root",
        type=Path,
        help="Format native renderers in an explicitly selected Handler checkout",
    )
    args = parser.parse_args()
    npm = shutil.which("npm.cmd") or shutil.which("npm")
    assert npm, "npm is required for the pinned development formatter"
    command = [
        npm,
        "exec",
        "--yes",
        "--cache",
        str(ROOT / ".npm-cache"),
        "--package",
        "prettier@3.6.2",
        "--",
        "prettier",
        "--check" if args.check else "--write",
        "--single-quote",
        "--trailing-comma",
        "none",
        "--tab-width",
        "4",
        "src/tactic_stream/shared_ui/**/*.mjs",
    ]
    subprocess.run(command, cwd=ROOT, check=True)
    command[-1] = "frontend/src/frame/**/*.{vue,css}"
    command[command.index("--tab-width") + 1] = "2"
    subprocess.run(command, cwd=ROOT, check=True)
    command[-1] = "frontend/src/features/administration/**/*.{vue,js}"
    subprocess.run(command, cwd=ROOT, check=True)
    command[-1] = "tools/frame_foundation/*.{vue,js,html,mjs}"
    subprocess.run(command, cwd=ROOT, check=True)
    command[-1] = "tools/frame_controls/*.{vue,js,html,mjs}"
    subprocess.run(command, cwd=ROOT, check=True)
    command[-1] = "frontend/src/features/workspace/{DockWorkspace.vue,docks.js}"
    subprocess.run(command, cwd=ROOT, check=True)
    command[-1] = "frontend/tests/{frame_controls*,frame_icons,icons}.mjs"
    subprocess.run(command, cwd=ROOT, check=True)
    for pattern in ["frontend/src/features/help/**/*.{vue,js}", "tools/frame_help/*.{vue,js,html,mjs}", "frontend/tests/frame_{help*,window_lifecycle,dock_placement,dock_layout,dock_capture,dock_interaction,navigation*}.mjs"]:
        command[-1] = pattern
        subprocess.run(command, cwd=ROOT, check=True)
    for pattern in ["src/tactic_stream/shared_ui/**/*.json", "tools/frame_menus/*.{vue,js,html}", "frontend/tests/frame_menus.mjs", "frontend/src/features/connection/ConnectionMenu.vue"]:
        command[-1] = pattern
        subprocess.run(command, cwd=ROOT, check=True)
    controls = [
        "WorkspaceTabs.vue",
        "ActionRows.vue",
        "ActionRow.vue",
        "DockWorkspaceFooter.vue",
        "DocumentPane.vue",
        "NavigationRow.vue",
        "AppButton.vue",
        "AppIcon.vue",
        "AppColorInput.vue",
        "AppCheckbox.vue",
        "AppDateField.vue",
        "AppMenu.vue",
        "AppMenuItem.vue",
        "AppSelect.vue",
        "AppSplitter.vue",
        "AppTextArea.vue",
        "AppTextField.vue",
        "ColorPicker.vue",
        "IconPicker.vue",
        "UserComboBox.vue",
        "UserPicker.vue",
        "controlAppearance.js",
        "tooltip.js",
        "tooltip.css",
        "panelChrome.css",
    ]
    command[-1:] = ["frontend/src/controls/" + name for name in controls]
    subprocess.run(command, cwd=ROOT, check=True)
    command[-len(controls) :] = ["frontend/src/icons.js", "frontend/src/icons.css"]
    subprocess.run(command, cwd=ROOT, check=True)
    changed = []
    files = []
    if args.handler_root:
        files += sorted(
            (args.handler_root / "thlib/ui/qml/tactic_frame").rglob("*.qml")
        )
        files += [
            path
            for path in sorted((args.handler_root / "thlib/ui/qml").glob("*.qml"))
            if "tactic_frame" in path.read_text(encoding="utf-8")
        ]
        files += [
            path
            for path in sorted(
                (args.handler_root / "thlib/ui/qml/controls").glob("*.qml")
            )
            if "tactic_frame" in path.read_text(encoding="utf-8")
        ]
        files += sorted(
            (args.handler_root / "thlib/ui/qml/features/administration").rglob("*.qml")
        )
        files += sorted((args.handler_root / "thlib/ui/qml/features/support").rglob("*.qml"))
        files += [args.handler_root / "thlib/ui/qml/controls/DocumentPane.qml"]
        files += sorted((args.handler_root / "thlib/ui/qml/shell").rglob("*.qml"))
        files += [args.handler_root / "tests/fixtures/FrameControlsHarness.qml"]
        files += [args.handler_root / "tests/fixtures/DockWorkspaceHarness.qml"]
    for path in files:
        result = subprocess.run(
            [str(FORMATTER), "--newline", "unix", str(path)],
            capture_output=True,
            check=True,
        )
        formatted = result.stdout.replace(b"\r\r\n", b"\n").replace(b"\r\n", b"\n")
        assert formatted.strip(), path
        if formatted != path.read_bytes():
            changed.append(str(path))
            if not args.check:
                path.write_bytes(formatted)
    if args.check and changed:
        raise SystemExit("Unformatted Tactic Frame modules:\n" + "\n".join(changed))
    if files:
        print(
            f"{'Checked' if args.check else 'Formatted'} {len(files)} native renderers; {len(changed)} changed"
        )


if __name__ == "__main__":
    main()
