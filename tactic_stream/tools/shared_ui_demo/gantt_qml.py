"""Isolated native Gantt; captures real pointer operations without a server."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
TH = Path('D:/grav/Tactic Stream/TH')
parser = argparse.ArgumentParser()
parser.add_argument('--capture', action='store_true')
parser.add_argument('--language', choices=('en', 'ru'), default='ru')
parser.add_argument('--mode', choices=('dark', 'light'), default='dark')
args = parser.parse_args()
if args.capture:
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['QT_QUICK_BACKEND'] = 'software'
os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
os.environ['QT_FONT_DPI'] = '96'
from PySide6.QtCore import QPoint, QPointF, QUrl, Qt
from PySide6.QtGui import QGuiApplication, QFont, QFontDatabase, QFontInfo, QWheelEvent
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
sys.path.insert(0, str(TH))
from thlib.ui.icon_font import qml_icon_bindings

app = QGuiApplication([])
for name in ('segoeui.ttf', 'seguisb.ttf'):
    QFontDatabase.addApplicationFont('C:/Windows/Fonts/' + name)
app.setFont(QFont('Segoe UI', 9))
engine = QQmlEngine()
for name, value in qml_icon_bindings(TH, engine).items():
    engine.rootContext().setContextProperty(name, value)
spec = json.loads((HERE / 'gantt.json').read_text(encoding='utf-8'))
fixture = json.loads((HERE.parent.parent / 'frontend/tests/task_schedule_fixture.json').read_text(encoding='utf-8'))
palettes = json.loads((HERE / 'palettes.json').read_text(encoding='utf-8'))
cases = json.loads((HERE / 'gantt_cases.json').read_text(encoding='utf-8'))
for name, value in [('ganttSpec', spec), ('ganttFixture', fixture)]:
    engine.rootContext().setContextProperty(name, value)
OUT = HERE / 'output'
OUT.mkdir(exist_ok=True)
warnings = []
components = []
engine.warnings.connect(lambda messages: warnings.extend(message.toString() for message in messages))


def make(mode, language, width, height):
    for name, value in [('demoDark', mode == 'dark'), ('demoLanguage', language), ('demoPalette', palettes[mode])]:
        engine.rootContext().setContextProperty(name, value)
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(HERE / 'GanttDemo.qml')))
    components.append(component)
    if component.isError():
        raise RuntimeError('\n'.join(error.toString() for error in component.errors()))
    window = component.create()
    assert window is not None, '\n'.join(error.toString() for error in component.errors())
    window.setWidth(width)
    window.setHeight(height)
    window.show()
    QTest.qWait(100)
    return window


def prop(window, name):
    return window.property(name).toVariant()


def nodes(window, prefix='node:'):
    result = {}
    pending = [window.contentItem()]
    while pending:
        current = pending.pop()
        if current.objectName().startswith(prefix):
            result[current.objectName()[len(prefix):]] = current
        pending.extend(current.childItems())
    return result


def item(window, name):
    return nodes(window)[name]


def point(window, target):
    node = item(window, target)
    return node.mapToScene(QPointF(node.width() / 2, node.height() / 2)).toPoint()


def action(window, event):
    if event['type'] == 'key':
        item(window, event['target']).forceActiveFocus()
        QTest.keyClick(window, {'ArrowLeft': Qt.Key_Left}[event['code']])
        QTest.qWait(35)
        return
    if event['type'] == 'wheel':
        pt = QPointF(window.width() / 2, window.height() / 2)
        modifiers = Qt.ShiftModifier if event.get('shift') else Qt.ControlModifier if event.get('ctrl') else Qt.NoModifier
        wheel = QWheelEvent(pt, pt, QPoint(), QPoint(0, -event['dy']), Qt.NoButton, modifiers, Qt.ScrollUpdate, False)
        QGuiApplication.sendEvent(window, wheel)
        QTest.qWait(75)
        return
    start = point(window, event['target'])
    if event['type'] == 'click':
        # A check's input is 19px wide even when its label spans the row.
        if event['target'] == 'working-days':
            node = item(window, event['target'])
            start = node.mapToScene(QPointF(9, node.height() / 2)).toPoint()
        QTest.mouseClick(window, Qt.LeftButton, pos=start)
    elif event['type'] == 'drag':
        day = prop(window, 'scene')['geometry']['day']
        dx = event.get('dx', event.get('days', 0) * day)
        dy = event.get('dy', 0)
        QTest.mousePress(window, Qt.LeftButton, pos=start)
        for step in range(1, 5):
            QTest.mouseMove(window, start + QPoint(round(dx * step / 4), round(dy * step / 4)))
            QTest.qWait(15)
        if event.get('cancel'):
            QTest.keyClick(window, Qt.Key_Escape)
        QTest.mouseRelease(window, Qt.LeftButton, pos=start + QPoint(round(dx), round(dy)))
    else:
        raise ValueError(event)
    QTest.qWait(35)


def capture(window, mode, language, width, height, phase):
    QTest.mouseMove(window, QPoint(width - 3, height - 2))
    QTest.qWait(30)
    scene = prop(window, 'scene')
    boxes = {}
    controls = nodes(window)
    paints = nodes(window, 'paint:')
    styles = {}
    for layer in scene['layers']:
        for node in layer['nodes']:
            control = controls[node['id']]
            pt = control.mapToScene(QPointF(0, 0))
            boxes[node['id']] = {'x': pt.x(), 'y': pt.y(), 'width': control.width(), 'height': control.height()}
            paint = paints[node['id']]
            style = {}
            if node['kind'] == 'Rectangle':
                style['background'] = paint.property('color').getRgb()
            else:
                font = paint.property('font')
                style['fontSize'] = QFontInfo(font).pixelSize()
                style['fontWeight'] = int(font.weight())
                color = paint.property('contentColor') if node['kind'] == 'Button' else paint.property('contentItem').property('color') if node['kind'] == 'CheckBox' else paint.property('color')
                style['color'] = color.getRgb()
            styles[node['id']] = style
    image = f'gantt-qml-{mode}-{language}-{width}-{phase}.png'
    assert window.grabWindow().save(str(OUT / image))
    scene_hash = hashlib.sha256(window.property('sceneJson').encode('utf-8')).hexdigest()
    return {'mode': mode, 'language': language, 'width': width, 'height': height, 'phase': phase, 'image': image, 'sceneHash': scene_hash, 'boxes': boxes, 'styles': styles, 'state': prop(window, 'demoState')}


if args.capture:
    captures = []
    for mode in ('dark', 'light'):
        for language in ('en', 'ru'):
            for width, height in ((1100, 660), (840, 560)):
                window = make(mode, language, width, height)
                for case in cases:
                    for event in case['actions']:
                        action(window, event)
                    sample = capture(window, mode, language, width, height, case['phase'])
                    if case['phase'] == 'move':
                        assert sample['state']['tasks'][0]['start'] == '2026-10-04 09:13:00', sample['state']
                    if case['phase'] == 'resize-end':
                        assert sample['state']['tasks'][0]['end'] == '2026-10-11 17:20:00', sample['state']
                    if case['phase'] == 'resize-start':
                        assert sample['state']['tasks'][0]['start'] == '2026-10-05 09:13:00', sample['state']
                    if case['phase'] == 'progress':
                        assert sample['state']['tasks'][0]['progress'] > 35, sample['state']
                    if case['phase'] == 'cancel':
                        assert sample['state']['tasks'] == captures[-1]['state']['tasks']
                    if case['phase'] == 'batch':
                        assert sample['state']['workingDays'] and len(sample['state']['selected']) == 1
                        assert sample['state']['tasks'][0]['start'] == '2026-10-02 09:13:00'
                    if case['phase'] == 'schedule':
                        assert sample['state']['tasks'][3]['start'] == '2026-10-12 09:00:00'
                        assert sample['state']['tasks'][3]['end'] == '2026-10-16 17:00:00'
                    if case['phase'] == 'keyboard-progress':
                        assert sample['state']['tasks'][0]['progress'] == captures[-1]['state']['tasks'][0]['progress'] - 1
                    if case['phase'] == 'undo':
                        assert sample['state']['tasks'] == captures[-2]['state']['tasks']
                    if case['phase'] == 'redo':
                        assert sample['state']['tasks'] == captures[-2]['state']['tasks']
                    if case['phase'] == 'select-all':
                        assert len(sample['state']['selected']) == len(sample['state']['tasks'])
                    if case['phase'] == 'wheel-y':
                        assert sample['state']['y'] < captures[-1]['state']['y']
                    if case['phase'] == 'wheel-x':
                        assert sample['state']['x'] > captures[-1]['state']['x']
                    if case['phase'] == 'wheel-zoom':
                        assert sample['state']['zoom'] < captures[-1]['state']['zoom']
                    captures.append(sample)
                window.close()
                window.deleteLater()
                QTest.qWait(20)
    assert not warnings, '\n'.join(warnings)
    hashes = {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest() for name in ('gantt.json', 'gantt.state.mjs', 'gantt.ui.mjs', 'gantt_cases.json', 'GanttDemo.qml', 'gantt_qml.py', 'palettes.json')}
    (OUT / 'gantt-qml-measurements.json').write_text(json.dumps({'captures': captures, 'sha256': hashes}, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(f'PASS: {len(captures)} native Gantt states; real drag, resize, progress, cancel, batch, undo/redo, scroll, zoom, collapse')
else:
    window = make(args.mode, args.language, spec['viewport']['width'], spec['viewport']['height'])
    app.exec()
