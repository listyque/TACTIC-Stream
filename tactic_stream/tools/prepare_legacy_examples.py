"""Copy the shipped examples and repair six broken status references in Game 1.0.0."""
import argparse
from hashlib import file_digest
import json
from pathlib import Path
import shutil
import zipfile

from tools.file_project_delivery import ROOT

SOURCES = {
    'vfx-1.0.0.zip': '3dcebb7ad9bc1e0a64926b658af81854c27e86aa5dc4d3575e7f9733fbafcfbb',
    'game-1.0.0.zip': 'dba3f97494970b2957adb0f010c3f3668151fccd418188e5e2382cbfeb5c4fcf',
}


def digest(path):
    with path.open('rb') as stream:
        return file_digest(stream, 'sha256').hexdigest()


def prepare(source, output):
    if output.exists():
        raise FileExistsError('Example delivery needs a new directory')
    for name, expected in SOURCES.items():
        if digest(source / name) != expected:
            raise ValueError('Unknown example revision; review its references first: ' + name)
    output.mkdir(parents=True)
    shutil.copyfile(source / 'vfx-1.0.0.zip', output / 'vfx-1.0.0.zip')
    old = b"task_pipeline='game_status_default'"
    new = b"task_pipeline='game/status_default'"
    with zipfile.ZipFile(source / 'game-1.0.0.zip') as original:
        body = original.read('game/sthpw_pipeline.spt')
        assert body.count(old) == 6
        assert b'game/status_default' in body
        with zipfile.ZipFile(output / 'game-1.0.0-stream.1.zip', 'x') as target:
            for entry in original.infolist():
                data = original.read(entry)
                if entry.filename == 'game/sthpw_pipeline.spt':
                    data = body.replace(old, new)
                target.writestr(entry, data)
    manifest = dict(format='tactic-stream-legacy-example-templates', source_sha256=SOURCES,
                    repairs={'game-1.0.0-stream.1.zip': dict(file='game/sthpw_pipeline.spt',
                        references=6, before='game_status_default', after='game/status_default')},
                    files={name: digest(output / name) for name in
                           ('vfx-1.0.0.zip', 'game-1.0.0-stream.1.zip')})
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    (output / 'README.txt').write_text(
        'TACTIC examples for Stream 0.112.194 / Handler 0.6.0.141.\n'
        'VFX 1.0.0 is copied unchanged. Game stream.1 corrects only six task_pipeline references\n'
        'to the status pipeline actually defined in its archive; no server fallback is installed.\n'
        'Install through Manage templates / the project wizard or ProjectTemplateInstallerCmd.\n'
        'These templates contain definitions/configuration, not production objects or repository files.\n'
        'VFX prod/session_contents and Texture require excluded pyasm.prod classes; Maya Node Data\n'
        'has no table DDL in the source. Historical Maya/applet/Python-2 scripts and executable Mako\n'
        'views are not certified. Importing their text does not certify those workflows.\n', encoding='utf-8')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT.parent / 'legacy/src/install/start/templates')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.source.resolve(), args.output.resolve())
    print(json.dumps(dict(output=str(args.output), templates=len(result['files']))))
