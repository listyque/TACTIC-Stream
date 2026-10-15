"""GUI contracts against owned native file-project data, including the real HTTP path."""
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest
import ast
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from test_file_project import FileProjectFixture
import test_file_transfer as transfers
from tactic_client_lib.file_transfer import FileTransferClient
from tactic_client_lib.file_workspace import reconcile_workspace, local_page, local_sources, local_browse

ROOT = Path(__file__).resolve().parents[1]


class FileWorkspaceUiTest(FileProjectFixture, unittest.TestCase):
    http = transfers.FileTransferTest.http
    writer = transfers.FileTransferTest.writer
    client = transfers.FileTransferTest.client
    context = transfers.FileTransferTest.context

    def test_handler_catalog_offers_native_file_project_template(self):
        source = Path('D:/code/th_codex/thlib/tactic_query.py').read_text(encoding='utf-8')
        node = next(node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name == 'get_project_creation_catalog')
        scope = {}
        with self.context():
            exec(compile(ast.get_source_segment(source, node), 'handler-catalog', 'exec'), scope)
            catalog = scope['get_project_creation_catalog']()
        self.assertTrue(any(item['value'] == 'perforce_like' for item in catalog['templates']))

    def test_browser_command_keeps_native_storage_administrator_permissions(self):
        artist = self.writer()
        with self.http() as url:
            request = Request(url + '/file-project/command?project=files',
                data=json.dumps({'action': 'storage_policy', 'revision': 0, 'policy': {'max_parallel': 16}}).encode(),
                headers={'X-Tactic-Ticket': artist['ticket'], 'Content-Type': 'application/json'})
            with self.assertRaises(HTTPError) as error:
                with urlopen(request) as response:
                    response.read()
            self.assertEqual(error.exception.code, 403)
            error.exception.close()
        self.assertEqual(self.call('storage_status')['max_parallel'], 4)

    def test_administrator_loads_managed_blob_schema_without_leaking_file_access(self):
        from pyasm.common.errors import SecurityException
        from pyasm.biz.file_project import TABLES
        command = 'tactic.ui.panel.search_types_cmd.SearchTypesCmd'
        args = {'action':'load','project_code':'files','identity':'file_project/blob'}
        for kind in TABLES:
            with self.subTest(kind=kind):
                selected = {**args, 'identity':'file_project/'+kind}
                result = self.api.dispatch('execute_cmd', ({'ticket':self.token,'project':'files'}, command, selected))['info']
                self.assertEqual(result['identity'], selected['identity'])
                self.assertIn('total', result['metadata']['summary'])
        source = Path('D:/code/th_codex/thlib/ui/admin/search_types_api.py').read_text(encoding='utf-8')
        function = next(node for node in ast.parse(source).body if isinstance(node,ast.FunctionDef) and node.name=='search_types_request')
        scope = {}
        with self.context():
            exec(compile(ast.get_source_segment(source,function),'handler-search-types','exec'),scope)
            handler = json.loads(scope['search_types_request'](**args))
        self.assertIn('total', handler['metadata']['summary'])
        with self.assertRaises(SecurityException):
            self.api.dispatch('query', ({'ticket':self.token,'project':'files'}, 'file_project/blob', []))
        artist = self.writer()
        with self.assertRaises(SecurityException):
            self.api.dispatch('execute_cmd', ({'ticket':artist['ticket'],'project':'files'}, command, args))

    def test_tree_browse_and_numbered_changes_keep_native_permissions(self):
        from pyasm.common.errors import SecurityException
        artist = self.writer()
        change = self.call('create_change', workspace='work')
        with self.assertRaises(SecurityException):
            self.client(artist, 'status', change='#%d' % change['number'])
        self.call('create_depot', code='private')
        self.call('create_stream', code='private', depot='private')
        with self.assertRaises(SecurityException):
            self.client(artist, 'browse', stream='private')
        self.assertEqual(self.client(artist, 'browse', stream='main')['items'], [])

    def test_administrator_http_blob_schema_request_returns_success(self):
        with self.http() as url:
            payload = {'method':'execute_cmd','args':[
                {'ticket':self.token,'project':'files','language':'python'},
                'tactic.ui.panel.search_types_cmd.SearchTypesCmd',
                {'action':'load','project_code':'files','identity':'file_project/blob'}], 'kwargs':{}}
            request = Request(url+'/admin/rpc',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
            with urlopen(request) as response:
                self.assertEqual(response.status,200)
                result=json.load(response)
            self.assertEqual(result['result']['info']['identity'],'file_project/blob')

    def test_managed_search_tabs_use_bounded_native_admin_reads(self):
        from pyasm.common.errors import SecurityException
        from tactic_stream.server.search_configuration import search_configuration_request
        from pyasm.search import Search
        payload = {'search_type': 'file_project/depot', 'limit': 2, 'offset': 0, 'include_total': True}
        with self.context():
            page = search_configuration_request('query', payload)
            self.assertEqual(page['records'][0]['code'], 'main')
            self.assertEqual(page['total'], 1)
            with self.assertRaises(SecurityException):
                Search('file_project/depot').get_sobjects()
        self.assertEqual(self.call('admin_search', payload=payload)['records'], page['records'])
        artist = self.writer()
        with self.assertRaises(SecurityException):
            self.client(artist, 'admin_search', payload=payload)
        for change in ({'limit': 10000}, {'search_type': 'sthpw/login'}, {'search_type': 'file_project/depot?project=admin'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.call('admin_search', payload={**payload, **change})
        with self.assertRaises(ValueError):
            self.call('admin_search', operation='save', payload=payload)
        with self.assertRaises(ValueError):
            self.call('admin_search', payload={**payload, 'records':[{'column':'_expression'}]})

    def test_administrator_result_items_and_cells_use_native_read_scope(self):
        from pyasm.search import SearchType
        with self.context():
            policy = SearchType.get('file_project/depot').get_record_read_options()
            self.assertTrue(policy['available'])
            self.assertTrue(policy['readonly'])
        key = 'file_project/depot?project=files&code=main'
        with self.http() as url:
            for endpoint, values in (('result-items', {}), ('table-cells', {'view':'table'})):
                request = Request(url+'/admin/'+endpoint, data=json.dumps({
                    'ticket':self.token,'project':'files','search_type':'file_project/depot',
                    'search_keys':[key], **values}).encode(), headers={'Content-Type':'application/json'})
                with urlopen(request) as response:
                    self.assertEqual(response.status, 200)
                    result = json.load(response)
                if endpoint == 'result-items':
                    self.assertEqual(len(result['result']['items']),1)

    def test_sdk_preserves_http_error_and_server_message(self):
        with self.http() as url:
            client = FileTransferClient(url, self.token, 'files')
            with self.assertRaises(HTTPError) as error:
                client.rpc('unknown_action')
            self.assertEqual(error.exception.code, 400)
            self.assertIn('File-project action required', str(error.exception))

    def test_bounded_current_locks_and_changelist_filters(self):
        first, second = self.change(), self.change()
        self.call('checkout', change=first, paths=['file.txt'], mode='ordinary')
        self.call('checkout', change=second, paths=['file.txt'], mode='ordinary')
        holders = self.call('locks', stream='main', paths=['file.txt', 'absent.txt'])['items']
        self.assertEqual(len(holders), 1)
        self.assertEqual(len(holders[0]['holders']), 2)
        self.call('revert', change=first)
        self.assertEqual([row['change'] for row in self.call('locks', stream='main', paths=['file.txt'])['items'][0]['holders']], [second])
        self.assertEqual([row['code'] for row in self.call('changes', workspace='work', state='pending')['items']], [second])
        with self.assertRaises(ValueError):
            self.call('locks', stream='main', paths=['../unsafe'])

    def test_native_sdk_maps_local_files_and_reconciles_after_have(self):
        root = Path(self.temp.name) / 'local'
        (root / 'lib').mkdir(parents=True)
        (root / 'lib/新しい.txt').write_bytes(b'fresh mapped content')
        self.call('create_workspace', code='mapped', stream='main', local_root=root.as_posix(),
                  mappings=[{'stream': 'main', 'source': 'src/...', 'target': 'lib/...', 'writable': True}])
        change = self.call('create_change', workspace='mapped')['code']
        cache = Path(self.temp.name) / 'cache/local.sqlite'
        with self.http(worker=True) as url:
            client = FileTransferClient(url, self.token, 'files')
            reconcile_workspace(client, 'mapped', root, cache)
            page = local_page(cache, changes_only=False)
            self.assertEqual(page['items'][0]['source_path'], 'src/新しい.txt')
            result = client.upload(change, root, Path(self.temp.name) / 'upload.sqlite',
                                   sources=local_sources(cache, root, 'main'))
            self.assertEqual(result['state'], 'ready')
            client.rpc('submit', change=change)
            self.assertEqual(self.call('list', stream='main')['items'][0]['path'], 'src/新しい.txt')
            client.download('mapped', root)
            reconcile_workspace(client, 'mapped', root, cache)
            self.assertEqual(local_page(cache, changes_only=False)['items'][0]['local_status'], 'clean')
            (root / 'lib/新しい.txt').unlink()
            reconcile_workspace(client, 'mapped', root, cache)
            self.assertEqual(local_page(cache, changes_only=False)['items'][0]['local_status'], 'missing')

    def test_empty_unicode_directories_and_selected_download_are_bounded(self):
        root=Path(self.temp.name)/'empty-local';root.mkdir()
        (root/'Empty — 空'/'nested').mkdir(parents=True)
        change=self.change();blob=self.upload(change,b'fresh selected bytes')
        self.call('edit',change=change,edit_revision=0,chunk='files',operations=[{'path':path,'blob':blob} for path in ['only.txt','neighbor.txt']])
        self.call('submit',change=change)
        self.call('create_workspace',code='empty',stream='main',local_root=root.as_posix(),mappings=[{'stream':'main','source':'...','target':'...','writable':True}])
        cache=Path(self.temp.name)/'empty-cache.sqlite'
        with self.http() as url:
            client=FileTransferClient(url,self.token,'files')
            client.download('empty',root,paths=['only.txt'])
            self.assertEqual((root/'only.txt').read_bytes(),b'fresh selected bytes')
            self.assertFalse((root/'neighbor.txt').exists())
            (root/'only.txt').write_bytes(b'local edit')
            update=self.change();new_blob=self.upload(update,b'new head')
            self.call('edit',change=update,edit_revision=0,chunk='new-head',operations=[{'path':'only.txt','blob':new_blob}])
            self.call('submit',change=update)
            blocked = client.download('empty',root,paths=['only.txt'])
            self.assertEqual(blocked['state'], 'blocked')
            self.assertEqual(blocked['reason'], 'local_modified_or_untracked')
            client.rpc('transfer_cancel',task=client.status['task'])
            self.assertEqual((root/'only.txt').read_bytes(),b'local edit')
            reconcile_workspace(client,'empty',root,cache)
            from tactic_client_lib.file_workspace import inspect_local
            state=client.rpc('file_states',workspace='empty',paths=[{'stream':'main','path':'only.txt'}])['items']
            self.assertEqual(inspect_local(cache,root,state)[0]['local_status'],'modified')
            (root/'only.txt').write_bytes(b'changed again after scan')
            state=client.rpc('file_states',workspace='empty',paths=[{'stream':'main','path':'only.txt'}])['items']
            self.assertEqual(inspect_local(cache,root,state)[0]['local_status'],'modified')
            page=local_browse(cache,limit=1)
            self.assertEqual(page['items'][0]['path'],'Empty — 空/')
            self.assertEqual(local_browse(cache,'Empty — 空/')['items'][0]['path'],'Empty — 空/nested/')
            self.assertEqual(local_browse(cache,'Empty — 空/nested/')['items'],[])
            self.assertEqual(local_browse(cache,after=page['after'])['items'][0]['path'],'only.txt')

    def test_stream_interface_in_chromium(self):
        self.call('switch_workspace', workspace='work', revision=0, request_id='initial')
        seed = self.change()
        blob = self.upload(seed, b'base published content')
        for start, count in ((0, 1000), (1000, 1)):
            self.call('edit', change=seed, chunk='page-%d' % start, edit_revision=start // 1000,
                      operations=[{'path': '%04d.txt' % i, 'blob': blob} for i in range(start, start + count)])
        self.call('edit', change=seed, chunk='directories', edit_revision=2,
                  operations=[{'path': path, 'blob': blob} for path in ['assets/characters/hero.ma', 'assets/props/tool.ma', 'shots/Шот 01/layout.ma']])
        self.call('submit', change=seed)
        ours, theirs = self.change(), self.change()
        for change, content in ((ours, b'ours content'), (theirs, b'theirs content')):
            blob = self.upload(change, content)
            self.call('edit', change=change, chunk='content', edit_revision=0,
                      operations=[{'path': '0000.txt', 'blob': blob}])
        self.call('update_change', change=ours, edit_revision=1, request_id='title', description='Conflict change')
        self.call('submit', change=theirs)
        self.api.dispatch('execute_cmd', ({'ticket': self.token, 'project': 'admin'},
            'tactic.command.CreateProjectCmd', {'project_code': 'classic', 'project_title': 'Classic'}))
        with self.http() as url:
            run = subprocess.run([shutil.which('node'), str(ROOT / 'frontend/tests/file-workspace-inspection.mjs'), url,
                                  str(ROOT / '.screenshots/file-workspace')], cwd=ROOT / 'frontend',
                                 env=dict(os.environ, PLAYWRIGHT_BROWSERS_PATH=str(ROOT / '.browser-cache')),
                                 capture_output=True, text=True, encoding='utf-8', timeout=180)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        (ROOT / '.test-tmp/file-workspace-browser.json').write_text(run.stdout, encoding='utf-8')

