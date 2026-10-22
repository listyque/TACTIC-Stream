"""Measure original and Frame native dock headers with actual input."""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
TH = Path('D:/grav/Tactic Stream/TH')
HERE = Path(__file__).resolve().parent
OUT = HERE / 'output/docks'
OUT.mkdir(parents=True, exist_ok=True)
os.environ.update(QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software', QSG_RENDER_LOOP='basic')
sys.path[:0] = [str(TH), str(ROOT / 'tools/frame_admin')]
from PySide6.QtCore import QCoreApplication, QEvent, QObject, QPointF, QUrl, Slot
from PySide6.QtGui import QFont
from PySide6.QtQml import QQmlComponent, QQmlEngine
from tests.qt_application import gui_test_application
from tests.profile_ui_responsiveness import frame
from tests.test_sidebar_editor_qml import SidebarEditorQmlTests
from thlib.ui.icon_font import qml_icon_bindings
from native_capture import click, source_hashes


class Commands(QObject):
    def __init__(self):
        super().__init__()
        self.calls = []

    @Slot(str)
    def raise_panel(self, identity):
        self.calls.append(('raise', identity))

    @Slot(str)
    def close_panel(self, identity):
        self.calls.append(('close', identity))

    @Slot(str)
    def detach_panel(self, identity):
        self.calls.append(('detach', identity))

    @Slot(str)
    def open_help(self, topic):
        self.calls.append(('help', topic))


def geometry(item, parent):
    point = item.mapToItem(parent, QPointF())
    return dict(x=point.x(), y=point.y(), width=item.width(), height=item.height())


def main():
    app = gui_test_application()
    app.setFont(QFont('Segoe UI', 10))
    icons = qml_icon_bindings(TH, app)
    rows = []
    for original in (True, False):
        qml = HERE / 'reference/main/thlib/ui/qml' if original else TH / 'thlib/ui/qml'
        assert qml.is_dir(), 'Run check_main.py first to extract the archived original'
        for width in (280, 600, 1200):
            for stacked in (False, True):
                for floating in (False, True):
                    engine, commands, warnings = QQmlEngine(), Commands(), []
                    engine.warnings.connect(lambda errors: warnings.extend(error.toString() for error in errors))
                    for name, value in {**icons, 'dockModel': commands, 'windowModel': commands}.items():
                        engine.rootContext().setContextProperty(name, value)
                    component = QQmlComponent(engine)
                    component.setData(('import QtQuick\nimport QtQuick.Controls\nimport "' + qml.as_uri() + '" as TH\n'
                        'ApplicationWindow{id:window;visible:true;width:600;height:200;color:theme.workspace;'
                        'property bool stacked:false;property bool floating:false;'
                        'TH.Theme{id:theme;dark:true;clickAnimationsEnabled:false;hoverAnimationsEnabled:false;fadeAnimationsEnabled:false;popupAnimationsEnabled:false}'
                        'TH.DockPanel{id:panel;host:window.contentItem;theme:theme;panelId:"notes";kind:"notes";title:"Task Inspector";'
                        'panelX:0;panelY:0;panelWidth:1;panelHeight:1;modelVisible:true;panelOpen:true;stackActive:true;closable:true;stackOrder:0;'
                        'dockArea:window.floating?"floating":"right";canResizeLeft:false;canResizeRight:false;canResizeTop:false;canResizeBottom:false;'
                        'stackSize:window.stacked?3:1;stackPanels:window.stacked?'
                        '[{panelId:"notes",title:"Task Inspector",kind:"notes",active:true},{panelId:"snapshot",title:"Snapshots",kind:"snapshot",active:false},{panelId:"description",title:"Description",kind:"description",active:false}]:[];'
                        'contentComponent:Component{Item{}}}}').encode(), QUrl())
                    assert component.isReady(), [error.toString() for error in component.errors()]
                    window = component.createWithInitialProperties(dict(width=width, stacked=stacked, floating=floating))
                    assert window
                    try:
                        frame(window)
                        items = list(SidebarEditorQmlTests.descendants(window.contentItem()))
                        grip = next(item for item in items if item.objectName() == 'dockStackDrag_notes')
                        header = grip.parentItem().parentItem()
                        controls = {'dockGrip': geometry(grip, header)}
                        for name, tip, operation in [('dockHelp', 'Help for this dock', 'help'), ('dockDetach', 'Detach ', 'detach'), ('dockClose', 'Close ', 'close')]:
                            control = next(item for item in items if item.isVisible() and str(item.property('toolTip') or '').startswith(tip))
                            controls[name] = geometry(control, header)
                            before = len([call for call in commands.calls if call[0] == operation])
                            click(window, control)
                            assert len([call for call in commands.calls if call[0] == operation]) == before + 1
                        filename = f'{"original" if original else "frame"}-{width}-{int(stacked)}-{int(floating)}.png'
                        frame(window)
                        assert window.grabWindow().copy(0, 0, width, 60).save(str(OUT / filename))
                        rows.append(dict(original=original, width=width, stacked=stacked, floating=floating, controls=controls, image=filename))
                        assert not warnings, warnings
                    finally:
                        window.close()
                        window.deleteLater()
                        engine.deleteLater()
                        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    for current in [row for row in rows if not row['original']]:
        original = next(row for row in rows if row['original'] and all(row[key] == current[key] for key in ('width', 'stacked', 'floating')))
        assert current['controls'] == original['controls'], (current, original)
    shared, native = source_hashes(ROOT, TH, ['thlib/ui/qml/shell/docks/DockPanel.qml', 'thlib/ui/qml/shell/docks/DockTitleLabel.qml', 'thlib/ui/qml/shell/docks/DockTitleDrag.qml', 'thlib/ui/qml/shell/docks/DockHost.qml', 'thlib/ui/qml/shell/docks/DockResizeEdge.qml', 'thlib/ui/workspace_models/docks_resizing.py'])
    (OUT / 'native.json').write_text(json.dumps(dict(captures=rows, sha256=shared, nativeSources=native), indent=2), encoding='utf-8')
    print('Native dock headers: 12 original/Frame pairs; Help/Detach/Close first-click passed')


if __name__ == '__main__':
    main()
