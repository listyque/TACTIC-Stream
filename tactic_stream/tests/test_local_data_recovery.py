"""Existing-data checks never run application code or stop another process."""
from contextlib import closing
import json
import os
from pathlib import Path
import socket
import sqlite3
import tempfile
import unittest
from xml.etree import ElementTree as ET

from tools.local_data_recovery_check import monitor_exists, verify


@unittest.skipUnless(os.name == 'nt', 'Windows Robocopy/attributes boundary')
class LocalDataRecovery(unittest.TestCase):
    def create(self, root):
        source, work = root / 'source', root / 'work'
        work.mkdir()
        for name in ('assets/empty', 'db', 'config'):
            (source / name).mkdir(parents=True)
        payload = source / 'assets/read-only.bin'
        payload.write_bytes(b'owned fixture bytes')
        payload.chmod(0o444)
        with closing(sqlite3.connect(source / 'db/sthpw.db')) as db:
            db.execute('CREATE TABLE fixture(value TEXT)')
            db.execute("INSERT INTO fixture VALUES ('unchanged')")
            db.commit()
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            port = listener.getsockname()[1]
        config = ET.fromstring('<config><database><vendor>Sqlite</vendor></database><checkin><asset_base_dir/></checkin><services><start_port/></services></config>')
        config.find('checkin/asset_base_dir').text = (source / 'assets').as_posix()
        config.find('services/start_port').text = str(port)
        (source / 'config/tactic-conf.xml').write_text(ET.tostring(config, encoding='unicode'), encoding='utf-8')
        return source, work

    def test_native_copy_preserves_readonly_bytes_timestamps_empty_directories_and_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            source, work = self.create(Path(directory))
            result = verify(source, work)
            self.assertTrue(result['source_unchanged'])
            self.assertEqual(result['source_databases'], 1)
            self.assertEqual(result['rows'], 1)
            self.assertTrue((work / 'restored/assets/empty').is_dir())
            self.assertTrue((work / 'restored/assets/read-only.bin').stat().st_file_attributes & 1)
            self.assertFalse(result['application_scripts_started'])

    def test_active_monitor_refuses_copy_without_signalling_the_process(self):
        with self.assertRaises(ValueError):
            monitor_exists(True)
        with self.assertRaises(ValueError):
            monitor_exists(0)
        self.assertTrue(monitor_exists(os.getpid()))
        with tempfile.TemporaryDirectory() as directory:
            source, work = self.create(Path(directory))
            (source / 'temp/log').mkdir(parents=True)
            (source / 'temp/log/monitor.json').write_text(json.dumps(dict(monitor_pid=os.getpid())))
            with self.assertRaisesRegex(RuntimeError, 'active'):
                verify(source, work)
            self.assertEqual(list(work.iterdir()), [])
