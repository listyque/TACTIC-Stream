"""Native batched check-in, ACL, trigger visibility and transactional failure."""
from contextlib import contextmanager
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pyasm.biz import File
from pyasm.checkin import FileCheckin
from pyasm.command import Command, Trigger
from pyasm.common import Common, Container, Environment, Xml
from pyasm.common.errors import SecurityException
from pyasm.search import Search, SearchType, SObject, SqlException, Transaction
from pyasm.search.database_impl import SqliteImpl
from pyasm.search.search import RequestContext, request_context
from pyasm.search.sql import Insert, Sql
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from tactic_stream.server.api import Api


class CheckinObserver(Trigger):
    def execute(self):
        output = self.get_input()
        search = Search('sthpw/file')
        search.add_filter('snapshot_code', output['snapshot']['code'])
        search.add_order_by('id')
        rows = search.get_sobjects()
        assert [row.get_code() for row in rows] == [row['code'] for row in output['files']]
        Container.put('batch_observed', len(rows))
        if Container.get('batch_trigger_failure'):
            raise ValueError('late batch trigger failure')


class BatchCheckin(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.store = Store(self.root / 'data')
        self.store.initialize(hash_password('private-batch-test'))
        self.api = Api(self.store)
        self.admin_ticket = self.api.get_ticket('admin', 'private-batch-test')
        self.admin = dict(ticket=self.admin_ticket, project='one')
        self.api.dispatch('execute_cmd', (dict(ticket=self.admin_ticket, project='admin'),
            'tactic.command.CreateProjectCmd', dict(project_code='one', project_title='Batch tests', project_stype=['asset'])))
        self.parent = self.api.dispatch('insert', (self.admin, 'one/asset', dict(code='PARENT', name='Batch parent')))
        self.rules = ('<rules><rule group="project" code="one" access="allow"/>'
                      '<rule group="search_type" code="one/asset" project="one" access="allow"/>'
                      '<rule group="search_type" code="sthpw/snapshot" access="allow"/>'
                      '<rule group="search_type" code="sthpw/file" access="allow"/>%s</rules>')
        self.group = self.api.dispatch('insert', (self.admin, 'sthpw/login_group',
            dict(login_group='batch_writers', access_rules=self.rules % '')))
        self.api.dispatch('execute_python_script', (self.admin, '', dict(code=
            "from pyasm.security import Login\nLogin.create('batch_writer', 'private-batch-writer', groups=['batch_writers'])")))
        self.user_ticket = self.api.get_ticket('batch_writer', 'private-batch-writer')

    @contextmanager
    def scope(self, user='admin'):
        with request_context(RequestContext(self.store, user, 'one')):
            self.api.auth.bind_security(user, self.admin_ticket if user == 'admin' else self.user_ticket)
            yield

    def records(self):
        with self.scope():
            return {kind: [dict(row.data) for row in Search(kind).get_sobjects()]
                    for kind in ('sthpw/file', 'sthpw/snapshot', 'sthpw/transaction_log',
                                 'sthpw/sobject_log', 'sthpw/change_timestamp')}

    def test_cached_admin_object_cannot_bypass_revoked_user_read_rights(self):
        from pyasm.security import LoginGroup, Sudo
        with self.scope('batch_writer'):
            sudo = Sudo()
            try:
                self.assertIsNotNone(Search.get_by_code('one/asset', 'PARENT'))
            finally:
                sudo.exit()
            self.assertIsNotNone(Search.get_by_code('one/asset', 'PARENT'))
            group = LoginGroup.get_by_group_name('batch_writers')
            group.set_value('access_rules', (self.rules % '').replace(
                'code="one/asset" project="one" access="allow"',
                'code="one/asset" project="one" access="deny"'))
            manager = Environment.get_security().get_access_manager()
            manager.groups.pop('search_type', None)
            manager.add_xml_rules(group)
            self.assertFalse(manager.check_access('search_type',
                [{'code': 'one/asset', 'project': 'one'}], 'view', default='deny'))
            self.assertIsNone(Search.get_by_code('one/asset', 'PARENT'))

    def test_cached_project_setting_refreshes_after_native_write(self):
        from pyasm.biz import ProjectSetting
        with self.scope():
            command = Command()
            command.get_transaction().set_sync(False)
            def run():
                self.assertEqual(ProjectSetting.get_value_by_key('cache_probe'), '')
                ProjectSetting.create('cache_probe', 'first')
                for _ in range(3):
                    self.assertEqual(ProjectSetting.get_value_by_key('cache_probe'), 'first')
                ProjectSetting.create('cache_probe', 'second')
                self.assertEqual(ProjectSetting.get_value_by_key('cache_probe'), 'second')
            command.execute = run
            Command.execute_cmd(command)

    def test_cached_object_still_rejects_a_retired_project(self):
        with self.scope():
            command = Command()
            command.get_transaction().set_sync(False)
            def run():
                from pyasm.biz import Project
                Project.set_project('admin')
                self.assertIsNotNone(Search.get_by_code('one/asset?project=one', 'PARENT'))
                project = Search.get_by_code('sthpw/project', 'one')
                project.set_value('s_status', 'retired')
                project.commit()
                with self.assertRaises(LookupError):
                    Search.get_by_code('one/asset?project=one', 'PARENT')
            command.execute = run
            Command.execute_cmd(command)

    def checkin(self, count=300, user='admin', trigger=False, fail_trigger=False, random_codes=False):
        with self.scope(user):
            folder = Path(Environment.get_upload_dir()) if user != 'admin' else self.root / 'input'
            folder.mkdir(parents=True, exist_ok=True)
            paths = []
            for index in range(count):
                path = folder / ('part_%04d.bin' % index)
                path.write_bytes(str(index).encode())
                paths.append(path.as_posix())
            if trigger:
                handler = SearchType.create('config/trigger')
                handler.set_value('event', 'checkin')
                handler.set_value('class_name', 'test_batch_checkin.CheckinObserver')
                handler.set_value('mode', 'same process,same transaction')
                Trigger.append_static_trigger(handler)
                Container.put('batch_trigger_failure', fail_trigger)
            command = FileCheckin(Search.get_by_code('one/asset', 'PARENT'), paths,
                file_types=['main'] * count, source_paths=paths, context='bulk', checkin_type='strict',
                mode='uploaded' if user != 'admin' else 'copy', md5s='ignore',
                file_naming='{basefile}_v{version}.{ext}', dir_naming='{project.code}/batch/{snapshot.context}',
                do_update_versionless=False)
            command.get_transaction().set_sync(False)
            snapshot = Command.execute_cmd(command)
            if trigger:
                self.assertEqual(Container.get('batch_observed'), count)
            rows = snapshot.get_all_file_objects()
            self.assertEqual(len(rows), count)
            by_code = {row.get_code(): row for row in rows}
            for index, code in enumerate(snapshot.get_all_file_codes()):
                row = by_code[code]
                if random_codes:
                    self.assertRegex(row.get_code(), r'^CUSTOM[0-9a-f]{10}$')
                else:
                    self.assertEqual(row.get_code(), row.generate_code(row.get_id()))
                self.assertEqual(Path(row.get_lib_path()).read_bytes(), str(index).encode())
            return snapshot.get_code()

    def test_user_batches_keep_codes_trigger_visibility_and_undo_redo(self):
        batches = []
        original = Sql.do_update_multiple
        def saving(sql, updates, rows):
            batches.append((rows[0].get_base_search_type(), len(rows)))
            return original(sql, updates, rows)
        with patch.object(Sql, 'do_update_multiple', saving):
            code = self.checkin(user='batch_writer', trigger=True)
        self.assertEqual([count for kind, count in batches if kind == 'sthpw/file'], [250, 250, 50, 50, 250, 50])
        self.assertTrue(all(count <= 250 for _, count in batches))
        with self.scope():
            snapshot = Search.get_by_code('sthpw/snapshot', code)
            codes = [row.get_code() for row in snapshot.get_all_file_objects()]
            log = Search('sthpw/transaction_log'); log.add_order_by('id desc'); log = log.get_sobject()
            xml = Xml(Common.decompress_transaction(log.get_value('transaction')))
            nodes = [node for node in xml.get_nodes('transaction/sobject') if node.get('search_type') == 'sthpw/file']
            self.assertEqual(len(nodes), 600)
            for action in ('insert', 'update'):
                self.assertEqual([node.get('search_code') for node in nodes if node.get('action') == action], codes)
            for node in nodes:
                if node.get('action') == 'insert':
                    self.assertFalse({'id', 'code'}.intersection(column.get('name') for column in node))
            log_id = log.get_id()
            self.assertEqual(log.get_value('login'), 'batch_writer')
            index = Search('sthpw/sobject_log')
            index.add_filter('transaction_log_id', log_id)
            index.add_filter('search_code', code)
            self.assertEqual(index.get_count(), 1)
            index = Search('sthpw/sobject_log')
            index.add_filter('transaction_log_id', log_id)
            index.add_filter('search_code', 'PARENT')
            self.assertEqual(index.get_count(), 1)
        ticket = dict(ticket=self.user_ticket, project='one')
        self.assertTrue(self.api.dispatch('undo', (ticket, None, log_id)))
        with self.scope():
            self.assertIsNone(Search.get_by_code('sthpw/snapshot', code))
            self.assertFalse(Search.get_by_code('sthpw/file', codes))
        self.assertTrue(self.api.dispatch('redo', (ticket, None, log_id)))
        with self.scope():
            self.assertEqual([row.get_code() for row in Search.get_by_code('sthpw/snapshot', code).get_all_file_objects()], codes)

    def test_large_history_resolves_excluded_types_once_between_object_writes(self):
        from pyasm.search import TransactionLog
        with self.scope():
            file = '<sobject search_type="sthpw/file" search_code="FILE" action="insert"/>'
            asset = '<sobject search_type="one/asset?project=one" search_code="PARENT" action="update"/>'
            data = '<transaction>' + file * 200 + asset + file * 200 + '</transaction>'
            command = Command()
            command.get_transaction().set_sync(False)
            command.get_transaction().set_record(False)
            def execute():
                log = TransactionLog.create('pyasm.command.Command', data, 'history indexing')
                resolved = []
                get = SearchType.get
                def get_type(key, *args, **kwargs):
                    if key == 'sthpw/file':
                        resolved.append(key)
                    return get(key, *args, **kwargs)
                with patch.object(SearchType, 'get', side_effect=get_type):
                    TransactionLog.create_sobject_log(log, data)
                self.assertEqual(len(resolved), 2)
                rows = Search('sthpw/sobject_log')
                rows.add_filter('transaction_log_id', log.get_id())
                rows = rows.get_sobjects()
                self.assertEqual([(row.get_value('search_code'), row.get_value('action'))
                                  for row in rows], [('PARENT', 'update')])
            command.execute = execute
            Command.execute_cmd(command)

    def test_late_trigger_failure_rolls_back_all_batches_and_files(self):
        before = self.records()
        with self.assertRaisesRegex(ValueError, 'late batch trigger failure'):
            self.checkin(trigger=True, fail_trigger=True)
        self.assertEqual(self.records(), before)
        self.assertEqual(len(list((self.root / 'input').glob('*.bin'))), 300)
        self.assertFalse(list((self.store.data_dir / 'assets').rglob('*.bin')))

    def test_failure_after_first_file_batch_rolls_back_earlier_batch(self):
        before = self.records()
        original = Sql.do_update_multiple
        calls = 0
        def saving(sql, updates, rows):
            nonlocal calls
            if rows[0].get_base_search_type() == 'sthpw/file' and isinstance(updates[0], Insert):
                calls += 1
                if calls == 2:
                    # A later initial INSERT must roll back the earlier INSERT and code assignment.
                    updates[0].set_value('id', 100000000)
                    updates[1].set_value('id', 100000000)
            return original(sql, updates, rows)
        with patch.object(Sql, 'do_update_multiple', saving), self.assertRaisesRegex(SqlException, 'UNIQUE'):
            self.checkin()
        self.assertEqual(calls, 2)
        self.assertEqual(self.records(), before)
        self.assertFalse(list((self.store.data_dir / 'assets').rglob('*.bin')))

    def test_timestamp_batch_failure_rolls_back_completed_checkin(self):
        before = self.records()
        original = Sql.do_update_multiple
        calls = 0
        def saving(sql, updates, rows):
            nonlocal calls
            if rows[0].get_base_search_type() == 'sthpw/change_timestamp':
                calls += 1
                if calls == 2:
                    # A constraint failure must roll back the earlier INSERT portion too.
                    updates[0].set_value('id', 100000000)
                    updates[1].set_value('id', 100000000)
            return original(sql, updates, rows)
        with patch.object(Sql, 'do_update_multiple', saving), self.assertRaisesRegex(SqlException, 'UNIQUE'):
            self.checkin()
        self.assertEqual(calls, 2)
        self.assertEqual(self.records(), before)
        self.assertFalse(list((self.store.data_dir / 'assets').rglob('*.bin')))

    def test_revoked_field_on_later_batch_rolls_back_everything(self):
        rule = '<rule group="sobject_column" search_type="sthpw/file" column="snapshot_code" project="one" access="deny"/>'
        before = self.records()
        original = Sql.do_update_multiple
        calls = 0
        def saving(sql, updates, rows):
            nonlocal calls
            result = original(sql, updates, rows)
            if rows[0].get_base_search_type() == 'sthpw/file':
                calls += 1
                if calls == 1:
                    from pyasm.common import Environment
                    from pyasm.security import LoginGroup
                    group = LoginGroup.get_by_group_name('batch_writers')
                    group.set_value('access_rules', self.rules % rule)
                    Environment.get_security().get_access_manager().add_xml_rules(group)
            return result
        with patch.object(Sql, 'do_update_multiple', saving), self.assertRaises(SecurityException):
            self.checkin(user='batch_writer')
        self.assertEqual(self.records(), before)

    def test_generated_codes_keep_field_permissions_and_rollback_initial_insert(self):
        rule = '<rule group="sobject_column" search_type="sthpw/file" column="code" project="one" access="deny"/>'
        before = self.records()
        original = Sql.do_update_multiple
        inserted = []
        def saving(sql, updates, rows):
            result = original(sql, updates, rows)
            if updates[0].table == 'file' and isinstance(updates[0], Insert):
                inserted.append(len(rows))
                from pyasm.security import LoginGroup
                group = LoginGroup.get_by_group_name('batch_writers')
                group.set_value('access_rules', self.rules % rule)
                Environment.get_security().get_access_manager().add_xml_rules(group)
            return result
        with patch.object(Sql, 'do_update_multiple', saving), self.assertRaises(SecurityException):
            self.checkin(user='batch_writer')
        self.assertEqual(inserted, [250])
        self.assertEqual(self.records(), before)

    def test_unordered_returning_and_native_random_codes(self):
        for key, value in (('code_prefix', 'CUSTOM'), ('code_format', 'random')):
            self.api.dispatch('insert', (self.admin, 'config/prod_setting',
                dict(key=key, value=value, search_type='sthpw/file')))
        returning = []
        original = Sql._do_update
        def saving(sql, *args, **kwargs):
            result = original(sql, *args, **kwargs)
            if kwargs.get('returning'):
                returning.append(len(result))
                return list(reversed(result))
            return result
        with patch.object(Sql, '_do_update', saving):
            code = self.checkin(random_codes=True, trigger=True)
        self.assertTrue(any(count > 1 for count in returning))
        with self.scope():
            rows = Search.get_by_code('sthpw/snapshot', code).get_all_file_objects()
            self.assertEqual(len({row.get_code() for row in rows}), 300)

    def test_duplicate_input_names_keep_individual_ids_and_sizes(self):
        with self.scope():
            parent = Search.get_by_code('one/asset', 'PARENT')
            Container.put('Checkin:writing', {'parent': parent})
            rows = [File.create((self.root / str(index) / 'same.bin').as_posix(),
                        parent.get_search_type(), parent.get_id(), search_code=parent.get_code(),
                        requires_file=False, st_size=index + 1, commit=False) for index in range(3)]
            transaction = Transaction.get(create=True)
            transaction.set_sync(False)
            with patch.object(Sql, 'do_update_multiple', autospec=True, side_effect=Sql.do_update_multiple) as saving:
                try:
                    SObject.commit_multiple(rows, triggers='none')
                    self.assertFalse(any(call.args[1][0].table == 'file' for call in saving.call_args_list))
                    transaction.commit_all()
                except Exception:
                    if transaction.is_in_transaction():
                        transaction.rollback()
                    raise
            self.assertEqual(len({row.get_id() for row in rows}), 3)
            for index, row in enumerate(rows):
                stored = Search.get_by_code('sthpw/file', row.get_code())
                self.assertEqual(stored.get_value('st_size'), index + 1)
                self.assertEqual(stored.get_code(), row.generate_code(row.get_id()))

    def test_custom_code_generator_keeps_per_file_database_visibility(self):
        seen = []
        original = File.generate_code
        def generating(row, id=None):
            if row.get_id() == -1:
                seen.append(Search('sthpw/file').get_count())
            return original(row, id)
        with patch.object(File, 'generate_code', generating), patch.object(Sql, 'do_update_multiple',
                autospec=True, side_effect=Sql.do_update_multiple) as saving:
            self.checkin(count=3)
            self.assertEqual(seen, [1, 2, 3])
            self.assertFalse(any(call.args[1][0].table == 'file' for call in saving.call_args_list))

    def test_custom_hook_and_sql_trigger_tables_use_sequential_commits(self):
        seen = []
        staged = []
        original = File.on_update
        metadata = FileCheckin.update_metadata
        def remember(command, *args):
            Container.put('batch_file_objects', command.file_objects)
            return metadata(command, *args)
        def hook(row):
            if row.get_value('snapshot_code'):
                search = Search('sthpw/file'); search.add_filter('snapshot_code', row.get_value('snapshot_code'))
                seen.append(search.get_count())
                staged.append(sum(bool(file.get_value('snapshot_code')) for file in Container.get('batch_file_objects')))
            return original(row)
        with patch.object(FileCheckin, 'update_metadata', remember), patch.object(File, 'on_update', hook), patch.object(Sql, 'do_update_multiple', autospec=True, side_effect=Sql.do_update_multiple) as saving:
            self.checkin(count=3)
            self.assertEqual(seen, [1, 2, 3])
            self.assertEqual(staged, [1, 2, 3])
            self.assertFalse(any(call.args[1][0].table == 'file' for call in saving.call_args_list))
        with self.scope(), patch.object(SqliteImpl, 'has_table_triggers', return_value=True), patch.object(Sql, 'do_update_multiple') as saving:
            rows = Search('sthpw/file').get_sobjects()
            for row in rows:
                row.set_value('st_size', row.get_value('st_size') + 1)
            parent = Search.get_by_code('one/asset', 'PARENT')
            Container.put('Checkin:writing', {'parent': parent})
            transaction = Transaction.get(create=True)
            transaction.set_sync(False)
            try:
                SObject.commit_multiple(rows, triggers='none')
                transaction.commit_all()
            except Exception:
                if transaction.is_in_transaction():
                    transaction.rollback()
                raise
            saving.assert_not_called()
