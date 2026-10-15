"""Actual Handler naming and check-in procedures on the native CG preset."""
import ast
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from xmlrpc.client import Binary

from tools.checkin_benchmark import prepare, ROOT
from pyasm.common import Environment, Common
from pyasm.web.api_xmlrpc import ApiXMLRPC
from pyasm.search import Search
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store


class HandlerNaming(unittest.TestCase):
    def test_snapshot_version_matches_filename_for_code_and_id_keys(self):
        source = (ROOT.parents[1] / 'th_codex/thlib/tactic_query.py').read_text(encoding='utf-8')
        scripts = {node.name: ast.get_source_segment(source, node) +
                   '\nreturn ' + node.name + '(**kwargs["options"])'
                   for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)
                   and node.name in ('get_virtual_snapshot_extended', 'create_snapshot_extended')}
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            api, ticket = prepare(store)
            auth = dict(ticket=ticket, project='one')

            def execute(name, **options):
                return api.dispatch('execute_python_script', (auth, '',
                    dict(code=scripts[name], options=options)))['info']

            keys = ['cg/shot?project=one&code=SH001', 'cg/shot?project=one&id=1',
                    'cg/shot?code=SH001&project=one']
            with request_context(RequestContext(store, 'admin', 'one')):
                repository = Path(Environment.get_asset_dir())
            for mode in ('upload', 'inplace'):
                context = 'publish' if mode == 'upload' else 'model'
                previous = []
                for version, key in enumerate(keys, 1):
                    plan = json.loads(execute('get_virtual_snapshot_extended', search_key=key,
                        context=context, files_dict=json.dumps([
                            ['source', dict(t=['main'], e=['md'], s=[''], p=[''], m={})]])))
                    destination = plan[0][1]['versioned']
                    filename = ''.join(destination['names'][0])
                    self.assertIn('_v%03d.' % version, filename)
                    payload = ('native CG payload %s' % version).encode()
                    path = repository / destination['paths'][0] / filename
                    if mode == 'upload':
                        api.dispatch('upload_file', (auth, filename, Binary(payload)))
                    else:
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_bytes(payload)
                    info = dict(files_types=['main'], file_sizes=[len(payload)],
                        upload_file_names=[filename], version_files=[str(path)],
                        version_files_paths=destination['paths'],
                        version_metadata=[dict(filename='source', new_filename=Path(filename).stem,
                                               new_file_ext='md')], versionless_metadata=[{}])
                    saved = execute('create_snapshot_extended', search_key=key, context=context,
                        project_code='one', mode=mode, create_icon=False,
                        update_versionless=mode == 'upload', files_info=json.dumps(info),
                        transaction_title='Inplace Checkin' if mode == 'inplace' else None,
                        transaction_description='TH check-in finished' if mode == 'inplace' else None)
                    self.assertEqual(saved['version'], version)
                    paths = api.dispatch('get_all_paths_from_snapshot',
                                         (auth, 'sthpw/snapshot?code=' + saved['code']))
                    self.assertEqual(paths, [str(path).replace('\\', '/')])
                    previous.append((path, payload))
                    for old_path, old_payload in previous:
                        self.assertEqual(old_path.read_bytes(), old_payload)
                    if mode == 'inplace':
                        with request_context(RequestContext(store, 'admin', 'one')):
                            api.auth.bind_security('admin', ticket)
                            logs = Search('sthpw/transaction_log')
                            logs.add_order_by('id desc')
                            log = logs.get_sobject()
                            self.assertEqual(log.get_value('title'), 'Inplace Checkin')
                            self.assertIn('TH check-in finished', log.get_value('description'))
                            journal = log.get_value('transaction')
                            if journal.startswith('zlib:'):
                                self.assertGreater(len(Common.decompress_transaction(journal)), 10 * 1024)
                            index = Search('sthpw/sobject_log')
                            index.add_filter('transaction_log_id', log.get_id())
                            self.assertGreater(index.get_count(), 0)
                            log_id = log.get_id()
                        self.assertTrue(api.dispatch('undo', (auth, None, log_id)))
                        # Inplace staging precedes the Command; undo leaves that input intact.
                        self.assertEqual(path.read_bytes(), payload)
                        with request_context(RequestContext(store, 'admin', 'one')):
                            self.assertIsNone(Search.get_by_code('sthpw/snapshot', saved['code']))
                        self.assertTrue(api.dispatch('redo', (auth, None, log_id)))
                        self.assertEqual(path.read_bytes(), payload)

            # A failure while returning the completed save restores rows and history.
            plan = json.loads(execute('get_virtual_snapshot_extended', search_key=keys[0],
                context='model', files_dict=json.dumps([
                    ['source', dict(t=['main'], e=['md'], s=[''], p=[''], m={})]])))
            destination = plan[0][1]['versioned']
            filename = ''.join(destination['names'][0])
            path = repository / destination['paths'][0] / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'failed check-in input')
            info.update(version_files=[str(path)], version_files_paths=destination['paths'],
                        file_sizes=[len(path.read_bytes())], upload_file_names=[filename],
                        version_metadata=[dict(filename='source', new_filename=Path(filename).stem,
                                               new_file_ext='md')])
            def records():
                with request_context(RequestContext(store, 'admin', 'one')):
                    return {kind: [dict(obj.data) for obj in Search(kind).get_sobjects()]
                            for kind in ('sthpw/snapshot', 'sthpw/file', 'sthpw/transaction_log',
                                         'sthpw/sobject_log', 'sthpw/transaction_state')}
            before = records()
            files = {item: item.read_bytes() for item in repository.rglob('*') if item.is_file()}
            with patch.object(ApiXMLRPC, '_get_sobject_dict',
                              side_effect=ValueError('failure after snapshot save')):
                with self.assertRaisesRegex(ValueError, 'failure after snapshot save'):
                    execute('create_snapshot_extended', search_key=keys[0], context='model',
                        project_code='one', mode='inplace', create_icon=False,
                        update_versionless=False, files_info=json.dumps(info),
                        transaction_title='Inplace Checkin', transaction_description='failed')
            self.assertEqual(records(), before)
            self.assertEqual({item: item.read_bytes() for item in repository.rglob('*')
                              if item.is_file()}, files)
