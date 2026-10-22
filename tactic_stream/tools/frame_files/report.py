"""Publish source-checked original, native Frame and browser file UI captures."""

import hashlib
import html
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / os.environ.get("FILES_FRAME_OUTPUT", "tools/frame_files/output")


def figure(label, image):
    assert (OUT / image).is_file(), image
    return (
        "<figure><figcaption>"
        + html.escape(label)
        + '</figcaption><a href="'
        + image
        + '"><img loading="lazy" src="'
        + image
        + '"></a></figure>'
    )


def main():
    native = json.loads((OUT / "native.json").read_text(encoding="utf-8"))
    browser = json.loads((OUT / "browser.json").read_text(encoding="utf-8"))
    assert browser["status"] == "passed"
    for prefix, files in [
        (ROOT / "src/tactic_stream/shared_ui", native["shared"]),
        (Path("D:/grav/Tactic Stream/TH"), native["nativeSources"]),
        (ROOT, native["driverSources"]),
        (ROOT, browser["browserSources"]),
    ]:
        for name, digest in files.items():
            assert hashlib.sha256((prefix / name).read_bytes()).hexdigest() == digest, (
                "Stale source: " + name
            )
    sections = []
    for row in browser["captures"]:
        title = " · ".join(
            str(row["fixture"][key])
            for key in ("screen", "style", "dark", "language", "width")
        )
        title += " · " + row.get("comparison", "full-content")
        images = [
            figure(label, row["image"].replace("-stream-", part))
            for label, part in [
                ("Original Handler", "-original-"),
                ("Frame Handler", "-native-"),
                ("Frame Stream", "-stream-"),
            ]
        ]
        sections.append(
            "<section><h2>"
            + html.escape(title)
            + '</h2><div class="trio">'
            + "".join(images)
            + "</div></section>"
        )
    for row in native["captures"]:
        if row["original"] or not row["fixture"].get("nativeOnly"):
            continue
        title = " · ".join(
            str(row["fixture"][key]) for key in ("screen", "language", "width")
        )
        images = [
            figure(
                "Original native capability",
                row["image"].replace("-native-", "-original-"),
            ),
            figure("Frame native capability", row["image"]),
        ]
        sections.append(
            "<section><h2>"
            + html.escape(title)
            + ' — native capability</h2><div class="trio">'
            + "".join(images)
            + "</div></section>"
        )
    content = """<!doctype html><meta charset="utf-8"><title>B12 files and queues</title>
<style>body{font:14px Segoe UI,sans-serif;background:#202426;color:#eee;margin:24px}section{margin:36px 0}.trio{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}figure{margin:0}img{width:100%;border:1px solid #555}figcaption{padding:8px}h2{font-size:16px}a{color:#8bc7ec}</style>
<h1>B12 — Files, check-in and repository queues</h1>"""
    content += (
        "<p>Pinned original Handler: "
        + native["reference"]
        + ". "
        + str(len(browser["captures"]))
        + " current Qt/Vue pairs at scale "
        + str(native["scale"])
        + ". Both use production components and isolated records. Source fingerprints are verified before/after capture and when this report is built.</p>"
    )
    content += "<p>Current Qt/Vue pairs check common rectangles, typography and paint. Local filesystem operations, DCC, Repository Sync, native Submit and mappings remain explicit native capabilities. Original screenshots are independent references; native window chrome and compositor shadows are outside content comparisons.</p>"
    content += "<p>Queue comparisons cover the shared pane geometry, source rows, summary and common form fields. Its native server-queue switch and local/DCC mode are separate capability regions, shown in the complete screenshots. These are marked shared-fragments, not full-content parity.</p>"
    content += "<p>Actual input, authenticated check-in/revision/lost-response journeys, cancellation/retry, large queues and server-preset publication have separate checks. Physical touch, OS IME, desktop capture pixels, compositor/DCC and production PostgreSQL require deployment acceptance.</p>"
    (OUT / "index.html").write_text(content + "".join(sections), encoding="utf-8")
    print("Fresh files report:", OUT / "index.html")


if __name__ == "__main__":
    main()
