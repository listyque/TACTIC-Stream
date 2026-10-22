"""Publish source-checked original / Frame Handler / Frame Stream captures."""

import hashlib
import html
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / os.environ.get("MESSAGES_FRAME_OUTPUT", "tools/frame_messages/output")


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
        figures = []
        for label, part in [
            ("Original Handler", "-original-"),
            ("Frame Handler", "-native-"),
            ("Frame Stream", "-stream-"),
        ]:
            image = row["image"].replace("-stream-", part)
            assert (OUT / image).is_file(), "Missing capture: " + image
            figures.append(
                "<figure><figcaption>"
                + label
                + '</figcaption><a href="'
                + image
                + '"><img loading="lazy" src="'
                + image
                + '"></a></figure>'
            )
        sections.append(
            "<section><h2>"
            + html.escape(title)
            + '</h2><div class="trio">'
            + "".join(figures)
            + "</div></section>"
        )
    content = """<!doctype html><meta charset="utf-8"><title>B11 communication</title>
<style>body{font:14px Segoe UI,sans-serif;background:#202426;color:#eee;margin:24px}section{margin:36px 0}.trio{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}figure{margin:0}img{width:100%;border:1px solid #555}figcaption{padding:8px}h2{font-size:16px}a{color:#8bc7ec}</style>
<h1>B11 — Messages, activity and notifications</h1>"""
    content += (
        "<p>Pinned original Handler: "
        + native["reference"]
        + ". "
        + str(len(browser["captures"]))
        + " current Qt/Vue pairs at scale "
        + str(native["scale"])
        + ". Both use real production components and identical isolated records. Native text fonts are verified; source fingerprints are checked before and after capture and again when this report is built.</p>"
    )
    content += "<p>The original column remains an independent visual reference, not a claim of pixel identity with the new Frame rendering. Current pairs check common node bounds, typography and paint. Rich text keeps native selectable ports; the activity port uses Frame font advances to match browser wrapping. Scrollbar room, natural message width and popup dimensions are explicit.</p>"
    content += "<p>Handler alone exposes Repository Sync history and local file/cancel operations. Stream retains its phone composition, browser downloads and file reselection after reload. Window chrome and OS shadows are outside content comparisons. Original forms/popups are cropped from their actual owners; original toasts are captured from the original NotificationStack.</p>"
    content += "<p>These fixtures do not replace authenticated workflows. Sending, attachments, rights, read state, expiry and notification actions have separate private-server/native input checks. Physical touch, OS IME, compositor boundaries and production PostgreSQL remain outside this report.</p>"
    (OUT / "index.html").write_text(content + "".join(sections), encoding="utf-8")
    print("Fresh communication report:", OUT / "index.html")


if __name__ == "__main__":
    main()
