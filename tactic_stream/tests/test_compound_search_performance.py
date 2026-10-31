"""The actual Handler procedure, native grouped note ACLs and count contracts."""
import ast
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zlib

from test_foundation import fixture
from pyasm.biz.note import Note
from pyasm.common.errors import SecurityException, UnsupportedContract
from pyasm.search import Search
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from tactic_stream.server.api import Api

ROOT = Path(__file__).resolve().parents[1]


class NormalizedNote(Note):
    def get_value(self, name, *args, **kwargs):
        value = super().get_value(name, *args, **kwargs)
        return 'review' if name == 'process' and value == 'layout' else value


def procedure_source(name='query_sobjects'):
    source = (ROOT.parents[1] / 'TH/thlib/tactic_query.py').read_text(encoding='utf-8')
    node = next(node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name == name)
    return ast.get_source_segment(source, node) + '\nreturn %s(**kwargs["options"])' % name


class CompoundSearchPerformance(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.store = Store(Path(directory.name))
        self.store.initialize(hash_password('private-compound-test'))
        fixture(self.store)
        with self.store.connection(write=True) as db:
            db.execute('ALTER TABLE note ADD COLUMN s_status varchar(256)')
        self.api = Api(self.store)
        self.ticket = {'ticket': self.api.get_ticket('admin', 'private-compound-test'), 'project': 'one'}
        self.script = procedure_source()

    def query(self, search_type='contract/entity?project=one', **options):
        options = dict(dict(search_type=search_type, project_code='one', limit=50,
                       include_info=True, include_snapshots=False, compressed_return=False,
                       order_bys=['id asc']), **options)
        result = self.api.dispatch('execute_python_script', (self.ticket, '', dict(code=self.script, options=options)))['info']
        if result.startswith('zlib:'):
            result = zlib.decompress(bytes.fromhex(result[5:])).decode()
        return json.loads(result)

    def test_bootstrap_identifies_stream_without_a_feature_probe(self):
        script = procedure_source('get_projects_and_logins')
        result = self.api.dispatch('execute_python_script',
            (self.ticket, '', dict(code=script, options={})))['info']
        self.assertEqual(json.loads(result)['server_api'], 'stream')

    def note(self, db, code, parent='A', kind='contract/entity?project=one', process='publish', **extra):
        values = dict(code=code, search_code=parent, search_type=kind, process=process,
                      login='admin', note='Example')
        values.update(extra)
        db.execute('INSERT INTO note(%s) VALUES(%s)' % (','.join(values), ','.join('?' for _ in values)), list(values.values()))

    def test_legacy_search_signature_without_native_group_counts(self):
        with self.store.connection(write=True) as db:
            self.note(db, 'ONE')
            self.note(db, 'TWO', process=None)
            self.note(db, 'RETIRED', s_status='retired')
        add_column = Search.add_column

        def legacy_add_column(search, column, distinct=False, table=None, as_column=None):
            return add_column(search, column, distinct, table, as_column)

        with patch.object(Search, 'add_column', legacy_add_column), \
                patch.object(Search, 'get_group_counts'):
            del Search.get_group_counts
            result = self.query()
        parent = next(row for row in result['sobjects_list'] if row.get('code') == 'A')
        self.assertEqual(parent['__notes_count__'], 3)
        self.assertEqual(parent['__notes_count_by_process__'], {'publish': 3})

    def test_counts_collapse_note_rows_without_losing_null_processes_or_retirement_contract(self):
        with self.store.connection(write=True) as db:
            for index in range(1000):
                self.note(db, 'N%d' % index, process=(None, '', 'publish')[index % 3],
                          s_status='retired' if index % 5 == 0 else None)
        materialized = []
        native_get = Search.get_sobjects
        def get(search, *args, **kwargs):
            values = native_get(search, *args, **kwargs)
            if search.get_base_search_type() == 'sthpw/note':
                materialized.append(len(values))
            return values
        with patch.object(Search, 'get_sobjects', get):
            result = self.query()
        first = next(row for row in result['sobjects_list'] if row.get('code') == 'A')
        self.assertEqual(first['__notes_count__'], 1000)
        self.assertEqual(first['__notes_count_by_process__'], {'publish': 1000})
        self.assertEqual(sum(materialized), 0)

    def test_task_branches_and_task_root_counts_keep_all_group_sizes(self):
        with self.store.connection(write=True) as db:
            for code, context in [('T1', 'publish'), ('T2', 'publish/sub')]:
                db.execute('INSERT INTO task(code,search_type,search_code,process,context,project_code) VALUES(?,?,?,?,?,?)',
                           (code, 'contract/entity?project=one', 'A', 'publish', context, 'one'))
            self.note(db, 'ROOT')
            self.note(db, 'RETIRED_ROOT', s_status='retired')
            for index in range(5):
                self.note(db, 'BRANCH%d' % index, parent='T2', kind='sthpw/task?project=one')
            self.note(db, 'BAD_BRANCH', parent='T2', kind='other/type')
        parent = next(row for row in self.query()['sobjects_list'] if row.get('code') == 'A')
        self.assertEqual(parent['__notes_count__'], 7)
        details = parent['__task_details_by_process__']['publish']
        self.assertEqual({row['code']: row['__notes_count__'] for row in details}, {'T1': 2, 'T2': 5})
        task_rows = self.query('sthpw/task')['sobjects_list']
        self.assertEqual({row['code']: row['__notes_count__'] for row in task_rows}, {'T1': 1, 'T2': 5})

    def test_grouped_counts_preserve_private_note_visibility_and_code_less_parents(self):
        with self.store.connection(write=True) as db:
            db.execute('INSERT INTO login(code,login,password) VALUES(?,?,?)', ('artist', 'artist', hash_password('private-artist-test')))
            rules = '<rules><rule group="project" code="one" access="allow"/><rule group="project" key="one" access="allow"/><rule group="api_cmd" key="tactic.command.PythonCmd" access="allow"/><rule group="search_type" code="*" access="allow"/></rules>'
            db.execute('INSERT INTO login_group(code,login_group,access_rules) VALUES(?,?,?)', ('reader', 'reader', rules))
            db.execute("INSERT INTO login_in_group(code,login,login_group) VALUES('member','artist','reader')")
            self.note(db, 'PUBLIC')
            self.note(db, 'OWN', login='artist', access='private')
            self.note(db, 'OTHER_PRIVATE', login='admin', access='private')
            db.execute("INSERT INTO note(code,search_type,search_id,process,note,login) VALUES('ID_NOTE','contract/entity?project=one',4,'layout','By id','admin')")
        self.ticket = {'ticket': self.api.get_ticket('artist', 'private-artist-test'), 'project': 'one'}
        first = next(row for row in self.query()['sobjects_list'] if row.get('code') == 'A')
        self.assertEqual(first['__notes_count__'], 2)
        by_id = self.query(filters=[('id', 4)])['sobjects_list'][0]
        self.assertEqual(by_id['__notes_count__'], 1)
        raw = "from pyasm.search import Search\ns=Search('sthpw/note')\ns.add_column('COUNT(*)',quoted=False)\nreturn s.get_sobjects()"
        with self.assertRaises(SecurityException):
            self.api.dispatch('execute_python_script', (self.ticket, '', dict(code=raw)))

    def test_native_group_counts_validate_columns_and_keep_normal_count_filters(self):
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.ticket['ticket'])
            search = Search('contract/entity')
            search.add_filter('id', 1)
            search.set_limit(1)
            search.set_offset(100)
            self.assertEqual(search.get_group_counts(['name', 'name']), [('Первый', 1)])
            with self.assertRaises(ValueError):
                search.get_group_counts([])
            for columns in (['COUNT(*)'], ['name; DROP TABLE entity']):
                with self.assertRaises(UnsupportedContract):
                    search.get_group_counts(columns)
            search.set_null_filter()
            self.assertEqual(search.get_group_counts(['name']), [])

    def test_custom_note_getters_keep_their_original_count_behavior(self):
        with self.store.connection(write=True) as db:
            db.execute("UPDATE search_object SET class_name='test_compound_search_performance.NormalizedNote' WHERE search_type='sthpw/note'")
            self.note(db, 'CUSTOM', process='layout')
        parent = next(row for row in self.query()['sobjects_list'] if row.get('code') == 'A')
        self.assertEqual(parent['__notes_count_by_process__'], {'review': 1})
