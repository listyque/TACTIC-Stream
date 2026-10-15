"""Capture current Handler dock chrome/menus with isolated native Qt models."""
import hashlib
import json
import os
from pathlib import Path
import sys
from datetime import datetime, timezone
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
HANDLER = Path('D:/code/th_codex')
OUTPUT = ROOT/'.screenshots/workspace-current'


def main():
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    os.environ['QT_QUICK_BACKEND'] = 'software'
    os.environ['QT_SCALE_FACTOR'] = '1'
    sys.path.insert(0, str(HANDLER))
    from tests.qt_application import gui_test_application
    from tests.test_workspace_layout_presets_qml import _PresetController
    from PySide6.QtCore import QObject, QPointF, QUrl, Slot, Qt
    from PySide6.QtQml import QQmlComponent, QQmlEngine, QQmlExpression
    from PySide6.QtGui import QFontDatabase
    from PIL import Image
    from PySide6.QtTest import QTest
    from thlib.ui.icon_font import qml_icon_bindings
    from thlib.ui.workspace_models.docks import DockPanelModel
    from thlib.ui.controllers.item_actions import ItemActionsMixin

    class WindowModel(QObject):
        @Slot(str)
        def open_help(self, _key):
            pass

    app = gui_test_application(); engine = QQmlEngine()
    for font in ('segoeui.ttf', 'segoeuib.ttf'):
        assert QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+font) >= 0
    docks = DockPanelModel({}); presets = _PresetController(); windows = WindowModel()
    presets.records.replace([])
    context = engine.rootContext()
    context.setContextProperty('dockModel', docks)
    context.setContextProperty('windowModel', windows)
    context.setContextProperty('presetController', presets)
    for key, value in qml_icon_bindings(HANDLER, engine).items():
        context.setContextProperty(key, value)
    warnings = []; engine.warnings.connect(lambda errors: warnings.extend(error.toString() for error in errors))
    component = QQmlComponent(engine)
    component.setData(b'''
import QtQuick
import QtQuick.Controls
import "." as Handler
ApplicationWindow {
    id: win; width:520; height:300; visible:true; color: theme.background
    Handler.Theme { id:theme; dark:true; clickAnimationsEnabled:false; hoverAnimationsEnabled:false; popupAnimationsEnabled:false; fadeAnimationsEnabled:false }
    Item {
        id:host; anchors.fill:parent
        property bool dockResizeActive:false
        Handler.DockPanel {
            id:panel; host:host; theme:theme; panelId:"description"; title:"Description"; kind:"description"
            panelX:0; panelY:0; panelWidth:1; panelHeight:1; modelVisible:true; panelOpen:true; stackActive:true
            closable:true; stackOrder:1; dockArea:"floating"; canResizeLeft:true; canResizeRight:true; canResizeTop:true; canResizeBottom:true
            stackPanels:[]; stackSize:1
            contentComponent: Component { Item {} }
        }
    }
    Handler.DockMenu { id:menu; objectName:"captureDockMenu"; theme:theme; panelModel:dockModel; layoutPresetController:presetController }
    Handler.WorkspaceLayoutPresetMenuSection { id:section; objectName:"capturePresets"; visible:false; theme:theme; controller:presetController; width:330 }
    Handler.ActionMenu { id:actions; objectName:"captureItemMenu"; theme:theme; actions:[] }
    function dockMenu() { menu.openCenteredIn(contentItem) }
    function itemMenu(rows, expanded) { actions.actions=rows; actions.openCenteredIn(contentItem); actions.advancedExpanded=expanded }
}
''', QUrl.fromLocalFile(str(HANDLER/'thlib/ui/qml/_StreamWorkspaceReference.qml')))
    window = component.create()
    if not window:
        raise RuntimeError('\n'.join(error.toString() for error in component.errors()))
    OUTPUT.mkdir(parents=True, exist_ok=True)

    def settle():
        QTest.qWait(350); app.processEvents()

    def expression(code, obj=window):
        action = QQmlExpression(QQmlEngine.contextForObject(obj), obj, code)
        result = action.evaluate()
        if action.hasError():
            raise RuntimeError(action.error().toString())
        settle(); return result

    def save(name, crop=None):
        settle()
        popup = [item for item in app.allWindows() if item.isVisible() and 'Popup' in item.metaObject().className()]
        image = (popup[-1] if popup else window).grabWindow()
        if crop:
            image = image.copy(*crop)
        assert not image.isNull() and image.save(str(OUTPUT/(name+'.png'))), name
        print(name, image.width(), image.height(), flush=True)

    def close_popup():
        popup = next(item for item in app.allWindows() if item.isVisible() and 'Popup' in item.metaObject().className())
        QTest.keyClick(popup, Qt.Key_Escape); settle()

    try:
        width = Image.open(OUTPUT/'stream-dock-title.png').width if (OUTPUT/'stream-dock-title.png').exists() else 506
        window.resize(width+14,300); settle(); save('th-dock-title', (7, 7, width, 38))
        panel = window.findChild(QObject, 'dockPanel_description')
        stack_width = Image.open(OUTPUT/'stream-dock-stack-title.png').width
        window.resize(stack_width+14,300); settle()
        panel.setProperty('stackPanels', [dict(panelId='description',title='Description',kind='description',active=True,closable=True),
            dict(panelId='results',title='Results',kind='results',active=False,closable=False)])
        panel.setProperty('stackSize',2)
        save('th-dock-stack-title', (7,7,stack_width,38))
        panel.setProperty('stackSize',1); panel.setProperty('stackPanels',[])
        grip = window.findChild(QObject, 'dockStackDrag_description')
        point = grip.mapToScene(QPointF(grip.width()/2, grip.height()/2)).toPoint()
        QTest.mouseClick(window, Qt.RightButton, Qt.NoModifier, point); settle(); save('th-dock-context')
        close_popup()
        expression('dockMenu()'); save('th-dock-menu')
        expression('menu.close()')
        window.resize(330, 220)
        expression('host.visible=false; section.visible=true')
        save('th-presets')
        expression('section.visible=false')
        node = SimpleNamespace(node_type='sobject', source=None, watch_state='none', relationship='', is_multiple=False)
        owner = SimpleNamespace(_node_for_any=lambda _:node, _current_tab=lambda:None,
            _dcc_actions_for_node=lambda _:[], _node_has_snapshot=lambda _:False, server_user='', _server_clock=None)
        rows = ItemActionsMixin.item_menu_actions(owner, 'fixture')
        encoded = json.dumps(rows)
        window.resize(520, 600)
        expression('itemMenu('+encoded+',false)'); save('th-object-basic')
        expression('actions.close()')
        expression('itemMenu('+encoded+',true)'); save('th-object-advanced')
        expression('actions.close()')
        node.node_type = 'file'
        rows = ItemActionsMixin.item_menu_actions(owner, 'fixture')
        expression('itemMenu('+json.dumps(rows)+',false)'); save('th-file-menu')
        expression('actions.close()')
        sources = ['thlib/ui/qml/DockPanel.qml', 'thlib/ui/qml/DockTitleLabel.qml', 'thlib/ui/qml/controls/Typography.qml', 'thlib/ui/qml/DockMenu.qml', 'thlib/ui/qml/ActionMenu.qml',
            'thlib/ui/qml/WorkspaceLayoutPresetMenuSection.qml', 'thlib/ui/controllers/item_actions.py',
            'thlib/ui/controllers/search_tabs.py', 'thlib/ui/workspace_models/docks_records.py', 'thlib/ui/workspace_layout_presets.py']
        (OUTPUT/'native.json').write_text(json.dumps(dict(capturedAt=datetime.now(timezone.utc).isoformat(), sources={path:hashlib.sha256((HANDLER/path).read_bytes()).hexdigest() for path in sources},
            warnings=warnings, fixture='Native DockPanel/ActionMenu, DockPanelModel and preset test controller. Empty content; no network or user settings.'), ensure_ascii=False, indent=2)+'\n', encoding='utf8')
        assert not warnings, '\n'.join(warnings)
    finally:
        window.close(); window.deleteLater(); engine.deleteLater(); app.processEvents()


if __name__ == '__main__':
    main()
