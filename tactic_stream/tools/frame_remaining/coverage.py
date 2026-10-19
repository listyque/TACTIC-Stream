"""Check the explicit source ledger against a fresh complete UI inventory.

Classification is a routing/ownership check, not runtime or pixel acceptance.
The platform gate and each batch's workflow evidence remain separate.
"""

import hashlib
import json
from collections import Counter
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def check(inventory, ledger):
    expected = {
        (product, record["file"])
        for product in ("handler", "stream")
        for record in inventory[product]["files"]
    }
    actual = [(row["product"], row["file"]) for row in ledger["sources"]]
    assert len(actual) == len(set(actual)), "Duplicate surface classification"
    assert expected == set(actual), {
        "unclassified": sorted(expected - set(actual)),
        "removed": sorted(set(actual) - expected),
    }
    for row in ledger["sources"]:
        assert row["batch"] in {f"B{number:02d}" for number in range(1, 15)}
        assert row["disposition"] in ledger["dispositions"]
        if row["batch"] == "B07":
            assert row["disposition"] == "B07 partial"


def main():
    inventory = json.loads(
        (ROOT / "tools/frame_foundation/output/inventory.json").read_text("utf-8")
    )
    ledger_path = HERE / "surfaces.json"
    ledger = json.loads(ledger_path.read_text("utf-8"))
    check(inventory, ledger)
    # Ensure omissions cannot silently pass when a new source is introduced.
    incomplete = dict(ledger, sources=ledger["sources"][1:])
    try:
        check(inventory, incomplete)
    except AssertionError:
        pass
    else:
        raise AssertionError("Missing-source guard failed")
    counts = Counter(row["batch"] for row in ledger["sources"])
    output = HERE / "output"
    output.mkdir(parents=True, exist_ok=True)
    report = {
        "status": "classified",
        "scope": ledger["scope"],
        "sources": len(ledger["sources"]),
        "batches": dict(sorted(counts.items())),
        "ledgerSha256": hashlib.sha256(ledger_path.read_bytes()).hexdigest(),
        "inventoryHashes": {
            product: inventory[product]["hashes"] for product in ("handler", "stream")
        },
        "limits": [
            "B07 remains incomplete: remaining configured widgets/options need complete workflows; see docs/frame_table.md.",
            "Source ownership is not proof of full screen parity; typed presenters and client capabilities remain explicit.",
            "User scripts, plugin and DCC-generated UI keep their native execution owner and require their own runtime checks.",
        ],
    }
    (output / "coverage.json").write_text(json.dumps(report, indent=2) + "\n", "utf-8")
    rows = "".join(
        "<tr>"
        + "".join(
            "<td>" + escape(row[key]) + "</td>"
            for key in ("product", "file", "batch", "role", "disposition")
        )
        + "</tr>"
        for row in ledger["sources"]
    )
    (output / "coverage.html").write_text(
        '<!doctype html><meta charset="utf-8"><title>UI source ownership</title>'
        "<style>body{font:14px Segoe UI;background:#202427;color:#eee;margin:24px}td,th{padding:8px;text-align:left;border-bottom:1px solid #555}input{padding:12px;width:90%;position:sticky;top:0}</style>"
        "<h1>UI source ownership</h1><p>"
        + escape(ledger["scope"])
        + "</p><p>"
        + escape(" ".join(report["limits"]))
        + '</p><input placeholder="Filter product, file, batch or role" oninput="for(const row of document.querySelectorAll(\'tbody tr\'))row.hidden=!row.textContent.toLowerCase().includes(this.value.toLowerCase())">'
        "<table><thead><tr><th>Product</th><th>Source</th><th>Batch</th><th>Role</th><th>Disposition</th></tr></thead><tbody>"
        + rows
        + "</tbody></table>",
        "utf-8",
    )
    print(
        "PASS",
        len(ledger["sources"]),
        "explicit source classifications; B07 stays open",
    )


if __name__ == "__main__":
    main()
