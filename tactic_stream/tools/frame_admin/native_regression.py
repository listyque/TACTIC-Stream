"""Run native Frame regressions in independent Qt application processes."""

import argparse
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--failed", action="store_true")
parser.add_argument("--handler-root", type=Path, default=Path("D:/grav/Tactic Stream/TH"))
arguments = parser.parse_args()
ROOT = Path(__file__).resolve().parents[2]
TH = arguments.handler_root.resolve()
OUT = Path(__file__).resolve().parent / "output/native"
OUT.mkdir(parents=True, exist_ok=True)
os.environ.update(
    QT_QPA_PLATFORM="offscreen",
    QT_QUICK_BACKEND="software",
    TMP=str(ROOT / ".tmp/frame-tests"),
    TEMP=str(ROOT / ".tmp/frame-tests"),
)
sys.path.insert(0, str(TH))
if arguments.failed:
    rows = json.loads((OUT / "results.json").read_text(encoding="utf8"))
    for row in rows:
        if row["status"]:
            with (OUT / row["log"]).open("w", encoding="utf8") as log:
                try:
                    row["status"] = subprocess.run(
                        [
                            sys.executable,
                            "-B",
                            "-X",
                            "utf8",
                            "-X",
                            "faulthandler",
                            "-m",
                            "unittest",
                            "-q",
                            row["test"],
                        ],
                        cwd=TH,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        timeout=60,
                    ).returncode
                except subprocess.TimeoutExpired:
                    row["status"] = "timeout"
            print(row["test"], row["status"], flush=True)
    (OUT / "results.json").write_text(json.dumps(rows, indent=2), encoding="utf8")
    failed = sum(row["status"] != 0 for row in rows)
    print(json.dumps(dict(tests=len(rows), passed=len(rows) - failed, failed=failed)))
    raise SystemExit(bool(failed))

modules = [
    "test_administration_qml",
    "test_process_rules_qml",
    "test_admin_groups_ui",
    "test_admin_users_ui",
    "test_admin_security_ui",
    "test_raw_database",
    "test_search_type_columns",
    "test_admin_search_types",
    "test_columns_table_view",
    "test_layout_editor",
    "test_administration_documents",
    "test_schema_connections",
    "test_schema_node_actions",
    "test_process_rules",
    "test_naming_editor",
    "test_sidebar_editor_qml",
    "test_sidebar_editor",
    "test_administration_access",
    "test_schema_connection_qml",
    "test_schema_type_creation",
    "test_administration_api",
    "test_admin_security_matrix",
    "test_administration_menu_qml",
]


def cases(suite):
    for child in suite:
        if isinstance(child, unittest.TestSuite):
            yield from cases(child)
        else:
            yield child.id()


results = []
for module in modules:
    names = list(cases(unittest.defaultTestLoader.loadTestsFromName("tests." + module)))
    for name in names:
        filename = f"{len(results):04d}.log"
        with (OUT / filename).open("w", encoding="utf8") as log:
            try:
                status = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        "-X",
                        "utf8",
                        "-X",
                        "faulthandler",
                        "-m",
                        "unittest",
                        "-q",
                        name,
                    ],
                    cwd=TH,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    timeout=60,
                ).returncode
            except subprocess.TimeoutExpired:
                status = "timeout"
        results.append(dict(test=name, status=status, log=filename))
        if status:
            print("FAIL", name, status, flush=True)
    print(module, len(names), "checked", flush=True)
    (OUT / "results.json").write_text(json.dumps(results, indent=2), encoding="utf8")
failed = sum(row["status"] != 0 for row in results)
print(json.dumps(dict(tests=len(results), passed=len(results) - failed, failed=failed)))
raise SystemExit(bool(failed))
