"""Reject stale B13 evidence and generate the original/native/Vue review grid."""

import hashlib
import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "output"


def main():
    native = json.loads((OUT / "native.json").read_text(encoding="utf-8"))
    browser = json.loads((OUT / "browser.json").read_text(encoding="utf-8"))
    assert native["status"] == "captured" and browser["status"] == "passed"
    assert not native["quick"] and not browser["quick"], (
        "Quick previews cannot close B13"
    )
    for sources, root in (
        (native["sha256"], ROOT / "src/tactic_stream/shared_ui"),
        (native["nativeSources"], Path("D:/grav/Tactic Stream/TH")),
        (browser["webSources"], ROOT),
        (native["driverSources"], ROOT),
    ):
        for name, expected in sources.items():
            assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected, (
                "Stale evidence: " + name
            )
    assert (
        native["sha256"] == browser["sha256"]
        and native["nativeSources"] == browser["nativeSources"]
    )
    assert (
        hashlib.sha256(
            (ROOT / ".tmp/b13/original-handler.zip").read_bytes()
        ).hexdigest()
        == native["archiveSha256"]
    )
    keys = ("screen", "style", "dark", "language", "width", "height", "case")
    signature = lambda row: tuple(row[key] for key in keys)
    originals = {signature(row): row for row in native["captures"] if row["original"]}
    current = {signature(row): row for row in native["captures"] if not row["original"]}
    web = {signature(row): row for row in browser["captures"]}
    assert originals.keys() == current.keys()
    assert len(current) == 8 * 3 * 2 * 2 * 2 * 2
    assert len(web) == 3 * 3 * 2 * 2 * 2 * 2
    assert web.keys() == {
        key for key in current if key[0] in ("editor", "shelf", "bar")
    }
    cards = []
    for key, row in current.items():
        images = []
        for title, record in (
            ("Original QML", originals[key]),
            ("Current native", row),
            ("Vue shared composition", web.get(key)),
        ):
            if record:
                assert (OUT / record["file"]).is_file()
                images.append(
                    "<figure><figcaption>"
                    + title
                    + '</figcaption><a href="'
                    + record["file"]
                    + '"><img loading="lazy" src="'
                    + record["file"]
                    + '"></a></figure>'
                )
            else:
                images.append("<p>Native tool. No additional browser version.</p>")
        label = " · ".join(str(value) for value in key)
        cards.append(
            '<section data-label="'
            + escape(label, quote=True)
            + '"><h2>'
            + escape(label)
            + '</h2><div class="grid">'
            + "".join(images)
            + "</div></section>"
        )
    html = (
        """<!doctype html><html lang="en"><meta charset="utf-8"><title>B13 scripts and tools</title><style>body{font:15px Segoe UI,sans-serif;background:#202427;color:#eef1f3;margin:24px}input{width:90%;padding:12px;position:sticky;top:0}section{border-top:1px solid #687078;padding:16px 0}h2{font-size:16px}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}figure{margin:0}img{width:100%;height:auto}figcaption{margin-bottom:8px}p{max-width:1050px}</style><h1>B13 · Scripts and native tools</h1><p>Immutable pre-B13 QML → current native → current Vue compositions. Three themes, light/dark, EN/RU, 720/900 px, normal/locked states. Corresponding Frame controls are checked for geometry, typography, color and indicator placement. Existing typed code/tree/tab presenters and native-only execution capabilities are not a claim of full pixel identity. Full execution/save/recovery workflows run separately.</p><input id="filter" placeholder="Filter screen, style, language, width or case">"""
        + "".join(cards)
        + """<script>document.querySelector('#filter').oninput=event=>{for(const row of document.querySelectorAll('section'))row.hidden=!row.dataset.label.toLowerCase().includes(event.target.value.toLowerCase());};</script></html>"""
    )
    (OUT / "index.html").write_text(html, encoding="utf-8")
    (OUT / "report.json").write_text(
        json.dumps(
            {
                "status": "passed",
                "originalNativePairs": len(current),
                "nativeVuePairs": len(web),
                "rectangles": sum(row["count"]["rectangles"] for row in web.values()),
                "styles": sum(row["count"]["styles"] for row in web.values()),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        "PASS",
        len(current),
        "original/native surfaces and",
        len(web),
        "native/Vue compositions",
    )


if __name__ == "__main__":
    main()
