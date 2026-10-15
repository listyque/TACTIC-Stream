"""Compare two known offscreen menu failures against the independent Handler archive."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
HANDLER = Path("D:/code/th_codex")
OUT = Path(__file__).with_name("output") / "menu-baseline"
ARCHIVE = ROOT.parent / "backups/2026-10-15_103116_before_shared_ui_foundation/TH.zip"
CASES = [
    (
        "test_touch_controls",
        "TouchControlTests.test_touch_opens_action_menu_and_activates_its_item",
    ),
    (
        "test_compact_menus_qml",
        "CompactMenuTests.test_dock_groups_retain_all_panels_and_live_checks",
    ),
]


def child(qml, index):
    sys.path.insert(0, str(HANDLER))
    name, case = CASES[index]
    module = __import__("tests." + name, fromlist=[name])
    module.QML = qml
    result = unittest.TextTestRunner().run(
        unittest.defaultTestLoader.loadTestsFromName(case, module)
    )
    return int(not result.wasSuccessful())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qml-root", type=Path)
    parser.add_argument("--case", type=int, choices=range(len(CASES)))
    args = parser.parse_args()
    if args.qml_root:
        return child(args.qml_root, args.case)
    OUT.mkdir(parents=True, exist_ok=True)
    reference = OUT / "reference"
    with ZipFile(ARCHIVE) as archive:
        for name in archive.namelist():
            if name.endswith("/") or not name.startswith(
                ("thlib/ui/qml/", "thlib/ui/assets/fonts/")
            ):
                continue
            target = (reference / name).resolve()
            assert target.is_relative_to(reference.resolve())
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(name))
    environment = dict(
        os.environ, QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software"
    )
    rows = []
    for index, (module, case) in enumerate(CASES):
        row = dict(test=module + "." + case)
        for label, source in (
            ("original", reference / "thlib/ui/qml"),
            ("current", HANDLER / "thlib/ui/qml"),
        ):
            log = OUT / f"{index}-{label}.log"
            with log.open("w", encoding="utf-8") as stream:
                process = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        "-X",
                        "utf8",
                        __file__,
                        "--qml-root",
                        str(source.resolve()),
                        "--case",
                        str(index),
                    ],
                    cwd=ROOT,
                    env=environment,
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                    timeout=30,
                )
            row[label] = process.returncode
        assert row["original"] == row["current"], row
        rows.append(row)
    report = dict(
        platform="offscreen",
        archive_sha256=hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(),
        cases=rows,
        claim="No new failures in these cases; failing cases still require a window-system backend.",
    )
    (OUT / "results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
