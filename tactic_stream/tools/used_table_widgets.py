"""Table widgets mentioned anywhere in shipped/template/saved configs; read-only."""
import ast
from collections import Counter
import csv
import html
import json
from pathlib import Path
import re
import sqlite3
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'tools/frame_table/output/used_widgets'
OUT.mkdir(parents=True, exist_ok=True)
inventory = json.loads((ROOT / 'tools/frame_table/fixtures/legacy_inventory.json').read_text(encoding='utf-8'))
classes = inventory['classes']
aliases = {row['alias']: row['handler'] for row in inventory['catalog']}
sources = []
for path in (ROOT / 'src/tactic_stream/config/search_type/widget').rglob('*.xml'):
    sources.append((str(path.relative_to(ROOT)), path.read_text(encoding='utf-8-sig')))
template = ROOT.parent / 'cg/config_widget_config.spt'
for block in template.read_text(encoding='utf-8-sig').split('#-- Start Entry --#'):
    if not block.strip():
        continue
    values = {}
    for node in ast.walk(ast.parse(block)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'set_value' and len(node.args) == 2:
            values[ast.literal_eval(node.args[0])] = ast.literal_eval(node.args[1])
    if values.get('config'):
        sources.append(('cg-template:' + str(values.get('search_type')) + '/' + str(values.get('view')), values['config']))
for path in (ROOT / 'data/db').glob('*.db'):
    with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True) as db:
        if not db.execute("SELECT name FROM sqlite_master WHERE name='spt_widget_config'").fetchone():
            continue
        for code, kind, view, status, xml in db.execute('SELECT code,search_type,view,s_status,config FROM spt_widget_config'):
            if xml:
                sources.append((path.name + ':' + str(kind) + '/' + str(view) + '/' + str(code) + (' [retired]' if status == 'retired' else ''), xml))

def resolve(handler):
    if handler == 'tactic.ui.table.ExploreElementWdg':
        handler = 'tactic.ui.table.ExplorerElementWdg'
    name = handler.rsplit('.', 1)[-1]
    candidates = [c['qualified_class'] for c in classes if c['class'] == name]
    if '.' not in handler:
        candidates = [q for q in candidates if q.startswith('pyasm.widget.')]
    elif handler not in candidates:
        package = handler.rsplit('.', 1)[0] + '.'
        candidates = [q for q in candidates if q.startswith(package)]
    else:
        return handler
    return candidates[0] if len(candidates) == 1 else None

used = {}
invalid = []
for source, xml in sources:
    if not isinstance(xml, str) or not xml.lstrip().startswith('<'):
        invalid.append({'source': source, 'reason': 'Not XML; no execution attempted'})
        continue
    try:
        tree = ET.fromstring(xml)
    except ET.ParseError as error:
        invalid.append({'source': source, 'reason': str(error)})
        continue
    parents = {child: parent for parent in tree.iter() for child in parent}
    def location(node):
        parts = []
        while node is not None:
            parts.append(node.tag + ('[' + node.get('name') + ']' if node.get('name') else ''))
            node = parents.get(node)
        return '/'.join(reversed(parts))
    for node in tree.iter():
        references = []
        if node.get('class'):
            references.append((node.get('class'), 'class', [child.tag for child in node]))
        if node.get('widget') in aliases:
            references.append((aliases[node.get('widget')], 'widget:' + node.get('widget'), [child.tag for child in node]))
        if node.tag in {'dynamic_class', 'class_name'} and node.text:
            references.append((node.text.strip(), node.tag, []))
        # Explicit class mentions in embedded templates/scripts also count.
        for text in (node.text, node.tail):
            if text:
                references.extend((h, 'embedded reference', []) for h in re.findall(r'\b(?:tactic\.ui|pyasm\.(?:widget|prod))\.[\w.]+(?:Wdg|TableElement)\b', text))
        for handler, reference, options in references:
            canonical = resolve(handler)
            if not canonical and handler.rsplit('.', 1)[-1] not in {c['class'] for c in classes} and not handler.endswith('ExploreElementWdg'):
                continue
            key = canonical or handler
            row = used.setdefault(key, {'class': key, 'handlers': [], 'uses': [], 'status': 'Needs source/example/implementation', 'done': []})
            if handler not in row['handlers']:
                row['handlers'].append(handler)
            evidence = {'source': source, 'location': location(node), 'reference': reference, 'options': sorted(set(options))}
            if evidence not in row['uses']:
                row['uses'].append(evidence)
            if handler.startswith('pyasm.prod.'):
                row['status'] = 'Excluded: pyasm.prod'
            elif not canonical:
                row['status'] = 'Invalid class reference: repair configuration'
            elif canonical.endswith('.SnapshotServerElementWdg'):
                row['status'] = 'Excluded: unfinished source'
            elif canonical.endswith('.input_wdg.TextWdg'):
                row['status'] = 'Input widget / compatible table alias; separate form contract'
            elif canonical in inventory['supported']:
                row['status'] = 'Connected partially: check all used options and actions'

progress = OUT / 'used-widget-progress.json'
if progress.exists():
    for key, value in json.loads(progress.read_text(encoding='utf-8')).items():
        if key in used:
            used[key].update(value)
rows = sorted(used.values(), key=lambda row: row['class'])
assert rows and any(r['class'].endswith('.JsonElementWdg') for r in rows)
assert any(r['class'].endswith('.XmlWdg') for r in rows)
assert len(rows) == len({r['class'] for r in rows})
payload = {'sources_scanned': len(sources), 'source_issues': invalid, 'widgets': rows,
           'rule': 'Any mention counts, including definitions/dynamic/embedded references; not proof of runtime use. Databases opened mode=ro.'}
(OUT / 'used-table-widget-checklist.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
with (OUT / 'used-table-widget-checklist.csv').open('w', encoding='utf-8-sig', newline='') as f:
    writer = csv.writer(f, delimiter=';')
    writer.writerow(['Class', 'Handlers', 'Status', 'Checked', 'Source', 'Location', 'Options'])
    for row in rows:
        for use in row['uses']:
            writer.writerow([row['class'], ', '.join(row['handlers']), row['status'], ', '.join(row['done']), use['source'], use['location'], ', '.join(use['options'])])
status_ru = {
    'Needs source/example/implementation': 'Нужны исходник, пример и реализация',
    'Connected partially: check all used options and actions': 'Частично подключён: проверить все используемые опции и действия',
    'Excluded: pyasm.prod': 'Исключён: pyasm.prod',
    'Invalid class reference: repair configuration': 'Ошибка имени класса: исправить конфиг',
    'Excluded: unfinished source': 'Исключён: недописанный исходник',
    'Input widget / compatible table alias; separate form contract': 'Input / совместимый alias; отдельный контракт формы',
    'Display verified; inline editor pending': 'Отображение проверено; inline editor пока не готов',
    'Used read-only scenario verified': 'Используемый сценарий чтения проверен',
    'Current Handler scenario implemented; legacy options remain': 'Текущий сценарий ТХ перенесён; остальные legacy-опции проверяются отдельно',
}
escape = html.escape
body = ['<!doctype html><html lang="ru"><meta charset="utf-8"><title>Чеклист используемых Table View widgets</title><style>body{font:15px/1.5 system-ui;background:#24292e;color:#e5e9ed;margin:24px}table{width:100%;border-collapse:collapse}td,th{padding:10px;text-align:left;vertical-align:top;border-bottom:1px solid #4b5158}code{overflow-wrap:anywhere}a{color:#85c4e5}details{margin:8px 0}</style><h1>Чеклист используемых Table View widgets</h1>',
        f'<p>Просмотрено {len(sources)} конфигураций; {len(rows)} классов и отдельных ошибочных ссылок. Все упоминания входят в работу: definition, display, dynamic и встроенные тексты. Это не доказательство исполнения виджета. БД прочитаны mode=ro.</p>',
        '<p>Для каждого виджета: исходник/наследование → реальный пример → ТХ/ТС → параметры/действия/права → снимки → справка. Исключения и недописанные классы не переносим. Чекбокс сценария не означает завершённость всего класса/API.</p><p><a href="used-table-widget-checklist.csv">CSV</a> · <a href="used-table-widget-checklist.json">JSON</a> · <a href="table-view-audit.html">Полный каталог</a></p>']
for status, count in Counter(row['status'] for row in rows).items():
    body.append('<h2>'+escape(status_ru.get(status,status))+f' ({count})</h2><table><tr><th>Виджет</th><th>Проверено / осталось</th><th>Где упоминается</th></tr>')
    for row in [r for r in rows if r['status'] == status]:
        uses = ''.join('<li><code>'+escape(u['source']+' → '+u['location'])+'</code>; опции: '+escape(', '.join(u['options']) or 'нет')+'</li>' for u in row['uses'])
        checks = '<br>'.join('☑ '+escape(item) for item in row['done']) or '☐ Исходник, пример, действия и UI пока не проверены целиком'
        if row.get('todo'):
            checks += '<br>'+'<br>'.join('☐ '+escape(item) for item in row['todo'])
        body.append('<tr><td><code>'+escape(row['class'])+'</code></td><td>'+checks+'</td><td><details><summary>Упоминаний: '+str(len(row['uses']))+'</summary><ul>'+uses+'</ul></details></td></tr>')
    body.append('</table>')
body.append('</html>')
(OUT/'used-table-widget-checklist.html').write_text(''.join(body),encoding='utf-8')
for language in ['en','ru']:
    ru = language == 'ru'
    lines = ['---\ngroup: Guide\nicon: table\norder: 96\n---', '# '+('Table View: рабочий чеклист' if ru else 'Table View: active widget checklist'),
             '> '+('Все табличные виджеты, упомянутые в widget configs, включая definition и вложенные ссылки.' if ru else 'All table widgets mentioned in widget configs, including definitions and nested references.'),
             (f'Просмотрено {len(sources)} конфигураций; {len(rows)} классов/отдельных ошибочных ссылок. Системные XML, шаблон CG и сохранённые конфиги всех локальных проектов. Данные БД читались mode=ro и не менялись. Упоминание — критерий включения, а не доказательство запуска. Старый production и явные заготовки остаются исключениями.' if ru else f'{len(sources)} configurations scanned; {len(rows)} classes/separate invalid references. Shipped XML, CG template and saved configurations from every local project. Databases were read mode=ro without changes. A mention is an inclusion criterion, not proof of runtime execution. Old production and explicit stubs remain excluded.'),
             ('[Примеры и парные снимки](table_widget_examples.ru.md) · [Полный каталог](widget_database.ru.md)' if ru else '[Examples and paired captures](table_widget_examples.en.md) · [Complete database](widget_database.en.md)'),
             ('Критерии: изучен исходник и наследование; воспроизведены все используемые параметры и действия; сверены ТХ/ТС; проверены права и ошибки; сняты изображения; обновлена справка. Текущие сценарии ТХ, grouping/resize/reorder/presets/inline edit перенесены; см. table_view.ru.md. XML/JSON остаются structured display, как в текущем ТХ. Старые totals и остальные legacy-опции проверяются отдельно.' if ru else 'Criteria: source and inheritance reviewed; used options/actions reproduced; TH/Stream compared; permissions/errors checked; captures and Help added. Current Handler scenarios, grouping/resize/reorder/presets/inline editing are ported; see table_view.en.md. XML/JSON remain structured display as in current Handler. Old totals and remaining legacy options are tracked separately.')]
    for status,count in Counter(r['status'] for r in rows).items():
        lines += ['## '+(status_ru.get(status,status) if ru else status)+f' ({count})']
        for row in [r for r in rows if r['status'] == status]:
            lines.append('### `'+row['class']+'`')
            lines += ['- [x] '+(step if ru else {'Исходник и наследование':'Source and inheritance','Сравнение вычислений и ошибок':'Values and errors comparison','Typed transport ТХ/ТС':'TH/Stream typed transport','Парные снимки ТХ/ТС':'Paired TH/Stream captures','XML-пример и EN/RU Help':'XML example and EN/RU Help'}.get(step,step)) for step in row['done']]
            lines += ['- [ ] '+(step if ru else 'Remaining contract: inline editing') for step in row.get('todo',[])]
            lines.append(('Упоминания: ' if ru else 'References: ')+str(len(row['uses']))+'.')
            lines += ['- `'+u['source']+' → '+u['location']+'`'+(' — '+', '.join(u['options']) if u['options'] else '') for u in row['uses'][:3]]
            if len(row['uses'])>3:
                lines.append(('Все места и опции перечислены в полном HTML/CSV/JSON чеклисте в tools/frame_table/output/used_widgets.' if ru else 'All locations/options are listed in the HTML/CSV/JSON checklist under tools/frame_table/output/used_widgets.'))
    for folder in [ROOT/'frontend/public/help',ROOT/'src/tactic_stream/web/help']:
        (folder/f'table_widget_checklist.{language}.md').write_text('\n\n'.join(lines)+'\n',encoding='utf-8')
for folder in [ROOT/'frontend/public/help',ROOT/'src/tactic_stream/web/help']:
    path=folder/'index.json';index=json.loads(path.read_text(encoding='utf-8'))
    if not any(row['id']=='table_widget_checklist' for row in index):
        index.append({'id':'table_widget_checklist','languages':['en','ru']})
        path.write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'configs': len(sources), 'classes': len(rows), 'statuses': dict(Counter(r['status'] for r in rows)), 'non_xml': len(invalid)}, ensure_ascii=False))
