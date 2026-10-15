import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from pyasm.biz import NamingUtil
from pyasm.common import Config, Container
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store


class NamingPreparation(unittest.TestCase):
    def test_only_pattern_parts_are_reused_and_file_clock_config_values_stay_fresh(self):
        with tempfile.TemporaryDirectory() as directory:
            with request_context(RequestContext(Store(Path(directory)), 'admin')):
                util = NamingUtil()
                values = dict(file_name='shot_001.abc', base_type='file')
                file = SimpleNamespace(get_value=lambda key: values.get(key, ''))
                snapshot_values = dict(version=1)
                snapshot = SimpleNamespace(get_value=lambda key: snapshot_values.get(key, ''))
                sobject = SimpleNamespace(is_insert=lambda: True, get_value=lambda key: '')
                template = '{file.file_name}_{date,%Y%m%d}_{snapshot.version}'
                with patch('time.strftime', side_effect=['20261010', '20261011']):
                    self.assertEqual(util.naming_to_file(template, sobject, snapshot, file),
                                     'shot_001.abc_20261010_001')
                    parts = util._get_parts(template)
                    values['file_name'] = 'asset_002.exr'
                    snapshot_values['version'] = 2
                    Config.set_value('checkin', 'version_padding', '4')
                    self.assertEqual(util.naming_to_file(template, sobject, snapshot, file),
                                     'asset_002.exr_20261011_0002')
                    self.assertIs(util._get_parts(template), parts)
                directory_template = '{file.file_name}/{snapshot.version}'
                self.assertEqual(util.naming_to_dir(directory_template, sobject, snapshot, file),
                                 'asset_002.exr/0002')
                values['file_name'] = 'shot_003.abc'
                self.assertEqual(util.naming_to_dir(directory_template, sobject, snapshot, file),
                                 'shot_003.abc/0002')
                for index in range(300):
                    util._get_parts('template_%d/{file.file_name}' % index)
                self.assertLessEqual(len(Container.get_full_dict('NamingUtil:parts')), 256)
            with request_context(RequestContext(Store(Path(directory)), 'admin')):
                self.assertIsNone(Container.get('NamingUtil:parts'))
