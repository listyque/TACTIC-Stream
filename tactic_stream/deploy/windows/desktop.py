"""Prepare only a new desktop configuration; native CLI owns installation and serving."""
from importlib.resources import files
import json
import os
from pathlib import Path
import sys
import subprocess
from xml.etree import ElementTree as ET

from pyasm.common.config import save_config_file
from pyasm.search.storage import Store
from tactic_stream.server.startup import read_server_config


def describe(data_dir, port):
    data_dir = Path(data_dir).resolve()
    if not 1 <= port <= 65535:
        raise ValueError('Invalid local server port')
    os.environ['TACTIC_DATA_DIR'] = data_dir.as_posix()
    path = data_dir / 'config/tactic-conf.xml'
    if not path.exists():
        if (data_dir / 'db').exists():
            raise FileExistsError('Existing databases require their original configuration')
        text = files('tactic_stream').joinpath('config/tactic-conf.xml').read_text(encoding='utf-8')
        root = ET.fromstring(text)
        root.find('./install/hostname').text = '127.0.0.1'
        root.find('./services/start_port').text = str(port)
        root.find('./services/process_count').text = '1'
        root.find('./checkin/asset_base_dir').text = (data_dir / 'assets').as_posix()
        root.find('./checkin/win32_local_base_dir').text = (data_dir / 'local').as_posix()
        root.find('./checkin/win32_sandbox_dir').text = (data_dir / 'sandbox').as_posix()
        path.parent.mkdir(parents=True, exist_ok=True)
        save_config_file(path, ET.tostring(root, encoding='unicode'), expected_revision=None)
    settings = read_server_config(data_dir)
    return dict(initialized=Store(data_dir).is_initialized(), log_dir=settings['log_dir'],
                port=(settings['ports'] or [settings['port']])[0])


if __name__ == '__main__':
    if sys.argv[1] == '--initialize':
        raise SystemExit(subprocess.call([sys.executable, '-I', '-B', '-X', 'utf8',
            '-m', 'tactic_stream', '--data-dir', sys.argv[2], 'init', '--if-needed'],
            creationflags=subprocess.CREATE_NEW_CONSOLE))
    print(json.dumps(describe(sys.argv[1], int(sys.argv[2]))))
