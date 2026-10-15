"""Render the current Handler Snapshot Browser, with the browser's real native projection."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
HANDLER = Path('D:/code/th_codex')
OUTPUT = ROOT / '.screenshots/snapshot-browser-current'


def main():
    sys.path.insert(0,str(HANDLER))
    from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlComponent, QQmlEngine
    from PySide6.QtQuick import QQuickWindow
    from PySide6.QtTest import QTest
    from thlib.ui.icon_font import qml_icon_bindings
    from thlib.ui.controllers.commands import CommandsMixin
    from thlib.ui.workspace_models.records import RecordListModel
    from thlib.ui.workspace_models.results import WorkspaceItemModel

    class Controller(QObject):
        changed = Signal()
        snapshot_browser_show_all = Property(bool,lambda self:self.show_all,notify=changed)
        snapshot_browser_show_more = Property(bool,lambda self:self.show_more,notify=changed)
        snapshot_browser_content_mode = Property(str,lambda self:self.content_mode,notify=changed)
        snapshot_browser_image_mode = Property(str,lambda self:'fit',constant=True)
        snapshot_browser_orientation = Property(str,lambda self:self.orientation,notify=changed)
        snapshot_browser_splitter_ratio = Property(float,lambda self:.52,constant=True)
        def __init__(self):
            super().__init__(); self.show_all = False; self.show_more = False; self.content_mode = 'both'; self.orientation = 'horizontal'
        @Slot(result='QVariantList')
        def snapshot_browser_actions(self):
            self._snapshot_browser_content_mode = self.content_mode
            self._snapshot_browser_show_all = self.show_all
            self._snapshot_browser_show_more = self.show_more
            self._snapshot_browser_orientation = self.orientation
            return CommandsMixin.snapshot_browser_actions(self)
        @Slot(bool,result='QVariantList')
        def snapshot_file_actions(self,editing): return CommandsMixin.snapshot_file_actions(self,editing)
        @Slot(str)
        def request_snapshot_preview_quality(self,_token): pass
        @Slot()
        def refresh_snapshot_browser(self): pass

    app = QGuiApplication([])
    engine = QQmlEngine()
    controller = Controller()
    data = json.loads((OUTPUT/'projection.json').read_text(encoding='utf-8'))
    files = [dict(row, size=WorkspaceItemModel._pretty_size(row.get('size',0)) if row['rowType'] == 'file' else '',
                  fileType=row.get('fileType',''),path=row.get('path',''),repository=row.get('repository',''),
                  baseType=row.get('baseType',''),exists=row.get('exists',True),checking=False,matchesRemote=True,
                  snapshotNodeId=row['snapshotKey'],version='') for row in data['rows']]
    pictures = [dict(token=row['file']['token'],url=row['localUrl'],title=row['title'],qualityUrl='',qualityRequested=True) for row in data['previews']]
    file_model = RecordListModel(tuple(files[0]))
    picture_model = RecordListModel(tuple(pictures[0]))
    for name,value in dict(appController=controller,snapshotPreviewModel=picture_model,snapshotFileModel=file_model).items():
        engine.rootContext().setContextProperty(name,value)
    for name,value in qml_icon_bindings(HANDLER,engine).items(): engine.rootContext().setContextProperty(name,value)
    component = QQmlComponent(engine)
    qml = '''import QtQuick
import QtQuick.Controls
import "%s" as Handler
ApplicationWindow {
    width:440; height:500; visible:true
    Handler.Theme { id:theme; dark:true }
    Handler.SnapshotBrowser { anchors.fill:parent; theme:theme }
}''' % (HANDLER/'thlib/ui/qml').as_uri()
    component.setData(qml.encode(),QUrl.fromLocalFile(str(ROOT/'tools/snapshot-browser-reference.qml')))
    window = None
    try:
        for width,height in ((440,500),(880,650)):
            for name in ('empty','both','all','more','vertical','files','preview'):
                controller.show_all = name in ('all','more','vertical','files','preview')
                controller.show_more = name in ('more','vertical','files','preview')
                controller.orientation = 'vertical' if name in ('vertical','files','preview') else 'horizontal'
                controller.content_mode = name if name in ('files','preview') else 'both'
                controller.changed.emit()
                file_model.replace([] if name == 'empty' else files)
                picture_model.replace([] if name == 'empty' else pictures)
                window = component.create()
                if window is None: raise RuntimeError('\n'.join(error.toString() for error in component.errors()))
                window.resize(width,height)
                QTest.qWait(220)
                if not window.grabWindow().save(str(OUTPUT/f'handler-{name}-{width}.png')): raise RuntimeError('Native screenshot failed')
                print(f'Handler Snapshot Browser {name} {width}',flush=True)
                window.close(); window.deleteLater(); app.processEvents(); window = None
        sources=['thlib/ui/qml/SnapshotBrowser.qml','thlib/ui/qml/SnapshotBrowserToolbar.qml','thlib/ui/qml/SnapshotBrowserOptionsMenu.qml',
                 'thlib/ui/qml/SnapshotPreviewLayers.qml','thlib/ui/controllers/snapshot_details.py','thlib/ui/controllers/snapshot_actions.py',
                 'thlib/ui/controllers/search_tabs.py','thlib/ui/workspace_models/state_snapshot_state.py']
        (OUTPUT/'native-source.json').write_text(json.dumps({path:hashlib.sha256((HANDLER/path).read_bytes()).hexdigest() for path in sources},indent=2)+'\n',encoding='utf-8')
    finally:
        if window: window.close(); window.deleteLater()
        engine.deleteLater(); app.processEvents()


if __name__ == '__main__': main()
