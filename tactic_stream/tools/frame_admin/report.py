"""Standalone paired screenshots from completed native/browser captures."""
import json
from pathlib import Path
import sys

screen = sys.argv[1]
assert screen.replace('_', '').isalnum(), 'Expected a report directory name'
out = Path(__file__).resolve().parents[1] / ('frame_' + screen) / 'output'
native = json.loads((out / 'qml.json').read_text(encoding='utf-8'))
checks = json.loads((out / 'vue.json').read_text(encoding='utf-8'))
pairs = []
for browser in checks['captures']:
    match = next(row for row in native['captures'] if all(row[key] == browser[key] for key in ('mode', 'language', 'width', 'phase')))
    pairs.append(dict(browser, native=match['image']))
html = '''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tactic Frame · __SCREEN__</title>
<style>body{margin:24px;font:15px 'Segoe UI',sans-serif;background:#1b1e20;color:#f6f8fa}h1{font-size:24px}p{color:#aeb1b3}select,button{margin:0 10px 12px 0;padding:8px;background:#3a3e41;color:inherit;border:1px solid #5a5e60;border-radius:8px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:16px}img{width:100%}figure{margin:0}figcaption{padding:8px 0;color:#78a6c4}.overlay .pair{display:block;position:relative}.overlay figure{max-width:1100px}.overlay figure:last-child{position:absolute;inset:0;opacity:var(--blend,.5)}.overlay figcaption{display:none}input{vertical-align:middle}@media(max-width:700px){.pair{grid-template-columns:1fr}}</style>
<h1>Tactic Frame · __SCREEN__</h1>
<p>__COUNT__ парных состояний рабочих QML/Vue-компонентов. Один скелет и переходы, отдельные сборки и штатные контролы. Изолированные данные; настоящие мышь, клавиатура и редактирование текста. EN/RU, dark/light, 1100/800/360 px.</p>
<p>__RECTS__ проверок геометрии, __STYLES__ проверок типографики/цвета, __INTERIORS__ проверок индикаторов. Хеши исходников проверяются перед сравнением. Разные растеризаторы Qt/Chromium не позволяют требовать побитового совпадения текста. Этот отчёт не подтверждает готовность других разделов или работу с боевой БД.</p>
<select id="mode"><option>dark</option><option>light</option></select><select id="language"><option>en</option><option>ru</option></select><select id="width"><option>1100</option><option>800</option><option>360</option></select><select id="phase"></select>
<button id="overlay">Наложение / рядом</button><input id="blend" type="range" min="0" max="100" value="50" aria-label="Прозрачность Vue">
<div class="pair"><figure><figcaption>TH · native QML</figcaption><img id="qml" alt="Native Qt"></figure><figure><figcaption>TS · Vue / Edge</figcaption><img id="vue" alt="Browser"></figure></div>
<script>const samples=__DATA__;const [mode,language,width,phase,qml,vue,overlay,blend]=['mode','language','width','phase','qml','vue','overlay','blend'].map(id=>document.getElementById(id));for(const name of [...new Set(samples.map(s=>s.phase))])phase.add(new Option(name,name));function show(){const sample=samples.find(s=>s.mode===mode.value&&s.language===language.value&&s.width===Number(width.value)&&s.phase===phase.value);qml.src=sample.native;vue.src=sample.image}document.querySelectorAll('select').forEach(el=>el.onchange=show);overlay.onclick=()=>document.body.classList.toggle('overlay');blend.oninput=()=>document.body.style.setProperty('--blend',blend.value/100);show()</script>'''
for name, value in dict(SCREEN=screen, COUNT=len(pairs), RECTS=checks['rectangles'], STYLES=checks['styles'], INTERIORS=checks['interiors'], DATA=json.dumps(pairs)).items():
    html = html.replace('__' + name + '__', str(value))
path = out / (screen + '-report.html')
path.write_text(html, encoding='utf-8')
print(path)
