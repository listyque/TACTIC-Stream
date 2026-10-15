"""Standalone paired review of the production Groups views."""
import json
import sys
from pathlib import Path

users = '--users' in sys.argv
screen = 'users' if users else 'groups'
out = Path(__file__).resolve().parents[1] / ('frame_' + screen) / 'output'
checks = json.loads((out / 'vue.json').read_text(encoding='utf-8'))
data = json.dumps(checks['captures'])
html = '''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Administration → Groups · Tactic Frame</title>
<style>body{margin:24px;font:15px 'Segoe UI',sans-serif;background:#1b1e20;color:#f6f8fa}h1{font-size:24px}p{color:#aeb1b3}select,button{margin:0 10px 12px 0;padding:8px;background:#3a3e41;color:inherit;border:1px solid #5a5e60;border-radius:8px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:16px}img{width:100%;background:#1b1e20}figure{margin:0}figcaption{padding:8px 0;color:#78a6c4}.overlay .pair{display:block;position:relative}.overlay figure{max-width:1100px}.overlay figure:last-child{position:absolute;inset:0;opacity:var(--blend,.5)}.overlay figcaption{display:none}input{vertical-align:middle}@media(max-width:700px){.pair{grid-template-columns:1fr}}</style>
<h1>Administration → Groups · Tactic Frame</h1>
<p>Рабочие SecurityGroupsView.qml и SecurityGroups.vue. Один контракт структуры и переходов, локальные копии .mjs и собственные controls в двух самостоятельных сборках. Qt со штатным стилем Material и Edge. Отдельно проверена строка с однострочным именем.</p>
<p>__COUNT__ парных состояний; __RECTS__ измеренных прямоугольников, __STYLES__ проверок типографики/цвета текста, __BACKGROUNDS__ сравнений RGBA поверхностей и __INTERIORS__ проверок внутренних элементов. EN/RU, dark/light, 1100/800/360 px. Проверены оба порядка загрузки CSS. Полосы прокрутки видны постоянно при переполнении; проверочный браузер больше не скрывает их. Проверяются значок создания и отступы индикаторов.</p>
<select id="mode"><option>dark</option><option>light</option></select><select id="language"><option>en</option><option>ru</option></select><select id="width"><option>1100</option><option>800</option><option>360</option></select><select id="phase"></select>
<button id="overlay">Наложение / рядом</button><input id="blend" type="range" min="0" max="100" value="50" aria-label="Прозрачность Vue">
<div class="pair"><figure><figcaption>TH · native QML</figcaption><img id="qml" alt="Native Qt Groups"></figure><figure><figcaption>TS · Vue / Edge</figcaption><img id="vue" alt="Browser Groups"></figure></div>
<p>Проверены: каталог и участники, поиск, черновик, вкладки, создание, подтверждение сброса, неизвестный результат сохранения, busy. Дополнительно: настоящие клавиатура/тач и серверные записи на отдельной базе, ревизии и откат.</p>
<p>Ограничения: Qt и Chromium по-разному растеризуют текст. Это проверка Groups, не всей оболочки Administration. Геометрия строки также проверена при Qt scale factor 1.5; остальные DPI-режимы и СУБД этим прогоном не покрыты.</p>
<details><summary>Границы проверки</summary><p>Целевые native проверки Groups, серверные процедуры и упаковка проходят. Полный набор прочих экранов в этой правке не запускался. Предыдущий расширенный прогон обнаруживал ошибки test_touch_opens_action_menu_and_activates_its_item и test_builtin_schema_is_inspectable_but_cannot_be_edited; эти проверки не подтверждают их исправление.</p></details>
<script>const samples=__DATA__;const [mode,language,width,phase,qml,vue,overlay,blend]=['mode','language','width','phase','qml','vue','overlay','blend'].map(id=>document.getElementById(id));for(const name of [...new Set(samples.map(s=>s.phase))])phase.add(new Option(name,name));function show(){const key=[mode.value,language.value,width.value,phase.value].join('-');qml.src='groups-qml-'+key+'.png';vue.src='groups-vue-'+key+'.png'}document.querySelectorAll('select').forEach(el=>el.onchange=show);overlay.onclick=()=>document.body.classList.toggle('overlay');blend.oninput=()=>document.body.style.setProperty('--blend',blend.value/100);show()</script>'''
html = html.replace('__COUNT__', str(len(checks['captures']))).replace('__RECTS__', str(checks['rectangles'])).replace('__STYLES__', str(checks['styles'])).replace('__BACKGROUNDS__', str(checks['backgrounds'])).replace('__INTERIORS__', str(checks['interiors'])).replace('__DATA__', data)
if users:
    html = html.replace('SecurityGroupsView.qml и SecurityGroups.vue', 'AdminUsersView.qml и SecurityUsers.vue').replace('Отдельно проверена строка с однострочным именем.', 'Profile, Account и Groups, включая License type, пароль и архивные аккаунты.')
    html = html.replace('Геометрия строки также проверена при Qt scale factor 1.5.', 'Сценарии проверены настоящими мышью, клавиатурой и тачем на временных данных.')
    html = html.replace('каталог и участники', 'каталог и состав групп').replace('подтверждение сброса', 'подтверждения сохранения и сброса')
    html = html.replace('Administration → Groups', 'Administration → Users').replace('Qt Groups', 'Qt Users').replace('Browser Groups', 'Browser Users').replace('проверка Groups', 'проверка Users').replace('проверки Groups', 'проверки Users').replace('переноса Groups', 'переноса Users')
    html = html.replace('Дополнительно: настоящие клавиатура/тач и серверные записи на отдельной базе, ревизии и откат.', 'Отдельно проверены настоящий тач/клавиатура, подтверждения, пароль, состав групп, неизвестный ответ и конфликт. API проверен на временной SQLite; клиентские снимки используют изолированный API fixture.')
    html = html.replace('groups-qml-', 'users-qml-').replace('groups-vue-', 'users-vue-')
path = out / (screen + '-report.html')
path.write_text(html, encoding='utf-8')
print(path)
