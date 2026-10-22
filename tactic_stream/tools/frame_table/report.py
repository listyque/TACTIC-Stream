"""Build a review page only when both table captures match current sources."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent / "output"


def main():
    native = json.loads((OUT / "native.json").read_text(encoding="utf-8"))
    browser = json.loads((OUT / "browser.json").read_text(encoding="utf-8"))
    inventory = json.loads((OUT / "inventory.json").read_text(encoding="utf-8"))
    assert native["status"] == "captured" and browser["status"] == "passed"
    for prefix, sources in (
        (ROOT / "src/tactic_stream/shared_ui", native["sha256"]),
        (Path("D:/grav/Tactic Stream/TH"), native["nativeSources"]),
        (ROOT, native["driverSources"]),
        (ROOT, browser["browserSources"]),
    ):
        for name, digest in sources.items():
            assert hashlib.sha256((prefix / name).read_bytes()).hexdigest() == digest, (
                name
            )
    payload = json.dumps(
        dict(native=native, browser=browser, inventory=inventory), ensure_ascii=False
    ).replace("</", "<\\/")
    template = (Path(__file__).parent / "report.html").read_text(encoding="utf-8")
    (OUT / "index.html").write_text(
        template.replace("__TABLE_DATA__", payload), encoding="utf-8"
    )
    print("Fresh table comparison:", OUT / "index.html")


if __name__ == "__main__":
    main()
