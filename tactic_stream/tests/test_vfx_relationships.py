"""Real VFX trees and native connection relations on SQLite and PostgreSQL."""
import ast
import json
from pathlib import Path
import tempfile

import test_plugin_installation as lifecycle
from test_project_writes import install_writer, set_rules, PASSWORD
from pyasm.search import Search, SearchType
from pyasm.search.search import RequestContext, request_context
from tactic_stream.server.api import Api
from tactic_stream.server.result_items import read_result_items
from tactic_stream.server.interface import read_interface, read_form
from tactic_stream.server.table_cells import read_table_cells
from tools.prepare_legacy_examples import prepare


def exercise(store, prefix):
    api = Api(store)
    api.protocol = 'json'
    ticket = api.get_ticket('admin', 'plugin-test-password')
    project = prefix + '_ok'
    auth = dict(ticket=ticket, project='admin')
    archive = Path(__file__).resolve().parents[2] / 'legacy/src/install/start/templates/vfx-1.0.0.zip'
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / 'examples'
        prepare(archive.parent, output)
        api.dispatch('execute_cmd', (auth, 'tactic.command.ProjectTemplateInstallerCmd',
            dict(project_code=project, path=str(output / 'vfx-1.0.0-stream.1.zip'), verbose=False)))
    auth['project'] = project

    def insert(stype, **values):
        return api.dispatch('insert', (auth, 'vfx/' + stype, values))['__search_key__']

    sequences = [insert('sequence', code=code) for code in ('SQ010', 'SQ020')]
    shot = insert('shot', code='SH010', sequence_code='SQ020', tc_frame_start=1001, tc_frame_end=1100,
                  frame_in=993, frame_out=1108)
    task = api.dispatch('create_task', (auth, shot), dict(process='animation', assigned='admin'))
    api.dispatch('update', (auth, task['__search_key__'], dict(
        bid_start_date='2026-10-20', bid_end_date='2026-10-24')))
    asset = insert('asset', code='ROBOT', name='Robot')
    insert('asset_in_shot', code='ROBOT_SH010', asset_code='ROBOT', shot_code='SH010')
    references = [insert('art_reference', name=name) for name in ('REF_A', 'REF_B', 'UNLINKED')]
    for owner in sequences:
        api.dispatch('connect_sobjects', (auth, references[0], owner, 'reference'))
    api.dispatch('connect_sobjects', (auth, references[0], sequences[1], 'second_context'))
    api.dispatch('connect_sobjects', (auth, references[1], sequences[1], 'reference'))
    api.dispatch('connect_sobjects', (auth, references[1], references[0], 'reference'))
    id_records = [(insert(stype), 'vfx/' + stype) for stype in ('camera', 'layer', 'submission')]

    with request_context(RequestContext(store, 'admin', project)):
        api.auth.bind_security('admin', ticket)
        from tactic_stream.server.activity_feed import activity_feed_request
        activity_feed_request(dict(filter='all'))
        for stype, view, key in (('vfx/sequence', 'sequence', sequences[1]),
                                 ('vfx/shot', 'shot', shot), ('vfx/asset', 'table', asset)):
            definition = read_interface(stype, view)
            cells = read_table_cells(stype, view, [key])[key]
            assert not {name: cell['error'] for name, cell in cells.items() if cell.get('error')}, cells
            if stype == 'vfx/sequence':
                schedule = next(item for item in definition['table']['elements'] if item['name'] == 'shot_task_schedule')
                assert schedule['cell']['supported'], schedule
                bar = cells['shot_task_schedule']['timeline']['bars'][0]
                assert bar['start'] == '2026-10-20' and bar['end'] == '2026-10-24', bar
                assert bar['mode'] == 'cascade' and bar['parentKeys'] == [shot], bar
            if stype == 'vfx/shot':
                assert all(item['cell']['supported'] for item in definition['table']['elements']), definition
                assert cells['frames']['text'] == '1001 - 1100 (993 - 1108)', cells['frames']
                assert cells['history']['nestedTable']['searchType'] == 'sthpw/snapshot'
                form = read_form(stype, search_key=key)
                assert {'tc_frame_start', 'tc_frame_end', 'frame_in', 'frame_out', 'frame_note'} <= {field['name'] for field in form['fields']}, form
        owners = [Search.get_by_search_key(key) for key in sequences]
        expression = "@SOBJECT(vfx/sequence['id', %s].vfx/art_reference)" % owners[1].get_id()
        assert {row.get_value('name') for row in Search.eval(expression)} == {'REF_A', 'REF_B'}
        # This is the actual request emitted by the sequence disclosure arrow.
        tree = read_result_items('vfx/sequence', [sequences[1]], dict(kind='children'))['items'][0]
        branches = {row.get('search_type'): row for row in tree['branches'] if row['kind'] == 'relation'}
        assert branches['vfx/shot']['count'] == 1
        assert branches['vfx/art_reference']['count'] == 2
        for stype, expected in (('vfx/shot', {'SH010'}), ('vfx/art_reference', {'REF_A', 'REF_B'})):
            branch = {name: branches[stype][name] for name in ('kind', 'search_type', 'path')}
            result = read_result_items('vfx/sequence', [sequences[1]], branch)
            field = 'code' if stype == 'vfx/shot' else 'name'
            assert {row['record'][field] for row in result['items']} == expected
        for key, stype in [(shot, 'vfx/shot'), (asset, 'vfx/asset'), (references[0], 'vfx/art_reference'), *id_records]:
            read_result_items(stype, [key], dict(kind='children'))
        assert SearchType.get('vfx/texture').get_record_read_options()['available'] is False
        assert SearchType.get('prod/session_contents').get_record_read_options()['available'] is False
        grouped = Search.get_related_by_sobjects(owners, 'vfx/art_reference')
        assert [{row.get_value('name') for row in grouped[key]} for key in sequences] == [{'REF_A'}, {'REF_A', 'REF_B'}]
        ref = Search.get_by_search_key(references[0])
        assert [row.get_value('name') for row in ref.get_related_sobjects('vfx/art_reference')] == ['REF_B']
        assert {row.get_code() for row in ref.get_related_sobjects('vfx/sequence')} == {'SQ010', 'SQ020'}
        search = Search('vfx/art_reference')
        search.add_relationship_filters(owners, op='not in')
        assert [row.get_value('name') for row in search.get_sobjects()] == ['UNLINKED']
        assert {row.get_value('name') for row in owners[1].get_all_children('vfx/art_reference')} == {'REF_A', 'REF_B'}
        owner_search = Search('vfx/sequence')
        owner_search.add_filter('code', 'SQ020')
        search = Search('vfx/art_reference')
        search.add_relationship_search_filter(owner_search)
        assert {row.get_value('name') for row in search.get_sobjects()} == {'REF_A', 'REF_B'}

    handler = Path(__file__).resolve().parents[3] / 'TH/thlib/tactic_query.py'
    source = handler.read_text(encoding='utf-8')
    function = next(node for node in ast.parse(source).body
                    if isinstance(node, ast.FunctionDef) and node.name == 'get_notes_and_stypes_counts')
    script = ast.get_source_segment(source, function)
    script += '\nreturn get_notes_and_stypes_counts([], ' + repr(sequences[1]) + ', ["vfx/shot", "vfx/art_reference"])'
    counts = api.dispatch('execute_python_script', (auth, '', dict(code=script)))['info']
    assert counts['stypes'] == {'vfx/shot': 1, 'vfx/art_reference': 2}
    query = next(node for node in ast.parse(source).body
                 if isinstance(node, ast.FunctionDef) and node.name == 'query_sobjects')
    script = ast.get_source_segment(source, query)
    script += '\nreturn query_sobjects(' + repr('vfx/art_reference?project=' + project) + ', filters=' + repr([['_expression', 'in', expression]]) + ', project_code=' + repr(project) + ', compressed_return=False)'
    payload = api.dispatch('execute_python_script', (auth, '', dict(code=script)))['info']
    payload = json.loads(payload) if isinstance(payload, str) else payload
    assert {row['name'] for row in payload['sobjects_list']} == {'REF_A', 'REF_B'}, payload
    table = next(node for node in ast.parse(source).body
                 if isinstance(node, ast.FunctionDef) and node.name == 'query_table_layout')
    script = ast.get_source_segment(source, table)
    script += '\nreturn query_table_layout("vfx/shot", search_keys=' + repr([shot]) + ', view="shot", project_code=' + repr(project) + ')'
    layout = api.dispatch('execute_python_script', (auth, '', dict(code=script)))['info']
    layout = json.loads(layout) if isinstance(layout, str) else layout
    assert layout['rows'][shot]['frames']['text'] == '1001 - 1100 (993 - 1108)', layout['rows'][shot]

    install_writer(store)
    rules = ('<rules><rule group="project" code="' + project + '" access="allow"/>'
             '<rule group="search_type" code="vfx/sequence" access="view"/>'
             '<rule group="search_type" code="vfx/art_reference" access="view"/>'
             '<rule group="search_type" code="sthpw/connection" access="view"/></rules>')
    set_rules(store, rules)
    user_ticket = api.get_ticket('project_writer', PASSWORD)
    with request_context(RequestContext(store, 'project_writer', project)):
        api.auth.bind_security('project_writer', user_ticket)
        owner = Search.get_by_search_key(sequences[1])
        assert {row.get_value('name') for row in owner.get_related_sobjects('vfx/art_reference')} == {'REF_A', 'REF_B'}
    set_rules(store, rules.replace('</rules>', '<rule group="search_filter" search_type="sthpw/connection" column="context" value="second_context"/></rules>'))
    with request_context(RequestContext(store, 'project_writer', project)):
        api.auth.bind_security('project_writer', user_ticket)
        owner = Search.get_by_search_key(sequences[1])
        assert [row.get_value('name') for row in owner.get_related_sobjects('vfx/art_reference')] == ['REF_A']
    set_rules(store, rules.replace('code="vfx/art_reference" access="view"', 'code="vfx/art_reference" access="deny"'))
    with request_context(RequestContext(store, 'project_writer', project)):
        api.auth.bind_security('project_writer', user_ticket)
        owner = Search.get_by_search_key(sequences[1])
        assert Search('vfx/art_reference').get_sobjects() == []
        assert owner.get_related_sobjects('vfx/art_reference') == []
    return dict(sequence_shots=True, references=True, native_handler_counts=True,
                grouped_unique=True, reverse=True, ordinary_read_policy=True)


class VfxRelationships(lifecycle.PluginInstallation):
    exercise = staticmethod(exercise)
