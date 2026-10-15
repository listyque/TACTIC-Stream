"""Compare independent UI copies; copying between products is always explicit."""
import argparse
import hashlib
import json
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / 'src/tactic_stream/shared_ui'


def sync(handler_root, check=False, copy_from=None):
    handler = Path(handler_root).resolve() / 'thlib/ui/qml/tactic_frame'
    if copy_from:
        if check or copy_from not in ('stream', 'handler'):
            raise ValueError('Choose either comparison or an explicit copy direction')
        source, target = (SOURCE, handler) if copy_from == 'stream' else (handler, SOURCE)
        files = sorted(source.rglob('*.mjs'))
        assert files, 'No Tactic Frame modules to copy'
        target.mkdir(parents=True, exist_ok=True)
        for path in files:
            destination = target / path.relative_to(source)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(path.read_bytes())
        hashes = {path.relative_to(handler).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(handler.rglob('*.mjs'))}
        (handler / 'manifest.json').write_text(json.dumps({'source': 'independent product copy', 'sha256': hashes}, indent=2) + '\n', encoding='utf-8')
    files = sorted(SOURCE.rglob('*.mjs'))
    assert files, 'No Stream Tactic Frame modules'
    assert {path.relative_to(SOURCE).as_posix() for path in files} == {path.relative_to(handler).as_posix() for path in handler.rglob('*.mjs')}, 'Different Tactic Frame module lists'
    for path in files:
        relative = path.relative_to(SOURCE)
        assert (handler / relative).read_bytes() == path.read_bytes(), f'Tactic Frame copies differ: {relative}'
    hashes = {path.relative_to(SOURCE).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    assert json.loads((handler / 'manifest.json').read_text(encoding='utf-8'))['sha256'] == hashes, 'Stale Handler manifest'
    print(f'{"Copied and checked" if copy_from else "Checked"} {len(files)} Tactic Frame modules')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--handler-root', required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true', help='Compare only (the default)')
    mode.add_argument('--copy-from', choices=('stream', 'handler'), help='Explicitly copy UI modules from this product')
    args = parser.parse_args()
    sync(args.handler_root, args.check, args.copy_from)
