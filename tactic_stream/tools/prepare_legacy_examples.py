"""Preserve the original examples and prepare explicitly adapted template copies."""
import argparse
from hashlib import file_digest
import json
import re
from pathlib import Path
import shutil
import zipfile

from tools.file_project_delivery import ROOT

SOURCES = {
    'vfx-1.0.0.zip': '3dcebb7ad9bc1e0a64926b658af81854c27e86aa5dc4d3575e7f9733fbafcfbb',
    'game-1.0.0.zip': 'dba3f97494970b2957adb0f010c3f3668151fccd418188e5e2382cbfeb5c4fcf',
}


def repair_vfx_config(text):
    """Replace obsolete frame/detail declarations with ordinary native widgets."""
    text = text.replace('<display class="pyasm.prod.web.FrameRangeWdg"/>',
        '<display class="tactic.ui.table.ExpressionElementWdg"><expression>@GET(.tc_frame_start)</expression><display_expression>'
        '{@GET(.tc_frame_start)} - {@GET(.tc_frame_end)} '
        '({@GET(.frame_in)} - {@GET(.frame_out)})</display_expression></display>')
    text = re.sub(r'<element name="frames">\s*<display class="pyasm.prod.web.FrameInputWdg"/>\s*'
                  r'<action class="pyasm.prod.web.FrameAction"/>\s*</element>',
        ''.join('<element name="' + name + '"/>' for name in
                ('tc_frame_start', 'tc_frame_end', 'frame_in', 'frame_out', 'frame_note')), text)
    # Edit views reference the compound definition; expand the same five fields there.
    fields = ''.join('<element name="' + name + '"/>' for name in
                     ('tc_frame_start', 'tc_frame_end', 'frame_in', 'frame_out', 'frame_note'))
    text = re.sub(r'<edit(?:\s[^>]*)?>.*?</edit>',
                  lambda match: match[0].replace('<element name="frames"/>', fields), text, flags=re.S)
    text = re.sub(r'<display[^>]*>\s*<dynamic_class>pyasm.prod.web.AssetDetailWdg</dynamic_class>\s*</display>',
                  '<display class="tactic.ui.table.SObjectDetailElementWdg"/>', text)
    # Camera inherits prod's form; its selector must use this template's shot type.
    text += '''
#-- Start Entry --#
insert = SearchType.create('config/widget_config')
insert.set_value('search_type', 'vfx/camera')
insert.set_value('view', 'edit')
insert.set_value('config', '<config><edit><element name="files"><display class="SimpleUploadWdg"><context>publish</context></display><action class="UploadAction"/></element><element name="shot_code"><display class="SelectWdg"><query>vfx/shot|code|code</query></display></element><element name="description"/></edit></config>')
#-- End Entry --#
'''
    return text


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
    with zipfile.ZipFile(source / 'vfx-1.0.0.zip') as original:
        with zipfile.ZipFile(output / 'vfx-1.0.0-stream.1.zip', 'x') as target:
            for entry in original.infolist():
                data = original.read(entry)
                if entry.filename == 'vfx/config_widget_config.spt':
                    data = repair_vfx_config(data.decode('utf-8')).encode('utf-8')
                target.writestr(entry, data)
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
                        references=6, before='game_status_default', after='game/status_default'),
                        'vfx-1.0.0-stream.1.zip': dict(file='vfx/config_widget_config.spt',
                            changes=['FrameRangeWdg to native expression', 'FrameInputWdg/FrameAction to five native fields',
                                     'AssetDetailWdg to native object inspector',
                                     'Camera edit form selects vfx/shot and preserves file upload'])},
                    files={name: digest(output / name) for name in
                           ('vfx-1.0.0.zip', 'vfx-1.0.0-stream.1.zip', 'game-1.0.0-stream.1.zip')})
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    (output / 'README.txt').write_text(
        'TACTIC examples for Stream 0.112.195 / Handler 0.6.0.142.\n'
        'VFX 1.0.0 is preserved. Install VFX stream.1 for native frame fields, object details and camera shot selection.\n'
        'Game stream.1 corrects only six task_pipeline references\n'
        'to the status pipeline actually defined in its archive; no server fallback is installed.\n'
        'Install through Manage templates / the project wizard or ProjectTemplateInstallerCmd.\n'
        'These templates contain definitions/configuration, not production objects or repository files.\n'
        'VFX prod/session_contents and Texture require excluded pyasm.prod classes; Maya Node Data\n'
        'has no table DDL in the source. Maya and applet scenarios are excluded by the user.\n'
        'Other unverified Python-2/Mako views are listed in RECOVERY_ACCEPTANCE.md.\n'
        'Importing their text does not certify those workflows.\n', encoding='utf-8')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT.parent / 'legacy/src/install/start/templates')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.source.resolve(), args.output.resolve())
    print(json.dumps(dict(output=str(args.output), templates=len(result['files']))))
