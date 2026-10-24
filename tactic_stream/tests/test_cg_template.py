"""Import the real supplied template; reuse the existing SQLite/PG lifecycle."""
import ast
import os
from pathlib import Path
import unittest
import zipfile
from unittest.mock import patch

import test_plugin_installation as lifecycle
from pyasm.biz import Project, Schema, Pipeline
from pyasm.command import Command
from pyasm.common import Xml
from pyasm.search import Search, SearchType, DbResource
from pyasm.search.search import RequestContext, request_context
from tactic.command import ProjectTemplateInstallerCmd
from tactic_stream.server.api import Api
from tactic_stream.server.navigation import read_navigation
from tactic_stream.server.result_items import read_result_items
from pyasm.common.errors import SecurityException


def records(text):
    for block in text.split('#-- Start Entry --#')[1:]:
        yield {ast.literal_eval(node.args[0]): ast.literal_eval(node.args[1])
               for node in ast.walk(ast.parse(block)) if isinstance(node, ast.Call)
               and isinstance(node.func, ast.Attribute) and node.func.attr == 'set_value'}


def exercise(store, prefix):
    archive = Path(os.environ.get('STREAM_CG_TEMPLATE', Path(__file__).resolve().parents[2] / 'cg.zip'))
    if not archive.is_file():
        raise unittest.SkipTest('Set STREAM_CG_TEMPLATE to the supplied cg.zip')
    api = Api(store)
    token = api.get_ticket('admin', 'plugin-test-password')
    context = dict(ticket=token, project='admin', language='python')
    failed = prefix + '_bad'
    with request_context(RequestContext(store, 'admin', 'admin')):
        api.auth.bind_security('admin', token)
        cmd = Command()
        def abort():
            cmd.get_transaction().set_sync(False)
            ProjectTemplateInstallerCmd(project_code=failed, path=str(archive), verbose=False).execute()
            raise ValueError('abort completed template import')
        cmd.execute = abort
        with unittest.TestCase().assertRaisesRegex(ValueError, 'abort completed template import'):
            Command.execute_cmd(cmd)
        assert Project.get_by_code(failed) is None
        resource = DbResource.get_default(failed)
        assert not resource.get_database_impl().database_exists(resource)
        registry = Search('sthpw/search_object'); registry.add_filter('namespace', 'cg')
        assert registry.get_count() == 0
        log = Search('sthpw/exception_log')
        log.add_filter('message', 'abort completed template import')
        assert log.get_count() == 1, 'Diagnostics survive rollback of the current project'

    code = prefix + '_ok'
    api.dispatch('execute_cmd', (context, 'tactic.command.ProjectTemplateInstallerCmd',
        dict(project_code=code, project_title='CG Test', path=str(archive), verbose=False)))
    with request_context(RequestContext(store, 'admin', code)), zipfile.ZipFile(archive) as package:
        api.auth.bind_security('admin', token)
        assert Project.get().get_value('title') == 'CG Test'
        assert Project.get().get_value('type') == 'cg'
        assert Project.get().get_database_name() == code
        summary = {}
        for name in package.namelist():
            if not name.endswith('.spt'):
                continue
            values = list(records(package.read(name).decode('utf-8-sig')))
            stype = Path(name).stem.replace('_', '/', 1)
            if stype.startswith('cg/'):
                definition = SearchType.get(stype)
                if 'default_layout' in values[0]:
                    assert definition.get_value('default_layout') == values[0]['default_layout']
                assert Search(stype).get_count() == 0
                assert 'id' in Search(stype).get_columns()
            elif stype.startswith('config/'):
                search = Search(stype); search.set_show_retired(True)
                objects = search.get_sobjects()
                imported_codes = {row['code'] for row in values}
                if stype == 'config/process':
                    # Pipeline.get_defaults synchronizes definitions with its XML
                    # and removes obsolete process names, as in the original.
                    for row in values:
                        pipeline_code = row.get('pipeline_code', '')
                        if '/' in pipeline_code:
                            pipeline_code = code + '/' + pipeline_code.split('/', 1)[1]
                        pipeline = Pipeline.get_by_code(pipeline_code)
                        if pipeline and row['process'] not in pipeline.get_process_names():
                            imported_codes.discard(row['code'])
                objects = [row for row in objects if row.get_code() in imported_codes]
                assert {row.get_code() for row in objects} == imported_codes, (stype, imported_codes - {row.get_code() for row in objects})
                # Preserve JSON documents and mixed text in XML verbatim.
                if stype == 'config/widget_config':
                    original = {row['code']: row['config'] for row in values}
                    assert {row.get_code(): row.get_value('config') for row in objects} == original
                summary[stype] = len(objects)
        assert Schema.get().get_code() == code
        pipelines = Search('sthpw/pipeline'); pipelines.add_filter('project_code', code)
        assert all(row.get_code().startswith(code + '/') for row in pipelines.get_sobjects())
        navigation = read_navigation()
        assert navigation['configured'] and navigation['entries']
        summary['navigation'] = [row['name'] for row in navigation['entries']]
        text = '<config><view>before <element name="one"/> after</view></config>'
        assert Xml(text).to_string(pretty=False) == text
    sample = Path(os.environ.get('STREAM_CG_SAMPLE', Path(__file__).resolve().parents[1] / 'tools/cg_sample_data.py')).read_text(encoding='utf-8')
    sample += '\nreturn run(server, project_code, disable_telegram=True)\n'
    sample_context = dict(context, project=code)
    result = api.dispatch('execute_python_script', (sample_context, '', {'code': sample, 'project_code': code}))['info']
    assert sum(result['objects'].values()) == 32, result
    assert result['tasks'] == 13 and result['notes'] == 47 and result['relationships'] == 45, result
    assert result['total_tasks'] >= 13, result
    repeated = api.dispatch('execute_python_script', (sample_context, '', {'code': sample, 'project_code': code}))['info']
    assert repeated.pop('disabled_telegram') == [], repeated
    result.pop('disabled_telegram')
    assert repeated == result, (repeated, result)
    summary['sample'] = result
    with request_context(RequestContext(store, 'admin', code)):
        api.auth.bind_security('admin', token)
        key = 'cg/assets?project=' + code + '&code=DEMO_ROBOT'
        presented = read_result_items('cg/assets', [key])
        item = presented['items'][0]
        assert any(process['key'] == 'model' for process in presented['organization']['processes']), presented['organization']
        assert 'model' in presented['organization']['statuses'], presented['organization']
        assert all('status' in task for task in item['tasks']), item['tasks']
        assert item['task_count'] == 1 and item['note_count'] == 3, item
        asset_branch = next(row for row in item['branches'] if row.get('search_type') == 'cg/assets')
        branch = {name: asset_branch[name] for name in ('kind', 'search_type', 'path')}
        children = read_result_items('cg/assets', [key], branch, limit=1)
        assert children['has_next'] and len(children['items']) == 1
        children['items'] += read_result_items('cg/assets', [key], branch, offset=1)['items']
        assert {row['record']['code'] for row in children['items']} == {'DEMO_BODY', 'DEMO_TOOL'}, children
        episode = 'cg/scenes?project=' + code + '&code=DEMO_EP01'
        item = read_result_items('cg/scenes', [episode])['items'][0]
        assert item['accent'] == SearchType.get('cg/scenes').get_value('color'), item
        assert item['subtitle'] == 'Sample episode · Dialog', item
        assert any(row['text'] == '120' for row in item['info_items']), item
        assert next(row for row in item['progress_items'] if row['name'] == 'assets')['total'] == 3, item
        assert item['branches'][0]['kind'] == 'relation', item
        assert all(row['accent'] for row in item['branches']), item
        counted = read_result_items('cg/scenes', [episode], dict(kind='children'))['items'][0]
        assert next(row for row in counted['branches'] if row.get('search_type') == 'cg/shot')['count'] == 2, counted
        assert next(row for row in counted['branches'] if row.get('search_type') == 'cg/assets')['count'] == 3, counted
        first_process = next(row for row in counted['branches'] if row['kind'] == 'process')
        assert first_process['task_count'] >= 1 and not first_process['has_children'], first_process
        from tactic.command.sobject_link_cmd import SObjectLinkCmd
        asset_relation = next(row for row in counted['branches'] if row.get('search_type') == 'cg/assets')
        arm = 'cg/assets?project=' + code + '&code=DEMO_ARM'
        arm_item = read_result_items('cg/assets', [arm])['items'][0]
        assert arm_item['subtitle'] == 'Sample asset: Robot Arm · 3D Asset · Props', arm_item['subtitle']
        texture = read_result_items('cg/texture', ['cg/texture?project=' + code + '&code=DEMO_TEX_METAL'])['items'][0]
        assert [row['title'] for row in texture['branches'] if row['kind'] == 'process'] == ['Icon', 'Attachment', 'Publish']
        assert [(row['column'], row['text']) for row in texture['info_items']] == [('assets_category_code', 'Materials'), ('texture_type', 'Diffuse')], texture['info_items']
        for parent, relation, original_count in ((episode, asset_relation, 3), (key, asset_branch, 2)):
            args = dict(parent_key=parent, search_type='cg/assets', path=relation['path'])
            for _ in range(2):
                api.dispatch('execute_cmd', (sample_context, 'tactic.command.sobject_link_cmd.SObjectLinkCmd',
                    dict(args, insert_search_keys=[arm])))
                owner = Search.get_by_search_key(parent)
                from tactic_stream.server.result_items import relation_search
                assert relation_search(owner, relation).get_count() == original_count + 1
            api.dispatch('execute_cmd', (sample_context, 'tactic.command.sobject_link_cmd.SObjectLinkCmd',
                dict(args, exclude_search_keys=[arm])))
            assert relation_search(owner, relation).get_count() == original_count
            command = Command()
            def abort_link():
                Command.execute_cmd(SObjectLinkCmd(**dict(args, insert_search_keys=[arm])))
                raise ValueError('abort instance link')
            command.execute = abort_link
            with unittest.TestCase().assertRaisesRegex(ValueError, 'abort instance link'):
                Command.execute_cmd(command)
            assert relation_search(owner, relation).get_count() == original_count
        created = api.dispatch('execute_cmd', (sample_context, 'tactic.command.sobject_link_cmd.SObjectLinkCmd',
            dict(create=True, instance_parent_key=episode, search_type='cg/assets', path=asset_relation['path'],
                 view='insert', input_prefix='insert', element_names=['name']),
            dict(search_type='cg/assets', search_id='-1', **{'insert|name': 'Linked test asset'})))['info']['created_key']
        assert Search.get_by_search_key(created).get_value('name') == 'Linked test asset'
        assert relation_search(Search.get_by_search_key(episode), asset_relation).get_count() == 4
        api.dispatch('delete_sobject', (sample_context, created))
        assert relation_search(Search.get_by_search_key(episode), asset_relation).get_count() == 3
        shot_branch = next(row for row in item['branches'] if row.get('search_type') == 'cg/shot')
        children = read_result_items('cg/scenes', [episode], {name: shot_branch[name] for name in ('kind', 'search_type', 'path')})
        assert {row['record']['code'] for row in children['items']} == {'DEMO_SH010', 'DEMO_SH020'}
        shot = children['items'][0]
        episode_parent = next(row for row in shot['related_parents'] if row['search_type'] == 'cg/scenes')
        parent_rows = read_result_items('cg/shot', [shot['record']['__search_key__']],
            {name: episode_parent[name] for name in ('kind', 'search_type', 'path')})['items']
        assert [row['record']['code'] for row in parent_rows] == ['DEMO_EP01']
        with unittest.TestCase().assertRaises(ValueError):
            read_result_items('cg/shot', [shot['record']['__search_key__']], dict(kind='parent', search_type='sthpw/login'))
        for invalid in (dict(branch=dict(kind='relation', search_type='sthpw/login', path='')),
                        dict(branch=branch, limit=True), dict(branch=branch, offset=-1)):
            with unittest.TestCase().assertRaises(ValueError):
                read_result_items('cg/assets', [key], **invalid)
        with unittest.TestCase().assertRaises(ValueError):
            read_result_items('cg/assets', [key.replace('project=' + code, 'project=admin')])
        with patch('pyasm.security.Security.is_admin', return_value=False):
            assert read_result_items('cg/assets', [key])['items'][0]['record']['__search_key__'] == key
    # The real template explicitly asks for symlinks. This unrelated fixture's
    # thumbnails use copies on Windows accounts without Developer Mode.
    if os.name == 'nt':
        from pyasm.biz import ProjectSetting
        with request_context(RequestContext(store, 'admin', code)):
            api.auth.bind_security('admin', token)
            setting = ProjectSetting.get_by_key('versionless_mode')
            if setting:
                api.dispatch('update', (sample_context, setting.get_search_key(), dict(value='copy')))
    # Real upload/check-in operations exercise versionless -> version children.
    import base64
    from xmlrpc.client import Binary
    image = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')
    for filename in ('result-one.png', 'result-two.png'):
        api.dispatch('upload_file', (sample_context, filename, Binary(image)))
        api.dispatch('simple_checkin', (sample_context, key, 'publish', filename),
                     dict(file_type='icon', create_icon=False, keep_file_name=True))
    with request_context(RequestContext(store, 'admin', code)):
        api.auth.bind_security('admin', token)
        current = read_result_items('cg/assets', [key], dict(kind='process', process='publish'))['items']
        assert len(current) == 1 and current[0]['record']['version'] < 0, current
        versions = read_result_items('sthpw/snapshot', [current[0]['record']['__search_key__']], dict(kind='versions', process='publish'))['items']
        assert [row['record']['version'] for row in versions] == [2, 1], versions
        assert all(row['preview']['files'] for row in versions), versions
        assert current[0]['snapshot_display']['version'] == 'latest'
        assert [row['snapshot_display']['version'] for row in versions] == ['v002', 'v001']
        assert all(row['snapshot_display']['title'] == 'publish' for row in versions), 'Native snapshots without a main file use their context as title'
    api.dispatch('upload_file', (sample_context, 'detail.txt', Binary(b'Nested process context')))
    api.dispatch('simple_checkin', (sample_context, key, 'publish/details', 'detail.txt'),
                 dict(file_type='main', create_icon=False, keep_file_name=True))
    with request_context(RequestContext(store, 'admin', code)):
        api.auth.bind_security('admin', token)
        nested = read_result_items('cg/assets', [key], dict(kind='process', process='publish'))['items']
        assert {row['record']['context'] for row in nested} == {'publish', 'publish/details'}
        root = read_result_items('cg/assets', [key])['items'][0]
        assert not any(row.get('process') == 'publish/details' for row in root['branches']), 'Subcontexts belong under their process, not in duplicate process rows'
        expanded = read_result_items('cg/assets', [key], dict(kind='children'))['items'][0]
        assert {row['record']['context'] for row in expanded['direct_snapshots']} == {'publish', 'publish/details'}
        detail = next(row for row in nested if row['record']['context'] == 'publish/details')
        assert detail['snapshot_display']['title'] == 'Hero Robot_publish_details.txt', detail['snapshot_display']
        assert detail['snapshot_display']['exists'] and detail['snapshot_display']['size'] == 22
        exact = read_result_items('sthpw/snapshot', [current[0]['record']['__search_key__']], dict(kind='versions', process='publish'))['items']
        assert [row['record']['version'] for row in exact] == [2, 1], 'Sibling subcontexts cannot leak into snapshot version children'
    # Actual Handler image check-in in the supplied project's shared repository.
    # Preserve its server procedure unchanged, including delete/append of latest.
    import json
    from pyasm.common import Environment
    handler = Path(os.environ.get('STREAM_HANDLER_QUERY') or
                   Path(__file__).resolve().parents[3] / 'TH/thlib/tactic_query.py')
    source = handler.read_text(encoding='utf-8')
    function = next(node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)
                    and node.name == 'create_snapshot_extended')
    source = ast.get_source_segment(source, function) + '\nreturn create_snapshot_extended(**kwargs["options"])'
    with request_context(RequestContext(store, 'admin', code)):
        root = Path(Environment.get_asset_dir())
    for version in (1, 2):
        directories = [code + '/handler/v%s' % version, code + '/handler/latest']
        paths = []
        for directory in directories:
            folder = root / directory; folder.mkdir(parents=True, exist_ok=True)
            files = [(folder / (kind + '.png')).as_posix() for kind in ('main', 'web', 'icon')]
            for path in files:
                Path(path).write_bytes(image + bytes([version]))
            paths.append(files)
        info = dict(files_types=['main', 'web', 'icon'], file_sizes=[len(image) + 1] * 3,
            version_files=paths[0], versionless_files=paths[1], version_files_paths=[directories[0]] * 3,
            versionless_files_paths=[directories[1]] * 3, version_metadata=[dict(test=version)] * 3,
            versionless_metadata=[dict(test=version)] * 3)
        saved = api.dispatch('execute_python_script', (sample_context, '', dict(code=source, options=dict(
            search_key=key, project_code=code, context='handler_image', mode='inplace',
            repo_name='default', files_info=json.dumps(info), create_icon=False))))['info']
        assert saved['version'] == version, saved
        aliases = ast.literal_eval(api.dispatch('query', (sample_context, 'sthpw/snapshot',
                                  [['context', 'handler_image'], ['version', -1]])))
        assert len(aliases) == 1, aliases
        for snapshot in (saved, aliases[0]):
            actual = api.dispatch('get_all_paths_from_snapshot', (sample_context, 'sthpw/snapshot?code=' + snapshot['code']))
            assert len(actual) == 3, actual
            assert all(Path(path).read_bytes() == image + bytes([version]) for path in actual), actual
        if version == 2:
            assert all(path.read_bytes() == image + bytes([1]) for path in (root / directories[0].replace('v2', 'v1')).glob('*.png'))
    return summary


class CgTemplate(lifecycle.PluginInstallation):
    exercise = staticmethod(exercise)
