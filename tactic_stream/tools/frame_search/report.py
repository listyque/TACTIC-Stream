"""Build the local review page from fresh search captures and input results."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "output"


def main():
    native = json.loads((OUT / "native.json").read_text(encoding="utf-8"))
    browser = json.loads((OUT / "browser.json").read_text(encoding="utf-8"))
    assert native["status"] == "captured" and browser["status"] == "passed"
    for prefix, sources in (
        (ROOT / "src/tactic_stream/shared_ui", native["sha256"]),
        (Path("D:/code/th_codex"), native["nativeSources"]),
        (ROOT, native.get("driverSources", {})),
        (ROOT, browser["browserSources"]),
    ):
        for name, digest in sources.items():
            assert hashlib.sha256((prefix / name).read_bytes()).hexdigest() == digest, (
                name
            )
    payload = json.dumps(
        dict(native=native, browser=browser), ensure_ascii=False
    ).replace("</", "<\\/")
    template = (Path(__file__).parent / "report.html").read_text(encoding="utf-8")
    (OUT / "index.html").write_text(
        template.replace("__SEARCH_DATA__", payload), encoding="utf-8"
    )
    print("Fresh search comparison:", OUT / "index.html")


if __name__ == "__main__":
    main()
