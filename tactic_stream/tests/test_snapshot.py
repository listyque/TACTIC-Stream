import test_read_parity as read_tests
from pathlib import Path
import sys
from pyasm.search.search import RequestContext, request_context
from tools.snapshot_probe import run_snapshot_case


class SnapshotParity(read_tests.ReadParity):
    maxDiff = None
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
        import snapshot_contract
        import expression_contract
        with cls.store.connection(write=True) as db:
            snapshot_contract.install_fixture(db)
            expression_contract.install_fixture(db)
        cls.cases = [dict(method='expression_contract', project='admin', name='expression_language'),
                     dict(method='naming_contract', project='admin', name='naming_templates'),
                     dict(method='snapshot_contract', project='admin', name='metadata_and_files'),
                     dict(method='api_body', project='admin', name='snapshot_api_files', call='get_snapshot',
                          args=['contract/snapshot_entity?project=admin&code=A'], kwargs={'include_files': True}),
                     dict(method='api_body', project='admin', name='snapshot_api_missing_context', call='get_snapshot',
                          args=['contract/snapshot_entity?project=admin&code=A'], kwargs={'context': 'missing'}),
                     dict(method='api_body', project='admin', name='snapshot_api_empty_files', call='get_snapshot', expect_type_error=True,
                          args=['contract/snapshot_entity?project=admin&code=A'], kwargs={'context': 'empty', 'include_files': True})]

    def new_result(self, case):
        if case['method'] == 'api_body':
            return self.api.dispatch(case['call'], ({'ticket': self.ticket, 'project': 'admin'}, *case['args']), case['kwargs'])
        with request_context(RequestContext(self.store, 'admin', 'admin')):
            return run_snapshot_case(case)

    def assert_case_result(self, case, result, original):
        if case['method'] == 'expression_contract':
            old = original.pop('fixes')
            new = result.pop('fixes')
            years = sorted('%d_%s_%s' % (year, unit, direction)
                           for year in range(1, 12) for unit in ('YEAR', 'YEARS')
                           for direction in ('AGO', 'AHEAD'))
            self.assertEqual(old, {
                'env_cache': [[1], [1]], 'numeric_filter': 'SqlException',
                'empty_case': 'IndexError', 'field_as_code': '42suffix', 'quoted_var': 'OReilly',
                'quoted_filter': 'SyntaxError',
                'years': ['%d_YEARS_AGO', '%d_YEARS_AHEAD', '%d_YEAR_AGO', '%d_YEAR_AHEAD'],
                'state_after_error': [{'sthpw/snapshot': [['code', 'missing']]}, 'array'],
            })
            self.assertEqual(new, {
                'env_cache': [[1], [2]], 'numeric_filter': 2,
                'empty_case': 'fallback', 'field_as_code': '""" + str(6 * 7) + """suffix',
                'quoted_var': "O'Reilly", 'quoted_filter': [], 'years': years,
                'state_after_error': [{'sentinel': []}, 'sentinel'],
            })
            return super().assert_case_result(case, result, original)
        if case['method'] == 'naming_contract':
            self.assertEqual(original.pop('fixes'), {
                'dir_ext': 'UnboundLocalError', 'hash_dir': '!',
                'ext_override': 'frame.####.exr', 'float_file': 'TypeError',
                'float_dir': 'TypeError', 'nullable_dir': '', 'identifier': '00001',
                'no_file': 'AttributeError', 'leading_hash': 'frame',
            })
            self.assertEqual(result.pop('fixes'), {
                'dir_ext': 'exr', 'hash_dir': 'frame',
                'ext_override': 'frame.####.abc', 'float_file': '12.5',
                'float_dir': '12.5', 'nullable_dir': '', 'identifier': 'human_id',
                'no_file': '', 'leading_hash': 'frame',
            })
            return super().assert_case_result(case, result, original)
        if case.get('expect_type_error'):
            self.assertEqual(original, {'error': 'TypeError'})
            self.assertEqual(result['code'], 'CE')
            self.assertEqual(result['__files__'], [])
            return
        if case['method'] != 'snapshot_contract':
            return super().assert_case_result(case, result, original)
        old_build = original['construction']
        new_build = result['construction']
        self.assertEqual(old_build['versions'], {'2': 'UnboundLocalError', '7': 'UnboundLocalError'})
        self.assertEqual(new_build['versions'], {'2': [2, 2], '7': [7, 1]})
        self.assertEqual(old_build['manual_flags'], 'NameError')
        self.assertEqual(old_build['fresh_flags'], 'NameError')
        self.assertEqual(new_build['manual_flags'], {'is_latest': True, 'is_current': ''})
        self.assertEqual(new_build['fresh_flags'], {'is_latest': True, 'is_current': True})
        for field in ('xml', 'serialized'):
            old_fref = next(node for node in old_build[field][2] if node[0] == 'fref')
            new_fref = next(node for node in new_build[field][2] if node[0] == 'fref')
            self.assertEqual(old_fref[1]['node_name'], 'instance')
            self.assertEqual(new_fref[1]['node_name'], 'forward_node')
            old_fref[1]['node_name'] = 'forward_node'
        for field in ('versions', 'manual_flags', 'fresh_flags'):
            old_build[field] = new_build[field]
        self.assertEqual(original.pop('fixes'), {'first': 0, 'revision': 0, 'active': 'C1', 'retired': 'C1', 'frames': 2.5})
        self.assertEqual(result.pop('fixes'), {'first': 0, 'revision': 1, 'active': 'C1', 'retired': 'C3', 'frames': 3})
        # Original raw OR SQL applies retirement only to the last parent's clause.
        self.assertEqual(original['by_parents'], ['D1', 'C3', 'C2', 'C1', 'C0'])
        self.assertEqual(result['by_parents'], ['D1', 'C2', 'C1', 'C0'])
        self.assertEqual(original['latest_map']['contract/snapshot_entity?project=admin&code=A'], 'C3')
        self.assertEqual(result['latest_map']['contract/snapshot_entity?project=admin&code=A'], 'C2')
        original['by_parents'].remove('C3')
        original['latest_map']['contract/snapshot_entity?project=admin&code=A'] = 'C2'
        super().assert_case_result(case, result, original)

    def test_snapshot_read_options_and_invalid_writes_preserve_data(self):
        from pyasm.common.errors import UnsupportedContract
        key = 'contract/snapshot_entity?project=admin&code=A'
        ticket = {'ticket': self.ticket, 'project': 'admin'}
        before = {kind: self.api.dispatch('query', (ticket, kind)) for kind in ('sthpw/snapshot', 'sthpw/file')}
        for option in ('include_full_xml', 'versionless'):
            result = self.api.dispatch('get_snapshot', (ticket, key), {option: True})
            self.assertIsInstance(result, dict)
        from pyasm.search.sql import SqlException
        with self.assertRaises(SqlException):
            self.api.dispatch('insert', (ticket, 'sthpw/snapshot', {'code': 'forbidden', 'version': -1}))
        with self.assertRaises(UnsupportedContract):
            self.api.dispatch('insert', (ticket, 'sthpw/file_access', {'code': 'forbidden'}))
        self.assertEqual({kind: self.api.dispatch('query', (ticket, kind)) for kind in before}, before)

    def test_drafts_require_transaction_and_support_directory_metadata(self):
        import tempfile
        from pyasm.biz import Snapshot, File
        from pyasm.common import Xml
        from pyasm.common.errors import UnsupportedContract
        from pyasm.search import Search
        before = self.store.database_path('sthpw').read_bytes()
        with request_context(RequestContext(self.store, 'admin', 'admin')):
            self.api.auth.bind_security('admin', self.ticket)
            parent = Search.get_by_code('contract/snapshot_entity', 'A')
            draft = Snapshot.create(parent, 'file', 'draft', commit=False)
            file = File.create('missing.ma', parent.get_search_type(), parent.get_id(),
                               requires_file=False, commit=False)
            for operation in (lambda: Snapshot.create(parent, 'file', 'draft'),
                              lambda: File.create('missing.ma', parent.get_search_type(), parent.get_id()),
                              draft.commit, file.commit):
                with self.assertRaises(UnsupportedContract):
                    operation()
            with tempfile.TemporaryDirectory() as folder:
                directory = File.create(folder, parent.get_search_type(), parent.get_id(), commit=False)
                self.assertEqual(directory.get_value('base_type'), File.BASE_TYPE_DIR)
                self.assertEqual(directory.get_id(), -1)
            from pyasm.common import XmlException
            with self.assertRaises(XmlException):
                Snapshot.create(parent, 'file', 'draft', snapshot_data='<!DOCTYPE snapshot><snapshot/>', commit=False)
            xml = Xml('<snapshot><group/></snapshot>')
            group = xml.get_node('snapshot/group')
            with self.assertRaises(ValueError):
                Xml.append_child(group, xml.get_root_node())
            self.assertEqual(len(xml.get_root_node()), 1)
        self.assertEqual(self.store.database_path('sthpw').read_bytes(), before)

    def test_palette_expressions_resolve_in_naming(self):
        from pyasm.biz import NamingUtil, Snapshot
        from pyasm.common.errors import UnsupportedContract
        from pyasm.search import Search
        with request_context(RequestContext(self.store, 'admin', 'admin')):
            self.api.auth.bind_security('admin', self.ticket)
            parent = Search.get_by_code('contract/snapshot_entity', 'A')
            snapshot = Snapshot.create(parent, 'file', 'naming_guard', commit=False)
            util = NamingUtil()
            for template in ("{@COLOR(color)}",):
                for operation in (lambda: util.naming_to_file(template, parent, snapshot),
                                  lambda: util.naming_to_dir(template, parent, snapshot),
                                  lambda: util.eval_template(template, parent, snapshot=snapshot)):
                    with self.subTest(template=template):
                        self.assertEqual(operation(), Search.eval('@COLOR(color)', single=True))

    def test_expression_cache_tracks_writes_and_rollback(self):
        from pyasm.biz import ExpressionParser, Snapshot
        from pyasm.common import Container
        from pyasm.search import Search, Transaction
        with request_context(RequestContext(self.store, 'admin', 'admin')):
            self.api.auth.bind_security('admin', self.ticket)
            parent = Search.get_by_code('contract/snapshot_entity', 'A')
            xp = ExpressionParser()
            expression = "@GET(sthpw/snapshot['context','expression_cache'].version)"
            self.assertEqual(xp.eval(expression), [])
            transaction = Transaction.get(create=True)
            try:
                snapshot = Snapshot.create(parent, 'file', 'expression_cache')
                self.assertEqual(xp.eval(expression), [1])
                snapshot.delete()
                self.assertEqual(xp.eval(expression), [])
                Snapshot.create(parent, 'file', 'expression_cache')
                self.assertEqual(xp.eval(expression), [1])
            finally:
                transaction.rollback()
            self.assertEqual(xp.eval(expression), [])
            xp.eval(expression)
            before = Container.get('Expression:keys').copy()
            xp.eval(expression, use_cache=False)
            self.assertEqual(Container.get('Expression:keys'), before)

    def test_expression_cache_and_search_copy_recheck_security(self):
        from pyasm.biz import ExpressionParser
        from pyasm.common import Environment, Xml
        from pyasm.search import Search, SearchType
        from pyasm.security import Security, Sudo
        with request_context(RequestContext(self.store, 'expression_reader', 'admin')):
            security = Security()
            security._is_logged_in = 1
            security._login = SearchType.create('sthpw/login')
            security._login.set_value('login', 'expression_reader', temp=True)
            Environment.set_security(security)
            security.get_access_manager().add_xml_rules(Xml('<rules><rule group="search_type" default="deny"/></rules>'))
            expression = '@GET(sthpw/login.login)'
            sudo = Sudo()
            try:
                query = Search('sthpw/login')
                self.assertEqual(ExpressionParser().eval(expression), ['admin'])
            finally:
                sudo.exit()
            for options in ({}, {'search': query}):
                with self.assertRaisesRegex(Exception, 'Search Permission Denied'):
                    ExpressionParser().eval(expression, **options)


class SnapshotWriteParity(read_tests.ReadParity):
    def test_file_code_rename_preserves_snapshot_parent(self):
        import shutil, tempfile
        from tactic_stream.server.api import Api
        from pyasm.search.storage import Store
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            api = Api(store)
            ticket = {'ticket': self.ticket, 'project': 'admin'}
            parent_key = 'contract/snapshot_entity?project=admin&code=A'
            api.dispatch('update', (ticket, 'sthpw/file?code=FA', {'code': 'RENAMED_FILE'}))
            snapshot = api.dispatch('get_by_code', (ticket, 'sthpw/snapshot', 'CA'))
            self.assertEqual(snapshot['search_code'], 'A')
            api.dispatch('update', (ticket, parent_key, {'code': 'RENAMED_PARENT'}))
            snapshot = api.dispatch('get_by_code', (ticket, 'sthpw/snapshot', 'CA'))
            self.assertEqual(snapshot['search_code'], 'RENAMED_PARENT')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
        import snapshot_contract
        with cls.store.connection(write=True) as db:
            snapshot_contract.install_fixture(db)
        cls.cases = [dict(method='snapshot_write_contract', project='admin', name='persisted_lifecycle'),
                     dict(method='snapshot_write_contract', project='admin', name='rollback', fail=True, context='rollback_contract')]

    def new_result(self, case):
        import tempfile, shutil
        from pyasm.search.storage import Store
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'admin')):
                return run_snapshot_case(case)

    def assert_case_result(self, case, result, original):
        if not case.get('fail'):
            # Original stale first object clears the other latest but never updates itself.
            for step in ('latest', 'current', 'current_back'):
                self.assertFalse(original[step][0][2])
                self.assertTrue(result[step][0][2])
                original[step][0][2] = True
            for step in ('current_back', 'deleted'):
                self.assertFalse(original[step][0][3])
                self.assertTrue(result[step][0][3])
                original[step][0][3] = True
        self.assertEqual(result, original)
        if case.get('fail'):
            self.assertEqual(result, {'error': 'snapshot rollback', 'after': []})
        else:
            self.assertEqual(result['events'], [[1, 0], [2, 1]])
            self.assertEqual(result['created'], [[1, 0, False, True, []], [2, 0, False, False, []], [2, 1, True, False, []]])
            self.assertEqual(result['latest'], [[1, 0, True, True, []], [2, 0, False, False, []], [2, 1, False, False, []]])
            self.assertEqual(result['current'], [[1, 0, True, False, []], [2, 0, False, False, []], [2, 1, False, True, []]])

    def test_security_version_serialization_and_versionless_naming_are_atomic(self):
        import shutil, tempfile, ast
        from concurrent.futures import ThreadPoolExecutor
        from tactic_stream.server.api import Api
        from pyasm.common.errors import UnsupportedContract, SecurityException
        from pyasm.security.authenticator import hash_password
        from pyasm.search.storage import Store
        from pyasm.search import Search
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            api = Api(store)
            ticket = {'ticket': self.ticket, 'project': 'admin'}
            key = 'contract/snapshot_entity?project=admin&code=A'
            with ThreadPoolExecutor(max_workers=3) as pool:
                versions = list(pool.map(lambda _: api.dispatch('create_snapshot', (ticket, key, 'concurrent'))['version'], range(6)))
            self.assertEqual(sorted(versions), list(range(1, 7)))
            rows = ast.literal_eval(api.dispatch('query', (ticket, 'sthpw/snapshot'), {'filters': [['context', 'concurrent']]}))
            self.assertEqual(sum(bool(row['is_latest']) for row in rows), 1)
            self.assertEqual(sum(bool(row['is_current']) for row in rows), 1)
            with store.connection(write=True) as db:
                db.execute("INSERT INTO snapshot_other (id,title) VALUES (2,'Second')")
            for identity in (1, 2, 1):
                api.dispatch('create_snapshot', (ticket, 'contract/snapshot_other?project=admin&id=' + str(identity), 'id_isolation'))
            grouped = ast.literal_eval(api.dispatch('query', (ticket, 'sthpw/snapshot'), {'filters': [['context', 'id_isolation']]}))
            self.assertEqual(sum(bool(row['is_latest']) for row in grouped), 2)
            level = 'contract/snapshot_other?project=admin&id=1'
            api.dispatch('create_snapshot', (ticket, key, 'level_isolation'), {'level_key': level})
            api.dispatch('create_snapshot', (ticket, key, 'level_isolation'))
            grouped = ast.literal_eval(api.dispatch('query', (ticket, 'sthpw/snapshot'), {'filters': [['context', 'level_isolation']]}))
            self.assertEqual(sum(bool(row['is_latest']) for row in grouped), 2)
            row = api.dispatch('create_snapshot', (ticket, key, 'named'))
            api.dispatch('create_snapshot', (ticket, key, 'named'))
            with store.connection(write=True) as db:
                db.execute("INSERT INTO spt_naming (search_type,snapshot_type,context,latest_versionless) VALUES ('contract/snapshot_entity','file','named',TRUE)")
            api.dispatch('update', (ticket, row['__search_key__'], {'is_latest': True}))
            aliases = ast.literal_eval(api.dispatch('query', (ticket, 'sthpw/snapshot'),
                                                   {'filters': [['context', 'named'], ['version', -1]]}))
            self.assertEqual(len(aliases), 1)
            self.assertFalse(aliases[0]['is_latest'])
            before = api.dispatch('query', (ticket, 'sthpw/snapshot'))
            api.dispatch('delete_sobject', (ticket, row['__search_key__']))
            remaining = ast.literal_eval(api.dispatch('query', (ticket, 'sthpw/snapshot'),
                                                      {'filters': [['context', 'named']]}))
            self.assertEqual(sum(bool(item['is_latest']) for item in remaining if item['version'] > 0), 1)
            self.assertFalse(any(item['is_latest'] for item in remaining if item['version'] <= 0))
            before = api.dispatch('query', (ticket, 'sthpw/snapshot'))
            login = api.dispatch('insert', (ticket, 'sthpw/login', {'login': 'snapshot_reader', 'password': hash_password('private-snapshot-reader')}))
            reader = {'ticket': api.get_ticket('snapshot_reader', 'private-snapshot-reader'), 'project': 'admin'}
            with self.assertRaises(SecurityException):
                api.dispatch('create_snapshot', (reader, key, 'forbidden'))
            self.assertEqual(api.dispatch('query', (ticket, 'sthpw/snapshot')), before)

    def test_nullable_upgrade_preserves_metadata_indexes_and_sequence(self):
        import shutil, tempfile, json
        from pyasm.search.storage import Store
        resource = Path('src/tactic_stream/compatibility/snapshot_upgrade.json')
        statement = json.loads(resource.read_text())['tables']['file']
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with store.connection(write=True) as db:
                db.execute('DROP TABLE file')
                db.execute(statement)
                db.execute('ALTER TABLE file ADD COLUMN contract_extra text')
                db.execute('CREATE INDEX contract_file_extra_idx ON file(contract_extra)')
                db.execute("INSERT INTO file (id,file_name,search_type,search_id,contract_extra) VALUES (100,'delete.ma','sthpw/project',1,'gone')")
                db.execute('DELETE FROM file WHERE id=100')
                db.execute("INSERT INTO file (id,file_name,search_type,search_id,contract_extra) VALUES (50,'keep.ma','sthpw/project',1,'kept')")
            self.assertTrue(store.upgrade())
            self.assertFalse(store.upgrade())
            with store.connection(write=True) as db:
                self.assertEqual(tuple(db.execute('SELECT id,file_name,contract_extra FROM file').fetchone()), (50, 'keep.ma', 'kept'))
                self.assertTrue(db.execute("SELECT 1 FROM sqlite_master WHERE name='contract_file_extra_idx'").fetchone())
                db.execute("INSERT INTO file (file_name,search_type) VALUES ('no_id.ma','sthpw/project')")
                self.assertEqual(db.execute("SELECT id FROM file WHERE file_name='no_id.ma'").fetchone()[0], 101)
