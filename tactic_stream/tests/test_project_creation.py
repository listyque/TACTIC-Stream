"""One isolated lifecycle check, run unchanged on SQLite and real PostgreSQL."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import uuid
from xml.etree.ElementTree import Element, SubElement, tostring

from pyasm.biz import Project
from pyasm.command import Command
from pyasm.common import Config, Environment
from pyasm.common.errors import SecurityException, UnsupportedContract
from pyasm.search import Search, SearchType, DbContainer, DbResource
from pyasm.search.transaction import PartialCommitException, FileUndo
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from tactic.command import CreateProjectCmd
from tactic_stream.server.api import Api


def exercise(store, prefix):
    api = Api(store)
    token = api.get_ticket('admin', 'project-test-password')
    ticket = dict(ticket=token, project='admin', language='python')
    code = prefix + '_ok'
    result = api.dispatch('execute_cmd', (ticket, 'tactic.command.CreateProjectCmd',
        dict(project_code=code, project_title='Проект', is_main_project=True, project_stype=['asset', code + '/shot'])))
    assert result == dict(status='OK', description='', info={'result': 'Finished creating project [%s].' % code})
    with request_context(RequestContext(store, 'admin', code)):
        api.auth.bind_security('admin', token)
        project = Project.get()
        assert project.get_base_type() == 'simple'
        assert project.get_value('title') == 'Проект'
        assert Project.get_default_project() == code
        resource = project.get_project_db_resource()
        assert resource.get_database() == code
        tables = set(store.tables(resource)) - {'sqlite_sequence'}
        assert {'spt_trigger', 'spt_custom_script', 'spt_naming', 'spt_process_state', 'spt_plugin', 'asset', 'shot'} <= tables
        assert Search(code + '/asset').get_count() == 0
        assert 'pipeline_code' in DbContainer.get(resource).get_column_info('asset')
        # A completed database is not owned by a later creation transaction.
        cmd = Command()
        cmd.execute = lambda: resource.get_database_impl().import_schema(resource, 'simple')
        with unittest.TestCase().assertRaises(UnsupportedContract):
            Command.execute_cmd(cmd)

    for suffix, failure in [('late', ValueError('late project failure')), ('cancel', KeyboardInterrupt())]:
        failed_code = prefix + '_' + suffix
        with request_context(RequestContext(store, 'admin', 'admin')):
            api.auth.bind_security('admin', token)
            cmd = Command()
            def execute():
                cmd.get_transaction().set_sync(False)
                Command.execute_cmd(CreateProjectCmd(project_code=failed_code, project_title='Rollback', project_stype=['asset']))
                Project.set_project(failed_code)
                record = SearchType.create(failed_code + '/asset')
                record.set_value('code', 'ROLLBACK')
                record.commit()
                raise failure
            cmd.execute = execute
            try:
                Command.execute_cmd(cmd)
            except type(failure):
                pass
            else:
                raise AssertionError('Creation failure was swallowed')
            assert Search.get_by_code('sthpw/project', failed_code, show_retired=True) is None
            assert not DbResource.get_default(failed_code).get_database_impl().database_exists(DbResource.get_default(failed_code))
            assert Search.get_by_code('sthpw/search_object', failed_code + '/asset') is None

    # Force failure AFTER the new DB has committed, before publishing sthpw.
    failed_code = prefix + '_commit'
    with request_context(RequestContext(store, 'admin', 'admin')):
        api.auth.bind_security('admin', token)
        system_sql = DbContainer.get('sthpw')
        config_path = Path(Config.get_config_path())
        previous_config = config_path.read_text(encoding='utf-8')
        with patch.object(system_sql, 'commit', side_effect=ValueError('system commit failure')):
            try:
                Command.execute_cmd(CreateProjectCmd(project_code=failed_code, project_title='Rollback', is_main_project=True))
            except ValueError as error:
                assert str(error) == 'system commit failure'
            else:
                raise AssertionError('System commit failure was swallowed')
        assert Project.get_by_code(failed_code) is None
        assert config_path.read_text(encoding='utf-8') == previous_config
        assert Project.get_default_project() == code
        resource = DbResource.get_default(failed_code)
        assert not resource.get_database_impl().database_exists(resource)
        # Retry in the same context catches stale connection/identity caches.
        Command.execute_cmd(CreateProjectCmd(project_code=failed_code, project_title='Retry'))
    for args in [dict(project_code=code, project_title='Duplicate'),
                 dict(project_code=prefix + '_bad', project_theme='legacy'),
                 dict(project_code='../outside')]:
        try:
            api.dispatch('execute_cmd', (ticket, 'tactic.command.CreateProjectCmd', args))
        except Exception:
            pass
        else:
            raise AssertionError('Invalid creation unexpectedly succeeded')
    with request_context(RequestContext(store, 'admin', 'admin')):
        assert Project.get_by_code(code).get_value('title') == 'Проект'
        assert Project.get_by_code(prefix + '_bad') is None
        api.auth.bind_security('admin', token)
        cmd = Command()
        def create_reader():
            cmd.get_transaction().set_sync(False)
            reader = SearchType.create('sthpw/login')
            reader.set_value('code', 'project_reader')
            reader.set_value('login', 'project_reader')
            reader.set_password('reader-project-password')
            reader.commit()
        cmd.execute = create_reader
        Command.execute_cmd(cmd)
    reader_ticket = dict(ticket=api.get_ticket('project_reader', 'reader-project-password'), project='admin', language='python')
    with unittest.TestCase().assertRaises(SecurityException):
        api.dispatch('execute_cmd', (reader_ticket, 'tactic.command.CreateProjectCmd', dict(project_code=prefix + '_deny')))
    # Native writes on independently created databases retain journal/index effects.
    second = prefix + '_other'
    first_ticket = dict(ticket=token, project=code, language='python')
    api.dispatch('create_search_type', (first_ticket, 'contract/project_asset', 'Asset'))
    api.dispatch('execute_cmd', (ticket, 'tactic.command.CreateProjectCmd',
        dict(project_code=second, project_title='Second', project_stype=['contract/project_asset'])))
    for project, title in [(code, 'Первый'), (second, 'Второй')]:
        current = dict(ticket=token, project=project, language='python')
        api.dispatch('add_column_to_search_type', (current, 'contract/project_asset', 'amount', 'integer'))
        api.dispatch('insert', (current, 'contract/project_asset', dict(code='A', name=title, amount=0)))
        api.dispatch('insert', (current, 'contract/project_asset', dict(code='B', name="O'Reilly")))
    writes = []
    with request_context(RequestContext(store, 'admin', code)):
        api.auth.bind_security('admin', token)
        for fail in (True, False):
            command = Command(log_exception=False)
            def write_projects():
                command.get_transaction().set_sync(False)
                for index, project in enumerate((code, second)):
                    obj = Search.get_by_code('contract/project_asset?project=' + project, 'A')
                    obj.set_value('amount', 21 + index)
                    obj.commit()
                if fail:
                    raise ValueError('late project write failure')
            command.execute = write_projects
            if fail:
                with unittest.TestCase().assertRaisesRegex(ValueError, 'late project write failure'):
                    Command.execute_cmd(command)
            else:
                Command.execute_cmd(command)
            for index, project in enumerate((code, second)):
                assert Search.get_by_code('contract/project_asset?project=' + project, 'A').get_value('amount') == (0 if fail else 21 + index)
            writes.append([Search.get_by_code('contract/project_asset?project=' + project, 'A').get_value('amount')
                           for project in (code, second)])
        log = Search('sthpw/transaction_log')
        log.add_order_by('id desc')
        journal = log.get_sobject().get_xml_value('transaction')
        assert journal.get_nodes('transaction/sobject')
        timestamps = Search('sthpw/change_timestamp')
        timestamps.add_filter('search_type', 'contract/project_asset?project=' + code)
        assert timestamps.get_count() > 0
        index = Search('sthpw/sobject_list')
        index.add_filter('search_type', 'contract/project_asset?project=' + code)
        assert index.get_count() > 0

        ddl = Command()
        def failed_ddl():
            ddl.get_transaction().set_sync(False)
            api.add_column_to_search_type(first_ticket, 'contract/project_asset', 'rolled_column', 'integer')
            raise ValueError('project DDL rollback')
        ddl.execute = failed_ddl
        with unittest.TestCase().assertRaisesRegex(ValueError, 'project DDL rollback'):
            Command.execute_cmd(ddl)
        resource = Project.get().get_project_db_resource()
        assert 'rolled_column' not in DbContainer.get(resource).get_column_info('project_asset', use_cache=False)

        # A failure after a committed existing DB must never claim full rollback.
        system_sql = DbContainer.get('sthpw')
        cmd = Command()
        source_file = store.data_dir / 'partial-source.txt'
        source_file.parent.mkdir(parents=True, exist_ok=True)
        source_file.write_text('committed record keeps its file', encoding='utf-8')
        destination = Path(Environment.get_asset_dir()) / 'partial-file.txt'
        assert destination.is_relative_to(store.data_dir)
        def partial_write():
            cmd.get_transaction().set_sync(False)
            obj = Search.get_by_code('contract/project_asset', 'A')
            obj.set_value('amount', 101)
            obj.commit()
            FileUndo.mkdir(str(destination.parent))
            FileUndo.copy(str(source_file), str(destination))
        cmd.execute = partial_write
        with patch.object(system_sql, 'commit', side_effect=ValueError('system commit failure')):
            with unittest.TestCase().assertRaisesRegex(PartialCommitException, 'already committed: ' + code):
                Command.execute_cmd(cmd)
        assert Search.get_by_code('contract/project_asset', 'A').get_value('amount') == 101
        assert destination.read_text(encoding='utf-8') == 'committed record keeps its file'
    return dict(tables=sorted(tables), writes=writes)


class ProjectCreation(unittest.TestCase):
    def test_lifecycle_sqlite_and_optional_postgres(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.dict(os.environ, {'TACTIC_CONFIG_PATH': '', 'TACTIC_TMP_CONFIG_PATH': ''}):
                Config.reload_config()
                store = Store(root / 'sqlite')
                store.initialize(hash_password('project-test-password'))
                config_path = store.data_dir / 'config/tactic-conf.xml'
                config_path.parent.mkdir(parents=True, exist_ok=True)
                config_path.write_text('<config version="2"><install/><custom>retain</custom></config>', encoding='utf-8')
                expected = exercise(store, 'project_contract')
            if not os.environ.get('STREAM_POSTGRES_HOST'):
                return
            import psycopg
            from psycopg import sql
            credentials = dict(host=os.environ['STREAM_POSTGRES_HOST'], port=os.environ.get('STREAM_POSTGRES_PORT', '5432'),
                user=os.environ.get('STREAM_POSTGRES_USER', 'stream'),
                password=Path(os.environ['STREAM_POSTGRES_PASSWORD_FILE']).read_text().strip())
            prefix = 'stream_pr_' + uuid.uuid4().hex[:12]
            database = prefix + '_sys'
            config = Element('config', version='2')
            section = SubElement(config, 'database')
            for key, value in dict(vendor='PostgreSQL', sobject_database=database,
                    password_file=os.environ['STREAM_POSTGRES_PASSWORD_FILE'],
                    **{k: v for k, v in credentials.items() if k != 'password'}).items():
                SubElement(section, key).text = value
            path = root / 'tactic-conf.xml'
            path.write_bytes(tostring(config))
            with psycopg.connect(dbname='postgres', autocommit=True, **credentials) as maintenance:
                try:
                    with patch.dict(os.environ, {'TACTIC_CONFIG_PATH': str(path), 'TACTIC_TMP_CONFIG_PATH': ''}):
                        Config.reload_config()
                        store = Store(root / 'postgres')
                        store.initialize(hash_password('project-test-password'))
                        self.assertEqual(exercise(store, prefix), expected)
                finally:
                    # All names were generated exclusively for this check.
                    for name in [database] + [prefix + '_' + suffix for suffix in ('ok', 'late', 'cancel', 'commit', 'bad', 'other')]:
                        maintenance.execute(sql.SQL('DROP DATABASE IF EXISTS {}').format(sql.Identifier(name)))
                    Config.reload_config()


if __name__ == '__main__':
    unittest.main()
