"""Capture the current Handler DescriptionEditor and its native state, offline."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
HANDLER = Path('D:/grav/Tactic Stream/TH')
OUTPUT = ROOT / '.screenshots/description-current'


def main():
    sys.path.insert(0,str(HANDLER))
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlComponent, QQmlEngine
    from PySide6.QtQuick import QQuickWindow
    from PySide6.QtTest import QTest
    from thlib.ui.icon_font import qml_icon_bindings
    from thlib.ui.workspace_models.state import WorkspaceState

    class Record:
        def __init__(self,description='Original description'): self.description = description
        def get_info(self): return {'description':self.description}
        def get_snapshot(self): return self.get_info()
        def get_search_key(self): return 'one/description_assets?project=one&code=DESCRIPTION_A'

    app = QGuiApplication([])
    engine = QQmlEngine()
    state = WorkspaceState()
    engine.rootContext().setContextProperty('workspaceState',state)
    for key,value in qml_icon_bindings(HANDLER,engine).items():
        engine.rootContext().setContextProperty(key,value)
    component = QQmlComponent(engine)
    qml = '''import QtQuick
import QtQuick.Window
import "%s" as Handler
Window {
    width:440; height:340; visible:true
    Handler.Theme { id:theme; dark:true }
    Handler.DescriptionEditor {
        anchors.fill:parent; theme:theme
        value:workspaceState.description
        targetTitle:workspaceState.descriptionTargetTitle
        targetKind:workspaceState.descriptionTargetKind
        editing:workspaceState.descriptionEditing
        pinned:workspaceState.descriptionPinned
        dirty:workspaceState.descriptionDirty
        saving:workspaceState.descriptionSaving
        errorText:workspaceState.descriptionError
        canSave:workspaceState.descriptionCanSave
        editorEnabled:workspaceState.descriptionTargetTitle.length > 0
    }
}''' % (HANDLER/'thlib/ui/qml').as_uri()
    component.setData(qml.encode(),QUrl.fromLocalFile(str(ROOT/'tools/description-reference.qml')))
    window = component.create()
    if window is None: raise RuntimeError('\n'.join(error.toString() for error in component.errors()))
    OUTPUT.mkdir(parents=True,exist_ok=True)
    titles = json.loads((OUTPUT/'browser-state.json').read_text(encoding='utf-8')) if (OUTPUT/'browser-state.json').exists() else {}
    try:
        for width,height in ((440,340),(720,420)):
            window.resize(width,height)
            for name in ('empty','read','edit','pinned','process','snapshot','saving','error'):
                state.unfreeze_description(); state.set_description_target(None,'','')
                title = titles.get(name,{}).get('title','Description A')
                if name != 'empty': state.set_description_target(Record(),'sobject',title)
                if name in ('edit','pinned','error'):
                    state.begin_description_edit(); state.set_description('Prepared description')
                if name == 'pinned': state.freeze_description()
                if name == 'process': state.set_description_target(Record('Process description'),'process',titles.get(name,{}).get('title','Publish'))
                if name == 'snapshot': state.set_description_target(Record('Snapshot description'),'snapshot',titles.get(name,{}).get('title','Publish'))
                if name == 'saving':
                    state.begin_description_edit(); state.set_description('Saved description'); state.commit_description()
                if name == 'error':
                    state.set_description('Retry description')
                    state.description_save_failed(Record().get_search_key(),'Unable to save description')
                QTest.qWait(180)
                if not window.grabWindow().save(str(OUTPUT/f'handler-{name}-{width}.png')):
                    raise RuntimeError('Native screenshot failed')
                print(f'Handler Description {name} {width}',flush=True)
        sources=['thlib/ui/qml/DescriptionEditor.qml','thlib/ui/qml/controls/CompactIconButton.qml','thlib/ui/workspace_models/state_detail_editing.py','thlib/ui/controllers/item_mutations.py']
        (OUTPUT/'native-source.json').write_text(json.dumps({path:hashlib.sha256((HANDLER/path).read_bytes()).hexdigest() for path in sources},indent=2)+'\n',encoding='utf-8')
    finally:
        window.close(); window.deleteLater(); engine.deleteLater(); app.processEvents()


if __name__ == '__main__': main()
