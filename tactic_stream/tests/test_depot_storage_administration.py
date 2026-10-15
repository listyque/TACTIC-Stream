"""Depot and storage administration through the native API and both actual UIs."""
from pathlib import Path
import subprocess
import threading
import unittest
from unittest.mock import patch

from test_file_project import FileProjectFixture
import test_file_transfer as transfers


class DepotStorageAdministrationTest(FileProjectFixture, unittest.TestCase):
    http = transfers.FileTransferTest.http
    writer = transfers.FileTransferTest.writer
    client = transfers.FileTransferTest.client
    context = transfers.FileTransferTest.context

    def test_native_index_stop_and_continue_on_old_project(self):
        import test_handler_file_workspace_ui as native
        from pyasm.biz.file_project import access, find
        from tactic.command.file_storage import maintenance
        from pyasm.command import Command
        from thlib.ui.file_workspace_catalog import storage_admin
        with self.context(), access('files'), maintenance('files'):
            command=Command()
            command.execute=lambda:find('chunk','storage-policy').delete(log=False)
            Command.execute_cmd(command)
        self.assertFalse(self.call('storage_status')['initialized'])
        self.call('storage_upgrade')
        self.assertFalse(self.call('storage_status')['indexed'])
        with self.http() as url:
            client=native.FileTransferClient(url,self.token,'files')
            state=native.initial_state()
            stopped=threading.Event();stopped.set()
            storage_admin(client,state,{'operation':'storage_index'},stopped)
            self.assertFalse(state['storage_info']['indexed'])
            self.assertEqual(state['storage_info']['index_table'],1)
            storage_admin(client,state,{'operation':'storage_index'},threading.Event())
            self.assertTrue(state['storage_info']['indexed'])

    def test_depot_editor_revision_permissions_and_private_repository(self):
        from pyasm.common import Environment
        from pyasm.common.errors import SecurityException
        roots = {'fast': str(Path(self.temp.name) / 'fast'), 'plugins': str(Path(self.temp.name) / 'plugins')}
        with patch.object(Environment, 'get_asset_dirs', return_value=roots):
            self.assertEqual(self.call('capabilities')['repositories'], ['default', 'fast'])
            row = self.call('create_depot', code='photos', title='Фото' * 100, repository='fast')
            self.assertEqual(row['storage'], {'repository': 'fast'})
            self.assertEqual(self.call('depot_status', depot='photos')['title'], 'Фото' * 100)
            row = self.call('update_depot', depot='photos', revision=0, title='Images', repository=None)
            self.assertIsNone(row['storage'])
            with self.assertRaisesRegex(ValueError, 'revision conflict'):
                self.call('update_depot', depot='photos', revision=0, title='Lost update')
            with self.assertRaises(ValueError):
                self.call('create_depot', code='long', title='я' * 513)
            with self.assertRaises(ValueError):
                self.call('update_depot', depot='photos', revision=1, repository='plugins')
        artist = self.writer()
        self.assertEqual(self.client(artist, 'capabilities')['repositories'], [])
        with self.assertRaises(SecurityException):
            self.client(artist, 'update_depot', depot='main', revision=0, title='denied')
        with self.assertRaises(SecurityException):
            self.client(artist, 'depot_status', depot='photos')

    def test_policy_exact_integers_conflicts_and_restored_gc(self):
        from pyasm.common.errors import SecurityException
        status = self.call('storage_status')
        self.assertTrue(status['initialized'])
        self.call('storage_policy', revision=status['policy_revision'], policy={'bytes_limit': '9223372036854775807', 'max_parallel':'16'})
        status = self.call('storage_status')
        self.assertEqual(status['policy_values']['bytes_limit'], '9223372036854775807')
        self.assertNotIn('leases', status)
        with self.assertRaisesRegex(ValueError, 'revision conflict'):
            self.call('storage_policy', revision='0', policy={'max_parallel':'4'})
        for value in ('-1', '1.2', '9223372036854775808', True, '١٢', '1e3'):
            with self.assertRaises(ValueError):
                self.call('storage_policy', revision=status['policy_revision'], policy={'files_limit':value})
        with self.assertRaises(ValueError):
            self.call('storage_policy', revision=status['policy_revision'], policy={'max_parallel':'17'})
        task = self.call('gc_begin', dry_run=True)
        status = self.call('storage_status')
        self.assertEqual(status['gc']['code'], task['code'])
        self.assertTrue(status['gc']['dry_run'])
        self.assertNotIn('marks_root', status['gc'])
        self.call('gc_cancel', task=task['code'])
        self.assertEqual(self.call('storage_status')['gc']['state'], 'cancelled')
        artist = self.writer()
        self.assertNotIn('gc', self.client(artist, 'storage_status'))
        with self.assertRaises(SecurityException):
            self.client(artist, 'gc_begin', dry_run=True)

    def test_native_forms_actual_qml_and_controller(self):
        self.check_native_forms()

    def check_native_forms(self, captures=None, url=None):
        from contextlib import nullcontext
        import test_handler_file_workspace_ui as native
        from PySide6.QtCore import QUrl, QCoreApplication, QEvent
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtQml import QQmlEngine, QQmlComponent
        from PySide6.QtQuick import QQuickWindow
        from PySide6.QtTest import QTest
        from thlib.ui.file_workspace import FileWorkspaceController
        from thlib.side.client.tactic_client_lib.file_transfer import FileTransferClient
        app = QGuiApplication.instance() or QGuiApplication([])
        from PySide6.QtGui import QFont
        font=QFont('Segoe UI');font.setPointSizeF(9.25);app.setFont(font)
        translator=native.CatalogTranslator(native.HANDLER/'thlib/ui/translations/ru.json')
        application = native.Application()
        controller = FileWorkspaceController(application)
        engine = QQmlEngine()
        warnings = []
        engine.warnings.connect(lambda rows: warnings.extend(row.toString() for row in rows))
        for name, value in native.qml_icon_bindings(native.HANDLER, engine).items():
            engine.rootContext().setContextProperty(name, value)
        theme_component = QQmlComponent(engine, QUrl.fromLocalFile(str(native.QML / 'Theme.qml')))
        theme = theme_component.createWithInitialProperties({'dark':True})
        component = QQmlComponent(engine, QUrl.fromLocalFile(str(native.QML / 'FileWorkspaceCatalog.qml')))
        view = component.createWithInitialProperties({'theme':theme, 'controller':controller})
        self.assertIsNotNone(view, str(component.errors()))
        window = QQuickWindow()
        view.setParentItem(window.contentItem())
        window.show()
        try:
            with (self.http() if url is None else nullcontext(url)) as url:
                client = FileTransferClient(url, self.token, 'files')
                for source in ('depots','storage'):
                    controller._data = controller._execute(client, controller.data, Path(self.temp.name)/'cache', 'catalog_page', {'source':source}, threading.Event())
                    if source == 'depots' and not captures:
                        controller._data = controller._execute(client, controller.data, Path(self.temp.name)/'cache', 'depot_editor', {'depot':'main'}, threading.Event())
                    elif source == 'depots':
                        controller.set_value('catalog_detail',client.rpc('depot_status',depot='photos'))
                    controller.stateChanged.emit()
                    if captures:
                        for capture in (row for row in captures if row['source']==source):
                            if capture['language']=='ru':app.installTranslator(translator)
                            else:app.removeTranslator(translator)
                            engine.retranslate();theme.setProperty('dark',capture['mode']=='dark')
                            width,height=capture['width'],capture['height']
                            window.resize(width,height);view.setWidth(width);view.setHeight(height);QTest.qWait(100)
                            self.assertLessEqual(view.childrenRect().width(),width+1)
                            window.grabWindow().save(str(Path(__file__).resolve().parent/'artifacts/depot-storage'/('native-'+capture['stem']+'.png')))
                    for dark in (True,False):
                        theme.setProperty('dark',dark)
                        for width in (1280,600,360):
                            window.resize(width,800);view.setWidth(width);view.setHeight(800);QTest.qWait(50)
                            self.assertLessEqual(view.childrenRect().width(),width+1)
                    if source == 'storage':
                        before=self.call('storage_status')['policy_values']['max_parallel']
                        self.assertEqual(controller.data['storage_draft']['policy']['max_parallel'],before)
                        def items(item):
                            yield item
                            for child in item.childItems(): yield from items(child)
                        field=next(item for item in items(view) if item.objectName()=='storagePolicy_max_parallel')
                        self.assertEqual(field.property('text'),before)
                        value='8' if before!='8' else '9'
                        field.setProperty('text',value)
                        from PySide6.QtCore import QMetaObject
                        QMetaObject.invokeMethod(field,'textEdited')
                        self.assertEqual(controller.data['storage_draft']['policy']['max_parallel'],value)
                        self.assertFalse(controller.can_leave())
                        controller._data = controller._execute(client, controller.data, Path(self.temp.name)/'cache','storage_admin',{'operation':'storage_policy'},threading.Event())
                        controller.stateChanged.emit();QTest.qWait(10)
                        self.assertEqual(controller.data['storage_draft']['policy']['max_parallel'],value)
                        self.assertTrue(controller.can_leave())
                self.assertFalse(warnings,warnings)
        finally:
            app.removeTranslator(translator)
            controller.shutdown();window.close()
            for value in (view,controller,theme,component,theme_component,engine,window,application):value.deleteLater()
            QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)

    def test_browser_forms_against_owned_server(self):
        from pyasm.common import Config
        get_value = Config.get_value
        def configured(section, key, *args, **kwargs):
            return 'tactic,files' if (section,key)==('services','enable') else get_value(section,key,*args,**kwargs)
        with patch.object(Config,'get_value',side_effect=configured), self.http() as url:
            result = subprocess.run(['node','frontend/tests/depot-storage-administration.mjs',url,str(Path(__file__).resolve().parent/'artifacts'/'depot-storage')],
                                    cwd=Path(__file__).resolve().parents[1],capture_output=True,text=True,encoding='utf-8',timeout=90)
            self.assertEqual(result.returncode,0,result.stdout+'\n'+result.stderr)
            import json
            captures=json.loads((Path(__file__).resolve().parent/'artifacts/depot-storage/panes.json').read_text(encoding='utf-8'))
            self.check_native_forms(captures,url)
