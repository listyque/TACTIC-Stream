"""Verify the real toolbar in original Handler, Frame Handler and Stream."""

import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", action="store_true")
    args = parser.parse_args()
    sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "tests")]
    os.environ.update(
        PLAYWRIGHT_BROWSERS_PATH=str(ROOT / ".browser-cache"),
        TMP=str(ROOT / ".tmp/frame-tests"),
        TEMP=str(ROOT / ".tmp/frame-tests"),
    )
    for arguments in [[], ["--original"]]:
        subprocess.run(
            [
                sys.executable,
                "-B",
                "-X",
                "utf8",
                "tools/frame_foundation/main_qml.py",
                *arguments,
                *(["--workspace"] if args.workspace else []),
            ],
            cwd=ROOT,
            check=True,
            timeout=120 if args.workspace else 40,
        )

    from test_transport import Transport

    # This UI-only fixture never resets a directory while its collectors own it.
    Transport.setUpClass()
    try:
        subprocess.run(
            [
                "node",
                "tests/frame_main_browser.mjs",
                Transport.url,
                *(["--workspace"] if args.workspace else []),
            ],
            cwd=ROOT / "frontend",
            check=True,
            timeout=180 if args.workspace else 60,
        )
    finally:
        Transport.tearDownClass()


if __name__ == "__main__":
    main()
