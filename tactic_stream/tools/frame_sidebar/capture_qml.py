"""Production Sidebar Editor, isolated native controller and real input."""
import hashlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

REPO = Path(__file__).resolve().parents[2]
TH = Path('D:/code/th_codex')
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
from tests.test_sidebar_editor_qml import SidebarEditorQmlTests
from tests.profile_ui_responsiveness import frame
from native_capture import controls, click, text, snapshot, source_hashes

native_names = ['thlib/ui/qml/features/administration/sidebar/SidebarEditorView.qml', 'thlib/ui/sidebar_editor.py']
initial_sources = source_hashes(REPO,TH,native_names)

SidebarEditorQmlTests.setUpClass()
for name in ('segoeui.ttf', 'seguisb.ttf'):
    QFontDatabase.addApplicationFont('C:/Windows/Fonts/' + name)
cases = json.loads((HERE / 'cases.json').read_text())
samples = []
quick = os.environ.get('FRAME_CAPTURE_QUICK') == '1'
group_records = [dict(code='G' + str(i), login_group='group_' + str(i), description='Group ' + str(i).zfill(2), access_rules='') for i in range(30)]

class Group:
    def __init__(self, row): self.row = row
    def get_info(self): return self.row
    def get_login_group(self): return self.row['login_group']
    def get_pretty_name(self): return self.row['description']

for mode in ('dark',) if quick else ('dark', 'light'):
    for language in ('en',) if quick else ('en', 'ru'):
        for width, height in ((1100, 740),) if quick else ((1100, 740), (800, 740), (360, 740)):
            fixture = SidebarEditorQmlTests()
            fixture.setUp()
            editor, engine, window = fixture.controller, QQmlEngine(), None
            translator = CatalogTranslator(TH / 'thlib/ui/translations/ru.json')
            if language == 'ru': fixture.app.installTranslator(translator)
            warnings = []
            engine.warnings.connect(lambda errors: warnings.extend(error.toString() for error in errors))
            try:
                from xml.etree import ElementTree
                from thlib.ui.sidebar_editor import _serialize
                for view, document in editor._documents.items():
                    if any(child.tag == 'element' for child in document):
                        container = ElementTree.Element('view', {'name': view})
                        for child in list(document): document.remove(child); container.append(child)
                        document.append(container)
                editor._original_xml = {view:_serialize(document) for view, document in editor._documents.items()}
                editor._security_objects = {row['code']: Group(row) for row in group_records}
                editor._rebuild_entries()
                for name, value in fixture.icons.items(): engine.rootContext().setContextProperty(name, value)
                engine.rootContext().setContextProperty('sidebarEditorController', editor)
                engine.rootContext().setContextProperty('windowModel', fixture.application.window_model)
                catalog = dict(documents=editor._original_xml, entries=editor.entryRecords, selected=editor.selectedRow, xml=editor.xmlText,
                    source='handler', collapsed=[], updates=[], previewGroup='', groups=[dict(code=r['code'],label=r['description'],allowed=False) for r in group_records],
                    groupRecords=group_records, revision='fixture-revision', project='demo', projectTitle='Demo', searchTypes=[dict(value='demo/assets',label='Assets',color='#e35062')],
                    library=[dict(view='workspace_layout@review',title='Review',category='workspace_layout',search_type='SideBarWdg')])
                (OUT / 'catalog.json').write_text(json.dumps(catalog, ensure_ascii=False), encoding='utf-8')
                component = QQmlComponent(engine, QUrl.fromLocalFile(str(HERE / 'SidebarHarness.qml')))
                assert component.isReady(), [e.toString() for e in component.errors()]
                window = component.create()
                assert window, [e.toString() for e in component.errors()]
                window.resize(width, height); window.setProperty('language', language); window.setProperty('dark', mode == 'dark')
                frame(window)
                for case in cases:
                    for action in case['actions']:
                        if action['type'] == 'state':
                            fixture.application.can_administer = action['value'] != 'readonly'
                            editor._users.canManageUsers = action['value'] != 'readonly'
                            editor._write_uncertain = action['value'] == 'uncertain'
                            editor._busy = action['value'] == 'busy'
                            editor.stateChanged.emit()
                        else:
                            item = controls(window)[action['id']]
                            if action['type'] == 'text': text(window, item, action['value'])
                            else: click(window, item)
                        frame(window)
                    window.blur(); QTest.mouseMove(window, QPointF(width - 1, height - 1).toPoint()); frame(window)
                    image = f'sidebar-qml-{mode}-{language}-{width}-{case["phase"]}.png'
                    assert window.grabWindow().save(str(OUT / image))
                    samples.append(dict(mode=mode, language=language, width=width, height=height, phase=case['phase'],image=image,
                        scene=json.loads(window.property('sceneJson')), state=json.loads(window.property('stateJson')), **snapshot(window)))
                assert not warnings, warnings
            finally:
                if window: window.close(); window.deleteLater()
                engine.deleteLater(); QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
                fixture.app.removeTranslator(translator)
                fixture.doCleanups()
assert source_hashes(REPO,TH,native_names) == initial_sources, 'Sources changed during native capture; repeat the run'
hashes,native = initial_sources
(OUT / 'qml.json').write_text(json.dumps(dict(sha256=hashes,nativeSources=native,captures=samples),ensure_ascii=False,indent=2),encoding='utf-8')
print(f'Captured {len(samples)} Sidebar Editor states')
