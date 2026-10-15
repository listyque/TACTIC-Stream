"""The shared graph brick, driven by real native mouse and keyboard input."""
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
sys.path[:0] = [str(TH), str(REPO / 'tools/frame_admin')]
from PySide6.QtCore import QPoint, Qt, QUrl, QCoreApplication, QEvent
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtTest import QTest
from thlib.ui.icon_font import qml_icon_bindings
from tests.test_admin_groups_ui import AdminGroupsUiTests
from tests.profile_ui_responsiveness import frame
from native_capture import snapshot, source_hashes

AdminGroupsUiTests.setUpClass()
from PySide6.QtGui import QGuiApplication
app = QGuiApplication.instance()
icons = qml_icon_bindings(TH, app)
sources = source_hashes(REPO, TH, [])
quick = os.environ.get('FRAME_CAPTURE_QUICK') == '1'
samples = []
cases = [
    dict(phase='initial', actions=[]),
    dict(phase='selected', actions=[dict(type='click', x=120, y=160)]),
    dict(phase='moved', actions=[dict(type='drag', x=120, y=160, toX=65, toY=190)]),
    dict(phase='keyboard', actions=[dict(type='key', key='Right')]),
    dict(phase='zoomed', actions=[dict(type='clickControl', id='graphZoomIn')]),
    dict(phase='centered', actions=[dict(type='key', key='F')]),
    dict(phase='reset', actions=[dict(type='clickControl', id='graphReset')]),
    dict(phase='pending', actions=[dict(type='clickControl', id='graphOutput_a')]),
    dict(phase='cancelled', actions=[dict(type='key', key='Escape')]),
]
(OUT / 'cases.json').write_text(json.dumps(cases), encoding='utf8')
from native_capture import controls, click
for mode in ('dark',) if quick else ('dark', 'light'):
    for language in ('en',) if quick else ('en', 'ru'):
        for width, height in ((1100, 740),) if quick else ((1100, 740), (800, 740), (360, 740)):
            engine = QQmlEngine()
            warnings = []
            engine.warnings.connect(lambda errors: warnings.extend(e.toString() for e in errors))
            for name, value in icons.items(): engine.rootContext().setContextProperty(name, value)
            component = QQmlComponent(engine, QUrl.fromLocalFile(str(HERE / 'GraphHarness.qml')))
            assert component.isReady(), [e.toString() for e in component.errors()]
            window = component.createWithInitialProperties({'width': width, 'height': height})
            assert window
            try:
                window.resize(width, height); window.setProperty('dark', mode == 'dark'); window.setProperty('language', language); frame(window)
                for case in cases:
                    for action in case['actions']:
                        if action['type'] == 'clickControl': click(window, controls(window)[action['id']])
                        elif action['type'] == 'key':
                            # Toolbar clicks transfer focus. Focus the graph canvas for its shortcuts.
                            graph = controls(window)['testGraph']; graph.forceActiveFocus()
                            QTest.keyClick(window, getattr(Qt, 'Key_' + action['key']))
                        elif action['type'] == 'click': QTest.mouseClick(window, Qt.LeftButton, pos=QPoint(action['x'], action['y']))
                        else:
                            QTest.mousePress(window, Qt.LeftButton, pos=QPoint(action['x'], action['y']))
                            QTest.mouseMove(window, QPoint(action['toX'], action['toY'])); QTest.mouseRelease(window, Qt.LeftButton, pos=QPoint(action['toX'], action['toY']))
                        frame(window)
                    window.blur(); QTest.mouseMove(window, QPoint(width-1, height-1)); frame(window)
                    image = f'graph-qml-{mode}-{language}-{width}-{case["phase"]}.png'
                    assert window.grabWindow().save(str(OUT / image))
                    samples.append(dict(mode=mode, language=language, width=width, height=height, phase=case['phase'], image=image, scene=json.loads(window.property('sceneJson')), state=json.loads(window.property('stateJson')), **snapshot(window)))
                assert not warnings, warnings
            finally:
                window.close(); window.deleteLater(); engine.deleteLater(); QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
assert sources == source_hashes(REPO, TH, [])
(OUT / 'qml.json').write_text(json.dumps(dict(sha256=sources[0], nativeSources=sources[1], captures=samples), ensure_ascii=False, indent=2), encoding='utf8')
print(f'Captured {len(samples)} graph states')
