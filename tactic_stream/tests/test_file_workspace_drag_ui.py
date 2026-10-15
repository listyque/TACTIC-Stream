"""Native Qt drag feedback, hover disclosure and edge-scroll cancellation."""
import json
import os
from pathlib import Path
import sys
from time import monotonic
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_QUICK_BACKEND', 'software')
os.environ.setdefault('QSG_RENDER_LOOP', 'basic')
sys.path.insert(0, 'D:/code/th_codex')
from PySide6.QtCore import QCoreApplication, QEvent, QMimeData, QPoint, QUrl, Qt
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDragMoveEvent, QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtTest import QTest
from thlib.ui.icon_font import qml_icon_bindings

HANDLER=Path('D:/code/th_codex')
QML=HANDLER/'thlib/ui/qml'


class FileWorkspaceDragUiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QGuiApplication.instance() or QGuiApplication([])

    def test_hover_expand_edge_scroll_and_leaving_the_drag_stop_timers(self):
        engine=QQmlEngine();warnings=[]
        engine.warnings.connect(lambda values:warnings.extend(value.toString() for value in values))
        for name,value in qml_icon_bindings(HANDLER,engine).items():engine.rootContext().setContextProperty(name,value)
        theme_component=QQmlComponent(engine,QUrl.fromLocalFile(str(QML/'Theme.qml')))
        theme=theme_component.createWithInitialProperties({'dark':True})
        component=QQmlComponent(engine)
        component.setData(b'''import QtQuick
import "."
import "FileWorkspaceMenus.js" as Menus
ListView {
    id:list;required property var theme
    property int disclosures:0
    property var context:({busy:false,controller:{current_user:"admin",application_project:"files"},state:{workspace:"work",streams:[{code:"main",writable:true}]}})
    model:100;clip:true
    delegate:FileWorkspaceTreeRow {
        required property int index
        theme:list.theme;width:list.width
        row:({id:"target/"+index,kind:"change",code:"target"+index,number:index+1,state:"pending",owner:"admin",workspace:"work",stream:"main",depth:0,expanded:false})
        caption:"Target "+index;acceptsDrop:true
        dropReason:(payload,urls)=>Menus.dropReason(list.context,row,payload,urls)
        dropCaption:(payload,urls)=>Menus.dropCaption(row,payload,urls)
        onDisclosure:list.disclosures++
    }
}''',QUrl.fromLocalFile(str(QML/'drag-test.qml')))
        view=component.createWithInitialProperties({'theme':theme})
        self.assertIsNotNone(view,str(component.errors()))
        window=QQuickWindow();view.setParentItem(window.contentItem());window.resize(340,90);view.setWidth(340);view.setHeight(90);window.show()
        def until(predicate):
            deadline=monotonic()+2
            while not predicate() and monotonic()<deadline:QTest.qWait(10)
            self.assertTrue(predicate(),f'height={view.property("contentHeight")}; y={view.property("contentY")}; disclosures={view.property("disclosures")}; warnings={warnings}; rows='+repr([(item.objectName(),item.property('dragFeedback'),item.property('caption'),item.height()) for item in view.childItems()[0].childItems() if item.objectName().startswith('workspaceTreeRow')]))
        try:
            QTest.qWait(30)
            mime=QMimeData();mime.setData('application/x-tactic-file-workspace',json.dumps({'project':'files','workspace':'work','scope':'depot','rows':[{'kind':'file','path':'a.txt','stream':'main'}]}).encode())
            QCoreApplication.sendEvent(window,QDragEnterEvent(QPoint(90,45),Qt.CopyAction,mime,Qt.LeftButton,Qt.NoModifier))
            QCoreApplication.sendEvent(window,QDragMoveEvent(QPoint(90,45),Qt.CopyAction,mime,Qt.LeftButton,Qt.NoModifier))
            until(lambda:view.property('disclosures')==1)
            self.assertEqual(view.property('contentY'),0,'Hover in the middle does not scroll')
            QCoreApplication.sendEvent(window,QDragMoveEvent(QPoint(90,84),Qt.CopyAction,mime,Qt.LeftButton,Qt.NoModifier))
            until(lambda:view.property('contentY')>0)
            QCoreApplication.sendEvent(window,QDragLeaveEvent())
            stopped=view.property('contentY');count=view.property('disclosures')
            QTest.qWait(100)
            self.assertEqual(view.property('contentY'),stopped,'Leaving/cancelling a drag stops edge scrolling')
            self.assertEqual(view.property('disclosures'),count)
            self.assertFalse(warnings,warnings)
        finally:
            window.close();view.setParentItem(None);view.deleteLater();window.deleteLater();theme.deleteLater();engine.deleteLater()
            QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)


if __name__=='__main__':unittest.main()
