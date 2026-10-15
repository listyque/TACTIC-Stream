"""Current TH table presenters with the same typed value samples as Vue."""
import json
import os
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
ROOT = HERE.parents[1]
QML = Path('D:/code/th_codex/thlib/ui/qml')
samples = json.loads((ROOT/'frontend/tests/fixtures/table-widget-catalog.json').read_text(encoding='utf-8'))
app = QGuiApplication([])
for name in ['segoeui.ttf', 'seguisb.ttf', 'consola.ttf']:
    QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)
engine = QQmlEngine()
measurements = []
for sample in [s for s in samples if s['key'] in {'array', 'xml', 'json', 'snapshot_version'}]:
    cell = sample['value']
    source = '''import QtQuick
import QtQuick.Controls
import "." as App
ApplicationWindow {
 id: root; width:320; height:128; visible:true; color:nativeTheme.panel
 App.Theme { id:nativeTheme; dark:true }
 function plainText(item) { return item.textFormat === TextEdit.PlainText }
 App.TacticTableCellDisplay {
  objectName:"sample"; x:CELLX; y:CELLY; width:CELLWIDTH; height:CELLHEIGHT
  theme:nativeTheme; controller:({}); columnsController:({}); userModel:({})
  nodeId:"fixture"; kind:KIND; cell:CELL; textValue:VALUE; columnIndex:1
  previewActive:false; previewUrl:""; previewRevealed:false; title:"Sample"
  accent:""; comments:0; tasks:0; displayOptions:OPTIONS
 }
}
'''
    structured = sample['element']['cell']['kind'] == 'structured'
    source = source.replace('CELLX', '10' if structured else '0').replace('CELLY', '10' if structured else '0').replace('CELLWIDTH', '300' if structured else '320').replace('CELLHEIGHT', '108' if structured else '128')
    source = source.replace('KIND', json.dumps(sample['element']['cell']['kind'])).replace('CELL', json.dumps(cell)).replace('VALUE', json.dumps(cell['text'])).replace('OPTIONS', json.dumps(sample['element']['display']['options']))
    component = QQmlComponent(engine)
    component.setData(source.encode(), QUrl.fromLocalFile(str(QML/'_UsedValueCapture.qml')))
    window = component.create()
    assert window, [e.toString() for e in component.errors()]
    try:
        QTest.qWait(150)
        pending = [window.contentItem()]
        reader = None
        while pending:
            item = pending.pop()
            pending.extend(item.childItems())
            if item.objectName() == 'tableStructuredText':
                reader = item
        if sample['element']['cell']['kind'] == 'structured':
            assert reader is not None and reader.property('readOnly')
            assert reader.property('text') == cell['text']
            assert window.plainText(reader)
            font = reader.property('font')
            measurements.append(dict(key=sample['key'], width=300, height=108, fontFamily=font.family(), points=font.pointSizeF(), readOnly=True))
        else:
            measurements.append(dict(key=sample['key'], width=300, height=108, kind='text'))
        for folder in [ROOT/'frontend/public/help/media', ROOT/'src/tactic_stream/web/help/media']:
            assert window.grabWindow().save(str(folder/('table-widget-'+sample['key']+'-th.png')))
    finally:
        window.close()
        window.deleteLater()
        app.processEvents()
(HERE/'value-th-measurements.json').write_text(json.dumps(measurements,indent=2),encoding='utf-8')
engine.deleteLater()
app.processEvents()
print(json.dumps(measurements))
