"""Reject stale/partial evidence and present the complete B05 comparison matrix."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HANDLER = Path("D:/grav/Tactic Stream/TH")
OUT = Path(__file__).resolve().parent / "output"


def verify(root, sources):
    for name, expected in sources.items():
        path = root / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, (
            f"Stale evidence: {path}"
        )


def main():
    from capture import CASES, TEMPLATE_REFERENCE

    CASES = dict(
        CASES,
        template_confirmation=["delete"],
        configuration_confirmation=["close"],
        cache_confirmation=["clear"],
    )

    native = json.loads((OUT / "native.json").read_text(encoding="utf-8"))
    browser = json.loads((OUT / "browser.json").read_text(encoding="utf-8"))
    assert native["status"] == "captured" and browser["status"] == "passed"
    assert not native["quick"], "Partial captures cannot close B05"
    for name, root in (
        ("sha256", ROOT / "src/tactic_stream/shared_ui"),
        ("nativeSources", HANDLER),
        ("driverSources", ROOT),
    ):
        assert native[name] == browser[name]
        verify(root, native[name])
    verify(ROOT, browser["webSources"])
    for name, digest in native["originalSources"].items():
        if name.startswith("pre-b05/"):
            verify(TEMPLATE_REFERENCE.parents[2], {name[len("pre-b05/") :]: digest})
        else:
            verify(ROOT / "tools/frame_foundation/reference", {name: digest})
    archive = Path(native["archive"])
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == native["archiveSha256"]
    pairs = []
    keys = ("screen", "style", "dark", "language", "viewportWidth", "case")
    signatures = set()
    for web in browser["captures"]:
        signature = tuple(web[key] for key in keys)
        assert signature not in signatures, signature
        signatures.add(signature)
        peers = [
            row
            for row in native["captures"]
            if tuple(row[key] for key in keys) == signature
        ]
        current = [row for row in peers if not row["original"]]
        original = [row for row in peers if row["original"]]
        assert len(current) == 1 and len(original) == (web["viewportWidth"] != 360)
        pairs.append(
            dict(
                web,
                native=current[0]["image"],
                original=original[0]["image"] if original else None,
            )
        )
        for image in (
            web["image"],
            current[0]["image"],
            original[0]["image"] if original else None,
        ):
            assert image is None or (OUT / image).is_file(), image
    expected = {
        (screen, style, dark, language, width, case)
        for screen, cases in CASES.items()
        for case in cases
        for style in ("md3", "material5", "fluent")
        for dark in (True, False)
        for language in ("en", "ru")
        for width in (1100, 800, 360)
    }
    assert signatures == expected, (expected - signatures, signatures - expected)
    summary = dict(
        status="passed",
        native=len(native["captures"]),
        original=sum(row["original"] for row in native["captures"]),
        pairs=len(pairs),
        rectangles=browser["rectangles"],
        styles=browser["styles"],
        interiors=browser["interiors"],
        archiveSha256=native["archiveSha256"],
    )
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    template = (Path(__file__).parent / "report.html").read_text(encoding="utf-8")
    content = template.replace(
        "__DATA__", json.dumps(pairs, ensure_ascii=False).replace("</", "<\\/")
    ).replace("__SUMMARY__", json.dumps(summary))
    (OUT / "index.html").write_text(content, encoding="utf-8")
    print(json.dumps(summary))
    print(OUT / "index.html")


if __name__ == "__main__":
    main()
