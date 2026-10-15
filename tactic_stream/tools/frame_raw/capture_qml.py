"""Production Raw database and its separate native Cell editor, isolated data."""
import json
import os
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
TH = Path('D:/code/th_codex')
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
from tests.test_raw_database import RawDatabaseQmlTests
from tests.profile_ui_responsiveness import frame
from native_capture import click, choose, controls, snapshot, text, value, source_hashes

native_names = ['thlib/ui/qml/AdminRawDatabaseView.qml', 'thlib/ui/qml/RawCellEditorView.qml', 'thlib/ui/admin/raw_database.py', 'thlib/ui/admin/editor.py', 'thlib/ui/frame_models.py']
initial_sources = source_hashes(REPO, TH, native_names)
RawDatabaseQmlTests.setUpClass()
for name in ('segoeui.ttf', 'seguisb.ttf'):
    QFontDatabase.addApplicationFont('C:/Windows/Fonts/' + name)
samples = []
cases = json.loads((HERE / 'cases.json').read_text())
quick = os.environ.get('FRAME_CAPTURE_QUICK') == '1'
for mode in ('dark',) if quick else ('dark', 'light'):
    for language in ('en',) if quick else ('en', 'ru'):
        for width, height in ((1100, 740),) if quick else ((1100, 740), (800, 740), (360, 740)):
            fixture = RawDatabaseQmlTests()
            fixture.setUp()
            editor, host, window = fixture.editor, fixture.fixture.fixture, None
            try:
                if language == 'en':
                    host.app.removeTranslator(host.translator)
                    host.engine.retranslate()
                parent_theme = fixture.fixture.item('rawDatabasePage').property('theme')
                parent_theme.setProperty('dark', mode == 'dark')
                fixture.fixture.item('rawDatabasePage').parentItem().setProperty('active', False)
                frame(fixture.fixture.window)
                editor._document = dict(offset=0, rows=[dict(key=[index + 1], revision='row-' + str(index), values=dict(id=index + 1, value='Row ' + str(index), number=7, password='[redacted]')) for index in range(50)])
                editor._metadata.update(total=145, offset=0)
                catalog = dict(catalog=editor.catalog, identity=editor.identity, revision='table-revision', metadata=editor.metadata, document=editor.document, canWrite=True)
                (OUT / 'catalog.json').write_text(json.dumps(catalog, ensure_ascii=False), encoding='utf-8')
                editor._document_loaded()
                editor.stateChanged.emit()
                component = QQmlComponent(host.engine, QUrl.fromLocalFile(str(HERE / 'RawHarness.qml')))
                assert component.isReady(), [error.toString() for error in component.errors()]
                window = component.create()
                assert window is not None, [error.toString() for error in component.errors()]
                window.resize(width, height)
                window.setProperty('dark', mode == 'dark')
                window.setProperty('language', language)
                frame(window)

                def cell_window():
                    result = fixture.cell_window()
                    result.resize(640 if width > 700 else width, 440 if width > 700 else height)
                    frame(result)
                    controls(result)['rawCellEditorPage'].setProperty('language', language)
                    frame(result)
                    return result

                for case in cases:
                    for action in case['actions']:
                        target = cell_window() if action.get('window') == 'cell' else window
                        if action['type'] == 'state':
                            editor._can_write = action['value'] != 'readonly'
                            editor._uncertain = action['value'] == 'uncertain'
                            editor._error = 'Connection failed' if editor._uncertain else ''
                            editor._worker = object() if action['value'] == 'busy' else None
                            editor.stateChanged.emit()
                        elif action['type'] == 'reveal':
                            grid = controls(window)['rawTableViewport']
                            node = value(grid.property('node'))
                            grid.setProperty('contentX', min(action['column'] * node['cellWidth'], max(0, grid.property('contentWidth') - grid.width())))
                            grid.setProperty('contentY', min(action['row'] * node['rowHeight'], max(0, grid.property('contentHeight') - grid.height())))
                        else:
                            item = controls(target)[action['id']]
                            if action['type'] == 'text':
                                text(target, item, action['value'])
                            elif action['type'] == 'choose':
                                choose(target, item, action['value'])
                            else:
                                click(target, item, window)
                        if target != window and editor.cell:
                            frame(target)
                        frame(window)
                    window.blur()
                    QTest.mouseMove(window, QPointF(width - 1, height - 1).toPoint())
                    frame(window)
                    parent = dict(scene=json.loads(window.property('sceneJson')), state=json.loads(window.property('stateJson')))
                    if not editor.cell:
                        image = f'raw-qml-{mode}-{language}-{width}-{case["phase"]}.png'
                        assert window.grabWindow().save(str(OUT / image))
                        samples.append(dict(mode=mode, language=language, width=width, height=height, phase=case['phase'], image=image, viewport=dict(width=width,height=height), **parent, **snapshot(window)))
                    if editor.cell:
                        modal = cell_window()
                        page = controls(modal)['rawCellEditorPage']
                        modal.contentItem().forceActiveFocus()
                        QTest.mouseMove(modal, QPointF(modal.width() - 1, modal.height() - 1).toPoint())
                        frame(modal)
                        phase = case['phase'] + '-cell'
                        image = f'raw-qml-{mode}-{language}-{width}-{phase}.png'
                        assert modal.grabWindow().save(str(OUT / image))
                        samples.append(dict(mode=mode, language=language, width=width, height=height, phase=phase, image=image, viewport=dict(width=modal.width(),height=modal.height()), parent=parent, scene=value(page.property('frameScene')), state=dict(ui=value(page.property('ui')), readonly=editor.cell['readonly']), **snapshot(modal)))
                assert not host.warnings, host.warnings
            finally:
                editor._worker = None
                editor.cancel_cell()
                if window:
                    window.close()
                    window.deleteLater()
                    frame(fixture.fixture.window)
                fixture.doCleanups()
assert initial_sources == source_hashes(REPO, TH, native_names), 'Sources changed during native capture'
hashes, native = initial_sources
(OUT / 'qml.json').write_text(json.dumps(dict(sha256=hashes, nativeSources=native, captures=samples), ensure_ascii=False, indent=2), encoding='utf-8')
print(f'Captured {len(samples)} Raw database / Cell editor states')
