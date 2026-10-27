from fixture import *
import time
from native_capture import source_hashes
HERE=Path(__file__).resolve().parent;OUT=HERE/'output';OUT.mkdir(exist_ok=True)
from thlib.ui.localization import CatalogTranslator
sources=source_hashes(ROOT,TH,['thlib/ui/qml/features/administration/layouts/LayoutEditorView.qml','thlib/ui/layout_editor.py','thlib/ui/source_editor.py']);samples=[]
quick=os.environ.get('FRAME_CAPTURE_QUICK')=='1'
for mode in ('dark',) if quick else ('dark','light'):
 for language in ('en',) if quick else ('en','ru'):
  for width,height in ((1100,740),) if quick else ((1100,740),(800,740),(360,740)):
   api=Api();pool=Pool();application=LayoutApplication()
   with patch.object(env_inst,'projects',{'demo':project}),patch.object(env_inst,'get_project_by_code',return_value=project),patch.object(env_inst,'server_pool',pool),patch.object(env_server,'get_server',return_value='http://localhost:9123'),patch.object(tc,'server_start',return_value=server),patch.object(tc,'_execute_read_only_procedure_serverside',side_effect=api.execute):
    controller=module.LayoutEditorHost(application);controller.reset('demo');controller._view='cards_example';controller.activate('demo')
    controller.previewModel.replace_nodes([WorkspaceNode(node_id='demo/asset?code=A1',node_type='sobject',search_key='demo/asset?code=A1',code='A1',title='Asset',values={'name':'Asset'},comments=2,tasks=3)])
    engine=QQmlEngine();warnings=[];engine.warnings.connect(lambda errors:warnings.extend(e.toString() for e in errors));translator=CatalogTranslator(TH/'thlib/ui/translations/ru.json')
    if language=='ru':app.installTranslator(translator)
    for name,value in icons.items():engine.rootContext().setContextProperty(name,value)
    engine.rootContext().setContextProperty('appController',application)
    engine.rootContext().setContextProperty('fixture',controller);component=QQmlComponent(engine,QUrl.fromLocalFile(str(HERE/'LayoutHarness.qml')));assert component.isReady(),[e.toString() for e in component.errors()]
    window=component.createWithInitialProperties({'width':width,'height':height,'dark':mode=='dark','language':language});assert window
    try:
     frame(window)
     deadline=time.monotonic()+5
     while controller.model['preview'] is None and time.monotonic()<deadline:QTest.qWait(10)
     assert controller.model['preview'] is not None,controller.model['error']
     frame(window)
     for page in ('design','configuration','xml','changes','resolved','new-form'):
      window.send({'type':'page','value':'design' if page=='new-form' else page});frame(window)
      if page=='new-form':click(window,controls(window)['layoutNewView'])
      if page=='design':window.send({'type':'select','name':'title'});frame(window)
      image=f'qml-{mode}-{language}-{width}-{page}.png';assert window.grabWindow().save(str(OUT/image))
      samples.append(dict(mode=mode,language=language,width=width,height=height,phase=page,image=image,scene=json.loads(window.property('sceneJson')),state=json.loads(window.property('stateJson')),**snapshot(window)))
     assert not warnings,warnings
    finally:window.close();window.deleteLater();controller.shutdown();engine.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete);app.removeTranslator(translator)
(OUT/'fixture.json').write_text(json.dumps(dict(configuration=Api().configuration(),items=[dict(kind='object',title='Asset',record={'name':'Asset','__search_key__':'demo/asset?code=A1'},note_count=2,task_count=3)])),encoding='utf8')
(OUT/'qml.json').write_text(json.dumps(dict(sha256=sources[0],nativeSources=sources[1],captures=samples),ensure_ascii=False,indent=2),encoding='utf8')
print('Captured',len(samples),'native Layout states')
