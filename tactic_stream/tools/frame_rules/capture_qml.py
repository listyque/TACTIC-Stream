import ast,copy,importlib.util,os,sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[2];TH=Path('D:/grav/Tactic Stream/TH')
os.environ.update(QT_QPA_PLATFORM='offscreen',QT_QUICK_BACKEND='software',QT_FONT_DPI='96',TMP=str(ROOT/'.tmp/frame-tests'),TEMP=str(ROOT/'.tmp/frame-tests'))
sys.path[:0]=[str(TH),str(ROOT/'tools/frame_admin')]
from PySide6.QtCore import QUrl,QPointF,QCoreApplication,QEvent
from PySide6.QtQml import QQmlEngine,QQmlComponent
from PySide6.QtGui import QFont
from tests.qt_application import gui_test_application
from tests.profile_ui_responsiveness import frame
from thlib.ui.icon_font import qml_icon_bindings
from native_capture import controls,text,click,choose,snapshot
from thlib.ui.admin import process_rules as module
from PySide6.QtGui import QFontDatabase
from thlib.ui.localization import CatalogTranslator
from native_capture import source_hashes
import json
app=gui_test_application();app.setFont(QFont('Segoe UI',10));icons=qml_icon_bindings(TH,app)
for name in ('segoeui.ttf','seguisb.ttf'):QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)
HERE=Path(__file__).resolve().parent;OUT=HERE/'output';OUT.mkdir(exist_ok=True)
sources=source_hashes(ROOT,TH,['thlib/ui/qml/features/administration/workflow/AdminProcessRulesView.qml','thlib/ui/admin/process_rules.py']);samples=[]
for mode in ('dark','light'):
 for language in ('en','ru'):
  for width,height in ((1100,740),(800,740),(360,740)):
    controller=module.ProcessRulesEditor(SimpleNamespace(can_manage_tools=True,debug_log=None,window_model=Mock()),SimpleNamespace(),None)
    controller._project='demo';controller._identity='PR1';controller._loaded=controller._can_write=True
    controller._metadata=dict(process='model',pipeline='demo/assets',searchType='demo/asset',sourceStatuses=['Pending','Complete'],processes=[dict(identity='model',label='Model',statuses=['Pending','Complete'])],outputs=['publish'],scriptPaths=['project/test'],naming=[dict(context='publish',directory='assets',file='main')],items=[dict(key='demo/asset?code=A1',label='Asset one')],itemCount=121,itemOffset=0)
    controller.add_rule('trigger');controller._document['rules'][0]['title']='Initial';controller._original=copy.deepcopy(controller.document);controller._document_loaded()
    (OUT/'fixture.json').write_text(json.dumps(dict(document=controller.document,metadata=controller.metadata,identity='PR1',canWrite=True,revision='R1')),encoding='utf8')
    engine=QQmlEngine();warnings=[];engine.warnings.connect(lambda errors:warnings.extend(e.toString() for e in errors));translator=CatalogTranslator(TH/'thlib/ui/translations/ru.json')
    if language=='ru':app.installTranslator(translator)
    for name,value in icons.items():engine.rootContext().setContextProperty(name,value)
    engine.rootContext().setContextProperty('fixture',controller);component=QQmlComponent(engine,QUrl.fromLocalFile(str(HERE/'RulesHarness.qml')));assert component.isReady(),[e.toString() for e in component.errors()]
    window=component.createWithInitialProperties({'width':width,'height':height,'dark':mode=='dark','language':language});assert window
    try:
     for phase in ('catalog','task_status','parent_status','task_create','task_date','custom_script','python_class','notification','naming','objects','readonly','unknown'):
      if phase=='task_status':window.send({'type':'select','index':0})
      if phase in ('task_status','parent_status','task_create','task_date','custom_script','python_class'):controller.set_rule_field('action',phase)
      if phase in ('notification','naming','objects'):window.send({'type':'page','value':phase})
      if phase=='notification':window.send({'type':'add'})
      if phase=='readonly':controller._can_write=False;controller.stateChanged.emit()
      if phase=='unknown':controller._can_write=True;controller._write_uncertain=True;controller.stateChanged.emit()
      frame(window);image=f'qml-{mode}-{language}-{width}-{phase}.png';assert window.grabWindow().save(str(OUT/image))
      samples.append(dict(mode=mode,language=language,width=width,height=height,phase=phase,image=image,scene=json.loads(window.property('sceneJson')),state=json.loads(window.property('stateJson')),**snapshot(window)))
     assert not warnings,warnings
    finally:window.close();window.deleteLater();controller.shutdown();engine.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete);app.removeTranslator(translator)
(OUT/'qml.json').write_text(json.dumps(dict(sha256=sources[0],nativeSources=sources[1],captures=samples),ensure_ascii=False,indent=2),encoding='utf8')
print('Captured',len(samples),'native Process dependencies states')
