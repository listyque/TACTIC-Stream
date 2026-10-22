"""Production Columns Editor; real native input on an isolated catalog."""
import hashlib
import json
import os
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
TH = Path('D:/grav/Tactic Stream/TH')
HERE = Path(__file__).resolve().parent
OUT = HERE / 'output'
OUT.mkdir(exist_ok=True)
os.environ.update(QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software', QT_FONT_DPI='96')
sys.path[:0] = [str(TH), str(REPO / 'tools/frame_admin')]
from PySide6.QtCore import QPointF, Qt, QUrl, QCoreApplication, QEvent
from PySide6.QtGui import QFontDatabase
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtTest import QTest
from thlib.ui.localization import CatalogTranslator
from thlib.ui.icon_font import qml_icon_bindings
from thlib.ui.columns_editor import ColumnsEditorController
from tests.test_columns_table_view import ColumnsTableViewTests, _Application, _SType
from tests.profile_ui_responsiveness import frame
from tests.test_sidebar_editor_qml import SidebarEditorQmlTests
from native_capture import controls, click, text, choose, snapshot, source_hashes

native_names = ['thlib/ui/qml/features/administration/columns/ColumnsEditorView.qml', 'thlib/ui/columns_editor.py']
initial_sources = source_hashes(REPO,TH,native_names)

ColumnsTableViewTests.setUpClass()
app = ColumnsTableViewTests.app
icons = qml_icon_bindings(TH,app)
for name in ('segoeui.ttf', 'seguisb.ttf'): QFontDatabase.addApplicationFont('C:/Windows/Fonts/' + name)
cases = json.loads((HERE / 'cases.json').read_text())
samples = []
quick = os.environ.get('FRAME_CAPTURE_QUICK') == '1'
for mode in ('dark',) if quick else ('dark', 'light'):
    for language in ('en',) if quick else ('en', 'ru'):
        for width, height in ((1100, 740),) if quick else ((1100, 740), (800, 740), (360, 740)):
            application = _Application(_SType())
            controller = ColumnsEditorController(application)
            records = application.stype.project.views.config_dict
            records += [dict(code='WIDGET002',search_type='demo/asset',view='custom_view',config='<config><custom_view class="custom.Layout" /></config>'),dict(code='WIDGET003',search_type='demo/shot',view='table',config='<config><table /></config>')]
            controller._set_definition_catalog('demo', application.stype.project, records, {'demo/asset':'Assets','demo/shot':'Shots'})
            controller.load_definition_catalog = lambda *_: None
            engine, window = QQmlEngine(), None
            translator = CatalogTranslator(TH / 'thlib/ui/translations/ru.json')
            if language == 'ru': app.installTranslator(translator)
            warnings = []
            engine.warnings.connect(lambda errors: warnings.extend(e.toString() for e in errors))
            try:
                for name,value in icons.items():engine.rootContext().setContextProperty(name,value)
                engine.rootContext().setContextProperty('columnsEditorController',controller)
                catalog = dict(records=[dict(row,id=index+1) for index,row in enumerate(controller.definitionCatalog)],searchTypes=controller.definitionCatalogSearchTypes,revision='fixture-revision')
                (OUT/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False),encoding='utf8')
                component = QQmlComponent(engine,QUrl.fromLocalFile(str(HERE/'ColumnsHarness.qml')))
                assert component.isReady(),[e.toString() for e in component.errors()]
                window = component.create(); assert window
                window.resize(width,height);window.setProperty('language',language);window.setProperty('dark',mode=='dark');frame(window)
                for case in cases:
                    for action in case['actions']:
                        if action['type']=='state':
                            window.setProperty('canWrite',action['value']!='readonly');controller._catalog_uncertain=action['value']=='uncertain';controller._busy=action['value']=='busy';controller.stateChanged.emit()
                        elif action['type']=='reveal':
                            # Position the control at the top while respecting native scroll limits.
                            all_items = list(SidebarEditorQmlTests.descendants(window.contentItem()))
                            viewport = next(item for item in all_items if item.objectName()==action['viewport'])
                            item = next(item for item in all_items if item.objectName()==action['id'])
                            y = viewport.property('contentY')+item.mapToItem(viewport,QPointF()).y()-12
                            viewport.setProperty('contentY',max(0,min(y,max(0,viewport.property('contentHeight')-viewport.height()))))
                        else:
                            item = controls(window)[action['id']]
                            if action['type']=='text':text(window,item,action['value'])
                            elif action['type']=='choose':choose(window,item,action['value'])
                            else:click(window,item)
                        frame(window)
                    window.blur();QTest.mouseMove(window,QPointF(width-1,height-1).toPoint());frame(window)
                    image=f'columns-qml-{mode}-{language}-{width}-{case["phase"]}.png'
                    assert window.grabWindow().save(str(OUT/image))
                    samples.append(dict(mode=mode,language=language,width=width,height=height,phase=case['phase'],image=image,scene=json.loads(window.property('sceneJson')),state=json.loads(window.property('stateJson')),**snapshot(window)))
                assert not warnings,warnings
            finally:
                if window:window.close();window.deleteLater()
                controller.shutdown();engine.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete);app.removeTranslator(translator)
assert source_hashes(REPO,TH,native_names) == initial_sources, 'Sources changed during native capture; repeat the run'
hashes,native = initial_sources
(OUT/'qml.json').write_text(json.dumps(dict(sha256=hashes,nativeSources=native,captures=samples),ensure_ascii=False,indent=2),encoding='utf8')
print(f'Captured {len(samples)} Columns Editor states')
