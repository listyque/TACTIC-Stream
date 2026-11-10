"""Initialize only this package's empty data directory, then run as the app user."""
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys


def main():
    metadata = json.loads(Path(__file__).with_name('release.json').read_text(encoding='utf-8'))
    data = Path(os.environ['TACTIC_DATA_DIR']).resolve()
    marker = data / 'dsm-initialized.json'
    if marker.is_file():
        if json.loads(marker.read_text(encoding='utf-8')) != metadata:
            raise RuntimeError('Existing DSM data belongs to another edition/version; restore or migrate it explicitly')
        return
    if any(data.iterdir()):
        raise FileExistsError('DSM initialization refuses existing or partially initialized server data')
    os.chown(data, 10001, 10001)
    os.setgid(10001)
    os.setuid(10001)
    runpy.run_path(str(Path(__file__).with_name('init-postgres.py')))['prepare'](data)
    command = [sys.executable, '-B', '-m', 'tactic_stream', '--data-dir', str(data),
               'init', '--password-file', '/run/secrets/admin_password']
    if metadata['demo']:
        command += ['--demo', '/opt/tactic-demo']
    subprocess.run(command, check=True)
    with marker.open('x', encoding='utf-8') as output:
        json.dump(metadata, output)


if __name__ == '__main__':
    main()
