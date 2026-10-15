"""Build a local evidence page from actual original, native and browser captures."""

import html
import json
from pathlib import Path
import subprocess
import sys

from check_platform import fingerprints

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "output"


def read(name):
    return json.loads((OUTPUT / name).read_text(encoding="utf-8"))


def image(title, path):
    assert (OUTPUT / path).is_file(), path
    return dict(title=title, path=path)


def main():
    gate = read("platform/gate.json")
    assert gate["status"] == "passed", "Platform gate has not passed"
    handler = Path("D:/code/th_codex")
    assert gate["sources"] == fingerprints(handler), "Platform evidence is stale"
    subprocess.run(
        [
            sys.executable,
            "-B",
            "-X",
            "utf8",
            str(HERE.parent / "frame_admin/catalog.py"),
        ],
        check=True,
    )
    admin = json.loads(
        (HERE.parent / "frame_admin/output/summary.json").read_text(encoding="utf-8")
    )
    assert admin["native_tests"] == 249 and admin["browser_suites"] == 14
    performance = read("platform/list-performance.json")
    timings = "".join(
        f"<tr><td>{count:,}</td><td>{next(row['median'] for row in performance if row['count'] == count and row['label'] == 'original'):.2f} ms</td><td>{next(row['median'] for row in performance if row['count'] == count and row['label'] == 'current'):.2f} ms</td></tr>"
        for count in (1000, 4000)
    )
    assert all(step["status"] == 0 for step in gate["steps"])
    foundation = read("foundation.json")
    browser = read("browser-foundation.json")
    package = read("package.json")
    quality = read("quality/baseline.json")
    samples = []
    for row in read("main/stream.json"):
        width = row["width"]
        pictures = []
        for title, prefix in [("Исходный ТХ", "original"), ("Frame · ТХ", "frame")]:
            path = f"main/{prefix}-{width}.png"
            if (OUTPUT / path).is_file():
                pictures.append(image(title, path))
        pictures.append(image("Frame · ТС", "main/" + row["screenshot"]))
        samples.append(
            dict(
                label=f"Главная панель · {width} px",
                images=pictures,
                note="Сравнение именованных позиций и реального ввода. Меню и платформенные действия ещё различаются.",
            )
        )
    for row in read("administration/native.json"):
        if row["original"]:
            width = row["width"]
            pictures = [
                image("Исходный ТХ", f"administration/original-{width}.png"),
                image("Frame · ТХ", f"administration/frame-{width}.png"),
            ]
            pictures.append(image("Frame · ТС", f"administration/stream-{width}.png"))
            samples.append(
                dict(
                    label=f"Workflow целиком · {width} px",
                    images=pictures,
                    note="Библиотека возвращена в левую панель. Frame-ТХ/ТС сверены целиком на одинаковых данных; оформление всей оболочки ещё не совпадает с оригиналом.",
                )
            )
    for row in read("original-graph.json"):
        if row["original"]:
            stem = row["mode"] + "-"
            samples.append(
                dict(
                    label=f"Граф · {row['mode']} · {row['phase']}",
                    images=[
                        image(
                            "Исходный ТХ", stem + "original-" + row["phase"] + ".png"
                        ),
                        image("Frame · ТХ", stem + "frame-" + row["phase"] + ".png"),
                    ],
                    note="Отдельный редактор на одинаковых данных: видимые соединения, выбранная нода и связь.",
                )
            )
    native = read("docks/native.json")["captures"]
    stream = read("docks/stream.json")
    for row in native:
        if row["original"]:
            key = f"{row['width']}-{int(row['stacked'])}-{int(row['floating'])}"
            pictures = [
                image("Исходный ТХ", "docks/original-" + key + ".png"),
                image("Frame · ТХ", "docks/frame-" + key + ".png"),
            ]
            paired = next(
                (
                    item
                    for item in stream
                    if all(
                        item[field] == row[field]
                        for field in ("width", "stacked", "floating")
                    )
                ),
                None,
            )
            if paired:
                pictures.append(image("Frame · ТС", "docks/" + paired["image"]))
            samples.append(
                dict(
                    label=f"Док · {row['width']} px · {'вкладки' if row['stacked'] else 'одна панель'} · {'плавающий' if row['floating'] else 'закреплённый'}",
                    images=pictures,
                    note="12 исходных/Frame нативных пар и 9 браузерных случаев. ТС сохраняет свои maximize/position; у ТХ отдельное окно. Плавающие стеки в браузере не реализованы.",
                )
            )
    structure = quality["structure"]
    warning_counts = quality["lint"]["current"]
    fonts = sum(quality["smoke"]["current"]["fontWarnings"].values())
    page = """<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tactic Frame · фундамент и исходники</title>
<style>
body{margin:30px auto;padding:0 24px;max-width:1500px;background:#1b1e20;color:#eef0f2;font:15px/1.5 'Segoe UI',sans-serif}a{color:#8bb7d0}h1{font-size:26px}h2{font-size:20px}p{max-width:1100px;color:#c3c8cb}code,pre{font-family:Consolas,monospace}pre{padding:16px;background:#282d30;border-radius:10px;overflow:auto}.cards{display:flex;flex-wrap:wrap;gap:12px}.card{background:#303639;padding:12px 18px;border-radius:10px}.card strong{display:block;font-size:23px}select,button,input{font:inherit}select,button{max-width:100%;background:#363d41;color:inherit;border:1px solid #555e63;border-radius:8px;padding:8px;margin:5px 12px 5px 0}.pictures{display:flex;flex-wrap:wrap;gap:16px;align-items:start}.pictures figure{margin:0;flex:1;min-width:280px;max-width:100%}.pictures img{max-width:100%;height:auto;border:1px solid #4b5257;border-radius:6px}.pictures figcaption{padding:8px 0;color:#9ebfd2}.notice{padding:12px 18px;background:#343b3e;border-left:4px solid #78a6c4;border-radius:6px}details{margin:16px 0}summary{cursor:pointer}li{margin:6px 0}
</style>
<h1>Tactic Frame · фундамент и читаемые исходники</h1>
<p>Текущий checkpoint · 2026-10-16: TH __TH_VERSION__ / TS __TS_VERSION__. Общие модули поставляются независимыми копиями; QML использует собственные контролы Qt, Vue — браузерные контролы. WebEngine не используется.</p>
<h2>Подготовительная платформа</h2>
<p class="notice">Все __STEPS__ шагов общего gate прошли. Проверены контракты контролов, уникальные ключи и обязательные модели/Views, ввод и композиция, удаление редактируемой строки, списки на 10 000 записей, три масштаба, resize/dispose, обычный запуск окон и независимый пакет. Добавлены реальные маршруты Help, окон, доков и навигации. Отпечатки исходников проверены при сборке этого отчёта.</p>
<p>Убраны квадратичное согласование нативных списков и конфликт единиц шрифта. Сортировка сохраняет живой редактор, выделение и предварительный ввод IME. Исправлены потеря resize другого элемента и гонка события прокрутки с обновлением модели в браузере. Черновиками и сохранением по-прежнему владеет предметный экран.</p>
<p><a href="inventory.html">Инвентаризация UI и точек входа</a> · <a href="platform/gate.json">__STEPS__ шагов и хеши исходников</a> · <a href="../../frame_admin/output/index.html">Свежие __ADMIN_PAIRS__ парных состояний админки</a> · <a href="../../frame_help/output/index.html">Help: оригинал, Qt и Vue</a> · <a href="navigation/index.html">Навигационные строки</a> · <a href="../../frame_controls/output/ui-elements.html">Полный каталог исходников UI</a> · <a href="../../../docs/shared_ui_foundation_plan.md">План и границы завершения</a></p>
<p>249 нативных регрессий и все 14 веб-стендов прошли. Это сравнение текущих Frame-реализаций. Полное совпадение с исходным Handler остаётся отдельной фазой. Инвентаризация исходников не доказывает прохождение каждого динамического окна.</p>
<h3>Локальный замер списка: разворот записей</h3>
<table><thead><tr><th>Записей</th><th>До</th><th>После</th></tr></thead><tbody>__TIMINGS__</tbody></table>
<p>Медиана трёх обновлений одной настоящей Qt-сцены, включая ожидание кадра, software backend. Это замер конкретного пути, а не FPS приложения или гарантия GPU. <a href="platform/list-performance.json">Исходные измерения</a>.</p>
<p>Ниже сохранены карта кода и результаты предыдущего checkpoint: числа проверок темы/метрик относятся к тому этапу. Текущий gate и свежая матрица приведены выше.</p>
<div class="cards"><div class="card"><strong>47</strong>portable-модулей</div><div class="card"><strong>73</strong>форматированных QML-адаптера/рендерера</div><div class="card"><strong>__FOUNDATION__</strong>проверок основы с архивом</div><div class="card"><strong>__BROWSER__</strong>браузерных проверок основы</div></div>
<h2>Где читать код</h2>
<p><a href="../../../src/tactic_stream/shared_ui/README.md">Карта исходников и пример</a> · <a href="../../../docs/shared_ui_foundation_plan.md">Фактический план и незавершённый объём</a> · <a href="../../frame_admin/output/index.html">Матрица Administration</a> · <a href="../../../../backups/2026-10-15_103116_before_shared_ui_foundation/RESTORE.txt">Инструкция отката из проверенных архивов</a></p>
<pre>core/                         тема, типографика, метрики, контракт узлов
controls/                     graph, code, forms, tabs
shell/                        геометрия окон, минимумы, заголовки доков и main toolbar
features/administration/      оболочка и предметные разделы
    groups/ users/ security/ database/ columns/ sidebar/
    search_types/ naming/ workflow/ schema/ layouts/</pre>
<p>Нативные адаптеры расположены в qml/features/administration и qml/shell/windows, shell/docks. Публичные имена сохранены через qmldir. Описания UI, переходы состояния и платформенные обработчики отделены. Форматтер раскрывает вложенные деревья и обработчики; проверка --check закрепляет это правило.</p>
<p>Чистый wheel __WHEEL__ содержит ровно __MODULES__ модулей: проверены имена, байты и импорты без соседнего checkout. Архив обновления TH проверяет также вложенные нативные компоненты и индексы типов.</p>
<h2>Архивная галерея исходного checkpoint 0.6.0.96 / 0.112.145</h2><p>Снимки ниже сохранены с предыдущего этапа и не выдаются за свежие снимки фазы 0. Текущие парные снимки находятся в матрице Administration по ссылке выше.</p>
<p>Это не макеты: снимки получены из исходного архивного ТХ, настоящего Frame-ТХ и браузера. Наличие общей спецификации само по себе не доказывает совпадение с оригиналом.</p>
<select id="sample" aria-label="Сравнение"></select><button id="previous">←</button><button id="next">→</button><p id="note"></p><div id="pictures" class="pictures"></div>
<h2>Что ещё не закончено</h2>
<p class="notice">Завершена и проверена основа темы/типографики/метрик/motion. В остальных четырёх блоках есть рабочие общие части; полные состояния всех примитивов, деревья доков, меню и навигация главного окна, остальные экраны и полное совпадение админки с исходным ТХ остаются в работе. Общая архитектура не выдаётся за завершённый перенос всего продукта.</p>
<h2>Общие quality gates</h2>
<p>Проверка <code>check_quality_baseline.py</code> воспроизводит исходный архив и текущий UI при одинаковых условиях. Новых structure/lint/smoke регрессий нет. Это не означает, что старые общие gates стали зелёными.</p>
<ul><li>Structure: __BEFORE_FAILURES__ существующих ошибок до переноса, __CURRENT_FAILURES__ после; новых нет.</li><li>qmllint: __MISSING__ missing-property, __OVERRIDE__ property-override; те же значения были в архиве. Бюджеты не повышены.</li><li>Оба проверочных запуска загрузили, повторно открыли и закрыли зарегистрированные окна, код возврата 0. Архивный запуск выдал __OLD_FONTS__ предупреждений о point/pixel size; текущий — __FONTS__. Обычный smoke проходит, существующий долг structure/qmllint остаётся.</li></ul>
<p><a href="quality/baseline.json">Сравнение долга</a> · <a href="package.json">Независимая упаковка</a> · <a href="foundation.json">Основа: Qt / архив</a> · <a href="browser-foundation.json">Основа: браузер</a></p>
<p>Боевой сервер, PostgreSQL и системный композитор Windows этими стендами не проверены. Изображения не подтверждают новые серверные операции: сквозные сохранения и защита черновиков проверяются отдельными интеграционными сценариями.</p>
<script>
const samples=__SAMPLES__,select=document.getElementById('sample');
for(const [index,sample] of samples.entries())select.add(new Option(sample.label,index));
function show(){const sample=samples[Number(select.value)];document.getElementById('note').textContent=sample.note;const pictures=document.getElementById('pictures');pictures.replaceChildren();for(const picture of sample.images){const figure=document.createElement('figure'),caption=document.createElement('figcaption'),link=document.createElement('a'),image=document.createElement('img');caption.textContent=picture.title;image.src=picture.path;image.alt=picture.title+' — '+sample.label;link.href=picture.path;link.append(image);figure.append(caption,link);pictures.append(figure)}}
select.onchange=show;document.getElementById('previous').onclick=()=>{select.selectedIndex=(select.selectedIndex+samples.length-1)%samples.length;show()};document.getElementById('next').onclick=()=>{select.selectedIndex=(select.selectedIndex+1)%samples.length;show()};show();
</script></html>"""
    values = dict(
        TH_VERSION=gate["versions"]["handler"],
        TS_VERSION=gate["versions"]["stream"],
        STEPS=len(gate["steps"]),
        ADMIN_PAIRS=admin["pairs"],
        TIMINGS=timings,
        OLD_FONTS=sum(quality["smoke"]["before"]["fontWarnings"].values()),
        FOUNDATION=foundation["checks"],
        BROWSER=browser["checks"],
        WHEEL=html.escape(package["wheel"]),
        MODULES=package["modules"],
        BEFORE_FAILURES=len(structure["before"]["failures"]),
        CURRENT_FAILURES=len(structure["current"]["failures"]),
        MISSING=warning_counts["missing-property"],
        OVERRIDE=warning_counts["property-override"],
        FONTS=fonts,
        SAMPLES=json.dumps(samples, ensure_ascii=False).replace("<", "\\u003c"),
    )
    for name, value in values.items():
        page = page.replace("__" + name + "__", str(value))
    (OUTPUT / "index.html").write_text(page, encoding="utf-8")
    print(OUTPUT / "index.html")


if __name__ == "__main__":
    main()
