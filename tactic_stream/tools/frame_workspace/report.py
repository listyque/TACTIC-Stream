"""Verify fresh whole-shell evidence and show original/native/browser captures."""

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
    original = json.loads((OUT / "original.json").read_text(encoding="utf-8"))
    native = json.loads((OUT / "frame.json").read_text(encoding="utf-8"))
    browser = json.loads((OUT / "stream.json").read_text(encoding="utf-8"))
    shared, sources = source_hashes(ROOT, TH, list(native["nativeSources"]))
    for record in (original, native):
        assert record["sha256"] == shared and record["nativeSources"] == sources, (
            "Stale native evidence"
        )
    for path, digest in browser["sources"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path
    original_checks = paired_checks = color_checks = 0
    sections = []
    for current in browser["captures"]:
        key = (current["style"], current["language"], current["width"])
        frames = [("Frame TS", current)]
        if current["width"] > 700:
            records = [
                next(
                    row
                    for row in capture["captures"]
                    if (row["style"], row["language"], row["width"]) == key
                )
                for capture in (original, native)
            ]
            for part in ("geometry", "workspace"):
                assert records[0][part] == records[1][part], (
                    key,
                    part,
                    "Original reference",
                )
                original_checks += sum(
                    len(bounds) for bounds in records[1][part].values()
                )
                for name, bounds in current[part].items():
                    assert bounds == records[1][part][name], (key, part, name)
                    paired_checks += len(bounds)
            assert (
                records[0]["background"]
                == records[1]["background"]
                == current["background"]
            ), key
            assert (
                records[0]["avatarColor"]
                == records[1]["avatarColor"]
                == current["avatarColor"]
            ), (key, "avatar contrast")
            color_checks += 4
            frames = [("Original TH", records[0]), ("Frame TH", records[1]), *frames]
        pictures = "".join(
            f'<figure><figcaption>{label}</figcaption><img loading="lazy" src="{row["screenshot"]}" alt="{html.escape(str(key))}"></figure>'
            for label, row in frames
        )
        sections.append(
            f'<details><summary>{html.escape(str(key))}</summary><div class="pictures">{pictures}</div></details>'
        )
    assert len(native["captures"]) == 30 and len(browser["captures"]) == 36
    page = f"""<!doctype html><html lang="ru"><meta charset="utf-8"><title>B01: главное рабочее пространство</title>
<style>body{{background:#202528;color:#e1e6e9;font:15px/1.5 Segoe UI,sans-serif;margin:24px}}.pictures{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}}figure{{margin:0}}img{{max-width:100%;height:auto}}details{{margin:20px 0}}summary{{cursor:pointer}}</style>
<h1>B01: главное окно и рабочее пространство</h1>
<p>Настоящий Main оригинального ТХ → Main Frame ТХ → собранный ТС. Три темы, EN dark / RU light, 30 нативных состояний в каждой версии и 36 браузерных состояний. Проверены все три корневые области: панель управления, боковая полоса и хост доков, а также расположение контролов панели управления. {original_checks} проверок относительно оригинала, {paired_checks} измерений Qt/Vue и {color_checks} сравнений фона и контраста аватара. Отпечатки текущих исходников и ресурсов сборки проверены.</p>
<p>В каждом браузерном состоянии кнопки настроек, аккаунта и выбора проекта проверены настоящими кликами/тапами. На телефоне боковая полоса отсутствует по объявленной возможности клиента; нативный ТХ остаётся desktop-приложением. Контекст: выбран Administration, поисковый тип ещё не открыт. Дополнительная кнопка открытия навигации в пустом ТС сохранена. Этот отчёт проверяет общую оболочку; содержимое поиска, таблиц и остальных экранов относится к следующим пакетам. Растеризация шрифтов и композитор Windows не объявляются идентичными.</p>
<p>Сценарии сессии, восстановления раскладки/вкладок, мобильных черновиков и отмены жестов проверяются отдельно через tools/frame_navigation/check_workflows.py, tests/test_workbench.py и обязательный Frame platform gate. Их результаты не подменяются этими снимками.</p>{"".join(sections)}</html>"""
    (OUT / "index.html").write_text(page, encoding="utf-8")
    print(
        f"Workspace: {original_checks} original, {paired_checks} paired and {color_checks} color checks: {OUT / 'index.html'}"
    )


if __name__ == "__main__":
    main()
