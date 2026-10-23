"""Check the actual embedded runtime and reject changed or additional program files."""
from hashlib import file_digest
from importlib.metadata import version
import json
from pathlib import Path
import sys

import PySide6
import tactic_stream


root = Path(sys.argv[1]).resolve()
manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
assert all(Path(item).is_relative_to(root) for item in sys.path)
assert tactic_stream.__version__ == version('tactic-stream') == manifest['server_version']
assert PySide6.__version__ == manifest['dependencies']['PySide6']
expected = {entry['path'] for entry in manifest['files']} | {'manifest.json'}
actual = {path.relative_to(root).as_posix() for path in root.rglob('*') if path.is_file()}
assert actual == expected, dict(extra=sorted(actual - expected), missing=sorted(expected - actual))
for entry in manifest['files']:
    path = (root / entry['path']).resolve()
    assert path.is_relative_to(root)
    assert path.stat().st_size == entry['bytes'], entry['path']
    with path.open('rb') as source:
        assert file_digest(source, 'sha256').hexdigest() == entry['sha256'], entry['path']
print(json.dumps(dict(python=sys.version.split()[0], qt=PySide6.__version__, stream=tactic_stream.__version__,
                      inventory_files=len(manifest['files']), program_files_unchanged=True)))
