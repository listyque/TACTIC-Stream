"""Shipped Search Types view, native controller, isolated records and real input."""
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
from thlib.ui.admin.search_types import SearchTypesEditor
from thlib.ui.icon_font import qml_icon_bindings
from thlib.ui.localization import CatalogTranslator
from native_capture import controls,click,text,choose,snapshot,source_hashes

app=gui_test_application()
QQuickWindow.setTextRenderType(QQuickWindow.NativeTextRendering)
app.setFont(QFont('Segoe UI',10))
for name in ('segoeui.ttf','seguisb.ttf'):QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)
icons=qml_icon_bindings(TH,app)
sources=source_hashes(REPO,TH,['thlib/ui/qml/features/administration/search_types/AdminSearchTypesView.qml','thlib/ui/admin/search_types.py'])
catalog=[dict(identity='demo/asset',label='Assets',table='asset',namespace='demo',projectLocal=True,color='#ab67c8'),dict(identity='demo/shot',label='Shots',table='shot',namespace='demo',projectLocal=True,color='#df6464')]
catalog += [dict(identity=f'demo/entry_{i:02}',label=f'Entry {i:02}',namespace='demo',projectLocal=True,table=f'entry_{i:02}') for i in range(30)]
document=dict(title='Assets',description='Project assets',color='#ab67c8',columns=[],removedColumns=[])
metadata=dict(table='asset',database='demo',projectLocal=True,tableAvailable=True,columns={'code':{'data_type':'varchar','is_nullable':'NO'},'description':{'data_type':'text'},**{f'field_{i:02}':{'data_type':'text'} for i in range(25)}},columnRemovalBlocks={'code':'identity'},summary=dict(total=230,active=215,retired=15,fields=27,pipelines=1,processes=8),relationships=[dict(schema='demo',relationship='code',type='hierarchy',**{'from':'demo/asset','to':'demo/shot'})],hasPipeline=True,pipelines=[dict(identity='demo/assets',label='Asset workflow',description='Model and review',shared=False,processCount=8)])
cases=json.loads((HERE/'cases.json').read_text())
samples=[]
quick=os.environ.get('FRAME_CAPTURE_QUICK')=='1'
for mode in ('dark',) if quick else ('dark','light'):
 for language in ('en',) if quick else ('en','ru'):
  for width,height in ((1100,740),) if quick else ((1100,740),(800,740),(360,740)):
   controller=SearchTypesEditor(SimpleNamespace(can_manage_tools=True,debug_log=None))
   controller._project='demo';controller._loaded=controller._can_write=True
   controller._catalog=copy.deepcopy(catalog);controller._identity='demo/asset';controller._document=copy.deepcopy(document);controller._original=copy.deepcopy(document);controller._metadata=copy.deepcopy(metadata);controller._revision='fixture-revision';controller._document_loaded()
   fixture=dict(catalog=catalog,identity='demo/asset',document=document,metadata={**metadata,'relationshipGraph':controller.relationshipGraph},revision='fixture-revision',canWrite=True)
   (OUT/'catalog.json').write_text(json.dumps(fixture,ensure_ascii=False),encoding='utf8')
   engine=QQmlEngine();warnings=[]
   translator=CatalogTranslator(TH/'thlib/ui/translations/ru.json')
   if language=='ru':app.installTranslator(translator)
   engine.warnings.connect(lambda errors:warnings.extend(e.toString() for e in errors))
   for name,value in icons.items():engine.rootContext().setContextProperty(name,value)
   engine.rootContext().setContextProperty('searchTypesFixtureController',controller)
   component=QQmlComponent(engine,QUrl.fromLocalFile(str(HERE/'TypesHarness.qml')))
   assert component.isReady(),[e.toString() for e in component.errors()]
   window=component.createWithInitialProperties({'width':width,'height':height})
   assert window
   try:
    window.setProperty('dark',mode=='dark');window.setProperty('language',language);frame(window)
    for case in cases:
     for action in case['actions']:
      if action['type']=='state':controller._can_write=action['value']!='readonly';controller._write_uncertain=action['value']=='uncertain';controller._worker=SimpleNamespace() if action['value']=='busy' else None;controller.stateChanged.emit()
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
     image=f'types-qml-{mode}-{language}-{width}-{case["phase"]}.png'
     assert window.grabWindow().save(str(OUT/image))
     samples.append(dict(mode=mode,language=language,width=width,height=height,phase=case['phase'],image=image,scene=json.loads(window.property('sceneJson')),state=json.loads(window.property('stateJson')),**snapshot(window)))
    assert not warnings,warnings
   finally:
    controller._worker=None;window.close();window.deleteLater();controller.shutdown();engine.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete);app.removeTranslator(translator)
assert sources==source_hashes(REPO,TH,['thlib/ui/qml/features/administration/search_types/AdminSearchTypesView.qml','thlib/ui/admin/search_types.py'])
(OUT/'qml.json').write_text(json.dumps(dict(sha256=sources[0],nativeSources=sources[1],captures=samples),ensure_ascii=False,indent=2),encoding='utf8')
print(f'Captured {len(samples)} Search Types states')
