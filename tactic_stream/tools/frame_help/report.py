"""Build a source-checked original/native/browser Help comparison."""
import hashlib
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TH = Path('D:/grav/Tactic Stream/TH')
OUT = Path(__file__).resolve().parent / 'output'


def verify(root, sources):
    for name, expected in sources.items():
        path = root / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, f'Stale evidence: {path}'


def main():
    native = json.loads((OUT / 'native.json').read_text(encoding='utf-8'))
    browser = json.loads((OUT / 'stream.json').read_text(encoding='utf-8'))
    verify(ROOT / 'src/tactic_stream/shared_ui', native['sha256'])
    verify(TH, native['nativeSources'])
    verify(ROOT / 'tools/frame_foundation/reference/thlib/ui/qml', native['originalSources'])
    verify(ROOT, browser['webSources'])
    sections = []
    for row in browser['captures']:
        signature = [row[key] for key in ('style', 'dark', 'language', 'width')]
        peers = [item for item in native['captures'] if [item[key] for key in ('style', 'dark', 'language', 'width')] == signature]
        assert len(peers) == 2
        original = next(item for item in peers if item['original'])
        current = next(item for item in peers if not item['original'])
        images = []
        for title, item in [('Исходный ТХ', original), ('Frame · ТХ', current), ('Frame · ТС', row)]:
            assert (OUT / item['image']).is_file()
            images.append(f'<figure><figcaption>{title}</figcaption><a href="{item["image"]}" target="_blank"><img loading="lazy" src="{item["image"]}" alt="{title}"></a></figure>')
        diagnostics = '; '.join(original['originalDiagnostics'])
        label = f'{row["style"]} · {"тёмная" if row["dark"] else "светлая"} · {row["language"]} · {row["width"]} px'
        sections.append('<details open><summary>' + html.escape(label) + '</summary><div class="comparison">' + ''.join(images) + '</div>' + (f'<p>Дефект эталона: {html.escape(diagnostics)}</p>' if diagnostics else '') + '</details>')
    content = f'''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tactic Frame · Help</title><style>body{{font:14px/1.5 Segoe UI,sans-serif;background:#1d2022;color:#eee;margin:24px}}h1{{font-size:24px}}a{{color:#8ebad3}}.comparison{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}}figure{{margin:0}}img{{width:100%;height:auto}}figcaption{{padding:8px 0}}details{{margin:20px 0;padding:12px;border:1px solid #555;border-radius:14px}}summary{{cursor:pointer}}.note{{max-width:1000px}}@media(max-width:800px){{.comparison{{grid-template-columns:1fr}}}}</style>
<h1>Help: исходный ТХ → Frame ТХ → Frame ТС</h1>
<p>{len(browser['captures'])} пар Qt/Vue; {browser['comparisons']:,} проверок фактических границ, видимого текста и поверхностей. Три темы, светлая/тёмная, EN/RU, 1100/320 px. Отпечатки исходников и статей проверены при сборке отчёта.</p>
<p class="note">В сравнении используется один комплект статей текущего Handler; исходный UI взят из сохранённой копии до переноса. Снимки показывают содержимое окна без системной рамки. Нативный QTextDocument и браузерный Markdown имеют разные механизмы вёрстки и растеризации: содержимое документа не объявляется попиксельно идентичным. У исходного Help нет отдельной телефонной страницы тем. Выявленные дефекты эталона перечислены рядом со снимками.</p>
<p class="note">Проверки поведения выполняются отдельно: настоящий поиск, контекстные переходы, экспорт, язык, возврат прокрутки и экземпляра окна, ownership, фокус, мышь/клавиатура/тач. Этот отчёт не закрывает весь атлас контролов или полную композицию главного workspace.</p>
{''.join(sections)}</html>'''
    (OUT / 'index.html').write_text(content, encoding='utf-8')
    print(OUT / 'index.html')


if __name__ == '__main__':
    main()
