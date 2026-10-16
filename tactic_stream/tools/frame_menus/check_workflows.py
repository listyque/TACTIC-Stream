"""Exercise shipped main menus against a private disposable server fixture."""

import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "output"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "tests")]
    os.environ.update(
        TMP=str(ROOT / ".tmp/frame-tests"), TEMP=str(ROOT / ".tmp/frame-tests")
    )
    from test_transport import Transport

    Transport.setUpClass()
    try:
        environment = dict(
            os.environ,
            STREAM_CHECK_LOGIN="admin",
            STREAM_CHECK_PASSWORD="private-test-password",
            STREAM_CHECK_PROJECT="one",
        )
        for name in ("main_shortcuts", "connection_menu"):
            with (OUT / (name + ".log")).open("w", encoding="utf-8") as log:
                result = subprocess.run(
                    ["node", "tests/" + name + ".mjs", Transport.url],
                    cwd=ROOT / "frontend",
                    env=environment,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    timeout=90,
                )
            assert result.returncode == 0, f"{name}: see {OUT / (name + '.log')}"
            print(name, "passed", flush=True)
    finally:
        Transport.tearDownClass()


if __name__ == "__main__":
    main()
