"""Source-checked original / Frame QML / Frame Vue review gallery."""

import hashlib
import html
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / os.environ.get("SCHEDULE_FRAME_OUTPUT", "tools/frame_schedule/output")


def main():
    native = json.loads((OUT / "native.json").read_text(encoding="utf-8"))
    browser = json.loads((OUT / "browser.json").read_text(encoding="utf-8"))
    assert browser["status"] == "passed"
    for prefix, sources in [
        (ROOT / "src/tactic_stream/shared_ui", native["shared"]),
        (Path("D:/code/th_codex"), native["nativeSources"]),
        (ROOT, native["driverSources"]),
        (ROOT, browser["browserSources"]),
    ]:
        for name, digest in sources.items():
            assert hashlib.sha256((prefix / name).read_bytes()).hexdigest() == digest, (
                "Stale source: " + name
            )
    cards = []
    for row in browser["captures"]:
        title = " · ".join(
            str(row["fixture"][key])
            for key in ("screen", "style", "dark", "language", "width")
        )
        images = [
            row["image"].replace("-stream-", part)
            for part in ("-original-", "-native-", "-stream-")
        ]
        cards.append(
            "<section><h2>"
            + html.escape(title)
            + '</h2><div class="trio">'
            + "".join(
                "<figure><figcaption>"
                + label
                + '</figcaption><a href="'
                + image
                + '"><img src="'
                + image
                + '" loading="lazy"></a></figure>'
                for label, image in zip(
                    ("Original Handler", "Frame Handler", "Frame Stream"), images
                )
            )
            + "</div></section>"
        )
    content = """<!doctype html><meta charset="utf-8"><title>B10 production scheduling</title>
<style>body{font:14px Segoe UI,sans-serif;background:#202426;color:#eee;margin:24px}section{margin:36px 0}.trio{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}figure{margin:0}img{width:100%;border:1px solid #555}figcaption{padding:8px}h2{font-size:16px}a{color:#8bc7ec}</style>
<h1>B10 — Production Gantt, calendar and milestones</h1>"""
    content += (
        "<p>Pinned original: "
        + native["reference"]
        + ". "
        + str(len(browser["captures"]))
        + " paired states; current shared geometry, typography and paint checked in both production renderers. Original differences remain visible for review.</p>"
    )
    content += "<p>Common dependencies use loaded task IDs only. The new explicit native schedule form and native Agenda are additions to the original; server writes, revisions and client capabilities stay with the existing owners. Physical touch hardware and OS IME are separate acceptance.</p>"
    content += "<p>For editor rows the original column shows the original Gantt: it had no direct schedule form. The two current columns show the actual production form content. Two original milestone warnings reference the missing Theme.controlRadius; current captures allow no warnings.</p>"
    (OUT / "index.html").write_text(content + "".join(cards), encoding="utf-8")
    print("Fresh schedule review:", OUT / "index.html")


if __name__ == "__main__":
    main()
