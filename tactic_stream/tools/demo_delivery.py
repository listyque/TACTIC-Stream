"""Prepare fictional media and the existing installable examples for demo editions."""
import argparse
from hashlib import file_digest
import json
from pathlib import Path
import runpy
import shutil

from tools.file_project_delivery import ROOT
from tools.build_workspace_pulse import build as build_pulse


def build(output: Path) -> Path:
    output.mkdir(parents=True, exist_ok=False)
    example = ROOT.parent / 'examples/demo'
    shutil.copytree(example / 'assets', output / 'assets')
    (output / 'plugins').mkdir()
    review = runpy.run_path(str(ROOT.parent / 'examples/studio_review/build.py'))['build']
    review(output / 'plugins/studio-review.zip')
    build_pulse(output / 'plugins/workspace-pulse.zip')
    files = {}
    for path in sorted(output.rglob('*')):
        if path.is_file():
            with path.open('rb') as source:
                files[path.relative_to(output).as_posix()] = file_digest(source, 'sha256').hexdigest()
    (output / 'manifest.json').write_text(json.dumps(dict(format='tactic-stream-demo-1', files=files), indent=2), encoding='utf-8')
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New demonstration content directory')
    args = parser.parse_args()
    build(args.output.resolve())
