"""Actual schema/workflow views and domain controllers, without a server."""
import copy,json,os,sys
from pathlib import Path
from types import SimpleNamespace
REPO=Path(__file__).resolve().parents[2];TH=Path('D:/grav/Tactic Stream/TH');HERE=Path(__file__).resolve().parent;OUT=HERE/'output';OUT.mkdir(exist_ok=True)
os.environ.update(QT_QPA_PLATFORM='offscreen',QT_QUICK_BACKEND='software',QT_FONT_DPI='96');sys.path[:0]=[str(TH),str(REPO/'tools/frame_admin')]
from PySide6.QtCore import QCoreApplication,QEvent,QPointF,QUrl
from PySide6.QtQml import QQmlEngine,QQmlComponent
from PySide6.QtGui import QFont,QFontDatabase
from PySide6.QtQuick import QQuickWindow
from tests.qt_application import gui_test_application
from tests.profile_ui_responsiveness import frame
from tests.test_sidebar_editor_qml import SidebarEditorQmlTests
from thlib.ui.admin.graph_editor import GraphEditor
from thlib.ui.icon_font import qml_icon_bindings
from thlib.ui.localization import CatalogTranslator
from native_capture import controls,click,text,choose,snapshot,source_hashes
app=gui_test_application();app.setFont(QFont('Segoe UI',10));QQuickWindow.setTextRenderType(QQuickWindow.NativeTextRendering)
for name in ('segoeui.ttf','seguisb.ttf'):QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)
icons=qml_icon_bindings(TH,app);sources=source_hashes(REPO,TH,['thlib/ui/qml/features/administration/workflow/AdminGraphView.qml','thlib/ui/admin/graph_editor.py','thlib/ui/admin/schema_connections.py'])
cases=json.loads((HERE/'cases.json').read_text());samples=[];quick=os.environ.get('FRAME_CAPTURE_QUICK')=='1'
for editor_mode in ('schema','workflow'):
 names=['demo/asset','demo/shot'] if editor_mode=='schema' else ['model','publish']
 tag='search_type' if editor_mode=='schema' else 'process';root_tag='schema' if editor_mode=='schema' else 'pipeline'
 xml=f'<{root_tag}><!--custom--><{tag} name="{names[0]}" xpos="40" ypos="40" type="'+('search_type' if editor_mode=='schema' else 'manual')+f'" /><{tag} name="{names[1]}" xpos="340" ypos="40" type="'+('search_type' if editor_mode=='schema' else 'action')+f'" /><connect from="{names[0]}" to="{names[1]}"'+(' relationship="code" from_col="shot_code" to_col="code"' if editor_mode=='schema' else ' from_attr="success"')+f' /><extension value="kept" /></{root_tag}>'
 document={'xml':xml} if editor_mode=='schema' else dict(xml=xml,name='Assets',description='Project pipeline',color='#6688aa',searchType='demo/asset',processSettings={},processDescriptions={})
 metadata=dict(searchTypes=[dict(identity='demo/asset',label='Assets',table='asset'),dict(identity='demo/shot',label='Shots',table='shot')],nodeTypes=['manual','action','condition','approval','hierarchy','dependency','progress','status'],pipelines=[dict(identity='demo/assets',label='Assets',searchType='demo/asset'),dict(identity='demo/tasks',label='Task statuses',searchType='sthpw/task')],groups=[dict(identity='artists',label='Artists')],users=[dict(identity='admin',label='Administrator')],processes=[],canCreate=True)
 identity='demo' if editor_mode=='schema' else 'demo/assets';catalog=[dict(identity=identity,label='Assets',searchType='demo/asset')]
 columns={'demo/asset':dict(columns=[dict(name='code',type='varchar'),dict(name='shot_code',type='varchar')],tableAvailable=True),'demo/shot':dict(columns=[dict(name='code',type='varchar'),dict(name='id',type='integer')],tableAvailable=True)}
 fixture=dict(document=document,metadata=metadata,identity=identity,catalog=catalog,revision='fixture-revision',canWrite=True)
 (OUT/(editor_mode+'.json')).write_text(json.dumps(dict(fixture=fixture,columns=columns),ensure_ascii=False),encoding='utf8')
 for mode in ('dark',) if quick else ('dark','light'):
  for language in ('en',) if quick else ('en','ru'):
   for width,height in ((1100,740),(800,740),(360,740)):
    controller=GraphEditor(SimpleNamespace(can_manage_tools=False,can_administer=True,debug_log=None),editor_mode);controller._project='demo';controller._loaded=controller._can_write=True;controller._identity=identity;controller._catalog=copy.deepcopy(catalog);controller._document=copy.deepcopy(document);controller._original=copy.deepcopy(document);controller._metadata=copy.deepcopy(metadata);controller._revision='fixture-revision';controller._document_loaded()
    if controller.connectionEditor:
     def fixture_columns(owner=controller,catalog=columns):
      if not owner.connectionEditor._column_catalog:
       owner.connectionEditor._column_catalog=copy.deepcopy(catalog);owner.connectionEditor.changed.emit()
     fixture_columns();controller.selectionChanged.connect(fixture_columns)
    engine=QQmlEngine();warnings=[];translator=CatalogTranslator(TH/'thlib/ui/translations/ru.json')
    if language=='ru':app.installTranslator(translator)
    engine.warnings.connect(lambda errors:warnings.extend(error.toString() for error in errors))
    for key,value in icons.items():engine.rootContext().setContextProperty(key,value)
    engine.rootContext().setContextProperty('graphFixture',controller);component=QQmlComponent(engine,QUrl.fromLocalFile(str(HERE/'EditorHarness.qml')));assert component.isReady(),[e.toString() for e in component.errors()]
    window=component.createWithInitialProperties({'width':width,'height':height});assert window
    try:
     window.setProperty('dark',mode=='dark');window.setProperty('language',language);frame(window)
     for case in cases:
      for action in case['actions']:
       kind=action['type']
       if kind=='state':controller._can_write=action['value']!='readonly';controller._write_uncertain=action['value']=='uncertain';controller._worker=SimpleNamespace() if action['value']=='busy' else None;controller.stateChanged.emit()
       elif kind in ('select','edge'):window.send({'type':'selectNodes','identities':[names[action['identity']=='second']],'primary':names[action['identity']=='second']} if kind=='select' else {'type':'selectEdge','index':action['index']})
       elif kind=='phone':
        if width<800:
         items=controls(window);button=items.get('adminGraphPanels_'+action['value']);click(window,button) if button is not None else choose(window,items['adminGraphPanels'],action['value'])
       elif kind=='reveal':
        if editor_mode=='workflow' and action['id']=='adminRemoveGraphSelection':continue
        viewport=controls(window)[action['viewport']];item=next(item for item in SidebarEditorQmlTests.descendants(window.contentItem()) if item.objectName()==action['id']);top=viewport.property('contentY')+item.mapToItem(viewport,QPointF()).y()-12;viewport.setProperty('contentY',max(0,min(top,max(0,viewport.property('contentHeight')-viewport.height()))))
       elif kind in ('page','workflowPage'):
        if kind=='workflowPage' and editor_mode!='workflow':continue
        if editor_mode=='workflow' and action['selector']=='adminGraphInspectorPages':
         click(window,controls(window)['adminGraphAddNode']);assert json.loads(window.property('stateJson'))['ui']['inspector']==action['value']
         continue
        items=controls(window);button=items.get(action['selector']+'_'+action['value']);click(window,button) if button is not None else choose(window,items[action['selector']],action['value'])
       elif kind=='workflowClick':
        if editor_mode=='workflow':
         click(window,controls(window)[action['id']]);assert controller.selectedNode==''
       else:
        item=controls(window)[action['id']];text(window,item,action['value']) if kind=='text' else click(window,item)
       frame(window)
      window.blur();frame(window);image=f'{editor_mode}-qml-{mode}-{language}-{width}-{case["phase"]}.png';assert window.grabWindow().save(str(OUT/image))
      samples.append(dict(editor=editor_mode,mode=mode,language=language,width=width,height=height,phase=editor_mode+'-'+case['phase'],image=image,scene=json.loads(window.property('sceneJson')),state=json.loads(window.property('stateJson')),**snapshot(window)))
     assert not warnings,warnings
    finally:controller._worker=None;window.close();window.deleteLater();controller.shutdown();engine.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete);app.removeTranslator(translator)
assert sources==source_hashes(REPO,TH,['thlib/ui/qml/features/administration/workflow/AdminGraphView.qml','thlib/ui/admin/graph_editor.py','thlib/ui/admin/schema_connections.py'])
(OUT/'qml.json').write_text(json.dumps(dict(sha256=sources[0],nativeSources=sources[1],captures=samples),ensure_ascii=False,indent=2),encoding='utf8')
print(f'Captured {len(samples)} schema/workflow states')
