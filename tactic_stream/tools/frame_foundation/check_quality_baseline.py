"""Compare existing QML quality debt with the verified pre-migration archive."""

import argparse
import ast
from collections import Counter
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
TH = Path("D:/code/th_codex")
HERE = Path(__file__).resolve().parent
REFERENCE = HERE / "reference/quality"
OUTPUT = HERE / "output/quality"
ARCHIVE = ROOT.parent / "backups/2026-10-15_103116_before_shared_ui_foundation/TH.zip"


def original_sources():
    with ZipFile(ARCHIVE) as archive:
        for name in archive.namelist():
            source = Path(name)
            code = (
                name.startswith(("thlib/", "docs/", "tests/contracts/"))
                or name == "tests/test_ui_structure.py"
            )
            source_file = (
                source.suffix in (".py", ".qml", ".mjs", ".js", ".json", ".md")
                or source.name == "qmldir"
            )
            image = name in (
                "thlib/ui/assets/chat_bg_dark.png",
                "thlib/ui/assets/chat_bg_light.png",
                "thlib/ui/assets/tactic_favicon.ico",
            )
            if not ((code and source_file) or image):
                continue
            target = (REFERENCE / name).resolve()
            assert target.is_relative_to(REFERENCE.resolve())
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(name))


def content_sources():
    source = (REFERENCE / "thlib/ui/workspace_models/windows.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    model = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "FloatingWindowModel"
    )
    return next(
        ast.literal_eval(node.value)
        for node in model.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "_content_sources"
            for target in node.targets
        )
    )


def structure(directory, name):
    spec = importlib.util.spec_from_file_location(
        name, directory / "tests/test_ui_structure.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = unittest.TestResult()
    unittest.defaultTestLoader.loadTestsFromModule(module).run(result)
    return dict(
        tests=result.testsRun,
        failures=sorted(
            test._testMethodName for test, error in result.failures + result.errors
        ),
    )


def lint(directory):
    from tests.test_qml_lint import _qmllint_path

    files = sorted(directory.rglob("*.qml"))
    counts = Counter()
    diagnostics = []
    for offset in range(0, len(files), 25):
        command = [
            _qmllint_path(),
            "--json",
            "-",
            "-I",
            str(directory),
            *map(str, files[offset : offset + 25]),
        ]
        result = subprocess.run(
            command,
            cwd=TH,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
            timeout=30,
        )
        for record in json.loads(result.stdout)["files"]:
            counts.update(warning["id"] for warning in record.get("warnings", []))
            diagnostics.append(record)
    label = "before" if directory.is_relative_to(REFERENCE) else "current"
    (OUTPUT / ("lint-" + label + ".json")).write_text(
        json.dumps(diagnostics, indent=2), encoding="utf-8"
    )
    return dict(counts)


def smoke(label):
    with tempfile.TemporaryDirectory(dir=ROOT / ".tmp/frame-tests") as settings:
        os.environ.update(
            QT_QPA_PLATFORM="offscreen",
            QT_QUICK_BACKEND="software",
            QSG_RENDER_LOOP="basic",
            TACTIC_QML_SMOKE_WINDOWS="1",
            TACTIC_QML_SMOKE_OFFLINE="1",
            TACTIC_QML_TEST_SETTINGS_DIR=settings,
            LOCALAPPDATA=settings,
            APPDATA=settings,
            QT_QPA_FONTDIR="C:/Windows/Fonts",
            PYTHONDONTWRITEBYTECODE="1",
        )
        from thlib.ui import application
        from thlib.ui.workspace_models.windows import FloatingWindowModel

        if label == "before":
            application.UI_ROOT = REFERENCE / "thlib/ui"
            FloatingWindowModel._content_sources = content_sources()
        original_show = FloatingWindowModel.show_window
        original_write = application._write_stderr
        current = ["main"]
        messages = []

        def show(self, identity):
            current[0] = identity
            return original_show(self, identity)

        def record(message):
            messages.append(dict(window=current[0], text=str(message)))
            original_write(message)

        FloatingWindowModel.show_window = show
        application._write_stderr = record
        status = application.main()
        fonts = [
            row
            for row in messages
            if "Both point size and pixel size set" in row["text"]
        ]
        result = dict(
            status=status,
            fontWarnings=dict(Counter(row["window"] for row in fonts)),
            other=[row for row in messages if row not in fonts],
        )
        (OUTPUT / ("smoke-" + label + ".json")).write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )


def main():
    global ARCHIVE, REFERENCE, OUTPUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reference-archive",
        type=Path,
        help="Verified archive before the current migration batch",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Separate output and extracted reference for a batch comparison",
    )
    parser.add_argument(
        "--smoke", choices=("before", "current"), help=argparse.SUPPRESS
    )
    arguments = parser.parse_args()
    if arguments.reference_archive:
        assert arguments.output, "A batch baseline requires a separate output directory"
        ARCHIVE = arguments.reference_archive.resolve()
        REFERENCE = arguments.output.resolve() / "reference"
    if arguments.output:
        OUTPUT = arguments.output.resolve()
    sys.path.insert(0, str(TH))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if arguments.smoke:
        sys.argv = [sys.argv[0]]
        smoke(arguments.smoke)
        return
    original_sources()
    from thlib.ui.workspace_models.windows import FloatingWindowModel

    with patch.object(FloatingWindowModel, "_content_sources", content_sources()):
        before = structure(REFERENCE, "archived_structure")
    current = structure(TH, "current_structure")
    new_structure = sorted(set(current["failures"]) - set(before["failures"]))
    lint_before, lint_current = (
        lint(REFERENCE / "thlib/ui/qml"),
        lint(TH / "thlib/ui/qml"),
    )
    new_lint = {
        name: count
        for name, count in lint_current.items()
        if count > lint_before.get(name, 0)
    }
    for label in ("before", "current"):
        with (OUTPUT / ("smoke-" + label + ".log")).open("w", encoding="utf-8") as log:
            command = [sys.executable, "-B", "-X", "utf8", __file__, "--smoke", label]
            if arguments.reference_archive:
                command += ["--reference-archive", str(ARCHIVE)]
            if arguments.output:
                command += ["--output", str(OUTPUT)]
            subprocess.run(
                command,
                cwd=ROOT,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
                timeout=60,
            )
    smoke_before = json.loads((OUTPUT / "smoke-before.json").read_text())
    smoke_current = json.loads((OUTPUT / "smoke-current.json").read_text())
    report = dict(
        structure=dict(before=before, current=current, regressions=new_structure),
        lint=dict(before=lint_before, current=lint_current, regressions=new_lint),
        smoke=dict(before=smoke_before, current=smoke_current),
    )
    (OUTPUT / "baseline.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    assert not new_structure and not new_lint, report
    assert smoke_before["status"] == smoke_current["status"] == 0, report["smoke"]
    assert not smoke_current["fontWarnings"], report["smoke"]
    assert not smoke_before["other"] and not smoke_current["other"], report["smoke"]
    print(
        "No new structure/lint debt; current native smoke has no font/runtime warnings. Remaining unrelated gate failures are explicit in baseline.json"
    )


if __name__ == "__main__":
    main()
