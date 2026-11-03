"""Paired Access rules fixture: production QML, real input, no server writes."""
import json
import os
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
TH = Path(os.environ.get('TACTIC_HANDLER_ROOT', 'D:/grav/Tactic Stream/TH'))
HERE = Path(__file__).resolve().parent
OUT = HERE / 'output'
OUT.mkdir(exist_ok=True)
os.environ.update(QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software', QT_FONT_DPI='96')
os.environ.setdefault('QT_QUICK_CONTROLS_STYLE', 'Material')
sys.path[:0] = [str(TH), str(REPO / 'tools/frame_admin')]
from PySide6.QtCore import QPointF, Qt, QUrl
from PySide6.QtGui import QFontDatabase
from PySide6.QtQml import QQmlComponent
from PySide6.QtTest import QTest
from tests.test_admin_security_ui import AdminSecurityUiTests
from tests.security_matrix_fixture import seed_security
from tests.test_sidebar_editor_qml import SidebarEditorQmlTests
from tests.profile_ui_responsiveness import frame

from native_capture import assert_icons, source_hashes, click as click_visible
native_names = ['thlib/ui/qml/features/administration/security/AdminSecurityView.qml', 'thlib/ui/admin/security.py', 'thlib/ui/admin/editor.py', 'thlib/ui/admin/security_matrix.py']
initial_sources = source_hashes(REPO, TH, native_names)
AdminSecurityUiTests.setUpClass()
for name in ('segoeui.ttf', 'seguisb.ttf'):
    QFontDatabase.addApplicationFont('C:/Windows/Fonts/' + name)
samples = []
cases = json.loads((HERE / 'cases.json').read_text())
if os.environ.get('FRAME_CAPTURE_PHASES'):
    cases = [case for case in cases if case['phase'] in os.environ['FRAME_CAPTURE_PHASES'].split(',')]
quick = os.environ.get('FRAME_CAPTURE_QUICK') == '1'
for mode in ('dark',) if quick else ('dark', 'light'):
    for language in ('en',) if quick else ('en', 'ru'):
        for width, height in ((1100, 740),) if quick else ((1100, 740), (800, 740), (360, 740)):
            fixture = AdminSecurityUiTests()
            fixture.setUp()
            editor = fixture.editor
            window = None
            try:
                seed_security(editor, group_count=12, row_count=40)
                catalog = dict(document=editor.document, metadata=editor.metadata, canWrite=True, identity='demo', revision='fixture-revision')
                (OUT / 'catalog.json').write_text(json.dumps(catalog, ensure_ascii=False), encoding='utf-8')
                component = QQmlComponent(fixture.fixture.engine)
                harness = (HERE / 'SecurityHarness.qml').read_text(encoding='utf-8')
                harness = harness.replace('D:/grav/Tactic Stream/TH', TH.as_posix())
                component.setData(harness.encode('utf-8'), QUrl.fromLocalFile(str(HERE / 'SecurityHarness.qml')))
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

                def click(item):
                    click_visible(window, item)

                def choose(item, value):
                    options = item.property('model')
                    if hasattr(options, 'toVariant'):
                        options = options.toVariant()
                    target = next(index for index, option in enumerate(options) if option['value'] == value)
                    item.forceActiveFocus()
                    for _ in range((target - item.property('currentIndex')) % len(options)):
                        QTest.keyClick(window, Qt.Key_Down)
                        frame(window)

                for case in cases:
                    for action in case['actions']:
                        kind = action['type']
                        if kind == 'focus':
                            item = next(item for item in SidebarEditorQmlTests.descendants(window.contentItem()) if item.objectName() == action['id'] and item.isVisible())
                            item.forceActiveFocus()
                        elif kind == 'feature':
                            choose(controls()['adminBuiltinFeature'], action['value'])
                        elif kind == 'report':
                            choose(controls()['adminEffectiveView'], action['value'])
                        elif kind in ('scope', 'page'):
                            prefix = 'adminSecurityTab_' if kind == 'scope' else 'adminSecurityTechnicalPages_'
                            target = next((item for item in SidebarEditorQmlTests.descendants(window.contentItem())
                                           if item.objectName() == prefix + action['value'] and item.isVisible()), None)
                            if target is not None:
                                target.forceActiveFocus()
                                frame(window)
                            items = controls()
                            if prefix + action['value'] in items:
                                click(items[prefix + action['value']])
                            else:
                                choose(items['adminSecurityScope' if kind == 'scope' else 'adminSecurityTechnicalPages'], action['value'])
                        elif kind == 'state':
                            if action['value'] == 'clean':
                                import copy
                                editor._original = copy.deepcopy(editor.document)
                            if action['value'] == 'saved':
                                editor._message = 'Access rules saved on server'
                                editor.stateChanged.emit()
                                frame(window)
                                continue
                            editor._can_write = action['value'] != 'readonly'
                            editor._write_uncertain = action['value'] == 'uncertain'
                            editor._error = 'The save result is unknown. Reload access rules before trying again.' if editor._write_uncertain else ''
                            editor._worker = object() if action['value'] == 'busy' else None
                            editor.stateChanged.emit()
                        else:
                            assert action['id'] in controls(), (mode, language, width, case['phase'], action['id'])
                            item = controls()[action['id']]
                            click(item)
                            if kind == 'text':
                                QTest.keyClick(window, Qt.Key_A, Qt.ControlModifier)
                                QTest.keyClick(window, Qt.Key_Backspace)
                                for char in action['value']:
                                    QTest.keyClick(window, char)
                                    frame(window)
                        frame(window)
                    window.blur()
                    QTest.mouseMove(window, QPointF(width - 1, height - 1).toPoint())
                    frame(window)
                    assert_icons(window)
                    boxes, styles, interiors = {}, {}, {}
                    for name, item in controls().items():
                        pt = item.mapToScene(QPointF())
                        boxes[name] = dict(x=pt.x(), y=pt.y(), width=item.width(), height=item.height())
                        if item.property('text') is not None and item.property('font') is not None:
                            font, color = item.property('font'), item.property('color') or item.property('contentColor')
                            styles[name] = dict(fontSize=font.pixelSize(), weight=font.weight(), color=color.name() if color is not None else '')
                        if item.property('indicatorOffset') is not None:
                            indicator = item.property('indicator')
                            p = indicator.mapToScene(QPointF())
                            interiors[name] = dict(x=p.x(), y=p.y(), width=indicator.width(), height=indicator.height())
                    filename = f'security-qml-{mode}-{language}-{width}-{case["phase"]}.png'
                    assert window.grabWindow().save(str(OUT / filename))
                    samples.append(dict(mode=mode, language=language, width=width, height=height, phase=case['phase'], image=filename, scene=json.loads(window.property('sceneJson')), state=json.loads(window.property('stateJson')), boxes=boxes, styles=styles, interiors=interiors))
                assert not fixture.fixture.warnings, fixture.fixture.warnings
            finally:
                editor._worker = None
                if window:
                    window.close()
                    window.deleteLater()
                    frame(fixture.window)
                fixture.doCleanups()
assert initial_sources == source_hashes(REPO, TH, native_names), 'Sources changed during native capture'
hashes, native = initial_sources
(OUT / 'qml.json').write_text(json.dumps(dict(sha256=hashes, nativeSources=native, captures=samples), ensure_ascii=False, indent=2), encoding='utf-8')
print(f'Captured {len(samples)} Access rules states')
