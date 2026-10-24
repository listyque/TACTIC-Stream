"""Log in and open an imported asset using the delivered native Handler and real RPC."""
import json
import os
from pathlib import Path
import sys
import time
import traceback

bundle, address, login, project, destination = sys.argv[1:]
output = Path(destination)
output.mkdir(parents=True, exist_ok=False)
os.environ.update(
    PYTHONDONTWRITEBYTECODE='1',
    TACTIC_QML_TEST_SETTINGS_DIR=str(output / 'profile'), QT_QPA_PLATFORM='offscreen',
    QT_QUICK_BACKEND='software', QSG_RENDER_LOOP='basic', QT_FONT_DPI='96',
    QT_QPA_FONTDIR=str(Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts'))
for name in ('TACTIC_QML_SMOKE_OFFLINE', 'TACTIC_QML_SMOKE_EXIT_MS'):
    os.environ.pop(name, None)
sys.path.insert(0, str(Path(bundle) / 'TACTIC-Handler'))

from PySide6.QtCore import QPointF, QTimer, Qt
from PySide6.QtTest import QTest
from PySide6.QtQml import QQmlEngine
from PySide6.QtWidgets import QApplication
from thlib.environment import env_mode, env_server
from thlib.ui import application

assert Path(application.__file__).resolve().is_relative_to(Path(bundle).resolve())
env_mode.set_current_path(str(output / 'profile'))
env_server.reload()
env_server.set_server(address)
env_server.set_user(login)
env_server.set_ticket('')
env_server.save_defaults()
report = dict(login=login, project=project, status='failed', rendering='Qt offscreen/software')


def wait(predicate, message, timeout=45):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return
        QTest.qWait(50)
    raise TimeoutError(message)


def items(root):
    yield root
    for child in root.childItems():
        yield from items(child)


def find(window, name):
    return next((item for item in items(window.contentItem()) if item.isVisible()
                 and (item.objectName() == name or item.property('frameId') == name)), None)


def click(window, item):
    assert item is not None
    point = item.mapToScene(QPointF(item.width() / 2, item.height() / 2)).toPoint()
    QTest.mouseClick(window, Qt.LeftButton, pos=point)
    QTest.qWait(150)


def text(window, name, value):
    item = find(window, name)
    assert item is not None, name
    click(window, item)
    item.forceActiveFocus()
    QTest.keyClick(window, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClick(window, Qt.Key_Backspace)
    for char in value:
        QTest.keyClick(window, char)
    QTest.qWait(100)


def surfaces(app):
    return [w for w in app.allWindows() if w.isVisible() and hasattr(w, 'contentItem')]


def check():
    app = QApplication.instance()
    controller = None
    try:
        window = next(w for w in app.allWindows() if w.title().startswith('TACTIC-Handler'))
        window.resize(1440, 1000)
        context = QQmlEngine.contextForObject(window)
        controller = context.contextProperty('appController')
        context.contextProperty('localizationController').set_language('en')
        QTest.qWait(500)
        controller.request_authentication()
        wait(lambda: any('Sign in' in w.title() for w in surfaces(app)), 'Login did not open')
        dialog = next(w for w in surfaces(app) if 'Sign in' in w.title())
        text(dialog, 'signIn_login', login)
        text(dialog, 'signIn_password', os.environ['RECOVERY_TEST_PASSWORD'])
        assert dialog.property('login') == login
        assert len(dialog.property('password')) == len(os.environ['RECOVERY_TEST_PASSWORD'])
        click(dialog, find(dialog, 'signInSubmit'))
        wait(lambda: not controller.authentication_required and controller.server_state == 'online',
             'Authentication failed')
        assert controller.can_administer == (login == 'admin')
        report['login_and_role'] = True
        click(window, find(window, 'mainProject'))

        def card():
            for surface in surfaces(app):
                for item in items(surface.contentItem()):
                    details = item.property('details')
                    if hasattr(details, 'toVariant'):
                        details = details.toVariant()
                    if item.isVisible() and isinstance(details, dict) and details.get('code') == project:
                        return surface, item

        wait(lambda: card() is not None, 'Project card missing')
        click(*card())
        wait(lambda: controller.current_project_code == project, 'Project did not load')
        QTest.qWait(1500)
        click(window, find(window, 'mainNavigation'))
        entry_key = 'vfx/asset@asset' if '_vfx_' in project else 'game/asset@asset_table'

        def navigation_entry():
            for surface in surfaces(app):
                for item in items(surface.contentItem()):
                    if item.isVisible() and item.property('entryKey') == entry_key:
                        return surface, item

        wait(lambda: navigation_entry() is not None, 'Asset navigation entry missing')
        click(*navigation_entry())
        wait(lambda: any(item.isVisible() and item.property('text') == 'Artist update'
                         for item in items(window.contentItem())), 'Imported asset was not rendered')
        QTest.qWait(250)
        window.grabWindow().save(str(output / 'project.png'))
        report.update(status='passed', project_selected=True, asset_visible=True,
                      can_administer=controller.can_administer, server_state=controller.server_state)
    except Exception as error:
        report['error'] = type(error).__name__ + ': ' + str(error)
        if controller is not None:
            report.update(server_state=controller.server_state,
                          authentication_error=controller.authentication_error)
        traceback.print_exc()
    finally:
        (output / 'result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n',
                                          encoding='utf-8')
        app.quit()


app = QApplication([])
QTimer.singleShot(2000, check)
status = application.main()
assert report['status'] == 'passed', report
raise SystemExit(status)
