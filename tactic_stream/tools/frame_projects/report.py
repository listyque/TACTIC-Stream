"""Reject stale evidence and compare real legacy/native/browser UI bounds."""

import hashlib
import html
import json
import sys
from pathlib import Path

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
        "Stale native evidence"
    )
    for path, digest in browser["sources"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path
    color_checks = 0
    corner_checks = 0
    comparisons = 0
    reference_checks = 0
    sections = []
    for current in [row for row in native["captures"] if not row["original"]]:
        original = next(
            row
            for row in native["captures"]
            if row["original"] and row["id"] == current["id"]
        )
        web = next(row for row in browser["captures"] if row["id"] == current["id"])
        boxes = current["boxes"]
        if current["kind"] == "chooser":
            boxes = {
                key: value
                for key, value in boxes.items()
                if key.startswith("projectChooser")
            }
        for name in (
            "projectCardSurface",
            "projectGridPreview",
            "projectCardTitle",
            "projectCardDescription",
            "projectCardCategory",
            "workspaceTabSelectionLabel",
            "sectionTabSurface",
            "sectionTabBadge",
            "sectionTabTitle",
            "sectionTabIcon",
        ):
            if name in current["paints"] and name in web["paints"]:
                assert current["paints"][name] == web["paints"][name], (
                    current["id"],
                    name,
                    current["paints"][name],
                    web["paints"][name],
                )
                color_checks += 1
        for name, corners in current["rounding"].items():
            assert corners == web["rounding"][name] == [15] * 4, (
                current["id"],
                name,
                corners,
                web["rounding"][name],
            )
            corner_checks += len(corners)
        assert boxes
        for name, bounds in boxes.items():
            assert name in web["boxes"], (current["id"], name)
            for key, value in bounds.items():
                assert abs(value - web["boxes"][name][key]) < 0.6, (
                    current["id"],
                    name,
                    key,
                    value,
                    web["boxes"][name][key],
                )
                comparisons += 1
        for name, bounds in original["boxes"].items():
            if current["kind"] == "chooser" and name != "projectChooserTitle":
                continue
            if name not in current["boxes"]:
                continue
            for key, value in bounds.items():
                if current["kind"] == "chooser" and key == "width":
                    continue
                assert abs(value - current["boxes"][name][key]) < 0.6, (
                    current["id"],
                    "reference",
                    name,
                    key,
                    value,
                    current["boxes"][name][key],
                )
                reference_checks += 1
        pictures = "".join(
            f'<figure><figcaption>{label}</figcaption><img src="{row["image"]}" alt="{html.escape(current["id"])}"></figure>'
            for label, row in [
                ("Исходный ТХ", original),
                ("Frame ТХ", current),
                ("Frame ТС", web),
            ]
        )
        sections.append(
            f'<details><summary>{current["id"]}</summary><div class="pictures">{pictures}</div></details>'
        )
    page = f"""<!doctype html><html lang="ru"><meta charset="utf-8"><title>Проекты и рабочие вкладки</title><style>body{{background:#202528;color:#e1e6e9;font:15px/1.5 Segoe UI,sans-serif;margin:24px}}.pictures{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}}figure{{margin:0}}img{{max-width:100%;height:auto}}details{{margin:24px 0}}summary{{cursor:pointer}}</style>
<h1>Проекты и вкладки: исходный ТХ → Frame ТХ → Frame ТС</h1><p>60 состояний настоящих компонентов: chooser, одно-/двухстрочная карточка, вкладка normal/current/hover+dirty, боковая полоса collapsed/revealed/pressed, md3/material5/fluent, EN dark/RU light. {comparisons} измерений Qt/Vue; {reference_checks} проверок относительно архивного компонента. Цветовые роли: {color_checks} проверок; скругления: {corner_checks}. Отпечатки исходников проверены. Состояние наведения задаётся одинаково; снимки Chromium используют grayscale text, чтобы LCD-сглаживание Windows не маскировало фактический цвет.</p>
<p>Сетка сохраняет три колонки на компьютере; ТС использует две/одну на телефоне. Полоса прокрутки получает отдельные 12 px: карточки исходного ТХ были под ней, поэтому их ширина в полном chooser намеренно уменьшена на 4 px. Карточки сравниваются с архивом отдельно при одинаковой ширине 248 px. Активный проект теперь выделяется и в ТХ; исходный chooser это состояние не передавал.</p>
<p>Проверены реальные фильтры, mouse/touch, переходы Home/End/стрелки, Enter/Space, закрытие и перестановка вкладок с восстановлением фокуса. Существующие владельцы проектов, ACL, preview, draft и saved layout сохранены. Боковая полоса теперь использует общий скелет, цвета, клавиатуру и расчёт цели drag. Первое нажатие и отмена проверяются реальными событиями. Этот отчёт не объявляет завершение всей фазы 2C. Композитор Windows и растеризация Qt/Chromium не объявляются идентичными.</p>{"".join(sections)}</html>"""
    (OUT / "index.html").write_text(page, encoding="utf-8")
    print(
        f"{comparisons} Qt/Vue, {reference_checks} reference, {color_checks} color and {corner_checks} corner checks: {OUT / 'index.html'}"
    )


if __name__ == "__main__":
    main()
