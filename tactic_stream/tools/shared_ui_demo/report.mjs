import {readFile, writeFile} from 'node:fs/promises'
import {fileURLToPath} from 'node:url'
import {scene} from './gantt.ui.mjs'

export async function report() {
  const base = new URL('./', import.meta.url), out = new URL('./output/', base)
  const load = async path => JSON.parse(await readFile(new URL(path, base), 'utf8'))
  const spec = await load('gantt.json'), fixture = await load('../../frontend/tests/task_schedule_fixture.json'), palettes = await load('palettes.json')
  const native = await load('output/gantt-qml-measurements.json'), web = await load('output/gantt-vue-measurements.json'), cases = await load('gantt_cases.json')
  const captures = native.captures.map(capture => {
    const s = scene(spec, fixture, capture.state, capture.width, capture.height, palettes[capture.mode], capture.language)
    return {mode:capture.mode, language:capture.language, width:capture.width, height:capture.height, phase:capture.phase, qml:capture.image, vue:web.captures.find(v => v.mode===capture.mode&&v.language===capture.language&&v.width===capture.width&&v.phase===capture.phase).image,
      layers:s.layers.map(layer => ({id:layer.id,x:layer.x,y:layer.y,width:layer.width,height:layer.height})),
      bricks:s.layers.reduce((all,layer) => all.concat(layer.nodes.filter(node=>node.action||node.drag).map(node=>({id:node.id,kind:node.kind,x:layer.x+node.x,y:layer.y+node.y,width:node.width,height:node.height}))),[]),
      task:capture.state.tasks[0], changes:capture.state.undo.length}
  })
  const data=JSON.stringify({captures,cases,rectangles:web.rectangles}).replace(/</g,'\\u003c')
  await writeFile(new URL('gantt-report.html',out),`<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Общий Гант · QML / Vue</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#1b1e20;color:#f6f8fa;font:14px 'Segoe UI',sans-serif}main{max-width:1500px;margin:auto;padding:24px}h1{font-size:24px;margin:0 0 12px}h2{font-size:19px;margin:22px 0 12px}p{line-height:1.55;color:#c2c8cd}a{color:#8bc1e3}nav,.selectors{display:flex;flex-wrap:wrap;align-items:center;gap:12px;margin:16px 0}button,select{background:#3a3e41;color:inherit;border:1px solid #5a5e60;border-radius:8px;padding:8px 12px;font:inherit;cursor:pointer}label{display:flex;align-items:center;gap:7px}.comparison{display:flex;gap:16px;overflow:auto}.shot{margin:0;flex:1;min-width:0}.shot figcaption{margin-bottom:8px}.frame{position:relative;width:100%!important;height:auto!important}.frame img{display:block;width:100%;height:auto}.frame svg{position:absolute;inset:0;pointer-events:none;width:100%;height:100%}.frame .overlay{position:absolute;inset:0;opacity:.5;height:100%}.details{background:#303538;padding:12px 16px;border-radius:12px;line-height:1.6}.live{overflow:auto;background:#303538;padding:12px;border-radius:12px}iframe{display:block;border:0}code{color:#9cc9e5}details{margin:12px 0}summary{cursor:pointer}pre{white-space:pre-wrap;word-break:break-word;padding:12px;background:#303538;border-radius:8px}table{border-collapse:collapse;width:100%}td,th{text-align:left;vertical-align:top;border-bottom:1px solid #404346;padding:10px}
</style><main>
<h1>Tactic Frame · один интерактивный Гант — два нативных представления</h1>
<p>Общими являются строки, шкала дат, геометрия, группировка, полосы, прогресс, прокрутка, масштабирование, черновик и история изменений. QML использует настоящие контролы Handler; Vue — AppButton и AppCheckbox. В этом стенде нет WebEngine и запросов к серверу.</p>
<div class="details">Проверено: <b>${web.captures.length} парных состояний</b>, <b>${web.rectangles.toLocaleString('ru-RU')} прямоугольников</b>, две темы, два языка, два размера окна. Тесты выполняют одинаковые реальные клики, перетаскивания и прокрутку отдельно в Qt и Edge; сравнивают историю состояния, общий граф сцены, фактические цвета и шрифты.</div>
<nav><a href="web/gantt.html?language=ru">Открыть интерактивный Vue отдельно</a><a href="../start_demo.cmd">Запуск QML и Vue: start_demo.cmd</a><a href="../gantt.json">Параметры и переводы</a><a href="../gantt.ui.mjs">Общий скелет UI</a><a href="../gantt.state.mjs">Общее состояние и обработчики</a><a href="../GanttDemo.qml">QML-рендерер</a><a href="../GanttDemo.vue">Vue-рендерер</a><a href="../README.md">Как устроен Tactic Frame</a><a href="../../../docs/shared_ui_contract.md">Правила реализации</a></nav>
<h2>Парные снимки настоящих движков</h2>
<div class="selectors"><label>Тема <select id="mode"><option value="dark">Тёмная</option><option value="light">Светлая</option></select></label><label>Язык <select id="language"><option value="ru">Русский</option><option value="en">English</option></select></label><label>Размер <select id="size"><option value="1100">1100 × 660</option><option value="840">840 × 560</option></select></label><label>Сценарий <select id="phase"></select></label><label><input id="skeleton" type="checkbox">Показать общий скелет</label><label><input id="overlay" type="checkbox">Наложить Vue поверх QML</label></div>
<p id="trace"></p><div id="comparison" class="comparison"></div>
<p>Жёлтые рамки — общие области компоновки; голубые — интерактивные кирпичики. Координаты берутся из общего скелета. Полупрозрачное наложение помогает заметить отличия отрисовки.</p>
<h2>Живой Vue</h2><p>Меняйте даты за тело и края полосы; нижний белый маркер меняет прогресс. Обзор внизу прокручивает время. Колесо прокручивает строки, Shift + колесо — время, Ctrl + колесо — масштаб. Escape отменяет незавершённое перетаскивание.</p>
<div class="live"><iframe id="live" title="Интерактивный общий Гант"></iframe></div>
<h2>Границы этого доказательства</h2>
<table><tr><th>Доказано на стенде</th><th>Не является готовым переносом рабочего Ганта</th></tr><tr><td>Один исходник действительно управляет сложным виджетом в Qt и браузере: 12 задач, группы и сворачивание, выделение, перемещение, оба края длительности, прогресс, назначение дат, групповой сдвиг с рабочими днями, изменение длительности, Undo/Redo, обзор и прокрутка.</td><td>Сохранение в TACTIC, ACL, серверные ошибки, конфликты ресурсов, инспектор, вехи и все операции текущего production-Ганта сюда не подключены. Изменения живут в памяти и сбрасываются при перезапуске. Исходные production-виджеты не заменены.</td></tr><tr><td>Геометрия общая; фиксируются фактические размеры Qt и DOM. Используются те же данные, роли цвета и Segoe UI.</td><td>Растеризация шрифта Qt и Chromium отличается. Это не доказательство совпадения каждого пикселя. Не проверены тысячи строк, другие ОС, масштаб Windows и мобильная компоновка.</td></tr></table>
<details><summary>Как запустить настоящее окно QML</summary><pre>cd D:\\code\\TACTIC_VUE\\tactic_stream
.venv\\Scripts\\python.exe -B tools\\shared_ui_demo\\gantt_qml.py --language ru --mode dark</pre></details>
<details><summary>Как воспроизвести проверку</summary><pre>.venv\\Scripts\\python.exe -B -X utf8 tools\\shared_ui_demo\\gantt_qml.py --capture
cd frontend
$env:STREAM_BROWSER_CHANNEL='msedge'
node tests/shared_gantt_demo.mjs</pre></details>
</main><script>
const data=${data};const $=id=>document.getElementById(id);
for(const c of data.cases){const option=document.createElement('option');option.value=c.phase;option.textContent=c.phase;$('phase').append(option)}
function draw(){const c=data.captures.find(c=>c.mode===$('mode').value&&c.language===$('language').value&&c.width===Number($('size').value)&&c.phase===$('phase').value);
 const svg=$('skeleton').checked?'<svg viewBox="0 0 '+c.width+' '+c.height+'" width="'+c.width+'" height="'+c.height+'">'+c.layers.map(l=>'<rect x="'+l.x+'" y="'+l.y+'" width="'+l.width+'" height="'+l.height+'" fill="none" stroke="#ffe06b" stroke-width="2"/><text x="'+(l.x+4)+'" y="'+(l.y+13)+'" fill="#ffe06b" font-size="11">'+l.id+'</text>').join('')+c.bricks.filter(b=>b.x>=0&&b.y>=0&&b.x+b.width<=c.width&&b.y+b.height<=c.height).map(b=>'<rect x="'+b.x+'" y="'+b.y+'" width="'+b.width+'" height="'+b.height+'" fill="none" stroke="#51c6ff" stroke-width="1"/>').join('')+'</svg>':'';
 const frame=(name,img,extra='')=>'<figure class="shot"><figcaption>'+name+'</figcaption><div class="frame" style="width:'+c.width+'px;height:'+c.height+'px"><img src="'+img+'" width="'+c.width+'" height="'+c.height+'">'+extra+svg+'</div></figure>';
 $('comparison').innerHTML=$('overlay').checked?frame('QML + Vue · наложение 50%',c.qml,'<img class="overlay" src="'+c.vue+'" width="'+c.width+'" height="'+c.height+'">'):frame('Нативный QML',c.qml)+frame('Vue / Edge',c.vue);
 $('trace').textContent='Robot body: '+c.task.start+' → '+c.task.end+' · прогресс '+c.task.progress+'% · история '+c.changes;
 const url='web/gantt.html?mode='+c.mode+'&language='+c.language;if($('live').getAttribute('src')!==url)$('live').src=url;$('live').width=c.width;$('live').height=c.height;
}
for(const id of ['mode','language','size','phase','skeleton','overlay'])$(id).addEventListener('change',draw);draw();
</script></html>`)
}

if (process.argv[1] === fileURLToPath(import.meta.url)) await report()
