import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'frame_layout'))
from fixture import *
from native_capture import source_hashes
HERE=Path(__file__).resolve().parent;OUT=HERE/'output';OUT.mkdir(exist_ok=True)
from thlib.ui.localization import CatalogTranslator
sources=source_hashes(ROOT,TH,['thlib/ui/qml/AdministrationView.qml','thlib/ui/administration.py']);samples=[]
quick=os.environ.get('FRAME_CAPTURE_QUICK')=='1'
for mode in ('dark','light'):
 for language in ('en','ru'):
  for width,height in ((1100,740),(800,740),(360,740)):
   engine=QQmlEngine();warnings=[];engine.warnings.connect(lambda errors:warnings.extend(e.toString() for e in errors));translator=CatalogTranslator(TH/'thlib/ui/translations/ru.json')
   if language=='ru':app.installTranslator(translator)
   for name,value in icons.items():engine.rootContext().setContextProperty(name,value)
   component=QQmlComponent(engine,QUrl.fromLocalFile(str(HERE/'ShellHarness.qml')));assert component.isReady(),[e.toString() for e in component.errors()]
   window=component.createWithInitialProperties({'width':width,'height':height,'dark':mode=='dark','language':language});assert window
   try:
    for phase in ('default','collapse','groups','locked'):
     if phase=='collapse':window.send({'type':'collapse'})
     if phase=='groups':window.send({'type':'section','value':'groups'})
     if phase=='locked':window.setProperty('model',dict(section='groups',project='demo',projects=[dict(value='demo',label='Demo')],locked=True,busy=False,drafts=['schema']));window.send({'type':'close'})
     frame(window);image=f'qml-{mode}-{language}-{width}-{phase}.png';assert window.grabWindow().save(str(OUT/image))
     samples.append(dict(mode=mode,language=language,width=width,height=height,phase=phase,image=image,scene=json.loads(window.property('sceneJson')),state=json.loads(window.property('stateJson')),**snapshot(window)))
    assert not warnings,warnings
   finally:window.close();window.deleteLater();engine.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete);app.removeTranslator(translator)
(OUT/'qml.json').write_text(json.dumps(dict(sha256=sources[0],nativeSources=sources[1],captures=samples),ensure_ascii=False,indent=2),encoding='utf8')
print('Captured',len(samples),'native Administration shell states')
