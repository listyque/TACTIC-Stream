"""Capture current, unmodified Handler Table View and Columns Editor on fixture.json."""
import ast
import hashlib
import json
import os
from pathlib import Path
import sys
from xml.etree import ElementTree

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['QT_QUICK_BACKEND'] = 'software'
os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
os.environ['QT_FONT_DPI'] = '96'
from PySide6.QtCore import QAbstractListModel, QModelIndex, QObject, Property, Qt, QUrl, Signal, Slot, QMetaObject, QPoint, QPointF
from PySide6.QtGui import QFont, QFontDatabase, QFontInfo, QFontMetricsF, QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickWindow, QQuickItem
from PySide6.QtTest import QTest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TH = Path('D:/code/th_codex')
sys.path.insert(0, str(TH))
from thlib.ui import tactic_definition
from thlib.ui.icon_font import qml_icon_bindings

fixture = json.loads((HERE/'fixture.json').read_text(encoding='utf-8'))
elements = fixture['definition']['table']['elements']
columns = [dict(name=element['name'], label=element['title'], kind=element['cell']['kind'], row=index,
    width=int(element['attributes'].get('width','160').removesuffix('px')),
    hideOrder=int(element['attributes'].get('th_hide_order','0')), editable=False, sortable=element['cell']['sortable'],
    dataType=fixture['definition']['columns'].get(element['cell']['field'],{}).get('data_type',''), displayOptions=element['display']['options']) for index,element in enumerate(elements)]


class Rows(QAbstractListModel):
    names = ['nodeId','nodeType','searchKey','itemCode','title','comments','tasks','values','accent','previewUrl','previewRequested','previewRevealed','expanded','childCount']

    def roleNames(self):
        return {Qt.UserRole + index: name.encode() for index,name in enumerate(self.names)}

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(fixture['records'])

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or role < Qt.UserRole:
            return None
        record = fixture['records'][index.row()]
        cells = fixture['cells'][record['__search_key__']]
        values = dict(nodeId=record['code'],nodeType='sobject',searchKey=record['__search_key__'],itemCode=record['code'],title=record['name'],
            comments=cells['notes']['count'],tasks=cells['task_pipeline_panels']['count'],values=record,accent=fixture['accent'],previewUrl='',
            previewRequested=True,previewRevealed=True,expanded=False,childCount=0)
        return values[self.names[role-Qt.UserRole]]


source = (TH/'thlib/ui/columns_editor.py').read_text(encoding='utf-8')
controller_class = next(node for node in ast.parse(source).body if isinstance(node,ast.ClassDef) and node.name == 'ColumnsEditorController')
wizard_methods = [node for node in controller_class.body if isinstance(node,ast.FunctionDef) and node.name in ('catalog_wizard','_catalog_xml_root')]
for node in wizard_methods:
    node.decorator_list = [decorator for decorator in node.decorator_list if isinstance(decorator,ast.Name) and decorator.id == 'staticmethod']
native_class = ast.fix_missing_locations(ast.Module(body=[ast.ClassDef(name='NativeWizard',bases=[],keywords=[],body=wizard_methods,decorator_list=[])],type_ignores=[]))
namespace = dict(ElementTree=ElementTree,tactic_definition=tactic_definition)
exec(compile(native_class,str(TH/'thlib/ui/columns_editor.py'),'exec'),namespace)
NativeWizard = namespace['NativeWizard']
xml = fixture['configuration']['sources'][0]['xml']
catalog = [dict(identity='1',row=0,id=1,view='table',searchType='cg/assets',login='',code='TABLE_FIXTURE',config=xml)]


class Catalog(QObject):
    stateChanged = Signal()
    focusRequested = Signal()
    _error = ''
    _catalog_xml_root = staticmethod(NativeWizard._catalog_xml_root)
    busy = Property(bool,lambda self:False,constant=True)
    dirty = Property(bool,lambda self:False,constant=True)
    error = Property(str,lambda self:'',constant=True)
    definitionCatalog = Property('QVariantList',lambda self:catalog,constant=True)
    definitionCatalogSearchTypes = Property('QVariantList',lambda self:[dict(value='cg/assets',label='Assets · cg/assets')],constant=True)
    definitionCatalogLoaded = Property(bool,lambda self:True,constant=True)
    focusPending = Property(bool,lambda self:False,constant=True)
    displayWidgetOptions = Property('QVariantList',lambda self:[dict(value=value,label=label) for value,label in tactic_definition.DISPLAY_WIDGETS],constant=True)

    @Slot(str)
    def load_definition_catalog(self, project):
        pass

    @Slot(str,result='QVariantMap')
    def catalog_wizard(self, source):
        return NativeWizard.catalog_wizard(self,source)


app = QGuiApplication([])
for name in ['segoeui.ttf','seguisb.ttf','consola.ttf']:
    QFontDatabase.addApplicationFont('C:/Windows/Fonts/' + name)
application_font = QFont('Segoe UI'); application_font.setPointSizeF(9.75); app.setFont(application_font)
engine = QQmlEngine()
bindings = qml_icon_bindings(TH,engine)
for name,value in bindings.items():
    engine.rootContext().setContextProperty(name,value)
rows = Rows(); editor = Catalog()
engine.rootContext().setContextProperty('fixtureModel',rows)
engine.rootContext().setContextProperty('columnsEditorController',editor)
results = []
table_qml = '''
 QtObject { id: ctrl; objectName:"captureController"; property var selected_result_node_ids: ["TABLE_ASSET_2"]
  property string result_sort_mode:"column:name:asc"; property string result_group_mode:"none"; property bool has_more:false; property string loading_mode:"pages"
  function process_count_actions(node,panel) { var key=keys[node]; var values=cells[key].notes.processes; return values.map(v=>({title:v.label||v.process,process:v.process,accent:v.accent||accent,badgeCount:v.count})) }
  function request_item_preview(node) {} function mark_item_preview_revealed(node) {}
  function open_process_details(node,panel,process) {} function open_process_task_details(node,panel,process,task) {}
  function item_menu_actions(node) { return [] } function select_result_node() {} function handle_item_double_click() {}
 }
 QtObject { id: cols; property var visibleColumns:COLUMNS; property bool busy:false; property bool dirty:false; property string error:""; property int cellRevision:0; property int dirtyTaskCount:0
  function begin_session() {} function row_cells(key,revision) {return cells[key]||{}}
 }
 QtObject { id: users; signal contentReplaced(); function lookup(kind,login) { return identities[login]||{} } }
 App.SearchResultTable { objectName:"tableFixture"; anchors.fill:parent; theme:theme; controller:ctrl; columnsController:cols; resultModel:fixtureModel; userModel:users; presentationActive:true }
'''
editor_qml = 'App.ColumnsEditorView { objectName:"editorFixture"; anchors.fill:parent; theme:theme; projectCode:"table_fixture"; saveActionsInHeader:true }'
identities = {task['assigned']:task['assignedIdentity'] for values in fixture['cells'].values() for task in values.get('task_pipeline_panels',{}).get('tasks',[]) if task.get('assignedIdentity')}
for kind,body in [('table',table_qml),('columns-editor',editor_qml)]:
    for mode in ['dark','light']:
        source = '''import QtQuick
import QtQuick.Controls
import "." as App
ApplicationWindow {
 width:1496; height:660; visible:true; color:theme.workspace
 property var cells:CELLS; property var keys:KEYS; property var identities:IDENTITIES; property string accent:ACCENT
 App.Theme {id:theme; dark:DARK; clickAnimationsEnabled:false; hoverAnimationsEnabled:false; fadeAnimationsEnabled:false; popupAnimationsEnabled:false}
 BODY
}
'''
        keys = {record['code']:record['__search_key__'] for record in fixture['records']}
        for token,value in dict(CELLS=json.dumps(fixture['cells']),KEYS=json.dumps(keys),IDENTITIES=json.dumps(identities),ACCENT=json.dumps(fixture['accent']),DARK=str(mode=='dark').lower(),BODY=body.replace('COLUMNS',json.dumps(columns))).items():
            source = source.replace(token,value)
        component = QQmlComponent(engine)
        component.setData(source.encode(),QUrl.fromLocalFile(str(TH/'thlib/ui/qml/_HandlerTableCapture.qml')))
        window = component.create()
        assert window, [error.toString() for error in component.errors()]
        try:
            QTest.qWait(600)
            if kind == 'columns-editor':
                wizard = window.findChild(QQuickItem,'definitionCatalogWizard')
                title = window.findChild(QQuickItem,'definitionCatalogTitle')
                assert wizard.property('selectedElementPath') == '0/0'
                assert title.property('text') == 'Preview'
            frame = window.grabWindow()
            assert not frame.isNull()
            assert frame.save(str(HERE/(kind+'-th-'+mode+'.png')))
            selected = []
            task_cells = []
            pending = [window.contentItem()]
            while pending:
                item = pending.pop(); pending.extend(item.childItems())
                if item.objectName() == 'tableTaskCell':
                    task_cells.append(item)
                if item.property('text') == 'Hero Robot' and item.property('font') is not None:
                    font = item.property('font')
                    selected.append(dict(name='bodyFont',family=font.family(),points=font.pointSizeF(),pixels=QFontInfo(font).pixelSize(),weight=font.weight(),advance=QFontMetricsF(font).horizontalAdvance('Hero Robot'),dpi=app.primaryScreen().logicalDotsPerInch()))
                if item.objectName() in ('tableHeaderSurface','searchResultTableRow','tableTaskRecord_0','tableNoteRecord_0','tableCellPreview','definitionCatalogElementList','definitionCatalogXmlPanel'):
                    selected.append(dict(name=item.objectName(),width=item.width(),height=item.height(),color=str(item.property('color'))))
            results.append(dict(kind=kind,mode=mode,width=1496,height=660,items=selected))
            if kind == 'table':
                window.findChild(QObject, 'captureController').setProperty('selected_result_node_ids', [record['code'] for record in fixture['records'][:2]])
                first_cell = min(task_cells, key=lambda item: item.mapToScene(QPointF(0, 0)).y())
                point = first_cell.mapToScene(QPointF(10, first_cell.height() / 2))
                window.requestActivate()
                QTest.qWait(50)
                QTest.mouseMove(window, QPoint(10, 600))
                QTest.mouseMove(window, QPoint(round(point.x()), round(point.y())))
                QTest.qWait(450)
                previews = [cell.findChild(QObject, 'tableTaskCardsPreview') for cell in task_cells]
                previews = [popup for popup in previews if popup and popup.property('visible')]
                assert len(previews) == 2, [(cell.property('nodeId'), cell.property('hoverActive')) for cell in task_cells]
                for popup in previews:
                    assert popup.property('width') == 456
                    assert popup.property('height') == 68
                bars = [popup.findChild(QQuickItem, 'tableTaskCardsPreviewScrollBar') for popup in previews]
                assert not any(bar.property('hasOverflow') for bar in bars)
                assert window.grabWindow().save(str(HERE/('task-preview-th-'+mode+'.png')))
                results.append(dict(kind='task-preview',mode=mode,width=1496,height=660,popups=[dict(width=popup.property('width'),height=popup.property('height'),availableWidth=popup.property('availableWidth'),availableHeight=popup.property('availableHeight')) for popup in previews]))
        finally:
            window.close(); window.deleteLater(); app.processEvents()
component = QQmlComponent(engine)
component.setData(b'''import QtQuick
import QtQuick.Controls
import "." as App
ApplicationWindow {
 width:200; height:58; visible:true; color:theme.surface
 property var writes: []
 App.Theme {id:theme; dark:true; clickAnimationsEnabled:false; hoverAnimationsEnabled:false; popupAnimationsEnabled:false}
 QtObject {id:columns; function cell_editor(node,column) {return {fieldName:"Name",fieldType:"string",fieldValue:"Hero Robot",submitName:"name",fieldOptions:[]}}}
 QtObject {id:controller; function update_selected_item_fields(node,changes) {writes = writes.concat([changes])}}
 App.TacticTableInlineEditor {objectName:"inlineFixture"; anchors.fill:parent; theme:theme; controller:controller; columnsController:columns; nodeId:"test"; columnName:"name"; editable:true}
}''', QUrl.fromLocalFile(str(TH/'thlib/ui/qml/_HandlerInlineCapture.qml')))
window = component.create()
assert window, [error.toString() for error in component.errors()]
try:
    editor = window.findChild(QQuickItem, 'inlineFixture')
    QMetaObject.invokeMethod(editor, 'beginEditing'); window.requestActivate(); QTest.qWait(100)
    QTest.keyClick(window, Qt.Key_A, Qt.ControlModifier)
    for char in 'Complete name':
        QTest.keyClick(window, char)
    assert editor.property('editing')
    assert window.property('writes').toVariant() == [], 'Typing must not commit the first character'
    assert window.grabWindow().save(str(HERE/'inline-th-dark.png'))
    QTest.keyClick(window, Qt.Key_Return); QTest.qWait(50)
    assert window.property('writes').toVariant() == [{'name':'Complete name'}]
    QMetaObject.invokeMethod(editor, 'beginEditing'); QTest.qWait(50)
    QTest.keyClick(window, Qt.Key_A, Qt.ControlModifier); QTest.keyClick(window, 'x'); QTest.keyClick(window, Qt.Key_Escape); QTest.qWait(50)
    assert window.property('writes').toVariant() == [{'name':'Complete name'}], 'Escape must cancel'
finally:
    window.close(); window.deleteLater(); app.processEvents()
paths = ['SearchResultTable.qml','SearchResultTableHeader.qml','SearchTableColumnLayout.js','TacticTableCellDisplay.qml','TacticTaskCell.qml','TacticTaskCards.qml','controls/Popup.qml','controls/ScrollBar.qml','ColumnsEditorView.qml','DefinitionCatalogWizard.qml','SObjectValueEditor.qml','TacticTableInlineEditor.qml']
(HERE/'native-measurements.json').write_text(json.dumps(dict(captures=results,sources={path:hashlib.sha256((TH/'thlib/ui/qml'/path).read_bytes()).hexdigest() for path in paths}),indent=2),encoding='utf-8')
engine.deleteLater(); app.processEvents()
print(json.dumps(dict(captures=len(results),current_qml=True,size=[1496,660])))
