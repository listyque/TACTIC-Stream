"""Compare real archived/current Qt and Vue drawer geometry; reject stale captures."""

import hashlib
import html
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
TH = Path("D:/code/th_codex")
OUT = Path(__file__).resolve().parent / "output"
sys.path[:0] = [str(TH), str(ROOT / "tools/frame_admin")]
from native_capture import source_hashes


def main():
    native = json.loads((OUT / "native.json").read_text(encoding="utf-8"))
    browser = json.loads((OUT / "browser.json").read_text(encoding="utf-8"))
    shared, sources = source_hashes(ROOT, TH, list(native["nativeSources"]))
    assert shared == native["sha256"] and sources == native["nativeSources"], (
        "Stale Qt evidence"
    )
    for path, digest in browser["sources"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path
    comparisons = 0
    sections = []
    for sample in (row for row in native["captures"] if not row["original"]):
        original = next(
            row
            for row in native["captures"]
            if row["original"] and row["id"] == sample["id"]
        )
        web = next(row for row in browser["captures"] if row["id"] == sample["id"])
        assert original["captions"] == sample["captions"] == web["captions"], sample["id"]
        for before, after in [
            (original["boxes"], sample["boxes"]),
            (sample["boxes"], web["boxes"]),
            (original["rows"], sample["rows"]),
            (sample["rows"], web["rows"]),
        ]:
            assert before
            assert set(before) <= set(after), (sample["id"], set(before) - set(after))
            for name, box in before.items():
                for key, value in box.items():
                    assert abs(value - after[name][key]) < 0.6, (
                        sample["id"],
                        name,
                        key,
                        value,
                        after[name][key],
                    )
                    comparisons += 1
        pictures = "".join(
            f'<figure><figcaption>{label}</figcaption><img src="{row["image"]}" alt="{html.escape(sample["id"])}"></figure>'
            for label, row in [
                ("Исходный ТХ", original),
                ("Frame ТХ", sample),
                ("Frame ТС", web),
            ]
        )
        sections.append(
            f'<details><summary>{sample["id"]}</summary><div class="pictures">{pictures}</div></details>'
        )
    page = f"""<!doctype html><html lang="ru"><meta charset="utf-8"><title>Frame: навигация</title>
<style>body{{background:#202528;color:#e1e6e9;font:15px/1.5 Segoe UI,sans-serif;margin:24px}}.pictures{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}}figure{{margin:0}}img{{max-width:100%;height:auto}}details{{margin:24px 0}}summary{{cursor:pointer}}a{{color:#8abbd5}}</style>
<h1>Навигация: исходный ТХ → Frame ТХ → Frame ТС</h1>
<p>12 состояний: md3/material5/fluent, EN dark/RU light, viewport 900×640 и 320×640. {comparisons} измерений контейнера, шапки, кнопок, списка и первых строк. Проверены реальные компоненты и отпечатки исходников, архив {native["reference"]}.</p>
<p>Общий модуль задаёт размеры и шапку, отступы списка, порог автозакрытия и клавиатурные переходы. Нативные списки/скроллбары и браузерные controls сохраняют ввод. Преднамеренное улучшение относительно архива: фокус панели при сохранении позиции прокрутки; стрелки пропускают скрытые, недоступные и разделители. Курсор должен сначала войти в панель, прежде чем удаление на 120 px её закроет.</p>
<p>Сценарии: первый клик/тап, закрытие/Escape/возврат фокуса, offscreen-строки и сворачивание. Мобильные слоты открытых разделов и панелей сохранены в ТС. Это проверка контейнера навигации, а не завершение переноса выбора проектов, rail вкладок и формата сессии. Растеризация Qt/браузера и системный композитор Windows не объявляются идентичными.</p>
<p><a href="../../../docs/shared_ui_foundation_plan.md">План</a> · <a href="native.json">Qt</a> · <a href="browser.json">Vue</a></p>{"".join(sections)}</html>"""
    (OUT / "index.html").write_text(page, encoding="utf-8")
    print(f"{comparisons} comparisons passed: {OUT / 'index.html'}")


if __name__ == "__main__":
    main()
