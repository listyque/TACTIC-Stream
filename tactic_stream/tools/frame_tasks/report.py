"""Build the source-checked, three-column task review gallery."""

import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / os.environ.get("TASK_FRAME_OUTPUT", "tools/frame_tasks/output")


def main():
    native = json.loads((OUT / "native.json").read_text(encoding="utf-8"))
    browser = json.loads((OUT / "browser.json").read_text(encoding="utf-8"))
    assert browser["status"] == "passed"
    for prefix, sources in (
        (ROOT / "src/tactic_stream/shared_ui", native["shared"]),
        (Path("D:/code/th_codex"), native["nativeSources"]),
        (ROOT, native["driverSources"]),
        (ROOT, browser["browserSources"]),
    ):
        for name, digest in sources.items():
            assert hashlib.sha256((prefix / name).read_bytes()).hexdigest() == digest, (
                "Stale source: " + name
            )
    payload = json.dumps(
        dict(native=native, browser=browser), ensure_ascii=False
    ).replace("</", "<\\/")
    template = (Path(__file__).parent / "report.html").read_text(encoding="utf-8")
    (OUT / "index.html").write_text(
        template.replace("__TASKS_DATA__", payload), encoding="utf-8"
    )
    print("Fresh task comparison:", OUT / "index.html")


if __name__ == "__main__":
    main()
