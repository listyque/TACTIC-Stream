"""Build the expanded paired catalog from current, actual host captures."""

import argparse
import hashlib
import json
from pathlib import Path
import re
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = HERE / "output/variants"


def verify_sources(native, browser, handler=Path("D:/grav/Tactic Stream/TH")):
    assert native.get("status") == browser.get("status") == "captured", (
        "Capture did not complete; recapture both hosts"
    )
    assert {
        "sha256",
        "nativeSources",
        "driverSources",
    } <= native.keys() and "sources" in browser, (
        "Capture schema changed; recapture the expanded gallery"
    )
    for root, hashes in (
        (ROOT / "src/tactic_stream/shared_ui", native["sha256"]),
        (handler, native["nativeSources"]),
        (ROOT, native["driverSources"]),
        (ROOT, browser["sources"]),
    ):
        for name, digest in hashes.items():
            assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, (
                "Stale capture: " + name
            )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()
    (OUT / "index.html").write_text(
        '<!doctype html><meta charset="utf-8"><p>Проверка парного каталога ещё не завершена. Смотрите журнал запуска.</p>',
        encoding="utf-8",
    )
    (OUT / "summary.json").write_text(
        json.dumps({"status": "checking"}), encoding="utf-8"
    )
    native = json.loads((OUT / "native.json").read_text(encoding="utf-8"))
    browser = json.loads((OUT / "browser.json").read_text(encoding="utf-8"))
    verify_sources(native, browser)
    assert native["backend"] == "windows-opengl", (
        "Rounded photos require the production graphics backend"
    )
    assert not browser["differences"], browser["differences"][:10]
    first, second = native["captures"], browser["captures"]
    assert len(first) == len(second)
    configurations = {
        (row["style"], row["mode"], row["language"], row["width"]) for row in first
    }
    assert len(configurations) == (1 if args.quick else 24), configurations
    styles, diagnostics, failures, pairs = 0, [], [], []
    for left, right in zip(first, second):
        identity = ["id", "style", "mode", "language", "width", "state"]
        assert all(left[key] == right[key] for key in identity)
        if left["id"] == "field-frame-error":
            icon_colors = []
            for row in (left, right):
                box = row["boxes"]["sample"]
                with Image.open(OUT / row["image"]) as source:
                    scale = source.width / row["width"]
                    # Sample the icon plate beside the glyph, inside its rounded edge.
                    icon_colors.append(
                        source.convert("RGB").getpixel(
                            (
                                round((box["x"] + 14 + 5) * scale),
                                round((box["y"] + 14 + 16) * scale),
                            )
                        )
                    )
            styles += 1
            if icon_colors[0] != icon_colors[1]:
                failures.append([left["image"], "error icon background", *icon_colors])
        for row in (left, right):
            assert (OUT / row["image"]).is_file(), row["image"]
            if row["id"] in ("preview-contain", "preview-photo", "preview-selected"):
                with (
                    Image.open(OUT / row["image"]) as source,
                    source.convert("RGB") as image,
                ):
                    box = row["boxes"]["sample"]
                    scale = image.width / row["width"]

                    def pixel(x, y):
                        return image.getpixel(
                            (
                                round((box["x"] + box["width"] * x) * scale),
                                round((box["y"] + box["height"] * y) * scale),
                            )
                        )

                    assert pixel(0.25, 0.5) == (204, 102, 85), (
                        row["image"],
                        "red photo region",
                    )
                    assert pixel(0.75, 0.5) == (85, 136, 170), (
                        row["image"],
                        "blue photo region",
                    )
                    if row["id"] == "preview-contain":
                        assert pixel(0.05, 0.5) == (85, 170, 102), (
                            row["image"],
                            "contain keeps the edge stripe",
                        )
                        assert pixel(0.25, 0.2) not in (
                            (204, 102, 85),
                            (85, 136, 170),
                            (85, 170, 102),
                        ), (row["image"], "contain letterbox")
                    else:
                        assert pixel(0.05, 0.5) == (204, 102, 85), (
                            row["image"],
                            "crop removes the edge stripe",
                        )
        if left.get("background"):
            styles += 1
            if left["background"] != right.get("background"):
                failures.append(
                    [
                        left["id"],
                        "background",
                        left["background"],
                        right.get("background"),
                    ]
                )
        for text in left["content"]:
            value = text["text"]
            matches = [
                candidate
                for candidate in right["content"]
                if candidate["text"] == value
            ]
            if not value.strip() or len(matches) != 1 or "\n" in value:
                continue
            actual = matches[0]
            for key in ("fontSize", "weight"):
                # Icon faces have host-specific family names/weight declarations;
                # their exact bundled maps and glyphs have their own platform gate.
                if key == "weight" and any(
                    0xE000 <= ord(char) <= 0xFFFF for char in value
                ):
                    continue
                styles += 1
                if abs(text[key] - actual[key]) > 0.05:
                    failures.append([left["id"], value, key, text[key], actual[key]])
            rgb = re.findall(r"\d+", actual["color"])[:3]
            color = "#" + "".join(f"{int(channel):02x}" for channel in rgb)
            styles += 1
            if color != text["color"] and "Emoji" not in text["family"]:
                failures.append([left["id"], value, "color", text["color"], color])
            if (
                value[0] < "\ue000"
                and text["advance"] <= min(text["width"], actual["width"]) + 0.1
            ):
                for key in ("x", "baseline", "advance"):
                    if abs(text[key] - actual[key]) > 0.6:
                        diagnostics.append(
                            {
                                **{key: left[key] for key in identity},
                                "text": value,
                                "metric": key,
                                "native": text[key],
                                "browser": actual[key],
                            }
                        )
        pairs.append(
            {
                **{key: left[key] for key in identity},
                "family": left["family"],
                "native": left["image"],
                "browser": right["image"],
            }
        )
    result = dict(
        status="failed" if failures else "passed",
        pairs=len(pairs),
        examples=len({row["id"] for row in first}),
        configurations=len(configurations),
        textStyles=styles,
        failures=failures,
        paintDiagnostics=diagnostics,
        limits=[
            "Text origins/baselines use different Qt/DOM metrics; diagnostics above are retained, not counted as passing pixel comparisons.",
            "Wrapped/elided text and Markdown are shown by their actual renderers; raw source advances are not line bounds.",
            "OS IME, physical touch devices, font rasterization and the Windows compositor require hardware acceptance.",
        ],
    )
    (OUT / "summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    assert not failures, failures[:20]
    template = (HERE / "variants-report.html").read_text(encoding="utf-8")
    payload = json.dumps(dict(summary=result, rows=pairs), ensure_ascii=False).replace(
        "<", "\\u003c"
    )
    (OUT / "index.html").write_text(
        template.replace("__DATA__", payload), encoding="utf-8"
    )
    print(
        f"{len(pairs)} actual pairs; {styles} strict text style/color checks; {len(diagnostics)} explicit paint-metric diagnostics"
    )


if __name__ == "__main__":
    main()
