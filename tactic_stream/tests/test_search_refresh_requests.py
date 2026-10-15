"""Real Handler search/detail consumers against an isolated native API."""
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import test_compound_search_performance as compound

sys.path.insert(0, 'D:/code/th_codex')
from thlib import tactic_classes as tc, tactic_query as tq, server_cache
from thlib.ui.controllers.search_runtime import SearchRuntimeMixin
from thlib.ui.controllers.snapshot_details import SnapshotDetailsMixin
from pyasm.security.authenticator import hash_password


class SearchRefreshRequests(unittest.TestCase):
    note = compound.CompoundSearchPerformance.note
    query = compound.CompoundSearchPerformance.query

    def setUp(self):
        compound.CompoundSearchPerformance.setUp(self)
        self.script = ''.join(tq._function_source_lines(tq.get_tasks_and_notes)) + self.script

    def seed(self):
        with self.store.connection(write=True) as db:
            for code, process in [('T1', 'layout'), ('T2', 'publish')]:
                db.execute('INSERT INTO task(code,search_type,search_code,process,project_code) VALUES(?,?,?,?,?)',
                           (code, 'contract/entity?project=one', 'A', process, 'one'))
            self.note(db, 'LAYOUT', process='layout')
            self.note(db, 'PUBLISH', process='publish')
            db.execute("UPDATE note SET project_code='one'")
            db.execute("INSERT INTO status_log(code,search_type,search_code,search_id,status,login) SELECT 'H1','sthpw/task','T1',id,'Pending','admin' FROM task WHERE code='T1'")
            for version in (1, 2):
                db.execute("INSERT INTO snapshot(code,search_type,search_code,project_code,process,context,version,is_latest,snapshot,login) VALUES(?,?,?,?,?,?,?,?,'<snapshot/>','admin')",
                           ('S%d' % version, 'contract/entity?project=one', 'A', 'one', 'publish', 'publish/main', version, version == 2))
            db.execute("INSERT INTO snapshot(code,search_type,search_code,project_code,process,context,version,is_latest,snapshot,login) VALUES('LAYOUT_SNAPSHOT','contract/entity?project=one','A','one','layout','layout/main',1,1,'<snapshot/>','admin')")
            db.execute("UPDATE snapshot SET snapshot='<snapshot><file name=\"preview.jpg\" type=\"web\" file_code=\"WEB\"/></snapshot>' WHERE code='S2'")
            db.execute("INSERT INTO file(code,file_name,search_type,search_id,search_code,snapshot_code,project_code,type) VALUES('WEB','preview.jpg','contract/entity?project=one',1,'A','S2','one','web')")

    def test_refresh_uses_one_rpc_and_keeps_all_processes_history_and_snapshots(self):
        self.seed()
        calls = []
        api = self.api
        ticket = self.ticket

        class Client:
            def build_search_type(self, kind, project):
                return kind + '?project=' + project

            def execute_python_script(self, script_path, kwargs):
                calls.append('execute_python_script')
                return api.dispatch('execute_python_script', (ticket, script_path, kwargs))

            def query_snapshots(self, **kwargs):
                calls.append('query_snapshots')
                return api.dispatch('query_snapshots', (ticket,), kwargs)

        project = SimpleNamespace(info={'code': 'one'}, get_code=lambda: 'one')
        with (
            patch.object(tc, 'server_start', return_value=Client()),
            patch.object(tc, 'env_read_config', return_value={}),
            patch.object(tc.env_inst, 'projects', {'one': project}),
            patch.object(server_cache, 'token', return_value=None) as cache_token,
            patch.object(server_cache, 'write_entry'),
            patch.object(server_cache, 'read_entry', return_value=None),
            patch.object(server_cache, 'invalidate_domains'),
            patch.object(tc, 'get_snapshots_updates_list', return_value=[]),
            patch.object(SearchRuntimeMixin, '_search_stype', return_value=None),
        ):
            objects, _info, _stype = SearchRuntimeMixin._query_sobjects(
                'contract/entity', 'one', (), [('code', 'A')], 50, 0, bypass_cache=True,
            )
            source = objects[0]

            def snapshots(_key, refresh=False):
                source.update_snapshots(order_bys=['timestamp desc'], force=refresh)
                return []

            owner = SimpleNamespace(workspace_model=SimpleNamespace(
                source_for_search_key=lambda key: source,
                snapshot_nodes_for=snapshots,
            ), _snapshot_browser_nodes_for_context=SnapshotDetailsMixin._snapshot_browser_nodes_for_context)
            _, tasks, notes, _ = SnapshotDetailsMixin._prepare_sobject_details(owner, source.get_search_key())
            print('Refresh RPCs:', calls, flush=True)
            self.assertEqual(calls, ['execute_python_script'])
            self.assertEqual({task.get_code() for task in tasks}, {'T1', 'T2'})
            self.assertEqual({note.get_code() for note in notes}, {'LAYOUT', 'PUBLISH'})
            self.assertEqual([entry.info['code'] for task in tasks if task.get_code() == 'T1' for entry in task.get_status_log()], ['H1'])
            self.assertEqual({row['code'] for row in source.info['__snapshots__']}, {'S1', 'S2', 'LAYOUT_SNAPSHOT'})
            contexts = source.get_all_processes()['publish'].get_contexts()
            preview = contexts['publish/main'].get_versions()['S2']
            self.assertEqual(preview.get_files()['web'][0]['file_name'], 'preview.jpg')
            _, _, process_notes, _ = SnapshotDetailsMixin._prepare_sobject_details(owner, source.get_search_key(), process='layout')
            self.assertEqual([note.get_code() for note in process_notes], ['LAYOUT'])
            self.assertEqual(calls, ['execute_python_script'])
            source.update_snapshots(order_bys=['timestamp desc'], force=True)
            self.assertEqual(calls, ['execute_python_script', 'query_snapshots'])
            cache_token.return_value = 'invalidated'
            source.update_snapshots(order_bys=['timestamp desc'])
            self.assertEqual(calls, ['execute_python_script', 'query_snapshots', 'query_snapshots'])

    def test_bundle_follows_selection_and_empty_result_has_no_details(self):
        self.seed()
        rows = self.query(include_details=True, include_snapshots=True,
                          details_search_key='skey://contract/entity?project=one&code=B')['sobjects_list']
        selected = next(row for row in rows if row['code'] == 'B')
        self.assertIn('__details__', selected)
        self.assertEqual(selected['__details__']['tasks'], [])
        self.assertTrue(selected['__snapshots_complete__'])
        self.assertTrue(all('__details__' not in row for row in rows if row['code'] != 'B'))
        self.assertEqual(self.query(include_details=True, filters=[('code', 'absent')])['sobjects_list'], [])

    def test_bundle_preserves_id_parent_and_excludes_same_code_of_other_type(self):
        self.seed()
        with self.store.connection(write=True) as db:
            db.execute("INSERT INTO note(code,search_type,search_id,process,note,login,project_code) VALUES('ID_NOTE','contract/entity?project=one',4,'layout','By id','admin','one')")
            self.note(db, 'OTHER_TYPE', kind='other/type')
            db.execute("UPDATE note SET project_code='one' WHERE code='OTHER_TYPE'")
        row = self.query(include_details=True, filters=[('id', 4)])['sobjects_list'][0]
        self.assertEqual([note['code'] for note in row['__details__']['notes']], ['ID_NOTE'])
        row = self.query(include_details=True, filters=[('code', 'A')])['sobjects_list'][0]
        self.assertEqual({note['code'] for note in row['__details__']['notes']}, {'LAYOUT', 'PUBLISH'})

    def test_bundle_keeps_private_notes_hidden(self):
        self.seed()
        with self.store.connection(write=True) as db:
            db.execute('INSERT INTO login(code,login,password) VALUES(?,?,?)', ('artist', 'artist', hash_password('private-artist-test')))
            rules = '<rules><rule group="project" code="one" access="allow"/><rule group="project" key="one" access="allow"/><rule group="api_cmd" key="tactic.command.PythonCmd" access="allow"/><rule group="search_type" code="*" access="allow"/></rules>'
            db.execute('INSERT INTO login_group(code,login_group,access_rules) VALUES(?,?,?)', ('reader', 'reader', rules))
            db.execute("INSERT INTO login_in_group(code,login,login_group) VALUES('member','artist','reader')")
            self.note(db, 'PRIVATE', login='admin', access='private')
            db.execute("UPDATE note SET project_code='one' WHERE code='PRIVATE'")
        self.ticket = {'ticket': self.api.get_ticket('artist', 'private-artist-test'), 'project': 'one'}
        row = self.query(include_details=True, filters=[('code', 'A')])['sobjects_list'][0]
        self.assertEqual({note['code'] for note in row['__details__']['notes']}, {'LAYOUT', 'PUBLISH'})


if __name__ == '__main__':
    unittest.main()
