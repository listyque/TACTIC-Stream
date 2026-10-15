"""Focused real PostgreSQL check for connections, instances, transactional DDL."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid
from xml.etree.ElementTree import Element, SubElement, tostring

from pyasm.common import Config
from pyasm.command import Command
from pyasm.search import Search, DbContainer
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from tactic_stream.server.api import Api


@unittest.skipUnless(os.environ.get('STREAM_POSTGRES_HOST'), 'Real isolated PostgreSQL required')
class SchemaPostgres(unittest.TestCase):
    def test_relationship_record_projection_matches_sqlite(self):
        import psycopg
        from psycopg import sql
        credentials = dict(host=os.environ['STREAM_POSTGRES_HOST'],
                           port=os.environ.get('STREAM_POSTGRES_PORT', '5432'),
                           user=os.environ.get('STREAM_POSTGRES_USER', 'stream'),
                           password=Path(os.environ['STREAM_POSTGRES_PASSWORD_FILE']).read_text().strip(),
                           connect_timeout=5)
        database = 'stream_relation_' + uuid.uuid4().hex
        sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
        import schema_api_contract
        def check(store):
            api = Api(store)
            auth = dict(ticket=api.get_ticket('admin', 'relation-test-password'), project='admin')
            parent_key = 'sthpw/project?code=admin'
            note = api.dispatch('create_note', (auth, parent_key, 'Relationship projection'), {'process': 'publish'})
            parent = api.dispatch('get_parent', (auth, note['__search_key__']), {'columns': ['code']})
            self.assertEqual(parent, {'code': 'admin', '__search_key__': parent_key, '__search_type__': 'sthpw/project'})
            rows = api.dispatch('get_all_children', (auth, parent_key, 'sthpw/note'), {'filters': [['code', note['code']]], 'columns': ['note', 'process', 'missing']})
            self.assertEqual(len(rows), 1)
            self.assertEqual(set(rows[0]), {'note', 'process', 'missing', '__search_key__', '__search_type__'})
            self.assertEqual(rows[0]['__search_key__'], note['__search_key__'])
            self.assertEqual(rows[0]['__search_type__'], 'sthpw/note')
            projected = {name: rows[0][name] for name in ('note', 'process', 'missing')}
            auth['project'] = 'one'
            parent, child = 'contract/schema_asset?project=one&code=ASSET', 'contract/schema_tag?project=one&code=TAG'
            api.dispatch('add_instance', (auth, parent, child))
            rows = api.dispatch('get_all_children', (auth, parent, 'contract/schema_tag'), {'columns': ['code']})
            self.assertEqual([row['code'] for row in rows], ['TAG'])
            self.assertEqual(set(rows[0]), {'code', '__search_key__', '__search_type__'})
            rows = api.dispatch('get_all_children', (auth, child, 'contract/schema_asset'), {'columns': ['code']})
            self.assertEqual([row['code'] for row in rows], ['ASSET'])
            other = api.dispatch('insert', (auth, 'contract/schema_asset', {'code': 'OTHER', 'name': 'Other asset'}))
            api.dispatch('add_instance', (auth, other['__search_key__'], child))
            with request_context(RequestContext(store, 'admin', 'one')):
                api.auth.bind_security('admin', auth['ticket'])
                for source_type, target_type, identity, expected in (
                    ('schema_asset', 'schema_tag', 'ASSET', ['TAG']),
                    ('schema_tag', 'schema_asset', 'TAG', ['ASSET', 'OTHER']),
                ):
                    source = Search.get_by_code('contract/' + source_type, identity)
                    result = Search('contract/' + target_type)
                    result.add_relationship_filters([source])
                    self.assertEqual([obj.get_code() for obj in result.get_sobjects()], expected)
                    self.assertEqual(result.get_sobject_codes(), expected)
                    self.assertEqual(result.get_sobject_ids(), [1] if target_type == 'schema_tag' else [1, 2])
                    self.assertEqual(result.get_sobject_codes(), expected)
                    grouped = Search.get_related_by_sobjects([source], 'contract/' + target_type)
                    self.assertEqual([obj.get_code() for obj in grouped[source.get_search_key()]], expected)
                    selected = Search('contract/' + source_type)
                    selected.add_column('name', as_column='code')
                    selected.add_filter('code', identity)
                    result = Search('contract/' + target_type)
                    result.add_relationship_search_filter(selected)
                    self.assertEqual([obj.get_code() for obj in result.get_sobjects()], expected)
                    self.assertEqual(result.get_sobject_codes(), expected)
                    self.assertEqual(result.get_sobject_ids(), [1] if target_type == 'schema_tag' else [1, 2])
                selected = Search('contract/schema_asset')
                selected.add_column('name', as_column='code')
                selected.add_column('code', as_column='id')
                selected.add_filter('code', 'ASSET')
                self.assertEqual(selected.get_sobject_codes(), ['ASSET'])
                self.assertEqual(selected.get_sobject_ids(), [1])
                selected = Search('contract/schema_asset')
                selected.add_column('name')
                selected.add_order_by('id desc')
                selected.set_limit(1)
                self.assertEqual(selected.get_sobject_codes(), ['OTHER'])
                self.assertEqual(selected.get_sobject_ids(), [2])
                selected = Search('contract/schema_asset')
                selected.add_filter('code', 'ASSET')
                result = Search('contract/schema_tag')
                result.add_relationship_search_filter(selected, op='not in')
                self.assertEqual([obj.get_value('_related_code') for obj in result.get_sobjects()], ['OTHER'])
            api.dispatch('remove_instance', (auth, other['__search_key__'], child))
            api.dispatch('remove_instance', (auth, parent, child))
            self.assertEqual(api.dispatch('get_all_children', (auth, parent, 'contract/schema_tag')), [])
            from test_search_self_instances import self_instance_fixture
            if store.get_db_resource().get_vendor() == 'PostgreSQL':
                with psycopg.connect(dbname=database, row_factory=psycopg.rows.dict_row, **credentials) as db:
                    with db.cursor() as cursor:
                        self_instance_fixture(store, projects=('one',), database_connection=cursor)
            else:
                self_instance_fixture(store, projects=('one',))
            with request_context(RequestContext(store, 'admin', 'one')):
                api.auth.bind_security('admin', auth['ticket'])
                owner = Search.get_by_code('contract/node', 'A')
                child = Search.get_by_code('contract/node', 'B')
                for source, path, expected in ((owner, None, ['A', 'B', 'B']), (child, 'child', ['A', 'A', 'E'])):
                    result = Search('contract/node')
                    result.add_relationship_filter(source, path=path)
                    self.assertEqual(result.get_sobject_codes(), expected)
                    grouped = Search.get_related_by_sobjects([source], 'contract/node', path=path)
                    self.assertEqual([obj.get_code() for obj in grouped[source.get_search_key()]], expected)
                selected = Search('contract/node')
                selected.add_column('name', as_column='code')
                selected.add_filter('code', 'B')
                result = Search('contract/node')
                result.add_relationship_search_filter(selected, path='child')
                self.assertEqual(result.get_sobject_codes(), ['A', 'A', 'E'])
                result = Search('contract/node')
                result.add_relationship_filter(owner)
                result.add_relationship_filter(child, path='child')
                self.assertEqual(result.get_sobject_codes(), ['A', 'A'])
                restored = Search('contract/node')
                restored.get_select().loads(result.get_select().dumps())
                self.assertEqual(restored.get_sobject_ids(), [1, 1])
            rows = api.dispatch('get_all_children', (auth, 'contract/node?project=one&code=A', 'contract/node'), {'columns': ['name']})
            self.assertEqual([row['name'] for row in rows], ['Owner one', 'Child', 'Child'])
            from test_self_instance_writes import cases as write_cases
            from tools.snapshot_probe import run_snapshot_case
            self_writes = []
            for case in write_cases():
                with request_context(RequestContext(store, 'admin', 'one')):
                    api.auth.bind_security('admin', auth['ticket'])
                    self_writes.append(run_snapshot_case(case))
            owner, member = 'contract/node?project=one&code=D', 'contract/node?project=one&code=E'
            first = api.dispatch('add_instance', (auth, owner, member))
            self.assertEqual((first['parent_code'], first['child_code']), ('D', 'E'))
            reverse = api.dispatch('add_instance', (auth, member, owner))
            api.dispatch('add_instance', (auth, owner, member))
            api.dispatch('remove_instance', (auth, owner, member))
            self.assertEqual([row['code'] for row in api.dispatch('get_instances', (auth, owner, 'contract/node'))], ['N6'])
            self.assertEqual(api.dispatch('get_by_search_key', (auth, reverse['__search_key__']))['child_code'], 'D')
            api.dispatch('remove_instance', (auth, member, owner))
            api.dispatch('add_instance', (auth, owner, owner))
            api.dispatch('remove_instance', (auth, owner, owner))
            self.assertEqual([row['code'] for row in api.dispatch('get_instances', (auth, owner, 'contract/node'))], ['N6'])
            from test_project_writes import committed_project_writes
            ordinary_writes = committed_project_writes(store)
            return dict(projection=projected, self_writes=self_writes, ordinary_writes=ordinary_writes)
        with tempfile.TemporaryDirectory(prefix='relationship-projection-') as directory, psycopg.connect(dbname='postgres', autocommit=True, **credentials) as maintenance:
            root = Path(directory)
            with patch.dict(os.environ, {'TACTIC_CONFIG_PATH': '', 'TACTIC_TMP_CONFIG_PATH': ''}):
                Config.reload_config()
                store = Store(root / 'sqlite')
                store.initialize(hash_password('relation-test-password'))
                with store.connection(write=True) as db:
                    db.execute("INSERT INTO project(code,title) VALUES ('one','Instance contract')")
                    schema_api_contract.install_fixture(db)
                expected = check(store)
            config = Element('config', version='2')
            section = SubElement(config, 'database')
            for key, value in dict(vendor='PostgreSQL', sobject_database=database,
                password_file=os.environ['STREAM_POSTGRES_PASSWORD_FILE'],
                **{k: v for k, v in credentials.items() if k not in ('password', 'connect_timeout')}).items():
                SubElement(section, key).text = value
            path = root / 'tactic-conf.xml'
            path.write_bytes(tostring(config))
            try:
                with patch.dict(os.environ, {'TACTIC_CONFIG_PATH': str(path), 'TACTIC_TMP_CONFIG_PATH': ''}):
                    Config.reload_config()
                    store = Store(root / 'postgres')
                    store.initialize(hash_password('relation-test-password'))
                    with psycopg.connect(dbname=database, **credentials) as db:
                        db.execute("INSERT INTO project(code,title) VALUES ('one','Instance contract')")
                        schema_api_contract.install_fixture(db, 'serial PRIMARY KEY')
                        db.execute("SELECT setval(pg_get_serial_sequence('schema_asset', 'id'), 1)")
                    self.assertEqual(check(store), expected)
            finally:
                maintenance.execute(sql.SQL('DROP DATABASE IF EXISTS {} WITH (FORCE)').format(sql.Identifier(database)))
                Config.reload_config()

    def test_schema_deletion_matches_sqlite(self):
        import psycopg
        from psycopg import sql
        from test_schema_delete import exercise_deletion
        credentials = dict(host=os.environ['STREAM_POSTGRES_HOST'],
                           port=os.environ.get('STREAM_POSTGRES_PORT', '5432'),
                           user=os.environ.get('STREAM_POSTGRES_USER', 'stream'),
                           password=Path(os.environ['STREAM_POSTGRES_PASSWORD_FILE']).read_text().strip())
        database = 'stream_drop_' + uuid.uuid4().hex
        project = 'drop_' + uuid.uuid4().hex[:20]
        def check(store):
            api = Api(store)
            auth = dict(ticket=api.get_ticket('admin', 'delete-test-password'), project='admin', language='python')
            api.dispatch('execute_cmd', (auth, 'tactic.command.CreateProjectCmd',
                {'project_code': project, 'project_title': 'Isolated deletion contract'}))
            auth['project'] = project
            return exercise_deletion(lambda method, *args: api.dispatch(method, (auth, *args)), project)
        with tempfile.TemporaryDirectory() as directory, psycopg.connect(dbname='postgres', autocommit=True, **credentials) as maintenance:
            root = Path(directory)
            with patch.dict(os.environ, {'TACTIC_CONFIG_PATH': '', 'TACTIC_TMP_CONFIG_PATH': ''}):
                Config.reload_config()
                store = Store(root / 'sqlite')
                store.initialize(hash_password('delete-test-password'))
                expected = check(store)
            config = Element('config', version='2')
            section = SubElement(config, 'database')
            for key, value in dict(vendor='PostgreSQL', sobject_database=database,
                password_file=os.environ['STREAM_POSTGRES_PASSWORD_FILE'],
                **{k: v for k, v in credentials.items() if k != 'password'}).items():
                SubElement(section, key).text = value
            path = root / 'tactic-conf.xml'
            path.write_bytes(tostring(config))
            try:
                with patch.dict(os.environ, {'TACTIC_CONFIG_PATH': str(path), 'TACTIC_TMP_CONFIG_PATH': ''}):
                    Config.reload_config()
                    store = Store(root / 'postgres')
                    store.initialize(hash_password('delete-test-password'))
                    self.assertEqual(check(store), expected)
            finally:
                for name in (project, database):
                    maintenance.execute(sql.SQL('DROP DATABASE IF EXISTS {} WITH (FORCE)').format(sql.Identifier(name)))
                Config.reload_config()

    def test_widget_authoring_matches_sqlite(self):
        import psycopg
        from psycopg import sql
        from test_widget_authoring import exercise_authoring
        from test_widget_preview import exercise_preview
        credentials = dict(host=os.environ['STREAM_POSTGRES_HOST'],
                           port=os.environ.get('STREAM_POSTGRES_PORT', '5432'),
                           user=os.environ.get('STREAM_POSTGRES_USER', 'stream'),
                           password=Path(os.environ['STREAM_POSTGRES_PASSWORD_FILE']).read_text().strip())
        database = 'stream_authoring_' + uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as directory, psycopg.connect(dbname='postgres', autocommit=True, **credentials) as maintenance:
            root = Path(directory)
            with patch.dict(os.environ, {'TACTIC_CONFIG_PATH': '', 'TACTIC_TMP_CONFIG_PATH': ''}):
                Config.reload_config()
                store = Store(root / 'sqlite')
                store.initialize(hash_password('authoring-password'))
                expected = exercise_authoring(store, 'authoring-password')
                preview_expected = exercise_preview(store, 'authoring-password')
            config = Element('config', version='2')
            section = SubElement(config, 'database')
            for key, value in dict(vendor='PostgreSQL', sobject_database=database,
                password_file=os.environ['STREAM_POSTGRES_PASSWORD_FILE'],
                **{k: v for k, v in credentials.items() if k != 'password'}).items():
                SubElement(section, key).text = value
            path = root / 'tactic-conf.xml'
            path.write_bytes(tostring(config))
            try:
                with patch.dict(os.environ, {'TACTIC_CONFIG_PATH': str(path), 'TACTIC_TMP_CONFIG_PATH': ''}):
                    Config.reload_config()
                    store = Store(root / 'postgres')
                    store.initialize(hash_password('authoring-password'))
                    self.assertEqual(exercise_authoring(store, 'authoring-password'), expected)
                    self.assertEqual(exercise_preview(store, 'authoring-password'), preview_expected)
            finally:
                maintenance.execute(sql.SQL('DROP DATABASE IF EXISTS {} WITH (FORCE)').format(sql.Identifier(database)))
                Config.reload_config()

    def test_calendar_forms_match_sqlite(self):
        import psycopg
        from psycopg import sql
        sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
        import calendar_form_contract
        import workflow_form_contract
        import upload_form_contract
        import compound_form_contract
        from tactic_stream.server.interface import read_form
        credentials = dict(host=os.environ['STREAM_POSTGRES_HOST'],
                           port=os.environ.get('STREAM_POSTGRES_PORT', '5432'),
                           user=os.environ.get('STREAM_POSTGRES_USER', 'stream'),
                           password=Path(os.environ['STREAM_POSTGRES_PASSWORD_FILE']).read_text().strip())
        database = 'stream_calendar_' + uuid.uuid4().hex
        def check(store):
            with request_context(RequestContext(store, 'admin', 'one')):
                result = calendar_form_contract.run({'operation': 'edit'})
            with request_context(RequestContext(store, 'admin', 'one')):
                workflow = workflow_form_contract.run({'operation': 'edit'})
            api = Api(store)
            token = api.get_ticket('admin', 'calendar-test-password')
            with request_context(RequestContext(store, 'admin', 'one')):
                api.auth.bind_security('admin', token)
                form = read_form('contract/calendar_entity', 'calendar_test', 'contract/calendar_entity?project=one&code=C')
                inputs = [field['input'] for field in form['fields'] if 'input' in field]
                self.assertEqual(inputs[0]['value'], '2026-11-02T10:30:15.25')
                self.assertEqual(inputs[0]['timezone'], 'Asia/Tokyo')
                self.assertEqual(inputs[1]['value'], '2026-11-05')
                task = read_form('contract/work_task', 'workflow_form_test', 'contract/work_task?project=one&code=TASK')
                assigned = next(field for field in task['fields'] if field['name'] == 'assigned')
                self.assertEqual(assigned['input']['type'], 'select')
                self.assertEqual(assigned['choices'], ['', 'alice'])
            with request_context(RequestContext(store, 'admin', 'one')):
                api.auth.bind_security('admin', token)
                uploaded = upload_form_contract.run({'operation': 'revision'})
                multi = upload_form_contract.run({'operation': 'multi_revision'})
                rich = upload_form_contract.run({'operation': 'rich_subcontext'})
                times = compound_form_contract.run({'operation': 'time_actions'})
                clock = compound_form_contract.run({'operation': 'time_only'})
                zipped = compound_form_contract.run({'operation': 'zip_handoff'})
                from pyasm.search import Search
                obj = Search.get_by_search_key(compound_form_contract.KEY)
                self.assertEqual(obj.get_sobject_dict(mode='fast')['clock'], '06:45:00')
            return dict(calendar=result, workflow=workflow, uploaded=uploaded, multi=multi, rich=rich, times=times, clock=clock, zipped=zipped)
        with tempfile.TemporaryDirectory() as directory, psycopg.connect(dbname='postgres', autocommit=True, **credentials) as maintenance:
            root = Path(directory)
            with patch.dict(os.environ, {'TACTIC_CONFIG_PATH': '', 'TACTIC_TMP_CONFIG_PATH': ''}):
                Config.reload_config()
                sqlite = Store(root / 'sqlite')
                sqlite.initialize(hash_password('calendar-test-password'))
                with sqlite.connection(write=True) as db:
                    db.execute("INSERT INTO project (code,title) VALUES ('one','One')")
                    calendar_form_contract.install_fixture(db)
                    workflow_form_contract.install_fixture(db)
                    upload_form_contract.install_fixture(db)
                    compound_form_contract.install_fixture(db)
                expected = check(sqlite)
            config = Element('config', version='2')
            section = SubElement(config, 'database')
            for key, value in dict(vendor='PostgreSQL', sobject_database=database,
                                   password_file=os.environ['STREAM_POSTGRES_PASSWORD_FILE'],
                                   **{k: v for k, v in credentials.items() if k != 'password'}).items():
                SubElement(section, key).text = value
            path = root / 'tactic-conf.xml'
            path.write_bytes(tostring(config))
            try:
                with patch.dict(os.environ, {'TACTIC_CONFIG_PATH': str(path), 'TACTIC_TMP_CONFIG_PATH': ''}):
                    Config.reload_config()
                    store = Store(root / 'postgres')
                    store.initialize(hash_password('calendar-test-password'))
                    with psycopg.connect(dbname=database, **credentials) as db:
                        db.execute("INSERT INTO project (code,title) VALUES ('one','One')")
                        calendar_form_contract.install_fixture(db, 'serial PRIMARY KEY')
                        workflow_form_contract.install_fixture(db, 'serial PRIMARY KEY', '%s')
                        upload_form_contract.install_fixture(db)
                        compound_form_contract.install_fixture(db)
                    self.assertEqual(check(store), expected)
            finally:
                maintenance.execute(sql.SQL('DROP DATABASE IF EXISTS {} WITH (FORCE)').format(sql.Identifier(database)))
                Config.reload_config()

    def test_schema_connections_instances_and_ddl_match_sqlite(self):
        import psycopg
        from psycopg import sql
        sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
        import schema_api_contract
        import schema_edit_contract
        import schema_template_contract
        import edit_form_contract
        import search_join_contract
        import metadata_checkin_contract
        import handoff_contract
        import command_listener_contract
        import ingestion_contract
        import directory_contract
        import workflow_nodes_contract
        import dependency_contract
        import process_commands_contract
        import pipeline_versions_contract
        import same_object_contract
        import process_delete_contract
        import process_type_contract
        import workflow_packages_contract
        import task_schedule_contract
        import task_status_contract
        import collection_contract
        import collection_commands_contract
        from test_metadata_checkin import indexed_checks
        from test_search_joins import EXPECTED as join_results
        credentials = dict(host=os.environ['STREAM_POSTGRES_HOST'],
                           port=os.environ.get('STREAM_POSTGRES_PORT', '5432'),
                           user=os.environ.get('STREAM_POSTGRES_USER', 'stream'),
                           password=Path(os.environ['STREAM_POSTGRES_PASSWORD_FILE']).read_text().strip())
        database = 'stream_schema_' + uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as directory, psycopg.connect(dbname='postgres', autocommit=True, **credentials) as maintenance:
            root = Path(directory)
            sqlite = Store(root / 'sqlite')
            with patch.dict(os.environ, {'TACTIC_CONFIG_PATH': '', 'TACTIC_TMP_CONFIG_PATH': ''}):
                Config.reload_config()
                sqlite.initialize(hash_password('schema-test-password'))
                with sqlite.connection(write=True) as db:
                    db.execute("INSERT INTO project (code,title) VALUES ('one','One')")
                    schema_api_contract.install_fixture(db)
                    schema_edit_contract.install_fixture(db)
                    schema_template_contract.install_fixture(db)
                    edit_form_contract.install_fixture(db)
                    search_join_contract.install_fixture(db)
                    command_listener_contract.install_fixture(db)
                    workflow_nodes_contract.install_fixture(db)
                    dependency_contract.install_fixture(db)
                    task_schedule_contract.install_fixture(db)
                    same_object_contract.install_fixture(db)
                    collection_contract.install_fixture(db)
                with request_context(RequestContext(sqlite, 'admin', 'one')):
                    collection_expected = collection_contract.run({'keywords': True})
                    collection_commands_expected = [collection_commands_contract.run({'operation': mode})
                                                    for mode in ('lifecycle', 'batch_cycle')]
                with request_context(RequestContext(sqlite, 'admin', 'one')):
                    with self.assertRaisesRegex(ValueError, 'late template failure'):
                        schema_template_contract.run({'fail': True})
                    self.assertNotIn('tmpl_copy', sqlite.tables('sthpw'))
                    template_expected = [schema_template_contract.run({'operation': mode}) for mode in ('copy', 'pipeline', 'pipeline_escaped', 'views', 'views_no_format')]
                    forms_expected = [edit_form_contract.run({'operation': mode}) for mode in ('metadata', 'edit')]
                    schema_edit_expected = [schema_edit_contract.run({'operation': mode}) for mode in ('code', 'id', 'cache', 'save', 'creator')]
                    expected = schema_api_contract.run({})
                    for operation, result in join_results.items():
                        self.assertEqual(search_join_contract.run(dict(operation=operation)), result, operation)
                with request_context(RequestContext(sqlite, 'admin', 'admin')):
                    metadata_expected = metadata_checkin_contract.run({'hook': True})
                indexed_checks(sqlite, 'schema-test-password')
                with request_context(RequestContext(sqlite, 'admin', 'admin')):
                    handoff_expected = handoff_contract.run({})
                with request_context(RequestContext(sqlite, 'admin', 'admin')):
                    listener_expected = command_listener_contract.run({})
                with request_context(RequestContext(sqlite, 'admin', 'admin')):
                    ingestion_expected = ingestion_contract.run({})
                    import_expected = ingestion_contract.import_files()
                with request_context(RequestContext(sqlite, 'admin', 'admin')):
                    directory_expected = directory_contract.run({})
                    directory_ingest_expected = directory_contract.ingest()
                workflow_expected = {}
                for code in workflow_nodes_contract.CASES:
                    with request_context(RequestContext(sqlite, 'admin', 'admin')):
                        workflow_expected[code] = workflow_nodes_contract.run({'graph': code})
                dependency_expected = {}
                for code in dependency_contract.CASES:
                    with request_context(RequestContext(sqlite, 'admin', 'one')):
                        dependency_expected[code] = dependency_contract.run({'graph': code})
                process_expected = {}
                for code in process_commands_contract.CASES:
                    with request_context(RequestContext(sqlite, 'admin', 'one')):
                        process_expected[code] = process_commands_contract.run({'graph': code})
                with request_context(RequestContext(sqlite, 'admin', 'one')):
                    packages_expected = workflow_packages_contract.run({})
                with request_context(RequestContext(sqlite, 'admin', 'one')):
                    type_expected = process_type_contract.run({})
                with request_context(RequestContext(sqlite, 'admin', 'one')):
                    delete_expected = process_delete_contract.run({})
                with request_context(RequestContext(sqlite, 'admin', 'one')):
                    same_expected = same_object_contract.run({})
                    same_middle_expected = same_object_contract.finish('SAME_ALT1::work')
                    same_second_expected = same_object_contract.finish('SAME_ALT2::work')
                    same_final_expected = same_object_contract.finish('work')
                with request_context(RequestContext(sqlite, 'admin', 'one')):
                    versions_expected = pipeline_versions_contract.run({})
                    version_lifecycle_expected = pipeline_versions_contract.native_lifecycle()
                    templates_expected = pipeline_versions_contract.templates()
                schedule_expected = {}
                for mode in task_schedule_contract.CASES:
                    with request_context(RequestContext(sqlite, 'admin', 'one')):
                        schedule_expected[mode] = task_schedule_contract.run({'operation': mode})
                status_expected = {}
                for mode in task_status_contract.CASES:
                    with request_context(RequestContext(sqlite, 'admin', 'one')):
                        status_expected[mode] = task_status_contract.run({'operation': mode})
            config = Element('config', version='2')
            section = SubElement(config, 'database')
            for key, value in dict(vendor='PostgreSQL', sobject_database=database,
                                   password_file=os.environ['STREAM_POSTGRES_PASSWORD_FILE'],
                                   **{k: v for k, v in credentials.items() if k != 'password'}).items():
                SubElement(section, key).text = value
            path = root / 'tactic-conf.xml'
            path.write_bytes(tostring(config))
            try:
                with patch.dict(os.environ, {'TACTIC_CONFIG_PATH': str(path), 'TACTIC_TMP_CONFIG_PATH': ''}):
                    Config.reload_config()
                    store = Store(root / 'postgres')
                    store.initialize(hash_password('schema-test-password'))
                    with psycopg.connect(dbname=database, **credentials) as db:
                        db.execute("INSERT INTO project (code,title) VALUES ('one','One')")
                        schema_api_contract.install_fixture(db, 'serial PRIMARY KEY')
                        schema_edit_contract.install_fixture(db, 'serial PRIMARY KEY')
                        schema_template_contract.install_fixture(db, 'serial PRIMARY KEY')
                        edit_form_contract.install_fixture(db, 'serial PRIMARY KEY')
                        search_join_contract.install_fixture(db, 'serial PRIMARY KEY')
                        command_listener_contract.install_fixture(db, 'serial PRIMARY KEY')
                        workflow_nodes_contract.install_fixture(db)
                        dependency_contract.install_fixture(db, id_definition='serial PRIMARY KEY')
                        task_schedule_contract.install_fixture(db)
                        same_object_contract.install_fixture(db)
                        collection_contract.install_fixture(db, 'serial PRIMARY KEY')
                    with request_context(RequestContext(store, 'admin', 'one')):
                        self.assertEqual(collection_contract.run({'keywords': True}), collection_expected)
                        self.assertEqual([collection_commands_contract.run({'operation': mode})
                                          for mode in ('lifecycle', 'batch_cycle')], collection_commands_expected)
                    with request_context(RequestContext(store, 'admin', 'one')):
                        with self.assertRaisesRegex(ValueError, 'late template failure'):
                            schema_template_contract.run({'fail': True})
                        self.assertNotIn('tmpl_copy', store.tables('sthpw'))
                        self.assertEqual([schema_template_contract.run({'operation': mode}) for mode in ('copy', 'pipeline', 'pipeline_escaped', 'views', 'views_no_format')], template_expected)
                        self.assertEqual([edit_form_contract.run({'operation': mode}) for mode in ('metadata', 'edit')], forms_expected)
                        self.assertEqual([schema_edit_contract.run({'operation': mode}) for mode in ('code', 'id', 'cache', 'save', 'creator')], schema_edit_expected)
                        self.assertEqual(schema_api_contract.run({}), expected)
                        for operation, result in join_results.items():
                            self.assertEqual(search_join_contract.run(dict(operation=operation)), result, operation)
                    with request_context(RequestContext(store, 'admin', 'admin')):
                        self.assertEqual(metadata_checkin_contract.run({'hook': True}), metadata_expected)
                    indexed_checks(store, 'schema-test-password')
                    with request_context(RequestContext(store, 'admin', 'admin')):
                        self.assertEqual(handoff_contract.run({}), handoff_expected)
                    with request_context(RequestContext(store, 'admin', 'admin')):
                        self.assertEqual(command_listener_contract.run({}), listener_expected)
                    with request_context(RequestContext(store, 'admin', 'admin')):
                        self.assertEqual(ingestion_contract.run({}), ingestion_expected)
                        self.assertEqual(ingestion_contract.import_files(), import_expected)
                    with request_context(RequestContext(store, 'admin', 'admin')):
                        self.assertEqual(directory_contract.run({}), directory_expected)
                        self.assertEqual(directory_contract.ingest(), directory_ingest_expected)
                    for code in workflow_nodes_contract.CASES:
                        with request_context(RequestContext(store, 'admin', 'admin')):
                            self.assertEqual(workflow_nodes_contract.run({'graph': code}), workflow_expected[code], code)
                    for code in dependency_contract.CASES:
                        with request_context(RequestContext(store, 'admin', 'one')):
                            self.assertEqual(dependency_contract.run({'graph': code}), dependency_expected[code], code)
                    from test_workflow_dependencies import concurrent_waiters
                    self.assertEqual(concurrent_waiters(store, 'schema-test-password'), ['complete', 'complete'])
                    for code in process_commands_contract.CASES:
                        with request_context(RequestContext(store, 'admin', 'one')):
                            self.assertEqual(process_commands_contract.run({'graph': code}), process_expected[code], code)
                    with request_context(RequestContext(store, 'admin', 'one')):
                        self.assertEqual(workflow_packages_contract.run({}), packages_expected)
                    with request_context(RequestContext(store, 'admin', 'one')):
                        self.assertEqual(process_type_contract.run({}), type_expected)
                    with request_context(RequestContext(store, 'admin', 'one')):
                        self.assertEqual(process_delete_contract.run({}), delete_expected)
                    with request_context(RequestContext(store, 'admin', 'one')):
                        self.assertEqual(same_object_contract.run({}), same_expected)
                        self.assertEqual(same_object_contract.finish('SAME_ALT1::work'), same_middle_expected)
                        self.assertEqual(same_object_contract.finish('SAME_ALT2::work'), same_second_expected)
                        self.assertEqual(same_object_contract.finish('work'), same_final_expected)
                    with request_context(RequestContext(store, 'admin', 'one')):
                        self.assertEqual(pipeline_versions_contract.run({}), versions_expected)
                        self.assertEqual(pipeline_versions_contract.native_lifecycle(), version_lifecycle_expected)
                        self.assertEqual(pipeline_versions_contract.templates(), templates_expected)
                    from test_pipeline_versions import concurrent_versions
                    self.assertEqual(concurrent_versions(store, 'schema-test-password'), [3, 4])
                    for mode in task_schedule_contract.CASES:
                        with request_context(RequestContext(store, 'admin', 'one')):
                            self.assertEqual(task_schedule_contract.run({'operation': mode}), schedule_expected[mode], mode)
                    for mode in task_status_contract.CASES:
                        with request_context(RequestContext(store, 'admin', 'one')):
                            self.assertEqual(task_status_contract.run({'operation': mode}), status_expected[mode], mode)
                    api = Api(store)
                    token = api.get_ticket('admin', 'schema-test-password')
                    ticket = {'ticket': token, 'project': 'one', 'language': 'python'}
                    created = api.dispatch('create_search_type', (ticket, 'contract/pg_created', 'PG Type', 'Описание', True))
                    self.assertEqual(created['database'], '{project}')
                    self.assertTrue(api.dispatch('add_column_to_search_type', (ticket, 'contract/pg_created', 'extra', 'varchar(80)')))
                    self.assertFalse(api.dispatch('add_column_to_search_type', (ticket, 'contract/pg_created', 'extra', 'varchar(80)')))
                    record = api.dispatch('insert', (ticket, 'contract/pg_created', {'code': 'PG_CREATED', 'extra': 'Тест'}))
                    self.assertEqual(record['extra'], 'Тест')
                    with request_context(RequestContext(store, 'admin', 'one')):
                        api.auth.bind_security('admin', token)
                        kinds = ('sthpw/search_object', 'sthpw/schema', 'config/naming', 'sthpw/sobject_list',
                                 'sthpw/transaction_log', 'sthpw/sobject_log', 'sthpw/change_timestamp')
                        before = [Search(kind).get_count() for kind in kinds]
                        command = Command()
                        def execute():
                            api.create_search_type(ticket, 'contract/pg_rolled', 'Rolled')
                            api.insert(ticket, 'contract/pg_rolled', {'code': 'ROLLBACK'})
                            api.add_column_to_search_type(ticket, 'contract/pg_rolled', 'late', 'integer')
                            raise ValueError('late PG DDL failure')
                        command.execute = execute
                        with self.assertRaisesRegex(ValueError, 'late PG DDL failure'):
                            Command.execute_cmd(command)
                        self.assertEqual([Search(kind).get_count() for kind in kinds], before)
                        self.assertNotIn('pg_rolled', store.tables(store.get_db_resource()))
                        self.assertNotIn('pg_rolled', DbContainer.get('sthpw').get_database_impl().get_table_info(store.get_db_resource()))
                    self.assertEqual(api.dispatch('get_by_search_key', (ticket, record['__search_key__']))['extra'], 'Тест')
                    self.assertFalse(store.upgrade())
            finally:
                maintenance.execute(sql.SQL('DROP DATABASE IF EXISTS {} WITH (FORCE)').format(sql.Identifier(database)))
                Config.reload_config()


if __name__ == '__main__':
    unittest.main(verbosity=2)
