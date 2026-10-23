"""Verify an existing stopped SQLite data tree using private copies and read-only SQL.

Never starts application jobs/scripts from customer data and never changes the source.
NTFS ownership/ACL disaster recovery is outside this content/attribute-copy check.
"""
import argparse
from contextlib import closing
import ctypes
from ctypes import wintypes
from hashlib import sha256
import json
from pathlib import Path
import socket
import sqlite3
import subprocess
import tempfile
from xml.etree import ElementTree as ET

from tools.file_project_delivery import ROOT
from tools.windows_delivery import digest


def inventory(root):
    files, directories = {}, []
    for path in sorted(root.rglob('*')):
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('External links require an explicit separate backup entry')
        relative = path.relative_to(root).as_posix()
        if path.is_dir():
            directories.append(relative)
        elif path.is_file():
            stat = path.stat()
            files[relative] = dict(bytes=stat.st_size, sha256=digest(path), mtime_ns=stat.st_mtime_ns,
                                   readonly=bool(stat.st_file_attributes & 1))
    return dict(files=files, directories=directories)


def database_counts(root):
    result = {}
    for path in sorted((root / 'db').glob('*.db')):
        with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as db:
            assert db.execute('PRAGMA integrity_check').fetchall() == [('ok',)], path.name
            tables = db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
            result[path.name] = {name: db.execute('SELECT count(*) FROM "' + name.replace('"', '""') + '"').fetchone()[0]
                                 for name, in tables}
    assert result, 'No SQLite databases in the copied data root'
    return result


def monitor_exists(pid):
    if type(pid) is not int or pid <= 0:
        raise ValueError('Invalid monitor PID')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1000, False, pid)
    if handle:
        kernel.CloseHandle(handle)
        return True
    error = ctypes.get_last_error()
    if error == 87:
        return False
    raise ctypes.WinError(error)


def verify(source, directory):
    assert not directory.is_relative_to(source) and not source.is_relative_to(directory)
    config = ET.parse(source / 'config/tactic-conf.xml')
    assert config.findtext('./database/vendor').lower() == 'sqlite'
    assets = Path(config.findtext('./checkin/asset_base_dir')).resolve()
    assert assets.is_relative_to(source), 'External repository needs its own coordinated backup'
    status = source / 'temp/log/monitor.json'
    if status.exists():
        pid = json.loads(status.read_text())['monitor_pid']
        if monitor_exists(pid):
            raise RuntimeError('Monitor PID is active or inaccessible; leave the source untouched')
    port = int(config.findtext('./services/start_port'))
    with socket.socket() as listener:
        listener.settimeout(.5)
        if listener.connect_ex(('127.0.0.1', port)) == 0:
            raise RuntimeError('Local application port is active; leave the source untouched')
    original = inventory(source)
    print('Existing source inventoried; copying stopped data without starting application code', flush=True)

    def copy(origin, target):
        assert not target.exists() and target.resolve().is_relative_to(directory.resolve())
        command = ['robocopy', str(origin), str(target), '/E', '/COPY:DAT', '/DCOPY:DAT',
                   '/R:0', '/W:0', '/XJ', '/NFL', '/NDL', '/NJH', '/NJS', '/NP']
        process = subprocess.run(command, capture_output=True)
        if process.returncode >= 8:
            (directory / 'copy-error.log').write_bytes(process.stdout + process.stderr)
            raise RuntimeError('Data copy failed; inspect private copy-error.log')

    copied, backup, restored = (directory / name for name in ('copy', 'backup', 'restored'))
    copy(source, copied)
    assert inventory(copied) == original
    counts = database_counts(copied)
    baseline = inventory(copied)
    copy(copied, backup)
    assert inventory(backup) == baseline
    copy(backup, restored)
    assert inventory(restored) == baseline
    assert database_counts(restored) == counts
    assert inventory(source) == original, 'Source changed during the trial; result is not accepted'
    tables = sum(len(value) for value in counts.values())
    return dict(source_unchanged=True, offline_only=True, source_databases=len(counts), tables=tables,
                rows=sum(sum(value.values()) for value in counts.values()), files=len(original['files']),
                bytes=sum(item['bytes'] for item in original['files'].values()),
                content_mtime_readonly_and_empty_directories=True, integrity_check=True,
                restored_from_separate_backup=True, original_login_hashes_preserved=True,
                source_inventory_sha256=sha256(json.dumps(original, sort_keys=True).encode()).hexdigest(),
                application_scripts_started=False, windows_acl_restore_verified=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-data', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='l12-existing-', dir=ROOT / '.tmp') as temporary:
        directory = Path(temporary).resolve()
        source = args.source_data.resolve()
        result = verify(source, directory)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result))
