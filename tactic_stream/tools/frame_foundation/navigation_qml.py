"""Original and shared neutral navigation rows on identical records."""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
TH = Path('D:/code/th_codex')
OUT = Path(__file__).resolve().parent / 'output/navigation'
OUT.mkdir(parents=True, exist_ok=True)
os.environ.update(QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software', QSG_RENDER_LOOP='basic')
sys.path[:0] = [str(TH), str(ROOT / 'tools/frame_admin')]
from PySide6.QtCore import QCoreApplication, QEvent, QUrl, QPointF
from PySide6.QtQml import QQmlEngine, QQmlComponent
from tests.qt_application import gui_test_application
from tests.profile_ui_responsiveness import frame
from thlib.ui.icon_font import qml_icon_bindings
from native_capture import snapshot, source_hashes
from tests.test_sidebar_editor_qml import SidebarEditorQmlTests


def main():
    app = gui_test_application()
    icons = qml_icon_bindings(TH, app)
    captures = []
    for original in (True, False):
        qml = ROOT / 'tools/frame_foundation/reference/thlib/ui/qml' if original else TH / 'thlib/ui/qml'
        for width in (200, 320):
            for depth in (0, 3):
                for selected in (False, True):
                    engine = QQmlEngine()
                    warnings = []
                    engine.warnings.connect(lambda errors: warnings.extend(error.toString() for error in errors))
                    for name, value in icons.items():
                        engine.rootContext().setContextProperty(name, value)
                    source = f'''import QtQuick
import QtQuick.Controls
import "{qml.as_uri()}" as TH
ApplicationWindow {{
    visible:true; width:{width}; height:176
    TH.Theme {{id:theme;dark:true;clickAnimationsEnabled:false;hoverAnimationsEnabled:false;fadeAnimationsEnabled:false;popupAnimationsEnabled:false}}
    Column {{width:parent.width
        TH.SidebarTreeRow {{objectName:"row0";theme:theme;width:parent.width;height:implicitHeight;rowType:"section";title:"Assets";expanded:true;depth:{depth}}}
        TH.SidebarTreeRow {{objectName:"row1";theme:theme;width:parent.width;height:implicitHeight;title:"Sample asset";glyph:"cube";badge:7;selected:{str(selected).lower()};depth:{depth}}}
        TH.SidebarTreeRow {{objectName:"row2";theme:theme;width:parent.width;height:implicitHeight;rowType:"separator"}}
        TH.SidebarTreeRow {{objectName:"row3";theme:theme;width:parent.width;height:implicitHeight;title:"Long navigation title for an example object";glyph:"folder";badge:120;depth:{depth}}}
    }}
}}'''
                    component = QQmlComponent(engine)
                    component.setData(source.encode(), QUrl())
                    assert component.isReady(), [error.toString() for error in component.errors()]
                    window = component.create()
                    assert window
                    try:
                        for _ in range(2):
                            frame(window)
                        image = f'{"original" if original else "native"}-{width}-{depth}-{int(selected)}.png'
                        assert window.grabWindow().save(str(OUT / image))
                        data = snapshot(window)
                        data['rows'] = []
                        for row in [item for item in SidebarEditorQmlTests.descendants(window.contentItem()) if item.objectName() in ('row0','row1','row2','row3')]:
                            boxes = {}
                            for item in SidebarEditorQmlTests.descendants(row):
                                name = item.objectName()
                                if name not in ('sidebarRowSurface','sidebarRowTitle','navigationRowIcon','navigationRowBadge','navigationRowCount','navigationSeparator'):
                                    continue
                                point = item.mapToItem(row, QPointF())
                                boxes[name] = dict(x=point.x(),y=point.y(),width=item.width(),height=item.height())
                            data['rows'].append(dict(id=row.objectName(),height=row.height(),boxes=boxes))
                        assert not warnings, warnings
                        captures.append(dict(original=original, width=width, depth=depth, selected=selected, image=image, **data))
                    finally:
                        window.close()
                        window.deleteLater()
                        engine.deleteLater()
                        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    shared, native = source_hashes(ROOT, TH, ['thlib/ui/qml/controls/NavigationRow.qml'])
    (OUT / 'native.json').write_text(json.dumps(dict(captures=captures, sha256=shared, nativeSources=native), indent=2), encoding='utf-8')
    print('Navigation: 8 original/current native row pairs, zero warnings.')


if __name__ == '__main__':
    main()
