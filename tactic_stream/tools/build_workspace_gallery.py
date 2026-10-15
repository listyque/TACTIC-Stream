"""Validate fresh QML/Chromium evidence and produce a local comparison gallery."""
import html
import json
from pathlib import Path

from PIL import Image

OUTPUT = Path(__file__).resolve().parents[1]/'.screenshots/workspace-current'
PAIRS = [
    ('Шапка дока', 'dock-title'),
    ('Вкладки внутри дока', 'dock-stack-title'),
    ('Меню грипа', 'dock-context'),
    ('Меню управления доками', 'dock-menu'),
    ('Пресеты леяута', 'presets'),
    ('Основное меню объекта', 'object-basic'),
    ('Расширенное меню объекта', 'object-advanced'),
    ('Меню файла', 'file-menu'),
]


def main():
    native = json.loads((OUTPUT/'native.json').read_text(encoding='utf8'))
    assert not native['warnings'], native['warnings']
    sections, sizes = [], {}
    for title, name in PAIRS:
        figures = []
        for label, prefix in [('Текущий ТХ / QML', 'th'), ('Stream / Chromium', 'stream')]:
            filename = f'{prefix}-{name}.png'
            with Image.open(OUTPUT/filename) as image:
                width, height = image.size
                assert width > 0 and height > 0
            sizes[filename] = [width, height]
            figures.append(f'<figure><figcaption>{label} · {width}×{height}</figcaption>'
                f'<a href="{filename}"><img src="{filename}" loading="lazy" alt="{html.escape(title)}"></a></figure>')
        sections.append(f'<section><h2>{html.escape(title)}</h2><div class="pair">'+''.join(figures)+'</div></section>')
    page = '''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Workspace · 0.112.35</title><style>
body{padding:24px;margin:0;background:#1b1f20;color:#eef0f2;font:14px 'Segoe UI',sans-serif}h1{font-size:24px}h2{font-size:18px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:16px}figure{margin:0;overflow:auto;background:#24292c;border-radius:10px}figcaption{padding:10px;color:#abc0ce}img{display:block;max-width:100%;height:auto}section{margin:28px 0}p{max-width:1000px;line-height:1.6}pre{overflow:auto;font-size:11px}a{color:#80adc5}body.actual img{max-width:none}@media(max-width:800px){.pair{grid-template-columns:1fr}}
</style><h1>Блок 4 · доки, контекстные меню, леяуты и вкладки · 0.112.35</h1>
<p>Слева — свежий запуск неизменённых QML и контроллеров ТХ на изолированных тестовых моделях.
Справа — Chromium с временной БД и настоящими native-командами. Пользовательские настройки и проекты не менялись.
Пара пресетов показывает native-секцию на отдельной поверхности и браузерное всплывающее меню;
высота native-кадра включает пустую тестовую область под секцией.
Скриншоты не редактировались. Меню Qt включают внешний отступ/тень; браузерные снимки ограничены самим контроллом.
Видимые отличия: веб-доки плавают внутри браузера, добавлены разворачивание и явное меню положения;
отдельных окон ОС нет. ТХ показывает полный каталог своих доков, веб — реализованные панели.
В меню объекта сохранены доступные браузерные дополнения. Это проверка структуры и геометрии в заявленном
браузерном объёме, а не заявление о полном пиксельном совпадении всех состояний ТХ.</p>
<label><input type="checkbox" onchange="document.body.classList.toggle('actual',this.checked)"> Исходные пиксели (1:1)</label>
'''
    page += '<p>Native capture: '+html.escape(native['capturedAt'])+'</p>'
    page += '<details><summary>Исходники / SHA-256</summary><pre>'+html.escape(json.dumps(native['sources'], indent=2))+'</pre></details>'
    page += ''.join(sections)+'</html>'
    (OUTPUT/'index.html').write_text(page, encoding='utf8')
    (OUTPUT/'comparison.json').write_text(json.dumps(dict(version='0.112.35',capturedAt=native['capturedAt'],pairs=PAIRS,images=sizes), ensure_ascii=False, indent=2)+'\n',encoding='utf8')
    print('Validated', len(PAIRS), 'pairs:', OUTPUT/'index.html')


if __name__ == '__main__':
    main()
