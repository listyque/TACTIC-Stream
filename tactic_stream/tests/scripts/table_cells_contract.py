"""One native cell scenario, shared by SQLite, PostgreSQL and browser fixtures."""
import base64
import re
from pyasm.command import Command
from pyasm.search import SearchType
from tactic_stream.server.table_cells import read_table_cells, safe_link

TYPE = 'sthpw/login_group'
VIEW = 'cells_native'
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')
XML = '''<config><cells_native layout="tactic.ui.panel.TableLayoutWdg">
<element name="login_group" title="Group" />
<element name="id" title="Number"><display widget="format"><type>float</type><format>-1234.12</format></display></element>
<element name="description" title="Website"><display widget="link" /></element>
<element name="is_default" title="Default"><display widget="format"><format>Checkbox</format></display></element>
<element name="label" title="Computed label"><display widget="expression"><expression>@GET(.login_group)</expression><calc_mode>fast</calc_mode><display_expression>'group '+$VALUE</display_expression></display></element>
<element name="amount" title="Computed amount"><display widget="expression"><expression>@GET(.id)</expression><display_format>-1234.12</display_format></display></element>
<element name="values" title="Computed list"><display widget="expression"><expression>@GET(sthpw/login_group['login_group','like','CELL_%'].id)</expression><expression_mode>absolute</expression_mode><calc_mode>fast</calc_mode><return>list</return></display></element>
<element name="enabled" title="Computed boolean"><display widget="expression"><expression>@GET(.is_default)</expression><mode>boolean</mode></display></element>
<element name="check" title="Computed check"><display widget="expression"><expression>@GET(.is_default)</expression><mode>check</mode></display></element>
<element name="preview" title="Preview"><display class="pyasm.widget.ThumbWdg"><filename>true</filename></display></element>
<element name="notes" title="Notes"><display class="tactic.ui.widget.DiscussionElementWdg"><allow_email>false</allow_email></display></element>
<element name="tasks" title="Tasks"><display class="tactic.ui.table.TaskElementWdg"><pipeline_code>admin/CELL_TASKS</pipeline_code></display></element>
<element name="completion" title="Completion"><display widget="completion" /></element>
<element name="checkin" title="Check-in"><display class="tactic.ui.table.CheckinButtonElementWdg"><process>publish</process></display></element>
<element name="error" title="Invalid date"><display widget="format"><column>login_group</column><format>1999-12-31</format></display></element>
<element name="bad_expression" title="Invalid expression"><display widget="expression"><expression>@BOGUS()</expression></display></element>
<element name="custom" title="Custom"><display class="custom.DoNotImport" /></element>
</cells_native></config>'''
# Keep every contract column accessible; responsive hiding is verified by handler_table.mjs.
XML = re.sub(r'(<element name="[^"]+")', r'\1 th_hide_order="0"', XML)


def install(api, auth):
    rows = [api.dispatch('insert', (auth, TYPE, dict(login_group='CELL_' + letter,
        description=url, is_default=enabled))) for letter, url, enabled in (
        ('A', 'https://example.com/a', True), ('B', 'javascript:alert(1)', False))]
    row = SearchType.create('config/widget_config')
    row.set_value('search_type', TYPE); row.set_value('view', VIEW); row.set_value('config', XML)
    command = Command(); command.execute = row.commit; command.get_transaction().set_sync(False)
    Command.execute_cmd(command)
    return rows


def exercise(api, ticket):
    import ast
    import datetime
    from unittest.mock import patch
    from pyasm.common import Common
    from pyasm.widget import WidgetConfigView
    from tactic.core.format_value import FormatValueMixin
    from tactic_stream.server.interface import read_interface
    auth = dict(ticket=ticket, project='admin', language='python')
    rows = install(api, auth)
    rows = [ast.literal_eval(row) if isinstance(row, str) else row for row in rows]
    code_key = rows[0]['__search_key__']
    id_key = TYPE + '?project=admin&id=' + str(rows[1]['id'])
    from xmlrpc.client import Binary
    api.dispatch('upload_file', (auth, 'cell preview.png', Binary(PNG)))
    api.dispatch('simple_checkin', (auth, code_key, 'icon', 'cell preview.png'),
                 dict(file_type='icon', create_icon=False, keep_file_name=True))
    from scripts.discussion_contract import exercise as discussion
    discussion(api, auth, code_key, rows[1]['__search_key__'])
    from scripts.task_cells_contract import exercise as tasks
    tasks(api, auth)
    with patch.object(Common, 'resolve_class', wraps=Common.resolve_class) as resolve:
        description = read_interface(TYPE, VIEW)
        cells = read_table_cells(TYPE, VIEW, [code_key, id_key, code_key])
        assert not any('custom.' in call.args[0] for call in resolve.call_args_list)
    assert cells[code_key]['id']['text'] == f"{rows[0]['id']:.2f}"
    assert cells[id_key]['id']['text'] == f"{rows[1]['id']:.2f}"
    assert cells[code_key]['description']['href'] == 'https://example.com/a'
    assert cells[id_key]['description']['href'] == ''
    assert cells[code_key]['tasks']['count'] == cells[id_key]['tasks']['count'] == 0, cells
    assert 'completion' in cells[code_key], next(element for element in description['table']['elements'] if element['name'] == 'completion')
    assert cells[code_key]['completion']['text'] == '0.0%' and cells[id_key]['completion']['completion'] is None
    assert cells[code_key]['is_default']['text'].lower() in ('true', '1')
    assert cells[id_key]['is_default']['text'].lower() in ('false', '0')
    assert cells[code_key]['label']['text'] == 'group CELL_A'
    assert cells[id_key]['label']['text'] == 'group CELL_B'
    assert cells[code_key]['amount']['text'] == f"{rows[0]['id']:.2f}"
    assert cells[code_key]['values']['text'] == ', '.join(str(row['id']) for row in rows), cells[code_key]['values']
    assert cells[code_key]['enabled']['checked'] is True and cells[id_key]['enabled']['checked'] is False
    assert cells[code_key]['check']['checked'] is True and cells[id_key]['check']['checked'] is False
    preview = cells[code_key]['preview']
    assert preview['image'].endswith('.png') and preview['files'][0]['href'] == preview['image'], preview
    assert preview['version'] == 1 and preview['context'] == 'icon'
    assert cells[id_key]['preview']['image'] == '' and cells[id_key]['preview']['files'] == []
    from pyasm.widget import ThumbWdg
    from pyasm.biz import Snapshot, File
    thumb = ThumbWdg(name='preview')
    assert ThumbWdg.get_link_path({'icon': 'icon.png', 'main': 'main.bin', 'web': 'web.png'}) == 'web.png'
    assert ThumbWdg.get_link_path({'icon': 'icon.png', 'main': 'main.bin'}, ['main']) == 'main.bin'
    assert cells[code_key]['bad_expression']['error']
    assert cells[code_key]['error']['error']
    assert next(item for item in description['table']['elements'] if item['name'] == 'custom')['cell']['supported'] is False
    config = WidgetConfigView.get_by_search_type(TYPE, VIEW)
    from pyasm.search import Search
    widget = config.get_display_widget('id'); widget.set_sobject(Search.get_by_id(TYPE, rows[0]['id']))
    assert widget.get_text_value() == f"{rows[0]['id']:.2f}"
    from tactic.ui.table import ExpressionElementWdg, ExpressionValueElementWdg, ExpressionRecalculateCmd
    from pyasm.biz import ExpressionParser
    from pyasm.security import Sudo
    objects = [Search.get_by_id(TYPE, row['id']) for row in rows]
    thumb.set_sobjects(objects); thumb.preprocess(); link = thumb.get_data(objects[0])
    assert link == preview['image'] and thumb.get_info()['icon'] == link
    thumb.set_current_index(1); assert thumb.get_cell_value()['image'] == ''
    assert thumb.get_info() == {}, 'A missing preview must not reuse the previous row files'
    snap = Search.get_by_code('sthpw/snapshot', preview['snapshot_key'].split('code=')[-1])
    thumb.set_sobjects([snap]); thumb.preprocess(); assert thumb.get_cell_value()['image'] == link
    thumb.set_sobjects([objects[0], objects[0]])
    with patch.object(Snapshot, 'get_by_sobjects', wraps=Snapshot.get_by_sobjects) as snapshots, patch.object(File, 'get_by_snapshots', wraps=File.get_by_snapshots) as files:
        thumb.preprocess(); thumb.get_cell_value(); thumb.set_current_index(1); thumb.get_cell_value()
        assert snapshots.call_count == files.call_count == 1, 'Preview reads must be batched'
    with patch.object(type(objects[0]), 'get_web_dir', return_value='https://example.com/files'), patch.object(File, 'get_full_file_name', return_value='space # ü?.png'):
        paths = ThumbWdg.get_file_info(snap.get_snapshot_xml(), thumb.file_objects, objects[0], snap)
        assert paths['icon'] == 'https://example.com/files/space%20%23%20%C3%BC%3F.png'
    from pyasm.common import Xml
    from unittest.mock import Mock
    two_files = Xml('<snapshot><file type="main" file_code="a"/><file type="main" file_code="b"/></snapshot>')
    with patch.object(type(objects[0]), 'get_web_dir', return_value='/files'), patch.object(type(objects[0]), 'get_lib_dir', return_value='D:/files'):
        files = []
        ThumbWdg.get_file_info(two_files, {key: Mock(get_full_file_name=lambda key=key: key+'.png', get_value=lambda *args, **kwargs: '') for key in ('a', 'b')}, objects[0], snap, files=files)
        assert [file['href'] for file in files] == ['/files/a.png', '/files/b.png'], 'Each same-type file needs its own URL'
    widget = config.get_display_widget('label'); widget.set_sobjects(objects); widget.preprocess()
    assert widget.is_sortable() and widget.get_option('order_by') == 'login_group'
    with patch.object(ExpressionParser, 'eval', autospec=True, side_effect=ExpressionParser.eval) as calculate:
        assert widget.get_text_value() == 'CELL_A'
        widget.set_current_index(1); assert widget.get_text_value() == 'CELL_B'
        assert sum(call.args[1] == '@GET(.login_group)' and call.kwargs.get('dictionary') is True
                   for call in calculate.call_args_list) == 1
    widget.set_sobjects([objects[1]]); assert widget.get_text_value() == 'CELL_B'
    widget.set_option('expression', '@GET(.id)'); assert widget.get_text_value() == rows[1]['id']
    widget.set_option('expression', '$SOBJECT_ID'); assert widget.get_text_value() == rows[1]['id']
    widget.set_option('alt_expression', "'ALT_'+$SOBJECT_CODE"); assert widget.get_text_value() == 'ALT_' + objects[1].get_code()
    values = config.get_display_widget('values'); values.set_sobject(objects[0])
    assert values.get_text_value() == ','.join(str(row['id']) for row in rows)
    with patch.object(ExpressionParser, 'eval', return_value=[1, 0, False]):
        assert values.get_text_value() == '1,0,False'
    stored = ExpressionValueElementWdg(name='login_group', value='1+2'); stored.set_sobject(objects[0])
    assert stored.get_text_value() == 3 and stored.get_cell_value()['text'] == '3.0'
    stored.set_value('@BOGUS()'); assert stored.get_text_value() == 0
    widget = ExpressionElementWdg(expression='@GET(GET_column)'); widget.preprocess()
    assert widget.get_option('order_by') == 'GET_column'
    widget = ExpressionElementWdg(name='sum', expression='@SUM(.id)', calc_mode='fast')
    widget.set_sobjects(objects); widget.preprocess()
    assert widget.get_text_value() == rows[0]['id']
    widget.set_current_index(1); assert widget.get_text_value() == rows[1]['id']
    assert not Sudo.is_sudo(), 'Expression reads must not leak administrator privileges'
    assert Search.get_by_id(TYPE, rows[0]['id']).get_value('login_group') == 'CELL_A'
    # Recalculation uses the saved definition and commits through native Command.
    definition = SearchType.create('config/widget_config')
    definition.set_value('search_type', TYPE); definition.set_value('view', 'definition')
    definition.set_value('config', "<config><definition><element name='description'><display widget='expression'><expression>'updated_'+$SOBJECT_CODE</expression><use_cache>true</use_cache></display></element></definition></config>")
    command = Command(); command.execute = definition.commit; command.get_transaction().set_sync(False)
    Command.execute_cmd(command)
    api.dispatch('execute_cmd', (auth, 'tactic.ui.table.ExpressionRecalculateCmd',
                               dict(search_keys=[code_key], element_name='description')))
    def descriptions():
        result = api.dispatch('query', (auth, TYPE, [('login_group', 'in', ['CELL_A', 'CELL_B'])], None, ['id asc']))
        result = ast.literal_eval(result) if isinstance(result, str) else result
        return [row['description'] for row in result]
    assert descriptions() == ['updated_CELL_A', 'javascript:alert(1)']
    with patch.object(ExpressionElementWdg, 'get_text_value', side_effect=['partial', ValueError('calculation failed')]):
        try:
            api.dispatch('execute_cmd', (auth, 'tactic.ui.table.ExpressionRecalculateCmd',
                dict(search_keys=[row['__search_key__'] for row in rows], element_name='description')))
        except ValueError:
            pass
        else:
            raise AssertionError('Failed recalculation accepted')
    assert descriptions() == ['updated_CELL_A', 'javascript:alert(1)']
    # Formatter copied from legacy: rounding, percent, timecode, datetime and size.
    formatter = FormatValueMixin(); formatter.get_option = lambda key: ''
    assert formatter.get_format_value(1.235, '-1234.12') == '1.24'
    assert formatter.get_format_value(.125, '-12.95%') == '12.50%'
    assert formatter.get_format_value(datetime.date(2026, 10, 8), '31/12/1999') == '08/10/2026'
    assert formatter.get_format_value(24, 'HH:MM:SS:FF') == '00:00:01:00'
    assert formatter.get_format_value(1024 ** 3, 'KB') == '1.0 GB'
    for url in ('data:text/html,evil', 'javascript:alert(1)', '//example.com', '/\\evil', '\x00https://example.com'):
        assert safe_link(url) == ''
    for url in ('https://example.com', '/admin/', 'mailto:example@example.com'):
        assert safe_link(url) == url
    for keys in ([TYPE + '?id=987654321'], [TYPE + '?project=other&id=1'], [code_key] * 501):
        try:
            read_table_cells(TYPE, VIEW, keys)
        except ValueError:
            pass
        else:
            raise AssertionError('Invalid cell selection accepted')
