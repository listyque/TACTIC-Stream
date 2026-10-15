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


if __name__ == '__main__':
    unittest.main()
