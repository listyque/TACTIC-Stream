"""Build the controls gallery only from complete, current native/browser evidence."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HANDLER = Path("D:/code/th_codex")
OUT = Path(__file__).with_name("output")


def read(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def verify_sources(native, browser, handler=HANDLER):
    for root, fingerprints in (
        (ROOT / "src/tactic_stream/shared_ui", native["sha256"]),
        (handler, native["nativeSources"]),
        (ROOT, browser["renderSources"]),
    ):
        for name, expected in fingerprints.items():
            assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected, (
                name
            )


def main():
    native, browser = read("qml.json"), read("vue.json")
    assert len(native["captures"]) == len(browser["captures"]) == 372
    assert not browser["errors"] and browser["inputScales"] == [1, 1.5, 2]
    verify_sources(native, browser)
    rows = []
    for first, second in zip(native["captures"], browser["captures"]):
        for key in ("style", "mode", "language", "width", "state", "part", "target"):
            assert first.get(key) == second.get(key), key
        for capture in (first, second):
            assert (OUT / capture["image"]).is_file(), capture["image"]
        rows.append(
            {
                key: first[key]
                for key in ("style", "mode", "language", "width", "state", "part")
            }
            | {
                "target": first.get("target", ""),
                "qml": first["image"],
                "vue": second["image"],
            }
        )
    summary = {
        key: browser[key]
        for key in (
            "rectangles",
            "styles",
            "interiors",
            "texts",
            "glyphs",
            "inputScales",
        )
    }
    summary["pairs"] = len(rows)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    page = """<!doctype html>
<html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tactic Frame · проверенная выборка контролов</title>
<style>
body{margin:24px;background:#1b1e20;color:#f3f4f5;font:15px/1.5 'Segoe UI',sans-serif}a{color:#9cc5dc}
h1{font-size:26px}p{max-width:1100px}nav{display:flex;gap:10px;flex-wrap:wrap;margin:20px 0}
select{font:inherit;padding:8px;background:#373d40;color:inherit;border:1px solid #596067;border-radius:8px}
.pair{display:flex;gap:16px;overflow:auto}.pair figure{margin:0;flex:1;min-width:320px}
img{max-width:100%;background:#24282a;border:1px solid #454c50}figcaption{margin:8px 0}.limit{color:#b7c1c8}
</style>
<h1>Tactic Frame · проверенная выборка контролов</h1>
<p>Это 16 карточек и примеры дерева, разделителя и Grid. Число состояний не является числом контролов;
вся библиотека здесь не представлена. <a href="ui-elements.html">Полный индекс UI, уровни, варианты и пробелы проверки</a>.</p>
<p>__COUNT__ парных состояний: настоящие штатные контролы Qt/QML и Vue. Три стиля, dark/light,
EN/RU, 900/360 px, обычное, недоступное, read-only, ошибка, загрузка и длинная подпись.
Hover, press и keyboard focus сняты реальным вводом. Геометрия, типографика, цвета и индикаторы
сверяются отдельно. Дополнительно проверяются координаты и базовая линия текста, ширина букв,
семейство шрифта и Unicode-глиф каждой показанной иконки. Допуск положения содержимого — 0.6 логического пикселя;
растеризация шрифтов движками может различаться. При сборке проверены отпечатки исходников.</p>
<p>Мышь, touch, Enter/Space, поиск и выбор пользователя, календарь с переходом через високосный месяц,
иконки, отмена/применение цвета, меню, tooltip, дерево, разделитель и прокрутка таблицы проверяются
исполняемыми сценариями при масштабе 1 / 1.5 / 2. Снимки основных состояний сняты при 1×.</p>
<p><a href="../../../src/tactic_stream/shared_ui/controls/catalog.ui.mjs">Общий исполняемый каталог</a> ·
<a href="summary.json">Счётчики</a> · <a href="../../frame_foundation/output/index.html">Проверки платформы</a></p>
<nav id="filters"></nav><p id="caption"></p><div class="pair">
<figure><figcaption>TACTIC Handler · QML</figcaption><img id="qml" alt="Нативный контрол"></figure>
<figure><figcaption>TACTIC Stream · Vue</figcaption><img id="vue" alt="Браузерный контрол"></figure>
</div>
<p class="limit">Это проверенная часть базового набора, а не подтверждение готовности всех контролов или совпадения всех экранов с исходным ТХ.
Миграция окон, доков и пользовательских Table View остаётся следующими этапами. Физическая OS IME,
видеодрайвер и системный композитор Windows не заменяются offscreen/DOM проверками.</p>
<script>
const rows=__DATA__, keys=['style','mode','language','width','state','part','target'], selects={};
for(const key of keys){const select=document.createElement('select');select.setAttribute('aria-label',key);
for(const value of [...new Set(rows.map(row=>String(row[key])))])select.add(new Option(value||'all controls',value));
select.onchange=()=>show(key);document.querySelector('#filters').append(select);selects[key]=select;}
function show(changed){const wanted=Object.fromEntries(keys.map(key=>[key,selects[key].value]));
let row=rows.find(row=>keys.every(key=>String(row[key])===wanted[key]));
if(!row)row=rows.filter(row=>String(row[changed])===wanted[changed]).sort((a,b)=>keys.filter(k=>String(b[k])===wanted[k]).length-keys.filter(k=>String(a[k])===wanted[k]).length)[0];
for(const key of keys)selects[key].value=row[key];document.querySelector('#caption').textContent=keys.map(key=>row[key]).filter(Boolean).join(' · ');
document.querySelector('#qml').src=row.qml;document.querySelector('#vue').src=row.vue;}
show('style');
</script></html>"""
    page = page.replace("__COUNT__", str(len(rows))).replace(
        "__DATA__", json.dumps(rows, ensure_ascii=False)
    )
    (OUT / "index.html").write_text(page, encoding="utf-8")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
