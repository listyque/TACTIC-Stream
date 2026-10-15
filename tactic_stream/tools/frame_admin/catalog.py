"""Build the Administration evidence index only from fresh, completed checks."""
import hashlib
import html
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
TH = Path('D:/code/th_codex')
OUT = Path(__file__).resolve().parent / 'output'
SCREENS = ['groups', 'users', 'security', 'raw', 'sidebar', 'columns', 'types',
           'naming', 'graph', 'graph_editor', 'layout', 'shell', 'rules', 'deletion']


TITLES = {'groups': 'Groups — группы и участники', 'users': 'Users — профили и аккаунты', 'security': 'Access rules — права доступа', 'raw': 'Raw database — строки и ячейки', 'sidebar': 'Sidebar Editor — навигация и доступ', 'columns': 'Columns Editor — колонки и виджеты', 'types': 'Search Types — типы, поля и сведения', 'naming': 'Search Types → Naming', 'graph': 'Search Types → Карта связей', 'graph_editor': 'Project schema и Workflow — редакторы графов', 'layout': 'Layout Editor — компоновка и XML', 'shell': 'Оболочка Administration — навигация и черновики', 'rules': 'Workflow → Зависимости и действия', 'deletion': 'Schema → Подтверждение удаления типа'}


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    runs = read(OUT / 'browser/results.json')
    assert {row['screen'] for row in runs} == set(SCREENS), 'Incomplete browser run'
    assert all(row['status'] == 0 for row in runs), 'A browser suite failed'
    native_runs = read(OUT / 'native/results.json')
    assert native_runs and all(row['status'] == 0 for row in native_runs), 'A native check failed'
    assert any('test_naming_editor.' in row['test'] for row in native_runs), 'Native run is incomplete'
    renderer = [path for path in (ROOT / 'frontend/src').rglob('*') if path.is_file()]
    totals = dict(pairs=0, rectangles=0, styles=0, interiors=0)
    rows = []
    for screen in SCREENS:
        directory = ROOT / 'tools' / ('frame_' + screen) / 'output'
        qml, vue = read(directory / 'qml.json'), read(directory / 'vue.json')
        assert {'thlib/ui/qml/controls/MaterialIcon.qml', 'thlib/ui/qml/Theme.qml'} <= qml['nativeSources'].keys(), screen + ': incomplete native dependencies'
        assert (directory / 'vue.json').stat().st_mtime >= (directory / 'qml.json').stat().st_mtime, screen + ': stale browser capture'
        assert all(path.stat().st_mtime <= (directory / 'vue.json').stat().st_mtime for path in renderer if path.is_file()), screen + ': changed renderer'
        for name, expected in qml['sha256'].items():
            assert hashlib.sha256((ROOT / 'src/tactic_stream/shared_ui' / name).read_bytes()).hexdigest() == expected, screen + ': changed module ' + name
        for name, expected in qml['nativeSources'].items():
            assert hashlib.sha256((TH / name).read_bytes()).hexdigest() == expected, screen + ': changed native source ' + name
        assert len(qml['captures']) == len(vue['captures']), screen + ': incomplete capture'
        for capture in [*qml['captures'], *vue['captures']]:
            assert (directory / capture['image']).is_file(), screen + ': missing image'
        count = len(vue['captures'])
        totals['pairs'] += count
        for key in ('rectangles', 'styles', 'interiors'):
            totals[key] += vue.get(key, 0)
        subprocess.run([sys.executable, '-B', '-X', 'utf8', str(Path(__file__).with_name('report.py')), screen], check=True)
        rows.append(f'<tr><td><a href="../../frame_{screen}/output/{screen}-report.html">{html.escape(TITLES[screen])}</a></td><td>{count}</td><td>{vue["rectangles"]}</td><td>{vue["styles"]}</td></tr>')
    evidence = dict(totals, native_tests=len(native_runs), browser_suites=len(runs))
    (OUT / 'summary.json').write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf-8')
    page = '''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tactic Frame · Administration</title><style>body{max-width:1100px;margin:32px auto;padding:0 20px;background:#1b1e20;color:#f3f4f5;font:16px/1.55 'Segoe UI',sans-serif}a{color:#8bb7d0}h1{font-size:28px}p{color:#c1c6ca}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:9px 14px;border-bottom:1px solid #45494c}th{background:#363b3e}.notice{padding:16px;border-radius:12px;background:#353a3e}code{color:#b6d6e7}</style>
<h1>Tactic Frame · вся Administration</h1>
<p>__MODULES__ локальных модулей в двух независимых продуктах. Общая структура, переходы и размеры; штатные контролы Qt/QML и Vue. Встроенного браузера в нативном Layout Editor нет.</p>
<p><strong>__PAIRS__ парных состояний · __NATIVE__ нативных проверок · 14 веб-стендов.</strong><br>__RECTS__ сверок геометрии, __STYLES__ типографики/цвета, __INTERIORS__ внутренних индикаторов. Настоящие мышь, клавиатура, touch и ввод текста; EN/RU, dark/light, три размера окна. Хеши и свежесть снимков проверены при сборке каталога.</p>
<table><thead><tr><th>Стенд / открыть сравнение</th><th>Пары</th><th>Геометрия</th><th>Типографика/цвета</th></tr></thead><tbody>__ROWS__</tbody></table>
<p>В каждом отчёте можно выбрать тему, язык, размер, состояние и наложение изображений. Прямоугольники контролов проверяются строго; центрирование текста учитывает измеренные ширины букв в разных растеризаторах Qt/Chromium.</p>
<p>Собранное приложение дополнительно проверено на приватной SQLite-базе: все разделы, скрытые черновики, ссылки Workflow, вложенный создатель типа; Layout — создание, проверка, подтверждение/запись, открытие, таблица/карточки/дерево, повторное использование и мобильное отображение. Сохранения проверяются отдельно от снимков.</p>
<p>Это сравнение двух Frame-реализаций. Оно не подтверждает совпадение всей админки с исходным ТХ. Независимые исходные снимки графа, библиотеки Workflow, главной панели и доков собраны в <a href="../../frame_foundation/output/index.html">отчёте по фундаменту</a>. Полная миграция пяти блоков продолжается.</p>
<p><a href="native/results.json">Нативные проверки и журналы</a> · <a href="browser/results.json">Веб-стенды и журналы</a> · <a href="summary.json">Итоговые счётчики</a></p>
<div class="notice"><strong>Границы проверки</strong><p>Боевой сервер, PostgreSQL и системный композитор/рамка Windows не проверены. В ТХ Open view использует системный браузер без ticket в URL; сервер должен поддерживать API layout-authoring. Старые вспомогательные QML-компоненты сохранены в соответствующих feature-каталогах.</p><p>Общие structure/lint/smoke gates имеют ошибки, существовавшие до этой работы. Они сопоставлены с архивом; новые регрессии от переноса исправлены, бюджеты не увеличены. Подробности и незавершённый объём приведены в отчёте по фундаменту.</p></div></html>'''
    for key, value in dict(MODULES=len(list((ROOT / 'src/tactic_stream/shared_ui').rglob('*.mjs'))), PAIRS=totals['pairs'], NATIVE=len(native_runs), RECTS=totals['rectangles'], STYLES=totals['styles'], INTERIORS=totals['interiors'], ROWS=''.join(rows)).items():
        page = page.replace('__' + key + '__', str(value))
    (OUT / 'index.html').write_text(page, encoding='utf-8')
    print(json.dumps(evidence))


if __name__ == '__main__':
    main()
