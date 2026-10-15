"""Reject a cached HTML/partial download before invoking the official pip zipapp.
TLS remains the upstream trust source; this is NOT a pre-pinned hash proof.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import re
import subprocess
import sys
import zipfile

def check_archive(path: Path):
    if not path.is_file() or not 100_000 <= path.stat().st_size <= 32*1024*1024:
        raise ValueError('pip download has an unexpected size; expected the .pyz FILE, not a directory page')
    if not zipfile.is_zipfile(path):
        raise ValueError('pip download is not a ZIP application (possibly cached HTML)')
    with zipfile.ZipFile(path) as z:
        if '__main__.py' not in z.namelist():raise ValueError('pip ZIP has no __main__.py')
        if sum(x.file_size for x in z.infolist())>128*1024*1024:raise ValueError('pip ZIP expanded size exceeds limit')
        bad=z.testzip()
        if bad:raise ValueError('pip ZIP CRC failure: '+bad)

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('path',type=Path);p.add_argument('--version',required=True);a=p.parse_args(argv)
    check_archive(a.path)
    result=subprocess.run([sys.executable,'-s',str(a.path),'--isolated','--version'],capture_output=True,text=True,timeout=60)
    if result.returncode or not re.match(r'^pip '+re.escape(a.version)+r'(?:\s|$)',result.stdout):
        raise ValueError('pip zipapp version check failed: '+(result.stderr or result.stdout).strip()[:500])
    print(result.stdout.strip());return 0

if __name__=='__main__':
    try:raise SystemExit(main())
    except (OSError,ValueError,zipfile.BadZipFile,subprocess.TimeoutExpired) as exc:
        print('Invalid pip download:',exc,file=sys.stderr);raise SystemExit(2)
