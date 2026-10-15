"""Shipped Naming view; native rule drafts and actual keyboard/mouse input."""
import copy
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

REPO=Path(__file__).resolve().parents[2]
TH=Path('D:/code/th_codex')
HERE=Path(__file__).resolve().parent
OUT=HERE/'output'
OUT.mkdir(exist_ok=True)
os.environ.update(QT_QPA_PLATFORM='offscreen',QT_QUICK_BACKEND='software',QT_FONT_DPI='96')
sys.path[:0]=[str(TH),str(REPO/'tools/frame_admin')]
from PySide6.QtCore import QPointF, QUrl, QCoreApplication, QEvent
from PySide6.QtQml import QQmlEngine,QQmlComponent
from PySide6.QtGui import QFont,QFontDatabase
from PySide6.QtQuick import QQuickWindow
from tests.qt_application import gui_test_application
from tests.profile_ui_responsiveness import frame
from tests.test_sidebar_editor_qml import SidebarEditorQmlTests
from thlib.ui.naming_editor import NamingEditorController, _DATA_FIELDS, _BOOLEAN_FIELDS
from thlib.ui.icon_font import qml_icon_bindings
from thlib.ui.localization import CatalogTranslator
from native_capture import controls,click,text,choose,snapshot,source_hashes

app=gui_test_application()
QQuickWindow.setTextRenderType(QQuickWindow.NativeTextRendering)
app.setFont(QFont('Segoe UI',10))
for name in ('segoeui.ttf','seguisb.ttf'):QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)
icons=qml_icon_bindings(TH,app)
sources=source_hashes(REPO,TH,['thlib/ui/qml/features/administration/naming/NamingEditorView.qml','thlib/ui/naming_editor.py'])
document={field:False if field in _BOOLEAN_FIELDS else '' for field in _DATA_FIELDS}
document.update(search_type='demo/asset',context='publish',checkin_type='strict',dir_naming='{project.code}/{search_type.table_name}/{sobject.code}/{snapshot.context}/versions',file_naming='{sobject.name}_v{version}.{ext}')
rules=[dict(identity='N1',document=document)]+[dict(identity=f'N{i+2}',document=dict(document,context=f'stage_{i:02}')) for i in range(18)]
fixture=dict(rules=rules,identity='N1',items=[dict(key='demo/asset?code=A1',label='Asset one')],itemCount=1,itemOffset=0,revision='fixture-revision')
(OUT/'catalog.json').write_text(json.dumps(fixture,ensure_ascii=False),encoding='utf8')
cases=json.loads((HERE/'cases.json').read_text())
samples=[]
quick=os.environ.get('FRAME_CAPTURE_QUICK')=='1'
for mode in ('dark',) if quick else ('dark','light'):
 for language in ('en',) if quick else ('en','ru'):
  for width,height in ((1100,740),) if quick else ((1100,740),(800,740),(360,740)):
   controller=NamingEditorController(SimpleNamespace(can_manage_tools=True,debug_log=None),SimpleNamespace(currentObject={}),None)
   controller._target=dict(projectCode='demo',searchType='demo/asset',title='Assets');controller._type_mode=True;controller._project_data={'code':'demo'};controller._preview_process='publish'
   controller._records=[controller._normalize_record(dict(row['document'],code=row['identity'],__search_key__='config/naming?project=demo&code='+row['identity'])) for row in rules]
   controller._select(0)
   engine=QQmlEngine();warnings=[]
   translator=CatalogTranslator(TH/'thlib/ui/translations/ru.json')
   if language=='ru':app.installTranslator(translator)
   engine.warnings.connect(lambda errors:warnings.extend(e.toString() for e in errors))
   for name,value in icons.items():engine.rootContext().setContextProperty(name,value)
   engine.rootContext().setContextProperty('namingFixtureController',controller)
   component=QQmlComponent(engine,QUrl.fromLocalFile(str(HERE/'NamingHarness.qml')))
   assert component.isReady(),[e.toString() for e in component.errors()]
   window=component.createWithInitialProperties({'width':width,'height':height})
   assert window
   try:
    window.setProperty('dark',mode=='dark');window.setProperty('language',language);frame(window)
    for case in cases:
     for action in case['actions']:
      if action['type']=='state':controller._write_uncertain=action['value']=='uncertain';controller._busy=action['value']=='busy';controller.stateChanged.emit()
      elif action['type']=='reveal':
       viewport=controls(window)[action['viewport']];item=next(item for item in SidebarEditorQmlTests.descendants(window.contentItem()) if item.objectName()==action['id'])
       top=viewport.property('contentY')+item.mapToItem(viewport,QPointF()).y()-12
       viewport.setProperty('contentY',max(0,min(top,max(0,viewport.property('contentHeight')-viewport.height()))))
      elif action['type']=='page':
       items=controls(window);button=items.get(action['selector']+'_'+action['value'])
       if button is not None:click(window,button)
       else:choose(window,items[action['selector']],action['value'])
      else:
       item=controls(window)[action['id']]
       if action['type']=='text':text(window,item,action['value'])
       elif action['type']=='choose':choose(window,item,action['value'])
       else:click(window,item)
      frame(window)
     window.blur();frame(window)
     image=f'naming-qml-{mode}-{language}-{width}-{case["phase"]}.png'
     assert window.grabWindow().save(str(OUT/image))
     samples.append(dict(mode=mode,language=language,width=width,height=height,phase=case['phase'],image=image,scene=json.loads(window.property('sceneJson')),state=json.loads(window.property('stateJson')),**snapshot(window)))
    assert not warnings,warnings
   finally:
    controller._busy=False;window.close();window.deleteLater();controller.shutdown();engine.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete);app.removeTranslator(translator)
assert sources==source_hashes(REPO,TH,['thlib/ui/qml/features/administration/naming/NamingEditorView.qml','thlib/ui/naming_editor.py'])
(OUT/'qml.json').write_text(json.dumps(dict(sha256=sources[0],nativeSources=sources[1],captures=samples),ensure_ascii=False,indent=2),encoding='utf8')
print(f'Captured {len(samples)} Naming states')
