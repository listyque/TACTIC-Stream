"""Real pointer/keyboard focus must reveal complete Frame fields in native scroll forms."""
import os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
TH=Path('D:/grav/Tactic Stream/TH')
os.environ.update(QT_QPA_PLATFORM='offscreen',QT_QUICK_BACKEND='software',QT_FONT_DPI='96')
sys.path[:0]=[str(TH),str(ROOT/'tools/frame_admin')]
from PySide6.QtCore import QUrl
from PySide6.QtGui import QFont
from PySide6.QtQml import QQmlComponent,QQmlEngine
from tests.qt_application import gui_test_application
from tests.profile_ui_responsiveness import frame
from native_capture import controls,click
app=gui_test_application();app.setFont(QFont('Segoe UI',10))
engine=QQmlEngine();warnings=[]
engine.warnings.connect(lambda errors:warnings.extend(error.toString() for error in errors))
component=QQmlComponent(engine)
component.setData(b"""import QtQuick
import QtQuick.Controls
import "file:///D:/grav/Tactic Stream/TH/thlib/ui/qml" as TH
import "file:///D:/grav/Tactic Stream/TH/thlib/ui/qml/tactic_frame" as Frame
import "file:///D:/grav/Tactic Stream/TH/thlib/ui/qml/tactic_frame/core/frame.mjs" as F
ApplicationWindow{visible:true;width:360;height:740
TH.Theme{id:theme;dark:true;clickAnimationsEnabled:false;hoverAnimationsEnabled:false}
Frame.FrameView{anchors.fill:parent;theme:theme;scene:({nodes:[F.node("Scroll","form",{x:0,y:344,width:348,height:384},{contentHeight:900,children:[F.node("Field","first",{x:12,y:0,width:320,height:38},{text:"first",enabled:true}),F.node("Field","partial",{x:12,y:360,width:320,height:38},{text:"partial",enabled:true}),F.node("Field","last",{x:12,y:500,width:320,height:38},{text:"last",enabled:true})]})]})}
}""",QUrl.fromLocalFile(str(ROOT/'tools/frame_admin/FocusHarness.qml')))
assert component.isReady(),[e.toString() for e in component.errors()]
window=component.create();assert window
try:
 frame(window);first=controls(window)['first'];click(window,controls(window)['partial']);assert controls(window)['form'].property('contentY')==14
 # Keyboard navigation uses the same full-control visibility rule.
 from PySide6.QtCore import Qt
 from PySide6.QtTest import QTest
 QTest.keyClick(window,Qt.Key_Tab);frame(window);assert controls(window)['form'].property('contentY')==154
 first.forceActiveFocus();frame(window);assert controls(window)['form'].property('contentY')==0
 assert not warnings,warnings
 print('Frame focus: pointer, Tab and programmatic focus reveal complete fields')
finally:window.close();window.deleteLater();app.processEvents()
