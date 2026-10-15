"""Side-by-side evidence from current Handler QML and private Chromium scenarios."""
from pathlib import Path
import html
import json
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / '.screenshots/collaboration-current'
PAIRS = [
    ('Inspector: no task', 'th-inspector-empty.png', 'stream-inspector-empty.png'),
    ('Inspector: task and work hours', 'th-inspector-task.png', 'stream-inspector-task.png'),
    ('Inspector: collapsed', 'th-inspector-collapsed.png', 'stream-inspector-collapsed.png'),
    ('Inspector: related tasks', 'th-inspector-related.png', 'stream-inspector-related.png'),
    ('Notes: short history', 'th-notes-single.png', 'stream-notes.png'),
    ('Messages: conversation', 'th-messages.png', '../messages-web.png'),
    ('Task Manager: Table', '../handler-current/tasks-workspace-populated.png', 'stream-manager-table.png'),
    ('Task Manager: Gantt', '../handler-current/tasks-gantt.png', 'stream-manager-gantt.png'),
    ('Task Manager: Calendar', '../handler-current/tasks-calendar.png', 'stream-manager-calendar.png'),
    ('Tasks: process cards', '../handler-current/task-process-cards-1232.png', 'stream-process-cards.png'),
    ('Tasks: compact rows', '../handler-current/task-process-compact-1232.png', 'stream-process-compact.png'),
]

def main():
    native = json.loads((OUTPUT/'native.json').read_text(encoding='utf8'))
    sections = []
    images = {}
    for title, reference, browser in PAIRS:
        figures = []
        for label, relative in [('Current Handler QML',reference),('Chromium / Stream',browser)]:
            path = OUTPUT/relative
            assert path.is_file(), path
            with Image.open(path) as image:
                width,height = image.size
                assert width > 0 and height > 0
            images[relative] = dict(width=width,height=height)
            figures.append('<figure><figcaption>'+html.escape(label)+f' · {width}×{height}</figcaption>'
                +'<a href="'+html.escape(relative)+'"><img loading="lazy" src="'+html.escape(relative)+'" alt="'+html.escape(title+' / '+label)+'"></a></figure>')
        sections.append('<section><h2>'+html.escape(title)+'</h2><div class="pair">'+''.join(figures)+'</div></section>')
    sources = '<details><summary>QML/controller SHA-256</summary><pre>'+html.escape(json.dumps(native['sources'],indent=2))+'</pre></details>'
    page = '''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Task collaboration · 0.112.34</title><style>
body{margin:0;padding:24px;background:#1b1f20;color:#eef0f2;font:14px 'Segoe UI',sans-serif}h1{font-size:24px}h2{font-size:18px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:16px}figure{margin:0;overflow:auto;background:#24292c;border-radius:10px}figcaption{padding:10px;color:#abc0ce}img{display:block;max-width:100%;height:auto}section{margin:28px 0}a{color:#80adc5}p{max-width:1050px;line-height:1.6}pre{overflow:auto;font-size:11px}body.actual img{max-width:none}@media(max-width:800px){.pair{grid-template-columns:1fr}}
</style><h1>Блок 3 · задачи, Inspector, заметки и сообщения · 0.112.34</h1>
<p>Слева — текущие неизменённые QML/контроллеры ТХ, запущенные через изолированные тестовые модели.
Справа — настоящий Chromium с отдельным временным backend и native-командами. Скриншоты не редактировались.
Данные тестов различаются: названия, даты, статусы, число связанных задач и наличие preview-файлов.
Белые preview справа — реальные однопиксельные изображения тестовых записей.
Номерные сценарии проверяют сохранение, конфликты и права; эти картинки показывают структуру и геометрию.
Различия данных и размеров кадра исключают заявление о полном пиксельном совпадении.</p>
<label><input type="checkbox" onchange="document.body.classList.toggle('actual',this.checked)"> Показать в исходных пикселях (1:1)</label>
'''+ '<p>Native capture: '+html.escape(native['capturedAt'])+'</p>'+sources+''.join(sections)+'</html>'
    (OUTPUT/'index.html').write_text(page,encoding='utf8')
    (OUTPUT/'comparison.json').write_text(json.dumps(dict(version='0.112.34',nativeCapturedAt=native['capturedAt'],pairs=PAIRS,images=images),ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Validated and saved',len(PAIRS),'pairs:',OUTPUT/'index.html')

if __name__ == '__main__': main()
