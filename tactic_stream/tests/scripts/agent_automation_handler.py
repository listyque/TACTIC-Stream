"""Actual Handler hooks, public API, shelf dispatch and native modal Frame consumer."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace
from unittest.mock import patch

parser = argparse.ArgumentParser()
parser.add_argument('--handler-root', type=Path, required=True)
parser.add_argument('--fixture', type=Path, required=True)
args = parser.parse_args()
sys.path.insert(0, str(args.handler_root))
os.environ.update(QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software', QSG_RENDER_LOOP='basic', QT_QUICK_CONTROLS_STYLE='Basic')
data = json.loads(args.fixture.read_text(encoding='utf-8'))
project = data.get('project', 'one')
search_key = data.get('search_key', 'contract/entity?project=one&code=A')

from PySide6.QtCore import QCoreApplication, QPointF, Qt, QUrl
from PySide6.QtGui import QFont, QFontDatabase, QFontMetrics
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtTest import QTest
from tests.qt_application import gui_test_application
from tests.test_script_shelf import _Application, _Users
from thlib.environment import env_mode, env_inst
env_mode.current_path = str(args.fixture.parent / 'native-profile')
from thlib import tactic_classes as tc
from thlib.side.client.tactic_client_lib import TacticServerStub
from thlib.ui.script_editor import ScriptEditorController
from thlib.ui.script_shelf import ScriptShelfController
from thlib.ui.script_triggers import ScriptTriggerController
from thlib.ui.checkin_out import CheckinOutController
from tactic_handler_api import HandlerAPI

app = gui_test_application()
if os.name == 'nt' and 'Segoe UI' not in QFontDatabase.families():
    # Windows offscreen Qt has no system font catalogue; the normal desktop plugin does.
    font = Path(os.environ['WINDIR']) / 'Fonts/segoeui.ttf'
    assert QFontDatabase.addApplicationFont(str(font)) >= 0
assert QFontMetrics(QFont('Segoe UI')).inFont('A')
server = TacticServerStub(server=data['server'], project=project, ticket=data['ticket'])
api = HandlerAPI(SimpleNamespace(server_start=lambda project: server),
                 SimpleNamespace(projects={project: tc.Project(dict(code=project, title=project))}))
with ThreadPoolExecutor(max_workers=1) as worker:
    native_state = worker.submit(lambda: api.project(project).automation.read()).result(30)
    worker.submit(api.close).result(5)

application = _Application()
editor = ScriptEditorController(None, None)
rows = server.query('config/custom_script')
objects = {row['code']: tc.SObject(row) for row in rows}
editor._done(dict(kind='load', projectCode=project, objects=objects, rows=[dict(row, token=row['code']) for row in rows]))
hooks = ScriptTriggerController(application, _Users(), editor, None, None)
hooks._project_code = project
hooks._refreshed((project, hooks._generation, native_state['records'], native_state['revision']))
# Keep the native execution/exception path. Only worker scheduling is synchronous in this probe.
def execute(operation, callback):
    try:
        result = operation()
    except Exception as error:
        callback(False, None, str(error))
    else:
        callback(True, result, '')
hooks._run_script_worker = execute
source = args.fixture.parent / 'blocked.bin'
source.write_bytes(b'owned source')
payload = dict(projectCode=project, searchKey=search_key,
               operation_id='native-checkin', process='publish', context='publish', files=[dict(path=str(source))])
before = len(server.query('sthpw/snapshot'))
completed = []
hooks.run_before('snapshot.save', CheckinOutController._trigger_context(SimpleNamespace(), payload),
                 lambda *result: completed.append(result))
assert completed and completed[-1][0] is False, completed
assert len(server.query('sthpw/snapshot')) == before
source = source.with_name('accepted.bin')
source.write_bytes(b'owned accepted source')
payload['files'][0]['path'] = str(source)
hooks.run_before('snapshot.save', CheckinOutController._trigger_context(SimpleNamespace(), payload),
                 lambda *result: completed.append(result))
assert completed[-1][0] is True, completed
snapshot = server.simple_checkin(payload['searchKey'], 'publish', str(source), mode='upload')
payload['_serverSnapshot'] = snapshot
hooks.run_after('snapshot.save', CheckinOutController._trigger_context(SimpleNamespace(), payload))
assert Path(data['marker']).read_text(encoding='utf-8') == snapshot['__search_key__']

# Render the actual shelf, click its Frame action and open the saved script's modal tool.
application.current_project_code = project
application.context = dict(entryKey=data.get('entry_key', 'contract/entity@entities'), title='Entities', shelfPreset=data['shelf_view'],
                           search_keys=[payload['searchKey']], tab_id='captured-tab')
shelf = ScriptShelfController(application, _Users(), editor)
shelf._project_code = project
shelf._active_mode = 'shared'
shelf._active_mode_selected = True
shelf._sync_records(server.query('config/widget_config', [('search_type', 'SideBarWdg')]))
assert shelf.buttons.records(), shelf._records
engine = QQmlEngine()
warnings = []
engine.warnings.connect(lambda errors: warnings.extend(e.toString() for e in errors))
engine.rootContext().setContextProperty('agentShelf', shelf)
qml = QUrl.fromLocalFile(str(args.handler_root / 'thlib/ui/qml')).toString()
component = QQmlComponent(engine)
component.setData(('''import QtQuick
import QtQuick.Window
import "''' + qml + '''" as TH
Window {
    width: 800; height: 160
    property bool dark: true
    property string applicationThemeStyleName: "md3"
    property color applicationThemeBaseColor: "#292d30"
    property color applicationThemeAccentColor: "#78a6c4"
    TH.Theme { id: toolTheme; dark: true }
    TH.ScriptShelfBar { anchors.fill: parent; theme: toolTheme; controller: agentShelf }
}''').encode(), QUrl.fromLocalFile(str(args.fixture.parent / 'Shelf.qml')))
deadline = time.monotonic() + 5
while component.status() == QQmlComponent.Loading and time.monotonic() < deadline:
    QTest.qWait(10)
parent = component.create()
assert parent is not None, [e.toString() for e in component.errors()]
env_inst.ui_main = parent
parent.show()
QTest.qWait(100)
def items(item):
    yield item
    for child in item.childItems():
        yield from items(child)
target = next((item for item in items(parent.contentItem())
               if item.property('frameId') == 'scriptShelfAction_' + data['button_id']
               or item.objectName() == 'scriptShelfAction_' + data['button_id']), None)
assert target is not None, [(item.objectName(), item.property('frameId')) for item in items(parent.contentItem())]
point = target.mapToScene(QPointF(target.width() / 2, target.height() / 2)).toPoint()
QTest.mouseClick(parent, Qt.LeftButton, pos=point)
application.context['search_keys'][:] = ['changed-after-click']
from side_tools.frame_tool.showcase import _windows
deadline = time.monotonic() + 5
while not _windows and time.monotonic() < deadline:
    QTest.qWait(20)
assert _windows, editor.output
window = _windows[-1][0]
assert window.modality() == Qt.WindowModal
assert window.property('records')[0]['id'] == payload['searchKey']
if data.get('screenshot'):
    assert window.grabWindow().save(data['screenshot'])
window.close()
QTest.qWait(20)
assert not _windows
assert not warnings, warnings
parent.close()
env_inst.ui_main = None
editor.shutdown()
print('Native Handler API, before rejection, real check-in, after program, shelf click/context and modal Frame lifecycle passed')
