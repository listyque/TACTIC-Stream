"""First-run paths preserve owned data and expose native Environment accessors."""
import os
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pyasm.common import Config, Environment, EnvironmentException
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from tactic.startup import FirstRunInit


class DataDirectories(unittest.TestCase):
    def test_incomplete_config_upgrade_preserves_user_values(self):
        from pyasm.common.config import initialize_config
        import xml.etree.ElementTree as ET
        with tempfile.TemporaryDirectory() as temporary:
            data = Path(temporary)
            path = data / 'config/tactic-conf.xml'
            path.parent.mkdir()
            for text in (
                    '<config version="2"><database><vendor>PostgreSQL</vendor></database><!--keep--><checkin><asset_base_dir>X:/repo</asset_base_dir><web_base_dir>/media</web_base_dir><win32_client_repo_dir>Z:/client</win32_client_repo_dir></checkin></config>',
                    '<config><database vendor="PostgreSQL"/><checkin asset_base_dir="X:/repo" web_base_dir="/media" win32_client_repo_dir="Z:/client"/></config>'):
                path.write_text(text, encoding='utf-8')
                initialize_config(data)
                root = ET.fromstring(path.read_text(encoding='utf-8'))
                checkin = root.find('checkin')
                values = {node.tag: node.text or '' for node in checkin} if root.get('version') else checkin.attrib
                self.assertEqual(values['asset_base_dir'], 'X:/repo')
                self.assertEqual(values['web_base_dir'], '/media')
                self.assertEqual(values['win32_client_repo_dir'], 'Z:/client')
                self.assertEqual(values['win32_local_base_dir'], 'C:/spt')
                self.assertIn('linux_client_handoff_dir', values)
                before = path.read_bytes()
                initialize_config(data)
                self.assertEqual(path.read_bytes(), before)
                if root.get('version'):
                    self.assertIn('<!--keep-->', path.read_text(encoding='utf-8'))

    def test_first_run_paths_overrides_and_existing_data(self):
        previous_path = sys.path.copy()
        self.addCleanup(lambda: sys.path.__setitem__(slice(None), previous_path))
        with tempfile.TemporaryDirectory() as temporary:
            data = Path(temporary)
            with patch.dict(os.environ, {'TACTIC_DATA_DIR': str(data), 'TACTIC_CONFIG_PATH': '', 'TACTIC_TMP_CONFIG_PATH': ''}):
                FirstRunInit().execute()
                for name in ('config', 'db', 'assets', 'plugins', 'templates', 'dist', 'temp/log'):
                    self.assertTrue((data / name).is_dir(), name)
                self.assertFalse((data / 'db/sthpw.db').exists())
                config = (data / 'config/tactic-conf.xml').read_bytes()
                marker = data / 'assets/keep.txt'
                marker.write_text('keep', encoding='utf-8')
                FirstRunInit().execute()
                self.assertEqual((data / 'config/tactic-conf.xml').read_bytes(), config)
                self.assertEqual(marker.read_text(), 'keep')
                with request_context(RequestContext(Store(data), 'admin')):
                    from tactic_stream.server.api import Api
                    bases = Api(Store(data)).get_base_dirs({'project': 'admin'})
                    self.assertEqual(bases['asset_base_dir'], (data / 'assets').as_posix())
                    self.assertEqual(bases['web_base_dir'], '/assets')
                    for platform in ('win32', 'linux'):
                        for name in ('sandbox_dir', 'client_repo_dir', 'local_base_dir', 'client_handoff_dir', 'server_handoff_dir'):
                            self.assertIn(platform + '_' + name, bases)
                    self.assertEqual(Environment.get_data_dir(), data.as_posix())
                    self.assertEqual(Environment.get_plugin_dir(), (data / 'plugins').as_posix())
                    self.assertEqual(Environment.get_template_dir(), (data / 'templates').as_posix())
                    self.assertEqual(Environment.get_dist_dir(), (data / 'dist').as_posix())
                    Config.set_value('install', 'tmp_dir', 'scratch')
                    Config.set_value('install', 'plugin_dir', 'extensions')
                    Config.set_value('checkin', 'asset_base_dir', {'default': 'repo', 'archive': 'archive'})
                    Config.set_value('checkin', 'base_dir_alias', {'archive': 'other'})
                    (data / 'config/tactic-conf.xml').write_text(Config.get_xml_data().to_string(), encoding='utf-8')
                    self.assertEqual(Environment.get_tmp_dir(), (data / 'scratch').as_posix())
                    self.assertEqual(Environment.get_asset_dir(), (data / 'repo').as_posix())
                    self.assertEqual(Environment.get_asset_dir(alias='archive'), (data / 'other').as_posix())
                    self.assertEqual(Environment.get_asset_dir(alias='plugins'), (data / 'extensions').as_posix())
                    bases = Api(Store(data)).get_base_dirs({'project': 'admin'})
                    self.assertEqual(bases['asset_base_dir'], {'default': 'repo', 'archive': 'archive'})
                    Config.set_value('checkin', 'win32_client_repo_dir', 'X:/client')
                    self.assertEqual(Api(Store(data)).get_base_dirs({})['win32_client_repo_dir'], 'X:/client')
                    self.assertEqual(Environment.get_upload_dir('owned-ticket'), (data / 'scratch/upload/owned-ticket').as_posix())
                    with self.assertRaises(EnvironmentException):
                        Environment.get_upload_dir('../../escape')
                    self.assertEqual(Environment.get_client_handoff_dir('owned-ticket'), (data / 'scratch/handoff/owned-ticket').as_posix())
                    self.assertFalse((data / 'scratch/handoff').exists())
                    prefix = 'win32' if os.name == 'nt' else 'linux'
                    Config.set_value('checkin', prefix+'_client_handoff_dir', '/client/handoff')
                    server_handoff = (data / 'server/handoff').as_posix()
                    Config.set_value('checkin', prefix+'_server_handoff_dir', server_handoff)
                    self.assertEqual(Environment.get_client_handoff_dir('owned-ticket'), '/client/handoff/owned-ticket')
                    self.assertEqual(Environment.get_server_handoff_dir('owned-ticket'), server_handoff + '/owned-ticket')
                    self.assertEqual(Environment.get_server_handoff_dir('owned-ticket', include_ticket=False), server_handoff)
                    with self.assertRaises(EnvironmentException):
                        Environment.get_client_handoff_dir('../../escape')
                    with self.assertRaises(EnvironmentException):
                        Environment.get_server_handoff_dir('../../escape')
                FirstRunInit().execute()
                self.assertTrue((data / 'scratch/log').is_dir())
                self.assertTrue((data / 'repo').is_dir())
                self.assertTrue((data / 'extensions').is_dir())

    def test_startup_to_transaction_audit_fixes(self):
        import asyncio
        from pyasm.security.authenticator import Authenticator, hash_password
        from pyasm.search.transaction import Transaction
        from pyasm.search.sql import DbResource
        from pyasm.search.search import SObject
        from tactic_stream.server.server_events import ServerEvents
        with tempfile.TemporaryDirectory() as temporary:
            data = Path(temporary)
            store = Store(data)
            db_path = store.database_path('sthpw')
            db_path.parent.mkdir(parents=True, exist_ok=True)
            db_path.write_bytes(b'')
            self.assertFalse(store.is_initialized())
            db_path.unlink()
            store.initialize(hash_password('audit-pass'))
            self.assertTrue(store.is_initialized())
            with patch.dict(os.environ, {'TACTIC_DATA_DIR': str(data), 'TACTIC_CONFIG_PATH': '', 'TACTIC_TMP_CONFIG_PATH': ''}),                  patch.object(sys, 'argv', ['tactic_stream', '--data-dir', str(data), 'init', '--if-needed']):
                from tactic_stream.__main__ import main
                self.assertFalse((data / 'config/tactic-conf.xml').exists())
                main()
                self.assertTrue((data / 'config/tactic-conf.xml').exists())
            auth = Authenticator(store)
            ticket = auth.get_ticket('admin', 'audit-pass')
            with request_context(RequestContext(store, 'admin', 'admin')):
                Config.set_value('security', 'case_insensitive_login', 'true')
                self.assertEqual(auth.validate(ticket), 'admin')
                tx = Transaction.get(create=True)
                with store.connection(write=False):
                    pass
                with store.connection('sthpw', write=False) as db:
                    pass
                res = DbResource.get_default('sthpw')
                self.assertTrue(tx.can_write_resource(res))
                tx.verified_resources.add('custom_key')
                SObject._clear_config_cache('sthpw/project')
                self.assertNotIn('custom_key', tx.verified_resources)
                tx.rollback()
            events = ServerEvents(data, interval=0.01)
            events.subscribers.append({'project': 'admin', 'subscription': {'channels': [], 'search_types': []}, 'since': 0, 'event': asyncio.Event(), 'changes': set(), 'client': {}})
            calls = []
            def flaky_read():
                calls.append(1)
                if len(calls) == 1:
                    raise PermissionError('transient windows lock')
                events.subscribers.clear()
                raise OSError('stop after retry')
            events.read_changes = flaky_read
            asyncio.run(events.watch())
            self.assertEqual(len(calls), 2)

    def test_performance_file_and_cache_audit_fixes(self):
        from pyasm.biz.file_catalog import FileCatalog
        from pyasm.biz.schema import Schema
        from pyasm.common import Container
        from pyasm.search import Search, SObject
        from pyasm.security import Sudo
        from test_project_writes import install_writer, set_rules, PASSWORD
        from tools.checkin_benchmark import prepare
        with tempfile.TemporaryDirectory() as temporary:
            store = Store(temporary)
            api, _ = prepare(store)
            install_writer(store)
            rules = '<rules><rule group="project" code="one" access="allow"/><rule group="project" key="one" access="allow"/><rule group="search_type" code="cg/shot" project="one" access="allow"/></rules>'
            set_rules(store, rules)
            ticket = api.get_ticket('project_writer', PASSWORD)
            with request_context(RequestContext(store, 'project_writer', 'one')):
                api.auth.bind_security('project_writer', ticket)
                self.assertIsNotNone(Schema.get_predefined_schema('admin'))
                self.assertIsNotNone(Schema._PREDEFINED_DEFINITIONS)
                shot = Search.get_by_code('cg/shot', 'SH001')
                self.assertIsNotNone(shot)
                with patch.object(Search, 'get_count', side_effect=AssertionError('get_count should not run on verified cache hit')),                      patch.object(Search, 'get_sobject', side_effect=AssertionError('get_sobject should not run on verified cache hit')):
                    cached_shot = Search.get_by_code('cg/shot', 'SH001')
                    self.assertIs(cached_shot, shot)
                from pyasm.security.security import _clear_account_cache
                set_rules(store, rules.replace('code="cg/shot" project="one" access="allow"', 'code="cg/shot" project="one" access="deny"'))
                _clear_account_cache()
                self.assertIsNone(Search.get_by_code('cg/shot', 'SH001'))
                SObject.get_cache_dict(search_type='cg/shot').clear()
                sudo = Sudo()
                try:
                    sudo_shot = Search.get_by_code('cg/shot', 'SH001')
                    self.assertIsNotNone(sudo_shot)
                finally:
                    sudo.exit()
                self.assertIsNone(Search.get_by_code('cg/shot', 'SH001'))
            saved_pages = {}
            loads = []
            def load_page(code):
                loads.append(code)
                return saved_pages[code]
            def save_page(node):
                code = f'page_{len(saved_pages)}'
                saved_pages[code] = node
                return code
            catalog = FileCatalog(load_page, save_page)
            self.assertEqual(catalog.CACHE_SIZE, 512)
            meta = catalog.store({'leaf': True, 'items': [{'path': 'a.txt', 'size': 4}]})
            self.assertIn(meta['code'], catalog.cache)
            self.assertEqual(catalog.node(meta['code'])['items'][0]['path'], 'a.txt')
            self.assertEqual(loads, [])
            from tactic_stream.server.api import ApiXMLRPC
            self.assertIs(ApiXMLRPC(store)._signatures, ApiXMLRPC._signatures)


if __name__ == '__main__':
    unittest.main()
