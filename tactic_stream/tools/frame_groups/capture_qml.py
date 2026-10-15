"""Capture the shipped Groups view and real native input on an isolated controller."""
import subprocess
import itertools
import json
import os
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
USERS = '--users' in sys.argv
HERE = REPO / 'tools' / ('frame_users' if USERS else 'frame_groups')
TH = Path('D:/code/th_codex')
os.environ.update(QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software', QT_FONT_DPI='96')
os.environ.setdefault('QT_QUICK_CONTROLS_STYLE', 'Material')
sys.path[:0] = [str(TH), str(REPO / 'tools/frame_admin')]
# Each case creates a complete application fixture; isolate Qt's global engine state.
requested=os.environ.get('FRAME_CAPTURE_CASE')
if not requested:
    captures=[];combined=None
    for mode,language,width in itertools.product(('dark','light'),('en','ru'),(1100,800,360)):
        key=f'{mode}-{language}-{width}'
        subprocess.run([sys.executable,'-B','-X','utf8','-X','faulthandler',__file__,*(['--users'] if USERS else [])],env=dict(os.environ,FRAME_CAPTURE_CASE=key),check=True)
        part=HERE/'output'/('.capture-'+key+'.json')
        result=json.loads(part.read_text(encoding='utf8'));part.unlink()
        if combined:
            assert result['sha256']==combined['sha256'] and result['nativeSources']==combined['nativeSources']
        combined=result;captures.extend(result['captures'])
    combined['captures']=captures
    (HERE/'output'/'qml.json').write_text(json.dumps(combined,ensure_ascii=False,indent=2),encoding='utf8')
    print('Captured',len(captures),'production',('Users' if USERS else 'Groups'),'states in isolated native Qt applications')
    raise SystemExit(0)
from PySide6.QtCore import QPointF, Qt, QUrl
from PySide6.QtGui import QFontDatabase
from PySide6.QtQml import QQmlComponent
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtTest import QTest
from tests.test_admin_groups_ui import AdminGroupsUiTests
from tests.test_admin_users_ui import AdminUsersUiTests
from tests.test_sidebar_editor_qml import SidebarEditorQmlTests
from tests.profile_ui_responsiveness import frame
from native_capture import assert_icons, source_hashes
native_names = ['thlib/ui/qml/features/administration/groups/SecurityGroupsView.qml', 'thlib/ui/administration.py'] + (['thlib/ui/qml/features/administration/users/AdminUsersView.qml', 'thlib/ui/admin/users.py'] if USERS else [])
initial_sources = source_hashes(REPO, TH, native_names)

OUT = HERE / 'output'
OUT.mkdir(exist_ok=True)
cases = json.loads((HERE / 'cases.json').read_text())
Fixture = AdminUsersUiTests if USERS else AdminGroupsUiTests
Fixture.setUpClass()
for name in ('segoeui.ttf', 'seguisb.ttf'):
    QFontDatabase.addApplicationFont('C:/Windows/Fonts/' + name)
samples = []
fixture = None
try:
    for mode in ('dark', 'light'):
        for language in ('en', 'ru'):
            for width, height in ((1100, 660), (800, 560), (360, 740)):
                if requested!=f'{mode}-{language}-{width}':continue
                fixture = Fixture()
                fixture.setUp()
                admin = fixture.admin
                catalog = json.loads(json.dumps(admin._catalog))
                if USERS:
                    editor = fixture.editor
                    catalog = {'fields': list(editor.FIELDS), 'groups': [dict(row, name=row['code']) for row in editor.groupsModel.records()],
                        'users': [dict(editor._identities[row['identity']], document={**{k:v for k,v in row['document'].items() if k != 'code'}, 'password':'', 'groups': sorted(editor.metadata['groups'].get(row['identity'], []))}, revision='revision-'+row['identity']) for row in editor.catalog]}
                    (OUT / 'catalog.json').write_text(json.dumps(catalog, ensure_ascii=False), encoding='utf-8')
                else:
                    (OUT / 'catalog.json').write_text(json.dumps({
                    'groups': admin.groups.records(), 'memberships': catalog['memberships'],
                    'users': [{key: value for key, value in row.items() if key != 'member'} for row in admin.members.records()]
                }, ensure_ascii=False), encoding='utf-8')
                component = QQmlComponent(fixture.fixture.engine, QUrl.fromLocalFile(str(HERE / ('UsersHarness.qml' if USERS else 'GroupsHarness.qml'))))
                assert not component.isError(), [error.toString() for error in component.errors()]
                window = component.create()
                assert window is not None, [error.toString() for error in component.errors()]
                window.resize(width, height)
                window.setProperty('dark', mode == 'dark')
                window.setProperty('language', language)
                frame(window)

                def controls():
                    result = {}
                    for item in SidebarEditorQmlTests.descendants(window.contentItem()):
                        if not item.objectName() or not item.isVisible():
                            continue
                        pt = item.mapToScene(QPointF())
                        parent, visible = item.parentItem(), True
                        while parent:
                            if parent.clip():
                                clip = parent.mapToScene(QPointF())
                                if pt.x() + item.width() <= clip.x() or pt.x() >= clip.x() + parent.width() or pt.y() + item.height() <= clip.y() or pt.y() >= clip.y() + parent.height():
                                    visible = False
                                    break
                            parent = parent.parentItem()
                        if visible:
                            result[item.objectName()] = item
                    return result

                for case in cases:
                    for event in case['actions']:
                        if event['type'] == 'state':
                            if USERS:
                                editor._can_write = event['value'] != 'readonly'
                                editor._uncertain = event['value'] == 'uncertain'
                                editor._error = 'The save result is unknown. Reload users before trying again.' if editor._uncertain else ''
                                editor._worker = object() if event['value'] == 'busy' else None
                                editor.stateChanged.emit()
                            elif event['value'] == 'single-line':
                                admin._catalog['users'][0]['displayName'] = 'user_0'
                                admin.set_user_query('user_0')
                                window.setQuery('user_0')
                            else:
                                admin._group_uncertain = event['value'] == 'uncertain'
                                admin._error = 'The save result is unknown. Reload groups before trying again.' if admin._group_uncertain else ''
                                admin._worker = object() if event['value'] == 'busy' else None
                                admin.stateChanged.emit()
                        else:
                            item = controls()[event['id']]
                            point = item.mapToScene(QPointF(item.width() / 2, item.height() / 2)).toPoint()
                            QTest.mouseClick(window, Qt.LeftButton, pos=point)
                            if event['type'] == 'text':
                                QTest.keyClick(window, Qt.Key_A, Qt.ControlModifier)
                                QTest.keyClick(window, Qt.Key_Backspace)
                                for character in event['value']:
                                    QTest.keyClick(window, character)
                                    frame(window)
                        frame(window)
                    window.blur()
                    QTest.mouseMove(window, QPointF(width - 1, height - 1).toPoint())
                    frame(window)
                    scene = json.loads(window.property('sceneJson'))
                    state = json.loads(window.property('stateJson'))
                    assert_icons(window)
                    boxes, styles, backgrounds, interiors = {}, {}, {}, {}
                    for name, item in controls().items():
                        pt = item.mapToScene(QPointF())
                        boxes[name] = dict(x=pt.x(), y=pt.y(), width=item.width(), height=item.height())
                        if item.property('text') is not None and item.property('font') is not None:
                            font = item.property('font')
                            color = item.property('color')
                            styles[name] = {'fontSize': font.pixelSize(), 'weight': font.weight(), 'color': color.name() if color is not None else ''}
                        background = item if item.metaObject().className().startswith('QQuickRectangle') else item.property('background')
                        if background is not None:
                            color = background.property('interactionColor') or background.property('color')
                            if color is not None:
                                backgrounds[name] = list(color.getRgb())
                        if item.property('indicatorOffset') is not None:
                            indicator = item.property('indicator')
                            p = indicator.mapToScene(QPointF())
                            interiors[name] = dict(indicator=dict(x=p.x(), y=p.y(), width=indicator.width(), height=indicator.height()))
                        if item.property('contentHeight') is not None and item.property('text') is not None and item.property('font') is not None:
                            interiors[name] = dict(textHeight=item.property('contentHeight'))
                        if name in ('createSecurityGroup', 'adminCreateDocument'):
                            icon = next(child for child in SidebarEditorQmlTests.descendants(item) if child.property('name') == 'person-add')
                            assert icon.isVisible() and icon.width() > 0
                            p = icon.mapToScene(QPointF())
                            label_item = next(child for child in SidebarEditorQmlTests.descendants(item) if child is not item and child.property('text') == item.property('text') and 'Label' in child.metaObject().className())
                            interiors[name] = dict(icon=dict(x=p.x(), y=p.y(), width=icon.width(), height=icon.height()), labelWidth=label_item.width(), spacing=item.property('spacing'))
                        if name.endswith('ScrollBar'):
                            assert item.width() == 12
                            interiors[name] = dict(visible=item.isVisible(), size=item.property('size'))
                    filename = f'{"users" if USERS else "groups"}-qml-{mode}-{language}-{width}-{case["phase"]}.png'
                    assert window.grabWindow().save(str(OUT / filename))
                    samples.append(dict(mode=mode, language=language, width=width, height=height, phase=case['phase'], image=filename, scene=scene, state=state, boxes=boxes, styles=styles, backgrounds=backgrounds, interiors=interiors))
                admin._worker = None
                if USERS: editor._worker = None
                assert not fixture.fixture.warnings, fixture.fixture.warnings
                window.close()
                window.deleteLater()
                frame(fixture.window)
                fixture.doCleanups()
                fixture = None
finally:
    if fixture is not None:
        fixture.admin._worker = None
        fixture.doCleanups()
assert initial_sources == source_hashes(REPO, TH, native_names), 'Sources changed during native capture'
hashes, native_sources = initial_sources
(OUT / ('.capture-'+requested+'.json')).write_text(json.dumps(dict(style=QQuickStyle.name(), sha256=hashes, nativeSources=native_sources, captures=samples), ensure_ascii=False, indent=2), encoding='utf-8')
print(f'Captured {len(samples)} production {"Users" if USERS else "Groups"} states in native Qt')
