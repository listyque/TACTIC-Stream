"""Native TH consumer against the disposable, container-local TS server only."""
import base64
import code
import json
import sys
import traceback
from pathlib import Path
import time
from types import SimpleNamespace

from PySide6.QtCore import QObject, QPointF, Qt, QUrl, Signal, QEvent
from PySide6.QtGui import QGuiApplication, QInputMethodEvent
from PySide6.QtCore import QCoreApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtTest import QTest

ROOT = Path('/work')
request = json.loads((ROOT/'request.json').read_text())
fixture = json.loads((ROOT/'fixture.json').read_text())
case = request['case']
document = request['document']
project = fixture['project']

from thlib.environment import env_mode, env_inst, env_server
env_mode.current_path = str(ROOT/'profile')
from thlib import tactic_classes as tc
from thlib.side.client.tactic_client_lib import TacticServerStub
from thlib.ui.script_editor import ScriptEditorController
from thlib.ui.script_shelf import ScriptShelfController
from thlib.ui.script_triggers import ScriptTriggerController
from thlib.ui.checkin_out import CheckinOutController
from thlib.ui.models import NavigationModel
from thlib.pool import ThreadsPool


class ObservedConsole(code.InteractiveConsole):
    failed = False

    def showtraceback(self):
        self.failed = True
        super().showtraceback()

    def showsyntaxerror(self, filename=None):
        self.failed = True
        super().showsyntaxerror(filename)

    def runcode(self, compiled):
        try:
            super().runcode(compiled)
        except BaseException:
            self.failed = True
            raise


# Native editor consoles intentionally print exceptions; trials must also observe their failure state.
code.InteractiveConsole = ObservedConsole


class Host(QObject):
    project_changed = Signal(str, str)
    search_state_changed = Signal()
    windowVisibilityChanged = Signal(str, bool)
    stateChanged = Signal()
    login = 'admin'
    canManageUsers = True
    current_project_code = ''

    def __init__(self):
        super().__init__()
        self.window_model = self
        self._registry = SimpleNamespace(register=lambda *args: None)
        self.navigation_model = NavigationModel()
        self.context = {}
        self.notifications = []

    def script_shelf_context(self):
        return self.context.copy()

    def _notify(self, message):
        self.notifications.append(str(message))
        print(message)


def items(item):
    yield item
    for child in item.childItems():
        yield from items(child)


def click(window, identity):
    target = next((item for item in items(window.contentItem())
                   if item.property('frameId') == identity or item.objectName() == identity), None)
    if target is None or not target.isVisible() or not target.isEnabled():
        raise AssertionError('UI action is unavailable: ' + identity)
    point = target.mapToScene(QPointF(target.width()/2, target.height()/2)).toPoint()
    QTest.mouseClick(window, Qt.LeftButton, pos=point)
    QTest.qWait(40)


def main():
    app = QGuiApplication([])
    unhandled = []
    def exception(kind, value, trace):
        unhandled.append(str(value))
        traceback.print_exception(kind, value, trace)
    sys.excepthook = exception
    host = Host()
    server = TacticServerStub(server='127.0.0.1:8081', project=project, ticket=fixture['ticket'])
    deadline = time.monotonic() + 12
    while True:
        try:
            scripts = server.query('config/custom_script')
            break
        except Exception:
            if time.monotonic() > deadline:
                raise
            time.sleep(.05)
    env_server.set_server('127.0.0.1:8081')
    env_server.set_user('admin')
    env_server.set_ticket(fixture['ticket'])
    env_server.save_defaults()
    env_inst.projects = {row['code']: tc.Project(row) for row in server.query('sthpw/project')}
    from tactic_handler_api import local
    from tactic_handler_api.api import _bind_current
    public_api = local()
    _bind_current(public_api)
    editor = ScriptEditorController(None, None)
    editor._done(dict(kind='load', projectCode=project,
        objects={row['code']: tc.SObject(row) for row in scripts},
        rows=[dict(row, token=row['code']) for row in scripts]))
    result = dict(status='passed', observations=[], screenshot=None)
    if document['kind'] == 'hook':
        pool = ThreadsPool(max_threads=2)
        hooks = ScriptTriggerController(host, host, editor, pool, None)
        hooks._project_code = project
        state = fixture['state']
        hooks._refreshed((project, hooks._generation, state['records'], state['revision']))
        def wait_callback():
            deadline = time.monotonic()+35
            while not completed and time.monotonic() < deadline:
                QTest.qWait(10)
            assert completed, 'Native hook did not complete before the trial limit'
        files = []
        (ROOT/'files').mkdir()
        for item in case['files']:
            path = ROOT/'files'/item['name']
            path.write_text(item['content'], encoding='utf-8')
            files.append(dict(path=str(path)))
        payload = dict(projectCode=project, searchKey=fixture['search_key'], operation_id=request['trial_id'],
                       process=case['process'], context=case['context'], files=files)
        before = len(server.query('sthpw/snapshot'))
        completed = []
        if document['phase'] == 'before':
            hooks.run_before('snapshot.save', CheckinOutController._trigger_context(SimpleNamespace(), payload),
                             lambda *values: completed.append(values))
            wait_callback()
            assert pool.is_started, 'The trial did not execute a matching hook'
            allowed = completed[-1][0]
            result['observations'].append(dict(before_allowed=allowed, message=completed[-1][1]))
            assert allowed == (case['expect'] == 'allow'), completed
            if not allowed:
                assert len(server.query('sthpw/snapshot')) == before
        if document['phase'] == 'after' or allowed:
            snapshot = server.simple_checkin(fixture['search_key'], case['context'], files[0]['path'],
                                            mode='upload', create_icon=False)
            snapshots = server.query('sthpw/snapshot')
            assert len(snapshots) > before and any(row['code'] == snapshot['code'] for row in snapshots)
            assert server.query('sthpw/file', [('snapshot_code', snapshot['code'])]), 'Check-in has no stored file'
            payload['_serverSnapshot'] = snapshot
            result['observations'].append(dict(snapshot=snapshot['__search_key__']))
            if document['phase'] == 'after':
                hooks.run_after('snapshot.save', CheckinOutController._trigger_context(SimpleNamespace(), payload),
                                lambda *values: completed.append(values))
                wait_callback()
                assert pool.is_started and not host.notifications, host.notifications
                assert completed and completed[-1][0], completed
        for artifact in case['artifacts']:
            path = ROOT/artifact['name']
            text = path.read_text(encoding='utf-8')
            assert artifact['contains'] in text, 'Expected artifact content is absent'
            result['observations'].append(dict(artifact=artifact['name'], text=text[:8192]))
        hooks.shutdown()
        assert pool.exit(2000), 'Native worker pool did not stop'
    else:
        engine = QQmlEngine()
        warnings = []
        engine.warnings.connect(lambda errors: warnings.extend(e.toString() for e in errors))
        shelf = ScriptShelfController(host, host, editor)
        shelf._project_code = project
        shelf._active_mode = 'shared'
        shelf._active_mode_selected = True
        shelf._sync_records(server.query('config/widget_config', [('search_type', 'SideBarWdg')]))
        applied = fixture['applied']
        preset = next(row for row in fixture['state']['shelves'] if row['code'] == applied['binding']['savedCode'])
        host.current_project_code = project
        host.context = dict(entryKey=document['entry_key'], title='Trial objects', shelfPreset=preset['view'],
                            search_keys=[fixture['search_key']], tab_id='trial-tab')
        shelf._context_changed()
        engine.rootContext().setContextProperty('trialShelf', shelf)
        qml = QUrl.fromLocalFile('/opt/trial/handler/thlib/ui/qml').toString()
        component = QQmlComponent(engine)
        component.setData(('''import QtQuick
import QtQuick.Window
import "''' + qml + '''" as TH
Window { width:800; height:160
    property bool dark:true
    property string applicationThemeStyleName:"md3"
    property color applicationThemeBaseColor:"#292d30"
    property color applicationThemeAccentColor:"#78a6c4"
    TH.Theme { id:toolTheme; dark:true }
    TH.ScriptShelfBar { anchors.fill:parent; theme:toolTheme; controller:trialShelf }
}''').encode(), QUrl.fromLocalFile('/work/Shelf.qml'))
        parent = component.create()
        assert parent is not None, [error.toString() for error in component.errors()]
        env_inst.ui_main = parent
        parent.show()
        QTest.qWait(120)
        click(parent, 'scriptShelfAction_' + applied['draft_id'])
        host.context['search_keys'][:] = ['changed-after-click']
        QTest.qWait(80)
        assert not editor.error, editor.output
        assert not any(console.failed for console in editor._local_consoles.values()), editor.output
        windows = [window for window in app.topLevelWindows() if window is not parent and window.isVisible()]
        assert len(windows) == 1, editor.output
        window = windows[0]
        assert window.modality() in (Qt.WindowModal, Qt.ApplicationModal), 'Shelf UI must be modal'
        for action in case['actions']:
            if action['kind'] == 'click':
                click(window, action['target'])
            elif action['kind'] == 'expect':
                value = window.property(action['target'])
                assert action['contains'] in json.dumps(value, default=str), 'UI property expectation failed'
            elif action['kind'] == 'point':
                assert action['x'] < window.width() and action['y'] < window.height(), 'Click is outside the tested window'
                QTest.mouseClick(window, Qt.LeftButton, pos=QPointF(action['x'], action['y']).toPoint())
            elif action['kind'] == 'text':
                target = QGuiApplication.focusObject()
                assert target is not None, 'No focused text control'
                event = QInputMethodEvent()
                event.setCommitString(action['text'])
                QCoreApplication.sendEvent(target, event)
            else:
                QTest.keyClick(window, Qt.Key_Backspace)
            QTest.qWait(30)
        image = window.grabWindow()
        assert not unhandled, unhandled
        assert image.save('/work/window.png')
        result['screenshot'] = base64.b64encode((ROOT/'window.png').read_bytes()).decode()
        result['observations'].append(dict(modal=True, title=window.title(), actions=len(case['actions'])))
        window.close()
        QTest.qWait(40)
        assert not [w for w in app.topLevelWindows() if w is not parent and w.isVisible()]
        assert not warnings, warnings
        parent.close()
        env_inst.ui_main = None
        parent.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        engine.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        assert not warnings, warnings
    editor.shutdown()
    public_api.close(wait=False)
    (ROOT/'report.json').write_text(json.dumps(result, default=str))


if __name__ == '__main__':
    main()
