"""Verify the real toolbar in original Handler, Frame Handler and Stream."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]

def main():
    sys.path[:0] = [str(ROOT), str(ROOT / 'src'), str(ROOT / 'tests')]
    os.environ.update(PLAYWRIGHT_BROWSERS_PATH=str(ROOT / '.browser-cache'),
                      TMP=str(ROOT / '.tmp/frame-tests'), TEMP=str(ROOT / '.tmp/frame-tests'))
    for arguments in [[], ['--original']]:
        subprocess.run([sys.executable, '-B', '-X', 'utf8', 'tools/frame_foundation/main_qml.py', *arguments],
                       cwd=ROOT, check=True, timeout=40)

    from test_transport import Transport

    # This UI-only fixture never resets a directory while its collectors own it.
    Transport.setUpClass()
    try:
        subprocess.run(['node', 'tests/frame_main_browser.mjs', Transport.url],
                       cwd=ROOT / 'frontend', check=True, timeout=60)
    finally:
        Transport.tearDownClass()


if __name__ == '__main__':
    main()
