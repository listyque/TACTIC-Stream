"""Validate current phone acceptance and QML reference images; build a local gallery."""
import html
import json
from pathlib import Path

from PIL import Image

OUTPUT = Path(__file__).resolve().parents[1] / '.screenshots/mobile-current'
SECTIONS = [
    ('Главное окно и компактные объекты', 'native-main/main.png', 'phone-items-360.png'),
    ('Задачи', 'native-main/main-with-tasks.png', 'phone-tasks-320.png'),
    ('Task Inspector и заметки', 'native/th-notes.png', 'phone-inspector-320.png'),
    ('Сообщения', 'native/th-messages.png', 'phone-messages-320.png'),
    ('Файлы снапшота: явные действия тапом', None, 'phone-snapshot-320.png'),
    ('Настольная раскладка до и после телефона', 'desktop-before.png', 'desktop-after.png'),
]


def main():
    acceptance = json.loads((OUTPUT / 'acceptance.json').read_text(encoding='utf8'))
    native = json.loads((OUTPUT / 'native/native.json').read_text(encoding='utf8'))
    assert not acceptance['errors'], acceptance['errors']
    assert {320, 360, 390, 640, 700, 1280}.issubset(acceptance['widths'])
    sections, sizes = [], {}
    for title, reference, phone in SECTIONS:
        figures = []
        for filename in [reference, phone]:
            if not filename:
                continue
            with Image.open(OUTPUT / filename) as image:
                width, height = image.size
                assert width > 0 and height > 0
            sizes[filename] = [width, height]
            label = 'Текущий ТХ / QML' if filename.startswith('native') else 'Stream / Chromium'
            figures.append(f'<figure><figcaption>{label} · {width}×{height}</figcaption>'
                f'<a href="{filename}"><img src="{filename}" loading="lazy" alt="{html.escape(title)}"></a></figure>')
        sections.append(f'<section><h2>{html.escape(title)}</h2><div class="pair">'+''.join(figures)+'</div></section>')
    page = '''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Мобильное приложение · 0.112.36</title><style>
body{padding:24px;margin:0;background:#1b1f20;color:#eef0f2;font:14px 'Segoe UI',sans-serif}h1{font-size:24px}h2{font-size:18px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:16px}figure{margin:0;overflow:auto;background:#24292c;border-radius:10px}figcaption{padding:10px;color:#abc0ce}img{display:block;max-width:100%;height:auto}section{margin:28px 0}p{max-width:1000px;line-height:1.6}pre{overflow:auto;font-size:11px}a{color:#80adc5}body.actual img{max-width:none}@media(max-width:800px){.pair{grid-template-columns:1fr}}
</style><h1>Блок 5 · мобильное приложение · 0.112.36</h1>
<p>Текущие неизменённые QML/контроллеры ТХ запущены на изолированных тестовых моделях.
Снимки браузера получены в Chromium с touch, временной БД и настоящими native-командами.
Телефонная компоновка — намеренная адаптация Stream: одна панель, компактные объекты и задачи,
скрытые доки/fast-sidebar, действия тапом, доступная область заметок и явная отправка.
Галерея не заявляет совпадение мобильного экрана с настольным ТХ. Последняя пара проверяет
возврат desktop-геометрии и вида, а не одинаковый контент после тестовых записей.
Проверены перенос строки, черновики, вложение заметки, запись статуса задачи, сообщение,
открытие файла, восстановление после reload и синтетический visual viewport клавиатуры.
Реальные Android/iOS-клавиатуры, Safari и Firefox ещё требуют проверки на устройствах.</p>
<p>Общая сверка исходников обнаружила изменения восьми файлов соседнего ТХ относительно
сохранённого манифеста. <a href="source-drift.json">Обе ревизии и следующий шаг аудита</a>.
Это отдельный незакрытый результат блока совместимости; мобильные сценарии проходят.</p>
<label><input type="checkbox" onchange="document.body.classList.toggle('actual',this.checked)"> Исходные пиксели (1:1)</label>
'''
    page += '<p>Chromium: '+html.escape(acceptance['capturedAt'])+' · QML: '+html.escape(native['capturedAt'])+'</p>'
    page += '<details><summary>Исходники / SHA-256</summary><pre>'+html.escape(json.dumps(native['sources'], indent=2))+'</pre></details>'
    page += ''.join(sections)+'</html>'
    (OUTPUT / 'index.html').write_text(page, encoding='utf8')
    (OUTPUT / 'comparison.json').write_text(json.dumps(dict(version='0.112.36', acceptance=acceptance,
        native=native['capturedAt'], images=sizes), ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print('Validated', len(SECTIONS), 'sections:', OUTPUT / 'index.html')


if __name__ == '__main__':
    main()
