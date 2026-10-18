"""Reject stale/partial B14 evidence and build the reviewable comparison grid."""

import argparse
import hashlib
import json
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "output"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handler-root", type=Path, required=True)
    parser.add_argument("--reference-archive", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT / "tools/frame_foundation"))
    from check_platform import fingerprints

    gate = json.loads(
        (ROOT / "tools/frame_foundation/output/platform/gate.json").read_text("utf-8")
    )
    assert gate["status"] == "passed", (
        "The integrated platform gate must pass before release"
    )
    assert gate["sources"] == fingerprints(args.handler_root), "Stale platform gate"
    native = json.loads((OUT / "native.json").read_text("utf-8"))
    browser = json.loads((OUT / "browser.json").read_text("utf-8"))
    workflows = json.loads((OUT / "workflows.json").read_text("utf-8"))
    coverage = json.loads((OUT / "coverage.json").read_text("utf-8"))
    assert (
        native["status"] == "captured"
        and browser["status"] == workflows["status"] == "passed"
    )
    assert not native["quick"] and not browser["quick"], (
        "Quick previews cannot close B14"
    )
    for sources, root in (
        (native["sha256"], ROOT / "src/tactic_stream/shared_ui"),
        (native["nativeSources"], args.handler_root),
        (native["driverSources"], ROOT),
        (browser["webSources"], ROOT),
        (workflows["sources"], ROOT),
    ):
        for name, expected in sources.items():
            assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected, (
                "Stale evidence: " + name
            )
    assert native["sha256"] == browser["sha256"]
    assert native["nativeSources"] == browser["nativeSources"]
    assert (
        hashlib.sha256(args.reference_archive.read_bytes()).hexdigest()
        == native["archiveSha256"]
    )
    assert (
        hashlib.sha256((OUT.parent / "surfaces.json").read_bytes()).hexdigest()
        == coverage["ledgerSha256"]
    )
    inventory = json.loads(
        (ROOT / "tools/frame_foundation/output/inventory.json").read_text("utf-8")
    )
    for product, root in (("handler", args.handler_root), ("stream", ROOT)):
        assert inventory[product]["hashes"] == coverage["inventoryHashes"][product]
        for name, expected in inventory[product]["hashes"].items():
            assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected, (
                "Stale inventory: " + name
            )
    keys = ("screen", "style", "dark", "language", "width", "height", "locked")
    signature = lambda row: tuple(row[key] for key in keys)
    panels = {signature(row): row for row in native["captures"] if row["panel"]}
    originals = {signature(row): row for row in native["captures"] if row["original"]}
    production = {
        signature(row): row
        for row in native["captures"]
        if not row["original"] and not row["panel"]
    }
    web = {signature(row): row for row in browser["captures"]}
    assert len(panels) == len(web) == 10 * 3 * 2 * 2 * 3 * 2
    assert len(production) == len(originals) == 11 * 2 * 2
    assert panels.keys() == web.keys() and originals.keys() == production.keys()
    cards = []
    for native_rows, other_rows, first, second in (
        (
            production,
            originals,
            "Current native production",
            "Original native production",
        ),
        (panels, web, "Current native composition", "Current Vue composition"),
    ):
        for key, row in native_rows.items():
            pictures = []
            for title, record in ((first, row), (second, other_rows[key])):
                assert (OUT / record["file"]).is_file()
                pictures.append(
                    "<figure><figcaption>"
                    + title
                    + '</figcaption><a href="'
                    + record["file"]
                    + '"><img loading="lazy" src="'
                    + record["file"]
                    + '"></a></figure>'
                )
            title = " · ".join(str(value) for value in key)
            cards.append(
                '<section data-label="'
                + escape(title, quote=True)
                + '"><h2>'
                + escape(title)
                + '</h2><div class="grid">'
                + "".join(pictures)
                + "</div></section>"
            )
    (OUT / "index.html").write_text(
        '<!doctype html><meta charset="utf-8"><title>B14 remaining surfaces</title><style>body{font:15px Segoe UI;background:#202427;color:#eee;margin:24px}input{width:90%;padding:12px;position:sticky;top:0}section{border-top:1px solid #687078;padding:16px 0}h2{font-size:16px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}figure{margin:0}img{width:100%;height:auto}</style>'
        "<h1>B14 · Remaining surfaces</h1><p>Knowledge Base, Work Hours, shared schema confirmation, API and journal adapters. 720 matched compositions across three themes, light/dark, EN/RU, 430/900/1200px, normal/locked; 44 immutable original/current native production pairs. Geometry, color, typography and indicators are checked for corresponding Frame controls. Rich text, engine text rasterization and client-specific capabilities retain typed presenters; this is not full-screen pixel parity.</p>"
        '<p><a href="coverage.html">Complete source ownership ledger</a> · <a href="workflows.json">Connected input/lifecycle workflows</a> · <a href="../../frame_foundation/output/platform/gate.json">Integrated platform gate</a>. B07 remains open (40 legacy widget classes).</p>'
        '<input placeholder="Filter screen, theme, language, width or state" oninput="for(const row of document.querySelectorAll(\'section\'))row.hidden=!row.dataset.label.toLowerCase().includes(this.value.toLowerCase())">'
        + "".join(cards),
        "utf-8",
    )
    result = {
        "status": "passed",
        "originalNativePairs": len(production),
        "nativeVuePairs": len(web),
        "sourceClassifications": coverage["sources"],
        "platformStages": len(gate["steps"]),
        "rectangles": sum(row["count"]["rectangles"] for row in web.values()),
        "styles": sum(row["count"]["styles"] for row in web.values()),
        "limits": coverage["limits"],
    }
    (OUT / "report.json").write_text(json.dumps(result, indent=2) + "\n", "utf-8")
    print("PASS", result)


if __name__ == "__main__":
    main()
