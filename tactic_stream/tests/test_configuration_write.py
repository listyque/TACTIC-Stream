"""Two independent processes cannot publish competing edits of one revision."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from pyasm.common.config import read_config_file


class ConfigurationWrite(unittest.TestCase):
    def test_update_collection_interval_bounds(self):
        from pyasm.common.config import ConfigException
        from tactic_stream.server.startup import parse_service_config
        self.assertEqual(parse_service_config({})['update_interval'], .5)
        for value in ('0.1', '0.75', '2'):
            self.assertEqual(parse_service_config({'update_interval': value})['update_interval'], float(value))
        for value in ('0', '-1', '0.01', '2.1', 'nan', 'inf', 'bad'):
            with self.assertRaises(ConfigException) as error:
                parse_service_config({'update_interval': value})
            self.assertEqual(error.exception.field, 'services/update_interval')

    def test_optional_versionless_file_modes(self):
        from pyasm.common.config import ConfigException
        from tactic_stream.server.configuration import validate_setting
        for mode in ('', 'copy', 'symlink', 'hardlink'):
            self.assertEqual(validate_setting('checkin/versionless_mode', mode), mode)
        with self.assertRaises(ConfigException):
            validate_setting('checkin/versionless_mode', 'unsupported')

    def test_two_processes_share_the_native_config_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            config = directory / 'tactic-conf.xml'
            original = '<config version="2"><services><process_count>1</process_count></services></config>'
            config.write_text(original, encoding='utf8')
            revision = read_config_file(config)[1]
            code = '''
from pathlib import Path
import sys,time
from pyasm.common.config import save_config_file,ConfigConflict
path,revision,value=Path(sys.argv[1]),sys.argv[2],sys.argv[3]
(path.parent/('ready-'+value)).touch()
while not (path.parent/'go').exists(): time.sleep(.01)
try:
    save_config_file(path,'<config version="2"><services><process_count>'+value+'</process_count></services></config>',expected_revision=revision,backup=True)
    print('saved')
except ConfigConflict:
    print('conflict')
'''
            processes = [subprocess.Popen([sys.executable, '-B', '-c', code, str(config), revision, value],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)) for value in ('2', '3')]
            try:
                deadline = time.monotonic() + 10
                while not all((directory / ('ready-' + value)).exists() for value in ('2', '3')):
                    if time.monotonic() >= deadline or any(process.poll() is not None for process in processes):
                        self.fail('Configuration writer did not start')
                    time.sleep(.01)
                (directory / 'go').touch()
                results = []
                for process in processes:
                    output, error = process.communicate(timeout=10)
                    self.assertEqual(process.returncode, 0, error)
                    results.append(output.strip())
                self.assertEqual(sorted(results), ['conflict', 'saved'])
                self.assertNotEqual(read_config_file(config)[1], revision)
                self.assertEqual(config.with_name(config.name + '.previous').read_text(encoding='utf8'), original)
            finally:
                for process in processes:
                    if process.poll() is None:
                        process.kill()
                    process.communicate(timeout=5)
