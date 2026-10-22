"""Native file presenters reach disposable servers and their existing owners."""

import json
from contextlib import ExitStack
from pathlib import Path
import threading
from time import monotonic
import unittest
from unittest.mock import patch

from test_file_project import FileProjectFixture
from test_handler_file_workspace_ui import (
    QGuiApplication,
    QQmlEngine,
    QQmlComponent,
    QUrl,
    QQuickWindow,
    QTest,
    QPointF,
    Qt,
    QCoreApplication,
    QEvent,
    env_inst,
    env_mode,
    ThreadsPool,
)
import test_file_transfer as transfers
from PySide6.QtGui import QInputMethodEvent
from tests.frame_files_fixture import Windows, Locale
from tests.test_frame_sync import Application, visual
import tests.test_repository_sync_editor as EditorFixtures
from thlib.ui.repository_sync import RepositorySyncController
from thlib.side.client.tactic_client_lib.tactic_server_stub import TacticServerStub

QML = Path("D:/grav/Tactic Stream/TH/thlib/ui/qml")


class NativeFileIntegrationTest(FileProjectFixture, unittest.TestCase):
    http = transfers.FileTransferTest.http

    @classmethod
    def setUpClass(cls):
        cls.app = QGuiApplication.instance() or QGuiApplication([])

    def test_repository_sync_preset_create_update_delete_through_xmlrpc(self):
        self.api.dispatch(
            "execute_cmd",
            (
                {"ticket": self.token, "project": "admin"},
                "tactic.command.CreateProjectCmd",
                {"project_code": "demo", "project_title": "Sync presets"},
            ),
        )
        pool = ThreadsPool(2)
        pool.start()
        notifications = []
        clients = []
        with ExitStack() as fixture, self.http(worker=True) as url:
            fixture.enter_context(patch.object(env_inst, "server_pool", pool))
            fixture.enter_context(
                patch.object(env_mode, "current_path", self.temp.name)
            )
            fixture.enter_context(
                patch("thlib.environment.cfg_controls.get_checkin", return_value={})
            )

            def connect(**kwargs):
                client = TacticServerStub(
                    server=url, project="demo", ticket=self.token, protocol="xmlrpc"
                )
                clients.append(client)
                return client

            fixture.enter_context(
                patch("thlib.tactic_classes.server_start", side_effect=connect)
            )
            controller, _requests = (
                EditorFixtures.RepositorySyncEditorTests().make_controller()
            )
            controller._notify = notifications.append
            sync = RepositorySyncController()
            application = Application()
            windows = Windows()
            locale = Locale("en")
            engine = QQmlEngine()
            warnings = []
            engine.warnings.connect(
                lambda values: warnings.extend(value.toString() for value in values)
            )
            for name, value in dict(
                windowModel=windows,
                localizationController=locale,
                repositorySyncEditorController=controller,
                repositorySyncPresetModel=controller.presets,
                repositorySyncTreeModel=controller.model,
                repositorySync=sync,
                repoSyncModel=sync.model,
                appController=application,
            ).items():
                engine.rootContext().setContextProperty(name, value)
            theme_component = QQmlComponent(
                engine, QUrl.fromLocalFile(str(QML / "Theme.qml"))
            )
            theme = theme_component.createWithInitialProperties(
                {"dark": True, "popupAnimationsEnabled": False}
            )
            component = QQmlComponent(
                engine, QUrl.fromLocalFile(str(QML / "RepositorySyncEditorView.qml"))
            )
            view = component.createWithInitialProperties(
                {"theme": theme, "windowId": "repository_sync_editor"}
            )
            self.assertIsNotNone(view, str(component.errors()))
            window = QQuickWindow()
            window.resize(1000, 800)
            view.setParentItem(window.contentItem())
            view.setWidth(1000)
            view.setHeight(800)
            window.show()

            def wait():
                deadline = monotonic() + 8
                while (
                    controller.busy or controller._workers
                ) and monotonic() < deadline:
                    QTest.qWait(10)
                    threading.Event().wait(0.005)
                QTest.qWait(50)
                self.assertFalse(controller.busy)
                self.assertFalse(controller.error, controller.error)

            def click(name):
                item = visual(window.contentItem(), name)
                self.assertIsNotNone(item, name)
                QTest.mouseClick(
                    window,
                    Qt.LeftButton,
                    Qt.NoModifier,
                    item.mapToScene(
                        QPointF(item.width() / 2, item.height() / 2)
                    ).toPoint(),
                )
                QTest.qWait(50)

            def stored():
                return connect().query(
                    "sthpw/wdg_settings",
                    [
                        ("key", "search_type:demo/asset:preset_name:nightly_review"),
                        ("project_code", "demo"),
                    ],
                )

            try:
                controller.reload_presets()
                wait()
                visual(view, "repositorySyncProcessPanel").setProperty(
                    "togglersExpanded", True
                )
                QTest.qWait(50)
                click("repositorySyncPresetAddButton")
                field = visual(window.contentItem(), "repositorySyncPresetName")
                self.assertIsNotNone(field)
                field.forceActiveFocus()
                event = QInputMethodEvent()
                event.setCommitString("Nightly review")
                QCoreApplication.sendEvent(self.app.focusObject(), event)
                click("repositorySyncPresetCreate")
                wait()
                rows = stored()
                self.assertEqual(len(rows), 1)
                self.assertEqual(
                    json.loads(rows[0]["data"])["pretty_preset_name"], "Nightly review"
                )
                click("repositorySyncOnlyUpdatesText")
                self.assertTrue(controller.onlyUpdates)
                click("repositorySyncPresetSaveButton")
                wait()
                self.assertTrue(json.loads(stored()[0]["data"])["only_updates"])
                click("repositorySyncPresetDeleteButton")
                click("confirmationAccept")
                wait()
                self.assertEqual(stored(), [])
                self.assertFalse(notifications, notifications)
                self.assertFalse(warnings, warnings)
            finally:
                sync.shutdown()
                pool.exit()
                for client in clients:
                    client.server.__exit__(None, None, None)
                window.close()
                for value in (
                    view,
                    window,
                    controller,
                    sync,
                    application,
                    windows,
                    locale,
                    theme,
                    component,
                    theme_component,
                    engine,
                    pool,
                ):
                    value.deleteLater()
                QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
