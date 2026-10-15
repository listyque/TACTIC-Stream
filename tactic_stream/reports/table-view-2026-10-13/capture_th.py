"""Capture the actual current TH completion presenter, without a server/DB."""
import os
import json
from pathlib import Path
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['QT_QUICK_BACKEND'] = 'software'
os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication, QFontDatabase
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

HERE = Path(__file__).resolve().parent
STREAM = HERE.parents[1]
QML = Path('D:/code/th_codex/thlib/ui/qml')
app = QGuiApplication([])
for name in ['segoeui.ttf', 'seguisb.ttf']:
    QFontDatabase.addApplicationFont('C:/Windows/Fonts/' + name)
engine = QQmlEngine()
source = '''import QtQuick
import QtQuick.Controls
import "." as App
ApplicationWindow {
 id: root; width:240; height:208; visible:true; color:nativeTheme.workspace
 App.Theme { id:nativeTheme; dark:true }
 Column {
  Repeater {
   model:[0,25,75,100]
   App.TacticCompletionCell {
    required property int modelData
    objectName:"cell_"+modelData; theme:nativeTheme; width:240; height:52
    percent:modelData; text:Number(modelData).toFixed(1)+"%"
   }
  }
 }
}
'''
component = QQmlComponent(engine)
component.setData(source.encode(), QUrl.fromLocalFile(str(QML / '_TableCatalogCapture.qml')))
window = component.create()
assert window, [e.toString() for e in component.errors()]
try:
    QTest.qWait(200)
    items = {}
    pending = [window.contentItem()]
    while pending:
        item = pending.pop()
        items[item.objectName()] = item
        pending.extend(item.childItems())
    values = []
    for percent in [0, 25, 75, 100]:
        cell = items['cell_' + str(percent)]
        track = cell.childItems()[0]
        fill = cell.findChild(QQuickItem, 'tableCellCompletionFill')
        assert track.width() == 220 and track.height() == 18 and track.x() == 10
        assert fill.width() == 220 * percent / 100
        label = next(item for item in track.childItems() if item.property('text') is not None)
        values.append(dict(percent=percent, cellWidth=cell.width(), cellHeight=cell.height(),
                           trackWidth=track.width(), trackHeight=track.height(), margin=track.x(),
                           fillWidth=fill.width(), trackColor=track.property('color').name(),
                           fillColor=fill.property('color').name(), labelColor=label.property('color').name(),
                           captionPoints=label.property('font').pointSizeF(), captionWeight=int(label.property('font').weight()),
                           backgroundColor=window.color().name()))
    for folder in [STREAM/'frontend/public/help/media', STREAM/'src/tactic_stream/web/help/media']:
        folder.mkdir(parents=True, exist_ok=True)
        assert window.grabWindow().save(str(folder/'table-widget-completion-th.png'))
    (HERE/'completion-th-measurements.json').write_text(json.dumps(values,indent=2),encoding='utf-8')
    print(json.dumps(values))
finally:
    window.close()
    window.deleteLater()
    engine.deleteLater()
    app.processEvents()
