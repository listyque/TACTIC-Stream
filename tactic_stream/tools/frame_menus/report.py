"""Reject stale sources and compare archived/current/native/browser menu evidence."""

import hashlib
import html
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
TH = Path("D:/grav/Tactic Stream/TH")
OUT = Path(__file__).resolve().parent / "output"
sys.path[:0] = [str(TH), str(ROOT / "tools/frame_admin")]
from native_capture import source_hashes


def main():
    native = json.loads((OUT / "native.json").read_text(encoding="utf-8"))
    browser = json.loads((OUT / "browser.json").read_text(encoding="utf-8"))
    shared, sources = source_hashes(ROOT, TH, list(native["nativeSources"]))
    assert shared == native["sha256"] and sources == native["nativeSources"], (
        "Stale native menu captures"
    )
    for path, fingerprint in browser["sources"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == fingerprint, (
            path
        )
    comparisons = 0
    sections = []
    for sample in (row for row in native["captures"] if not row["original"]):
        original = next(
            row
            for row in native["captures"]
            if row["original"] and row["id"] == sample["id"]
        )
        web = next(row for row in browser["captures"] if row["id"] == sample["id"])
        assert len(original["rows"]) == len(sample["rows"])
        for old, new in zip(original["rows"], sample["rows"]):
            assert (
                old["command"] == new["command"]
                and old["height"] == new["height"]
                and old["width"] == new["width"]
            )
            for old_id, new_id in [
                ("actionMenuIcon", "menuIcon"),
                ("actionMenuBadge", "menuBadge"),
            ]:
                if old_id not in old["boxes"]:
                    continue
                for key in ("x", "y", "width", "height"):
                    assert (
                        abs(old["boxes"][old_id][key] - new["boxes"][new_id][key]) < 0.6
                    ), (sample["id"], old["command"], key)
                    comparisons += 1
            if "actionMenuTitleLabel" in old["boxes"]:
                assert (
                    old["boxes"]["actionMenuTitleLabel"]["fontSize"]
                    == new["boxes"]["menuTitle"]["fontSize"]
                )
                comparisons += 1
        pictures = []
        for label, row in [
            ("Исходный ТХ", original),
            ("Frame ТХ", sample),
            ("Frame ТС", web),
        ]:
            pictures.append(
                f'<figure><figcaption>{label}</figcaption><img src="{row["image"]}" alt="{html.escape(sample["id"])}"><p>Footer</p><img src="{row["footerImage"]}" alt="footer"></figure>'
            )
        sections.append(
            f'<details open><summary>{html.escape(sample["id"])}</summary><div class="pictures">{"".join(pictures)}</div></details>'
        )
    page = f"""<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Tactic Frame · Главные меню</title>
<style>body{{background:#202426;color:#eee;font:15px/1.5 Segoe UI,sans-serif;margin:24px}}a{{color:#8abbd5}}.pictures{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}}figure{{margin:0}}img{{max-width:100%;height:auto}}details{{margin:24px 0}}summary{{cursor:pointer}}p{{max-width:1100px}}@media(max-width:760px){{.pictures{{grid-template-columns:1fr}}}}</style>
<h1>Главные меню и footer: исходный ТХ → Frame ТХ → Frame ТС</h1>
<p>18 состояний пользователя, настроек и подключения: md3/material5/fluent, EN dark/RU light. {comparisons} проверок размеров строк, иконок, счётчика и размера шрифта относительно исходного ТХ; {browser["comparisons"]} измерений общих строк между QML/Vue. Измерены высота footer и все четыре радиуса. Файлы проверяются по отпечаткам исходников.</p>
<p>Настоящие ActionMenu/AppMenu и controls, фиксированные записи. Эталон QML взят из архива {native["reference"]}. Здесь меню встроены в тестовый host для стабильного снимка. Нативные popup-окна и их ввод проверяются отдельными QTest-сценариями. Различия сглаживания Qt/браузера и системный композитор Windows не объявляются одинаковыми.</p>
<p>Дополнительные команды конкретного клиента сохранены: repository sync, watch folders, server, update и exit в ТХ; shelf, queue, tasks/timesheet, создание проекта и API/mobile guide в ТС. Поэтому список настроек отличается намеренно. Общая строка и общая команда используют одну раскладку и правила; команды исполняют исходные владельцы. Runtime MenuRegistry.replace/extend сохранены.</p>
<p>Проверки настоящего ввода: первый клик/touch/Enter/Space, навигация и возврат фокуса, disabled, переключение polling/SSE. Отдельный браузерный сценарий использует временную БД и настоящее приложение: команды, failure/retry, stale-ответ проекта, настройки, auth/logout, touch 320 px. <a href="../../../docs/frame/contract.md">План и ограничения</a> · <a href="native.json">QML</a> · <a href="browser.json">Vue</a></p>{"".join(sections)}</html>"""
    (OUT / "index.html").write_text(page, encoding="utf-8")
    print(OUT / "index.html")


if __name__ == "__main__":
    main()
