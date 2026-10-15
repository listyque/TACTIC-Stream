#!/usr/bin/env python3
"""Run existing test_*.cjs files separately; record actual suite exit codes.

This handoff helper does not edit application sources or start TACTIC.
A suite count is NOT a count of individual assertions/tests.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="TACTIC-5.0 source root")
    parser.add_argument("--output", type=Path, required=True, help="Directory for private logs/report")
    parser.add_argument("--node", default="node", help="Node executable, not a command string")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout per suite in seconds")
    args = parser.parse_args()
    root = args.root.expanduser().resolve()
    test_dir = root / "tests" / "native_ui"
    suites = sorted(test_dir.glob("test_*.cjs")) if test_dir.is_dir() else []
    if not suites or not (root / "NATIVE_UI_VERSION").is_file():
        parser.error("Not a recognized TACTIC source root, or no JavaScript suites were found")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    node = shutil.which(args.node)
    if node is None:
        parser.error("Node executable not found; specify --node with an existing executable")
    out = args.output.expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    report = {
        "source_root": str(root),
        "native_version": (root / "NATIVE_UI_VERSION").read_text(encoding="utf-8").strip(),
        "scope": "Separate existing JS suites; suite count is not individual test count",
        "started_unix": time.time(),
        "passed": False,
        "suites": [],
    }
    report_file = out / "js-suite-summary.json"
    try:
        for path in suites:
            command = [node, str(path)]
            log = out / (path.stem + ".log")
            started = time.monotonic()
            item = {"suite": path.name, "command": command, "log": str(log)}
            try:
                with log.open("wb") as stream:
                    completed = subprocess.run(
                        command, cwd=root, stdout=stream, stderr=subprocess.STDOUT,
                        timeout=args.timeout, check=False,
                    )
                item.update(returncode=completed.returncode,
                            status="passed" if completed.returncode == 0 else "failed")
            except subprocess.TimeoutExpired:
                item.update(returncode=None, status="timeout")
            except OSError as exc:
                item.update(returncode=None, status="launch_failed", error=str(exc))
            item["duration_seconds"] = round(time.monotonic() - started, 3)
            report["suites"].append(item)
            report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"{item['status']}: {path.name}", flush=True)
        report["passed"] = bool(report["suites"]) and all(
            item["status"] == "passed" for item in report["suites"]
        )
    except KeyboardInterrupt:
        report["interrupted"] = True
    finally:
        report["completed_unix"] = time.time()
        report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
