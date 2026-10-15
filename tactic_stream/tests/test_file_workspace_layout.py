"""Real Qt layout, splitter persistence and native changelist editor input."""
from pathlib import Path
from unittest.mock import patch
from time import monotonic
import threading
import unittest
from test_handler_file_workspace_ui import (
    Application, HANDLER, QML, FileWorkspaceController,
    QGuiApplication, QQmlEngine, QQmlComponent, QUrl, QQuickWindow, QQuickItem,
    QTest, QPointF, Qt, QCoreApplication, QEvent, qml_icon_bindings,
    env_mode, env_inst, env_server, ThreadsPool,
)
from test_file_project import FileProjectFixture
import test_file_transfer as transfers
from thlib.ui.workspace_models.windows import FloatingWindowModel
from thlib.ui.window_appearance import WindowAppearanceController
from PySide6.QtCore import QObject, Signal


class ConfigurationSignals(QObject):
    closeAllowed = Signal()


class FileWorkspaceLayoutTest(FileProjectFixture, unittest.TestCase):
    http = transfers.FileTransferTest.http

    @classmethod
    def setUpClass(cls):
        cls.app = QGuiApplication.instance() or QGuiApplication([])

    def setUp(self):
        FileProjectFixture.setUp(self)
        for target, name, value in ((env_mode, 'current_path', self.temp.name),
                                    (env_inst, 'projects', {}),
                                    (env_server, 'get_user', lambda: 'admin')):
            scope = patch.object(target, name, value)
            scope.start()
            self.addCleanup(scope.stop)
        self.application = Application()
        self.controller = FileWorkspaceController(self.application)
        self.controller._enabled = True
        self.windows = FloatingWindowModel({})
        self.appearance = WindowAppearanceController()
        self.configuration = ConfigurationSignals()
        self.engine = QQmlEngine()
        self.warnings = []
        self.engine.warnings.connect(lambda items: self.warnings.extend(item.toString() for item in items))
        for name, value in qml_icon_bindings(HANDLER, self.engine).items():
            self.engine.rootContext().setContextProperty(name, value)
        for name, value in [('fileWorkspaceController', self.controller),
                            ('windowModel', self.windows),
                            ('configurationController', self.configuration),
                            ('windowAppearanceController', self.appearance)]:
            self.engine.rootContext().setContextProperty(name, value)
        self.components = []
        self.theme = self.create('Theme.qml', {'dark': True})
        self.view = self.create('FileWorkspaceView.qml', {'theme': self.theme, 'controller': self.controller})
        self.window = QQuickWindow()
        self.view.setParentItem(self.window.contentItem())
        self.resize(1280, 800)
        self.window.setColor(self.theme.property('workspace'))
        self.window.show()
        QTest.qWait(30)

    def create(self, filename, values):
        component = QQmlComponent(self.engine, QUrl.fromLocalFile(str(QML / filename)))
        result = component.createWithInitialProperties(values)
        self.assertIsNotNone(result, str(component.errors()))
        self.components.append(component)
        return result

    def resize(self, width, height):
        self.window.resize(width, height)
        self.view.setWidth(width)
        self.view.setHeight(height)
        QTest.qWait(30)

    def find(self, name, root=None):
        root = root or self.view
        def walk(item):
            if item.objectName() == name:
                return item
            for child in item.childItems():
                result = walk(child)
                if result is not None:
                    return result
        result = walk(root)
        self.assertIsNotNone(result, name)
        return result

    def click(self, item, window=None):
        point=item.mapToScene(QPointF(item.width()/2, item.height()/2)).toPoint()
        QTest.mouseMove(window or self.window,point)
        QTest.qWait(20)
        QTest.mouseClick(window or self.window, Qt.LeftButton, Qt.NoModifier, point)
        QTest.qWait(30)

    def tearDown(self):
        self.controller.shutdown()
        self.window.close()
        for value in [self.view, self.controller, self.window, self.theme, *self.components,
                      self.engine, self.windows, self.appearance, self.configuration, self.application]:
            value.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)

    def test_stream_tree_native_editor_and_graph_entry(self):
        self.call('create_stream',code='dev',depot='main',parent='main',title='Development')
        self.call('create_stream',code='feature',depot='main',parent='dev',title='Feature')
        self.call('create_stream',code='release',depot='main',parent='main',stream_type='release')
        state=self.controller._data
        state['tabs'].append({'id':'streams','kind':'catalog','source':'streams','title':'Streams','icon':'source-branch'})
        state.update(active_tab='streams',catalog_source='streams',catalog_rows=self.call('streams')['items'])
        self.controller.stateChanged.emit();QTest.qWait(50)
        self.assertEqual(self.find('streamTreeList').property('count'),1)
        self.click(self.find('streamToggle_main'))
        self.assertEqual(self.find('streamTreeList').property('count'),3)
        self.click(self.find('streamToggle_dev'))
        self.assertEqual(self.find('streamTreeList').property('count'),4)
        pool=ThreadsPool(2);pool.start()
        dialog=self.view.findChild(QObject,'workspaceStreamEditor')
        def wait():
            deadline=monotonic()+5
            while (self.controller.busy or self.controller._read_worker is not None) and monotonic()<deadline:
                QTest.qWait(10);threading.Event().wait(.01)
            QTest.qWait(40)
            self.assertFalse(dialog.property('loading'));self.assertFalse(dialog.property('saving'))
            self.assertEqual(dialog.property('notice'),'')
        from thlib.ui.localization import CatalogTranslator
        translator=CatalogTranslator(HANDLER/'thlib/ui/translations/ru.json')
        try:
            with self.http() as url,patch.object(env_inst,'server_pool',pool),patch.object(env_inst,'commit_pool',pool),patch.object(env_inst,'local_pool',pool),patch.object(env_server,'get_server',return_value=url),patch.object(env_server,'get_ticket',return_value=self.token),patch.object(env_server,'get_proxy',return_value={'enabled':False}):
                item=self.find('streamRow_feature');point=item.mapToScene(QPointF(130,17)).toPoint()
                QTest.mouseDClick(self.window,Qt.LeftButton,Qt.NoModifier,point);wait()
                self.assertTrue(dialog.property('opened'))
                self.assertTrue(dialog.property('modal'));self.assertTrue(dialog.property('draggable'))
                self.assertEqual(dialog.findChild(QQuickItem,'streamEditorCode').property('text'),'feature')
                name=dialog.findChild(QQuickItem,'streamEditorName');name.setProperty('text','Updated feature')
                dialog.findChild(QQuickItem,'streamEditorDescription').setProperty('text','Edited through Handler')
                dialog.findChild(QQuickItem,'streamEditorParent').setProperty('text','main')
                output=Path(__file__).resolve().parents[1]/'.screenshots/file-workspace';output.mkdir(parents=True,exist_ok=True)
                for language in ('en','ru'):
                    if language=='ru':self.app.installTranslator(translator);self.engine.retranslate()
                    for dark in (True,False):
                        self.theme.setProperty('dark',dark)
                        for width in (700,1280):
                            self.resize(width,800);QTest.qWait(60)
                            self.assertGreaterEqual(dialog.property('x'),0)
                            self.assertLessEqual(dialog.property('x')+dialog.property('width'),width)
                            self.window.grabWindow().save(str(output/f'handler-stream-editor-{language}-{dark}-{width}.png'))
                self.click(dialog.findChild(QQuickItem,'streamEditorSave'));wait()
                self.assertFalse(dialog.property('opened'))
                saved=self.call('stream_status',stream='feature')
                self.assertEqual(saved['parent'],'main');self.assertEqual(saved['branch_parent'],'dev')
                self.assertEqual(saved['description'],'Edited through Handler')
                self.click(self.find('streamNewButton'));wait()
                dialog.findChild(QQuickItem,'streamEditorCode').setProperty('text','new-mainline')
                dialog.findChild(QQuickItem,'streamEditorName').setProperty('text','New mainline')
                self.click(dialog.findChild(QQuickItem,'streamEditorSave'));wait()
                self.assertEqual(self.call('stream_status',stream='new-mainline')['stream_type'],'mainline')
                self.controller.open_view('stream_graph');wait()
                graph=self.find('streamGraphNode_feature');point=graph.mapToScene(QPointF(60,25)).toPoint()
                QTest.mouseDClick(self.window,Qt.LeftButton,Qt.NoModifier,point);wait()
                self.assertTrue(dialog.property('opened'))
                self.assertEqual(dialog.findChild(QQuickItem,'streamEditorName').property('text'),'Updated feature')
                dialog.close()
                self.window.grabWindow().save(str(output/'handler-stream-graph.png'))
            self.assertFalse(self.warnings,self.warnings)
        finally:
            self.app.removeTranslator(translator);self.engine.retranslate();self.controller.shutdown();pool.exit()

    def test_checkout_target_is_centered_modal_movable_and_uses_shared_actions(self):
        from thlib.ui.localization import CatalogTranslator
        dialog=self.view.findChild(QObject,'workspaceTargetDialog')
        dialog.setProperty('operation','checkout');dialog.setProperty('creating',True)
        translator=CatalogTranslator(HANDLER/'thlib/ui/translations/ru.json')
        output=Path(__file__).resolve().parents[1]/'.screenshots/file-workspace';output.mkdir(parents=True,exist_ok=True)
        try:
            for language in ('en','ru'):
                if language=='ru':self.app.installTranslator(translator);self.engine.retranslate()
                for width in (360,900):
                    self.resize(width,640)
                    dialog.open();QTest.qWait(100)
                    self.assertTrue(dialog.property('modal'))
                    self.assertAlmostEqual(dialog.property('x')+dialog.property('width')/2,width/2,delta=1)
                    self.assertAlmostEqual(dialog.property('y')+dialog.property('height')/2,320,delta=1)
                    button=self.find('workspaceTargetAccept',self.window.contentItem())
                    self.assertEqual(button.property('text'),self.controller.tr('Checkout'))
                    self.assertGreaterEqual(button.mapToScene(QPointF()).x(),0)
                    self.assertLessEqual(button.mapToScene(QPointF(button.width(),button.height())).x(),width)
                    if width==900:
                        original=dialog.property('x')
                        header=dialog.property('header')
                        start=header.mapToScene(QPointF(100,25)).toPoint()
                        QTest.mousePress(self.window,Qt.LeftButton,Qt.NoModifier,start)
                        for distance in (20,40,80):QTest.mouseMove(self.window,start+QPointF(distance,20).toPoint(),20)
                        QTest.mouseRelease(self.window,Qt.LeftButton,Qt.NoModifier,start+QPointF(80,20).toPoint())
                        self.assertGreater(dialog.property('x'),original+10)
                        self.assertLessEqual(dialog.property('x')+dialog.property('width'),width)
                    self.window.grabWindow().save(str(output/f'handler-checkout-modal-{language}-{width}.png'))
                    QTest.keyClick(self.window,Qt.Key_Escape);QTest.qWait(30)
                    self.assertFalse(dialog.property('opened'))
            self.assertFalse(self.warnings,self.warnings)
        finally:
            self.app.removeTranslator(translator);self.engine.retranslate()

    def test_outside_workspace_drop_notice_has_only_ok_and_fits_localized_popup(self):
        from thlib.ui.file_workspace_files import WORKSPACE_DROP_MESSAGE
        from thlib.ui.localization import CatalogTranslator
        from PySide6.QtTest import QSignalSpy
        dialog=self.view.findChild(QObject,'workspaceDropBlocked')
        accepted=QSignalSpy(dialog.accepted)
        translator=CatalogTranslator(HANDLER/'thlib/ui/translations/ru.json')
        output=Path(__file__).resolve().parents[1]/'.screenshots/file-workspace'
        output.mkdir(parents=True,exist_ok=True)
        count=0
        try:
            for language in ('en','ru'):
                if language=='ru':self.app.installTranslator(translator);self.engine.retranslate()
                for dark in (True,False):
                    self.theme.setProperty('dark',dark)
                    for width in (360,760):
                        self.resize(width,480)
                        self.controller.dropRejected.emit(self.controller.tr(WORKSPACE_DROP_MESSAGE))
                        QTest.qWait(int(self.theme.property('motionMedium'))+30)
                        self.assertTrue(dialog.property('opened'))
                        ok=self.find('workspaceDropBlockedOk',self.window.contentItem())
                        self.assertEqual(ok.property('text'),'ОК' if language=='ru' else 'OK');self.assertTrue(ok.hasActiveFocus())
                        content=dialog.property('contentItem');surface=content.parentItem()
                        self.assertLessEqual(content.property('contentHeight'),content.height()+1)
                        self.assertGreaterEqual(ok.mapToItem(surface,QPointF()).x(),0)
                        self.assertLessEqual(ok.mapToItem(surface,QPointF(ok.width(),ok.height())).x(),surface.width()+1)
                        if language=='ru':self.assertIn('Перетаскивать',content.property('text'))
                        self.window.grabWindow().save(str(output/f'handler-drop-blocked-{language}-{dark}-{width}.png'))
                        self.click(ok);count+=1
                        self.assertFalse(dialog.property('opened'));self.assertEqual(accepted.count(),count)
        finally:
            self.app.removeTranslator(translator);self.engine.retranslate()
        self.assertEqual(self.controller.log_model.count(),0)
        self.assertFalse(self.warnings,self.warnings)

    def test_submit_dialog_file_selection_settings_tasks_and_local_only_save(self):
        from thlib.side.client.tactic_client_lib.file_transfer import FileTransferClient
        from thlib.ui.localization import CatalogTranslator
        change=self.call('create_change',workspace='work')
        blob=self.upload(change['code'], b'reviewed bytes')
        self.call('edit',change=change['code'],edit_revision=0,chunk='files',operations=[{'path':path,'blob':blob} for path in ('a.txt','b.txt')])
        self.call('shelve',change=change['code'],edit_revision=1,request_id='shelf')
        self.api.dispatch('insert', ({'ticket':self.token,'project':'files'},'sthpw/task',{
            'project_code':'files','search_type':'sthpw/project','search_code':'files','process':'publish','description':'Publish reviewed files'}))
        local=Path(self.temp.name)/'workspace';local.mkdir()
        for name in ('a.txt','b.txt'):(local/name).write_bytes(b'reviewed bytes')
        state=self.controller._data
        state.update(change=self.call('status',change=change['code']),workspace='work',stream='main',root=str(local))
        cache=Path(self.temp.name)/'review-cache'
        with self.http() as url:
            client=FileTransferClient(url,self.token,'files')
            FileWorkspaceController._execute(client,state,cache,'review_change',{'operation':'submit'},threading.Event())
            self.assertEqual(len(state['submit_review']['shelf_files']['items']),2)
            self.controller.stateChanged.emit();QTest.qWait(30)
            dialog=self.view.findChild(QObject,'workspaceSubmitDialog')
            translator=CatalogTranslator(HANDLER/'thlib/ui/translations/ru.json')
            output=Path(__file__).resolve().parents[1]/'.screenshots/file-workspace';output.mkdir(parents=True,exist_ok=True)
            with patch.object(self.controller,'action') as action:
                try:
                    for language in ('en','ru'):
                        if language=='ru':self.app.installTranslator(translator);self.engine.retranslate()
                        for width,height in ((1100,1050),(360,640)):
                            self.resize(width,height);dialog.open();QTest.qWait(100)
                            self.assertTrue(dialog.property('modal'))
                            self.assertEqual(len(dialog.property('review')['items']),2)
                            for name in ('submitCancel','submitSave','submitApply','submitAccept'):
                                button=self.find(name,self.window.contentItem())
                                self.assertGreaterEqual(button.mapToScene(QPointF()).x(),0)
                                end=button.mapToScene(QPointF(button.width(),button.height()))
                                self.assertLessEqual(end.x(),width);self.assertLessEqual(end.y(),height)
                            self.window.grabWindow().save(str(output/f'handler-submit-{language}-{width}.png'))
                            self.click(self.find('submitCancel',self.window.contentItem()));action.assert_not_called()
                    self.resize(1100,1050);dialog.open();QTest.qWait(100)
                    self.click(self.find('submitFileSelect:b.txt',self.window.contentItem()))
                    self.assertEqual(dialog.property('exceptions').toVariant(),['b.txt'])
                    dialog.setProperty('draft','Reviewed description')
                    self.find('submitRestricted',self.window.contentItem()).setProperty('checked',True)
                    task=state['submit_review']['tasks']['items'][0]
                    body=self.find('submitBody',self.window.contentItem())
                    body.setProperty('contentY',max(0,body.property('contentHeight')-body.height()))
                    QTest.qWait(30)
                    self.click(self.find('submitTaskSelect:'+task['code'],self.window.contentItem()))
                    selected=dialog.property('selectedTasks')
                    self.assertEqual((selected.toVariant() if hasattr(selected,'toVariant') else selected)[0]['code'],task['code'])
                    target=next(row['value'] for row in task['statuses'] if row['value']!=task['status'])
                    dialog.setProperty('taskStatus',target)
                    self.window.grabWindow().save(str(output/'handler-submit-tasks.png'))
                    self.click(self.find('submitApply',self.window.contentItem()))
                    operation,values=action.call_args.args
                    self.assertEqual(operation,'submit_save')
                    FileWorkspaceController._execute(client,state,cache,operation,dict(values),threading.Event())
                    self.controller.stateChanged.emit();QTest.qWait(50)
                    self.assertEqual(client.rpc('status',change=change['code'])['description'],'Reviewed description')
                    self.assertEqual(client.rpc('transfer_tasks')['items'],[])
                    self.assertTrue(dialog.property('opened'))
                    self.click(self.find('submitSave',self.window.contentItem()))
                    operation,values=action.call_args.args
                    FileWorkspaceController._execute(client,state,cache,operation,dict(values),threading.Event())
                    self.controller.stateChanged.emit();QTest.qWait(50)
                    self.assertFalse(dialog.property('opened'))
                    FileWorkspaceController._execute(client,state,cache,'review_change',{'operation':'submit'},threading.Event())
                    self.controller.stateChanged.emit();QTest.qWait(30)
                    dialog.open();QTest.qWait(50)
                    selected=dialog.property('selectedTasks')
                    self.assertEqual((selected.toVariant() if hasattr(selected,'toVariant') else selected)[0]['code'],task['code'])
                    self.assertEqual(dialog.property('taskStatus'),target)
                    dialog.setProperty('exceptions',['b.txt'])
                    action.reset_mock()
                    self.click(self.find('submitAccept',self.window.contentItem()))
                    operation,values=action.call_args.args
                    self.assertEqual(operation,'submit')
                    self.assertEqual(values['submit_options']['selection_paths'],['b.txt'])
                    self.assertEqual(values['task_status_updates'][0]['status'],target)
                    FileWorkspaceController._execute(client,state,cache,operation,dict(values),threading.Event())
                    self.assertEqual([row['path'] for row in client.rpc('list',stream='main')['items']],['a.txt'])
                    self.assertEqual(client.rpc('submit_task_status',change=change['code'])['updated'],0)
                    self.assertEqual((local/'b.txt').read_bytes(),b'reviewed bytes')
                finally:
                    self.app.removeTranslator(translator);self.engine.retranslate()
            self.assertFalse(self.warnings,self.warnings)

    def test_revert_options_for_file_group_and_change_default_to_keep_local_files(self):
        from thlib.ui.localization import CatalogTranslator
        change=self.call('create_change',workspace='work')
        self.controller._data.update(change=change,changes=[change],workspace='work',stream='main',root=self.temp.name,
            selection_scope='changes',selection_ids=['one'],selection_records={'one':{
                'path':'new.txt','parent':change['code'],'stream':'main','kind':'file','change_state':'pending','owner':'admin','workspace':'work'}})
        self.controller.stateChanged.emit()
        menu=self.view.findChild(QObject,'workspaceActionMenu')
        dialog=self.view.findChild(QObject,'workspaceRevertDialog')
        translator=CatalogTranslator(HANDLER/'thlib/ui/translations/ru.json')
        output=Path(__file__).resolve().parents[1]/'.screenshots/file-workspace';output.mkdir(exist_ok=True,parents=True)
        try:
            with patch.object(self.controller,'action') as action:
                for language in ('en','ru'):
                    if language=='ru':self.app.installTranslator(translator);self.engine.retranslate()
                    for dark in (True,False):
                        self.theme.setProperty('dark',dark)
                        for width in (360,760):
                            self.resize(width,600)
                            for command in ('revert','revert_files'):
                                menu.triggered.emit(command);QTest.qWait(50)
                                checkbox=self.find('workspaceRevertDeleteNew',self.window.contentItem())
                                self.assertFalse(checkbox.property('checked'))
                                self.click(checkbox);self.assertTrue(checkbox.property('checked'))
                                confirm=self.find('workspaceRevertAccept',self.window.contentItem())
                                content=dialog.property('contentItem');surface=content.parentItem()
                                self.assertGreaterEqual(confirm.mapToItem(surface,QPointF()).x(),0)
                                self.assertLessEqual(confirm.mapToItem(surface,QPointF(confirm.width(),confirm.height())).x(),surface.width()+1)
                                self.assertLessEqual(confirm.mapToScene(QPointF(confirm.width(),confirm.height())).y(),600)
                                self.window.grabWindow().save(str(output/f'handler-revert-{command}-{language}-{dark}-{width}.png'))
                                self.click(self.find('workspaceRevertCancel',self.window.contentItem()))
                                action.assert_not_called()
                menu.triggered.emit('revert_files');QTest.qWait(50)
                self.click(self.find('workspaceRevertDeleteNew',self.window.contentItem()))
                self.click(self.find('workspaceRevertAccept',self.window.contentItem()))
                action.assert_called_once()
                command,options=action.call_args.args
                self.assertEqual(command,'revert_files');self.assertTrue(options['delete_not_in_depot'])
                self.assertEqual(options['files'][0]['path'],'new.txt')
                self.assertFalse(dialog.property('opened'))
        finally:
            self.app.removeTranslator(translator);self.engine.retranslate()
        self.assertFalse(self.warnings,self.warnings)

    def test_confirmation_uses_shared_buttons_wraps_and_dispatches_once(self):
        from thlib.ui.localization import CatalogTranslator
        from PySide6.QtTest import QSignalSpy
        change=self.call('create_change',workspace='work',description='Confirmation test')
        change=self.call('inspect_change',change=change['code'])
        change['opened_files']=0
        self.controller._data.update(change=change,changes=[change],workspace='work',stream='main')
        self.controller.stateChanged.emit()
        menu=self.view.findChild(QObject,'workspaceActionMenu')
        dialog=self.view.findChild(QObject,'workspaceConfirmation')
        self.assertIsNotNone(dialog)
        accepted=QSignalSpy(dialog.accepted)
        translator=CatalogTranslator(HANDLER/'thlib/ui/translations/ru.json')
        output=Path(__file__).resolve().parents[1]/'.screenshots/file-workspace'
        output.mkdir(parents=True,exist_ok=True)
        try:
            with patch.object(self.controller,'action') as action:
                for language in ('en','ru'):
                    if language=='ru':self.app.installTranslator(translator);self.engine.retranslate()
                    for dark in (True,False):
                        self.theme.setProperty('dark',dark)
                        for width in (760,360):
                            self.resize(width,480)
                            menu.triggered.emit('remove_files')
                            QTest.qWait(int(self.theme.property('motionMedium'))+30)
                            self.assertTrue(dialog.property('opened'))
                            cancel=self.find('workspaceConfirmationCancel',self.window.contentItem())
                            confirm=self.find('workspaceConfirmationAccept',self.window.contentItem())
                            message=self.find('workspaceConfirmationMessage',self.window.contentItem())
                            self.assertTrue(any(child.property('name')=='delete' for child in confirm.findChildren(QQuickItem)))
                            self.assertTrue(confirm.property('destructive'))
                            if language=='ru':self.assertEqual(confirm.property('text'),'Убрать файлы')
                            self.assertTrue(cancel.hasActiveFocus())
                            for button in (cancel,confirm):
                                self.assertAlmostEqual(button.width(),button.implicitWidth(),delta=1)
                                point=button.mapToScene(QPointF(button.width(),button.height()))
                                self.assertLessEqual(point.x(),width+1);self.assertLessEqual(point.y(),481)
                                surface=message.parentItem()
                                start=button.mapToItem(surface,QPointF())
                                end=button.mapToItem(surface,QPointF(button.width(),button.height()))
                                self.assertGreaterEqual(start.x(),0)
                                self.assertLessEqual(end.x(),surface.width()+1)
                            self.assertLessEqual(message.property('contentHeight'),message.height()+1)
                            self.assertLess(dialog.property('height'),300)
                            self.window.grabWindow().save(str(output/f'handler-confirmation-{language}-{dark}-{width}.png'))
                            self.click(cancel)
                            self.assertFalse(dialog.property('opened'));action.assert_not_called()
                for command in ('mark_delete','delete_local','delete_change','delete_shelf_files','remove_files','query_delete','query_revert'):
                    menu.triggered.emit(command);QTest.qWait(int(self.theme.property('motionMedium'))+30)
                    self.assertTrue(dialog.property('opened'),command)
                    message=self.find('workspaceConfirmationMessage',self.window.contentItem())
                    for name in ('workspaceConfirmationCancel','workspaceConfirmationAccept'):
                        button=self.find(name,self.window.contentItem());surface=message.parentItem()
                        self.assertGreaterEqual(button.mapToItem(surface,QPointF()).x(),0)
                        self.assertLessEqual(button.mapToItem(surface,QPointF(button.width(),button.height())).x(),surface.width()+1)
                    self.click(self.find('workspaceConfirmationCancel',self.window.contentItem()))
                    action.assert_not_called()
                menu.triggered.emit('remove_files');QTest.qWait(50)
                QTest.keyClick(self.window,Qt.Key_Escape);QTest.qWait(30)
                self.assertFalse(dialog.property('opened'));action.assert_not_called()
                menu.triggered.emit('remove_files');QTest.qWait(50)
                self.click(self.find('workspaceConfirmationAccept',self.window.contentItem()))
                self.assertEqual(accepted.count(),1)
                action.assert_called_once_with('remove_files',{})
        finally:
            self.app.removeTranslator(translator);self.engine.retranslate()
        self.assertFalse(self.warnings,self.warnings)

    def test_history_table_selected_revision_details_and_lazy_preview(self):
        from thlib.ui.file_workspace import FileWorkspaceController
        from thlib.ui.localization import CatalogTranslator
        import threading
        first=self.change();blob=self.upload(first,b'first revision')
        self.call('edit',change=first,edit_revision=0,chunk='first',operations=[{'path':'docs/readme.txt','blob':blob}])
        self.call('update_change',change=first,edit_revision=1,request_id='desc1',description='First description')
        self.call('submit',change=first)
        second=self.change();blob=self.upload(second,b'second revision')
        self.call('edit',change=second,edit_revision=0,chunk='second',operations=[{'path':'docs/readme.txt','blob':blob}])
        self.call('update_change',change=second,edit_revision=1,request_id='desc2',description='Second description')
        self.call('submit',change=second)
        rows=self.call('history',stream='main',path='docs/readme.txt')['items']
        self.assertEqual([row['workspace'] for row in rows],['work','work'])
        state=self.controller._data
        state.update(active_tab='history',history=rows,history_path='docs/readme.txt',history_stream='main')
        if not any(tab['id']=='history' for tab in state['tabs']):state['tabs'].append({'id':'history','kind':'history','title':'History'})
        self.controller.stateChanged.emit();QTest.qWait(80)
        history=self.find('fileWorkspaceHistory')
        self.controller.set_value('history_details_height',300)
        state['history_details_height']=150
        self.controller._restore_geometry()
        self.assertEqual(state['history_details_height'],300)
        description=self.find('historyRevisionDescription')
        translator=CatalogTranslator(HANDLER/'thlib/ui/translations/ru.json')
        output=Path(__file__).resolve().parents[1]/'.screenshots/file-workspace';output.mkdir(parents=True,exist_ok=True)
        fixture=self
        class Client:
            def rpc(self,action,**kwargs):return fixture.call(action,**kwargs)
        with patch.object(self.controller,'action') as action:
            self.assertEqual(description.property('text'),'Second description')
            self.click(self.find('historyRevision_1'));QTest.qWait(40)
            self.assertEqual(description.property('text'),'First description');action.assert_not_called()
            revisions=self.find('workspaceHistoryRevisions');revisions.forceActiveFocus()
            QTest.keyClick(self.window,Qt.Key_Up);QTest.qWait(40)
            self.assertEqual(description.property('text'),'Second description')
            self.click(self.find('historyTab_preview'));QTest.qWait(40)
            action.assert_called_once()
            operation,values=action.call_args.args
            self.assertEqual(operation,'history_preview');self.assertEqual(values['published_change'],second)
            result=FileWorkspaceController._execute(Client(),state,Path(self.temp.name)/'cache',operation,values,threading.Event())
            self.controller._data=result;self.controller.stateChanged.emit();QTest.qWait(40)
            self.assertEqual(self.find('historyRevisionPreview').property('text'),'second revision')
            refreshed=FileWorkspaceController._execute(Client(),result,Path(self.temp.name)/'cache','history',
                {'stream':'main','path':'docs/readme.txt'},threading.Event())
            self.assertEqual(refreshed['history_preview']['revision'],rows[0]['code'])
            self.controller._data=refreshed;self.controller.stateChanged.emit();QTest.qWait(30)
            self.assertEqual(self.find('historyRevisionPreview').property('text'),'second revision')
            action.reset_mock()
            history.setProperty('visible',False)
            history.setProperty('revision',rows[1]);QTest.qWait(30)
            action.assert_not_called()
            history.setProperty('visible',True);QTest.qWait(30)
            action.reset_mock()
            history.setProperty('revision',rows[0]);QTest.qWait(30)
            action.reset_mock()
            self.click(self.find('historyRevision_1'));QTest.qWait(40)
            action.assert_called_once();self.assertEqual(self.find('historyRevisionPreview').property('text'),'')
            self.click(self.find('historyTab_details'));QTest.qWait(40)
            try:
                for language in ('en','ru'):
                    if language=='ru':self.app.installTranslator(translator);self.engine.retranslate()
                    for dark in (True,False):
                        self.theme.setProperty('dark',dark)
                        for width in (700,1600):
                            self.resize(width,1000);QTest.qWait(100)
                            self.assertGreater(revisions.height(),100)
                            self.assertGreater(self.find('historyRevisionInspector').height(),90)
                            self.window.grabWindow().save(str(output/f'handler-history-{language}-{dark}-{width}.png'))
            finally:
                self.app.removeTranslator(translator);self.engine.retranslate()
            state.update(history=[],history_path='another.txt')
            self.controller.stateChanged.emit();QTest.qWait(40)
            self.assertEqual(description.property('text'),'')
        self.assertFalse(self.warnings,self.warnings)

    def test_changelist_menu_reverts_unchanged_without_confirmation(self):
        from thlib.ui.localization import CatalogTranslator
        change=self.call('create_change',workspace='work')
        state=self.controller._data
        state.update(change=change,workspace='work',stream='main',selection_scope='changes',
            selection_ids=[change['code']],selection_records={change['code']:change})
        self.controller.stateChanged.emit();QTest.qWait(30)
        menu=self.view.findChild(QObject,'workspaceActionMenu')
        translator=CatalogTranslator(HANDLER/'thlib/ui/translations/ru.json')
        output=Path(__file__).resolve().parents[1]/'.screenshots/file-workspace';output.mkdir(parents=True,exist_ok=True)
        def descendants(item):
            for child in item.childItems():
                yield child
                yield from descendants(child)
        try:
            with patch.object(self.controller,'action') as action:
                for language in ('en','ru'):
                    if language=='ru':self.app.installTranslator(translator);self.engine.retranslate()
                    self.resize(900,720)
                    self.click(self.find('changelistActionsButton'));QTest.qWait(250)
                    entry=next(row for row in menu.property('actions').toVariant() if row.get('command')=='revert_unchanged_change')
                    self.assertTrue(entry['enabled'],entry)
                    button=next(item for item in descendants(menu.property('contentItem'))
                        if item.objectName()=='actionMenuPrimaryTarget' and item.parentItem().property('modelData').toVariant().get('command')=='revert_unchanged_change')
                    button.window().grabWindow().save(str(output/f'handler-revert-unchanged-{language}.png'))
                    self.click(button,button.window());QTest.qWait(250)
                    action.assert_called_once_with('revert_unchanged_change',{})
                    self.assertFalse(self.view.findChild(QObject,'workspaceConfirmation').property('opened'))
                    action.reset_mock()
                state['change']={**change,'state':'submitted'}
                self.controller.stateChanged.emit();QTest.qWait(30)
                self.click(self.find('changelistActionsButton'));QTest.qWait(250)
                entry=next(row for row in menu.property('actions').toVariant() if row.get('command')=='revert_unchanged_change')
                self.assertFalse(entry['enabled'])
                menu.close()
        finally:
            self.app.removeTranslator(translator);self.engine.retranslate()
        self.assertFalse(self.warnings,self.warnings)

    def test_multiple_empty_changelists_can_be_deleted_from_real_menu(self):
        from thlib.ui.file_workspace_files import execute_files
        from thlib.ui.localization import CatalogTranslator
        changes = [self.call('create_change', workspace='work') for _ in range(2)]
        codes = {row['code'] for row in changes}
        changes = [{**row, 'kind': 'change'} for row in self.call('changes', state='pending')['items'] if row['code'] in codes]
        self.assertTrue(all(row['opened_files'] == 0 for row in changes))
        state = self.controller._data
        state.update(change=changes[-1], changes=changes, change_tree=changes, workspace='work', stream='main',
            selection_scope='changes', selection_ids=[row['code'] for row in changes],
            selection_records={row['code']: row for row in changes}, selected=[])
        self.controller.stateChanged.emit(); QTest.qWait(30)
        menu = self.view.findChild(QObject, 'workspaceActionMenu')
        dialog = self.view.findChild(QObject, 'workspaceConfirmation')
        translator = CatalogTranslator(HANDLER/'thlib/ui/translations/ru.json')
        output = Path(__file__).resolve().parents[1]/'.screenshots/file-workspace'
        output.mkdir(parents=True, exist_ok=True)
        with patch.object(self.controller, 'action') as action:
            try:
                for language in ('en', 'ru'):
                    if language == 'ru': self.app.installTranslator(translator); self.engine.retranslate()
                    for width in (360, 900):
                        self.resize(width, 640)
                        self.click(self.find('changelistActionsButton'))
                        QTest.qWait(250)
                        entries = menu.property('actions').toVariant()
                        deletion = next(row for row in entries if row.get('command') == 'delete_change')
                        self.assertTrue(deletion['enabled'], deletion)
                        def descendants(item):
                            for child in item.childItems():
                                yield child
                                yield from descendants(child)
                        button = next(item for item in descendants(menu.property('contentItem'))
                            if item.objectName() == 'actionMenuPrimaryTarget' and item.parentItem().property('modelData').toVariant().get('command') == 'delete_change')
                        self.click(button, button.window()); QTest.qWait(250)
                        self.assertTrue(dialog.property('opened'))
                        message = self.find('workspaceConfirmationMessage', self.window.contentItem())
                        for row in changes: self.assertIn('#'+str(row['number']), message.property('text'))
                        self.assertLessEqual(message.property('contentHeight'), message.height()+1)
                        self.window.grabWindow().save(str(output/f'handler-delete-changes-{language}-{width}.png'))
                        self.click(self.find('workspaceConfirmationCancel', self.window.contentItem()))
                        action.assert_not_called()
                self.find('workspaceChangelistTree').forceActiveFocus()
                QTest.keyClick(self.window, Qt.Key_Delete); QTest.qWait(50)
                self.assertTrue(dialog.property('opened'))
                self.click(self.find('workspaceConfirmationAccept', self.window.contentItem()))
                action.assert_called_once()
                operation, values = action.call_args.args
                self.assertEqual(operation, 'delete_change')
                self.assertEqual(len(values['changes']), 2)
            finally:
                self.app.removeTranslator(translator); self.engine.retranslate()
        local = Path(self.temp.name)/'keep.txt'; local.write_text('keep my local file')
        calls = []
        class Client:
            def rpc(_, action, **kwargs):
                calls.append(action)
                return native.rpc(action, **kwargs)
        from thlib.side.client.tactic_client_lib.file_transfer import FileTransferClient
        with self.http() as url:
            native = FileTransferClient(url, self.token, 'files')
            execute_files(Client(), state, Path(self.temp.name), operation, values, threading.Event())
        self.assertEqual(calls, ['delete_change'])
        self.assertEqual(self.call('changes', state='pending')['items'], [])
        self.assertEqual(local.read_text(), 'keep my local file')
        self.assertEqual(state['selection_records'], {})
        self.assertFalse(self.warnings, self.warnings)

    def test_view_toolbar_aligns_buttons_with_tabs_and_reserves_scroll_gutter(self):
        from thlib.ui.localization import CatalogTranslator
        translator = CatalogTranslator(HANDLER/'thlib/ui/translations/ru.json')
        output = Path(__file__).resolve().parents[1]/'.screenshots/file-workspace'
        output.mkdir(parents=True, exist_ok=True)
        tabs = self.find('workspaceViewTabs')
        views = self.find('workspaceViewsButton')
        try:
            for language in ('en', 'ru'):
                if language == 'ru':
                    self.app.installTranslator(translator)
                    self.engine.retranslate()
                for dark in (True, False):
                    self.theme.setProperty('dark', dark)
                    for width in (700, 1600):
                        self.resize(width, 800)
                        for active in ('files', 'pending'):
                            tab = self.find('workspaceViewTab:'+active)
                            tabs.setProperty('contentX', max(0, tab.x()+tab.width()-tabs.width()))
                            QTest.qWait(190)  # Let the shared duplicate-input guard expire between clicks.
                            with patch.object(self.controller, 'action', side_effect=lambda *args: self.controller.stateChanged.emit()):
                                self.click(tab)
                            self.assertEqual(self.controller.data['active_tab'], active, (language, dark, width))
                            center = tab.mapToScene(QPointF(0, tab.height()/2)).y()
                            for button in (views, self.find('newChangelistButton')):
                                self.assertAlmostEqual(button.mapToScene(QPointF(0, button.height()/2)).y(), center, delta=.5)
                            overflow = tabs.property('contentWidth') > tabs.width()+.5
                            gutter = tabs.height()-tab.height()
                            self.assertEqual(gutter, 12 if overflow else 0)
                            QTest.qWait(250)  # Capture settled shared selection/hover animations.
                            self.window.grabWindow().save(str(output/f'handler-tab-toolbar-{language}-{dark}-{width}-{active}.png'))
            # The actual close target remains separate from tab activation.
            tab = self.find('workspaceViewTab:pending')
            point = tab.mapToScene(QPointF(tab.width()-20, tab.height()/2)).toPoint()
            with patch.object(self.controller, 'action', side_effect=lambda *args: self.controller.stateChanged.emit()):
                QTest.mouseClick(self.window, Qt.LeftButton, Qt.NoModifier, point)
                QTest.qWait(40)
            self.assertNotIn('pending', [row['id'] for row in self.controller.data['tabs']])
            self.assertFalse(self.warnings, self.warnings)
        finally:
            self.app.removeTranslator(translator)
            self.engine.retranslate()

    def test_splitter_hide_restore_geometry_and_primary_pane_at_top(self):
        pane = self.find('fileWorkspaceWorkingPane')
        tabs = self.find('workspaceViewTabs')
        log = self.find('fileWorkspaceLog')
        self.assertLessEqual(pane.mapToScene(QPointF()).y(), 9)
        self.assertLessEqual(tabs.mapToScene(QPointF()).y(), 12)
        views = self.find('workspaceViewsButton')
        menu = self.view.findChild(QObject, 'workspaceActionMenu')
        for width in (360, 1280):
            self.resize(width, 800)
            self.assertTrue(views.property('round'))
            self.assertEqual(views.property('iconName'), 'view-column')
            self.assertEqual(views.property('toolTip'), 'View')
            self.assertAlmostEqual(views.width(), views.height(), delta=1)
            self.click(views); QTest.qWait(250)
            self.assertTrue(menu.property('opened'))
            self.assertTrue(any(row.get('title') == 'Files' for row in menu.property('actions').toVariant()))
            QTest.keyClick(self.window, Qt.Key_Escape); QTest.qWait(250)
            output = Path(__file__).resolve().parents[1]/'.screenshots/file-workspace'
            output.mkdir(parents=True, exist_ok=True)
            self.window.grabWindow().save(str(output/f'handler-round-view-{width}.png'))
        self.assertNotIn('0 files', self.find('fileWorkspaceStatus').property('text'))
        main = self.find('fileWorkspaceMainSplit')
        old_height = main.height()
        point = QPointF(640, log.mapToScene(QPointF()).y()-5).toPoint()
        QTest.mousePress(self.window, Qt.LeftButton, Qt.NoModifier, point)
        QTest.mouseMove(self.window, point-QPointF(0, 90).toPoint(), 80)
        QTest.mouseRelease(self.window, Qt.LeftButton, Qt.NoModifier, point-QPointF(0, 90).toPoint())
        QTest.qWait(40)
        self.assertGreater(log.height(), 210)
        self.assertAlmostEqual(self.controller.data['log_height'], log.height(), delta=1)
        saved_height = log.height()
        self.click(self.find('fileWorkspaceHideLog'))
        self.assertFalse(log.isVisible())
        self.assertGreater(main.height(), old_height+130)
        self.click(self.find('fileWorkspaceToggleLog'))
        self.assertTrue(log.isVisible())
        self.assertAlmostEqual(log.height(), saved_height, delta=1)
        QTest.qWait(190)  # Shared control's duplicate-input window has elapsed.
        self.click(self.find('fileWorkspaceHideLog'))
        from thlib import tactic_classes as tc
        with patch.object(env_inst, 'projects', {'files': tc.Project({'code':'files','type':'file_project'})}):
            restored = FileWorkspaceController(self.application)
        try:
            self.assertFalse(restored.data['log_visible'])
            self.assertAlmostEqual(restored.data['log_height'], saved_height, delta=1)
        finally:
            restored.shutdown()
            restored.deleteLater()
        # Reopen from the actual View menu, without issuing a file request.
        self.click(self.find('workspaceViewsButton'))
        menu = self.view.findChild(QObject, 'workspaceActionMenu')
        self.assertTrue(any(row.get('command')=='toggle_log' for row in menu.property('actions').toVariant()))
        menu.close()
        self.controller.set_value('log_visible', True)
        for dark in (False, True):
            self.theme.setProperty('dark', dark)
            for width, height in ((760,600), (360,480), (1280,800)):
                self.resize(width, height)
                footer = self.find('fileWorkspaceFooter')
                self.assertLessEqual(footer.mapToScene(QPointF(footer.width(),footer.height())).y(), height+1)
                self.assertGreater(main.height(), 200)
                self.assertLessEqual(self.view.childrenRect().width(), width+1)
        output = Path(__file__).resolve().parents[1]/'.screenshots/file-workspace'
        output.mkdir(parents=True, exist_ok=True)
        self.window.grabWindow().save(str(output/'handler-layout-log-splitter.png'))
        self.assertFalse(self.warnings, self.warnings)

    def test_double_click_native_details_saves_description_via_api(self):
        change = self.call('create_change', workspace='work', description='Original description')
        blob = self.upload(change['code'], b'view contents')
        self.call('edit', change=change['code'], edit_revision=0, chunk='view', operations=[
            {'path': path, 'blob': blob} for path in ('shots/a.txt', 'docs/b.txt')])
        self.call('shelve', change=change['code'], edit_revision=1, request_id='shelf')
        task = self.api.dispatch('insert', ({'ticket':self.token,'project':'files'},'sthpw/task',{
            'project_code':'files','search_type':'sthpw/project','search_code':'files','process':'publish','description':'Review these files'}))
        change = self.call('update_change', change=change['code'], edit_revision=1, request_id='link', task_codes=[task['code']])
        self.controller._data.update(change=change, changes=[change], description=change['description'],
                                     workspace='work', stream='main', workspaces=[{'code':'work'}])
        self.controller._tree(self.controller._data)
        self.controller.stateChanged.emit()
        QTest.qWait(30)
        row = self.find('workspaceTreeRow:'+change['code'])
        point = row.mapToScene(QPointF(200,row.height()/2)).toPoint()
        with patch.object(self.application, 'open_window', side_effect=self.windows.show_window) as opened:
            QTest.mouseClick(self.window, Qt.LeftButton, Qt.NoModifier, point)
            QTest.qWait(30)
            opened.assert_not_called()
            QTest.mouseDClick(self.window, Qt.LeftButton, Qt.NoModifier, point)
            QTest.qWait(50)
            opened.assert_called_once_with('file_changelist')
            opened.reset_mock()
            row.forceActiveFocus()
            QTest.keyClick(self.window, Qt.Key_Return)
            opened.assert_called_once_with('file_changelist')
        self.assertEqual(self.controller.data['expanded_changes'], [])
        self.assertEqual(self.controller.log_model.count(), 0)
        index = self.windows.index(self.windows._row('file_changelist'), 0)
        properties = {role.decode(): self.windows.data(index,key) for key,role in self.windows.roleNames().items()}
        properties.update(theme=self.theme, ownerWindow=self.window, workspaceEnabled=True)
        with patch.object(self.controller, 'action') as action:
            details = self.create('shell/windows/FloatingWindow.qml', properties)
            QTest.qWait(60)
            initial_action = action.call_args.args
        try:
            QTest.qWait(60)
            self.assertTrue(details.isVisible())
            content = details.findChild(QQuickItem, 'fileWorkspaceChangelistDetails')
            self.assertIsNotNone(content, self.warnings)
            self.assertEqual(content.property('changeCode'), change['code'])
            editor = content.findChild(QQuickItem, 'fileWorkspaceChangelistDescription')
            self.assertEqual(editor.property('text'), 'Original description')
            self.assertLess(editor.mapToScene(QPointF()).y(), 250)
            self.assertTrue(editor.property('readOnly'))
            pool = ThreadsPool(1)
            pool.start()
            try:
                with self.http() as url, patch.object(env_inst,'commit_pool',pool), patch.object(env_inst,'server_pool',pool), patch.object(env_server,'get_server',return_value=url), patch.object(env_server,'get_ticket',return_value=self.token), patch.object(env_server,'get_proxy',return_value={'enabled':False}):
                    self.controller.action(*initial_action)
                    deadline=monotonic()+5
                    while self.controller._read_worker is not None and monotonic()<deadline:
                        QTest.qWait(10); threading.Event().wait(.01)
                    self.assertFalse(content.property('loading'))
                    self.assertFalse(self.controller.data['change_details'].get('error'),self.controller.data['change_details'])
                    self.assertEqual(len(self.controller.data['change_details']['files']['items']),2)
                    self.assertEqual(len(self.controller.data['change_details']['shelf_files']['items']),2)
                    self.assertEqual(self.controller.data['change_details']['tasks']['items'][0]['code'],task['code'])
                    self.click(content.findChild(QQuickItem,'fileWorkspaceDetailsEdit'), details)
                    self.assertFalse(editor.property('readOnly'))
                    editor.forceActiveFocus()
                    QTest.keyClick(details, Qt.Key_A, Qt.ControlModifier)
                    for char in 'saved description':
                        QTest.keyClick(details, Qt.Key(ord(char.upper())), Qt.ShiftModifier if char.isupper() else Qt.NoModifier)
                    self.click(content.findChild(QQuickItem,'fileWorkspaceDetailsSave'), details)
                    deadline=monotonic()+5
                    while self.controller.busy and monotonic()<deadline:
                        QTest.qWait(10)
                        threading.Event().wait(.01)
                    self.assertFalse(self.controller.busy)
                    self.assertEqual(self.controller.data['error'], '')
                    self.assertEqual(self.call('status',change=change['code'])['description'],'saved description')
                    self.assertFalse(content.property('dirty'))
                    self.click(content.findChild(QQuickItem,'fileWorkspaceDetailsActions'), details)
                    from PySide6.QtCore import QObject
                    menu=content.findChild(QObject,'fileWorkspaceDetailsMenu')
                    deadline=monotonic()+1
                    while not menu.property('opened') and monotonic()<deadline:
                        QTest.qWait(10)
                    self.assertTrue(menu.property('opened'))
                    self.assertIn('shelve',[row['command'] for row in menu.property('actions').toVariant()])
                    menu.close()
                    output=Path(__file__).resolve().parents[1]/'.screenshots/file-workspace'
                    output.mkdir(parents=True,exist_ok=True)
                    details.grabWindow().save(str(output/'handler-changelist-details.png'))
                    from thlib.ui.localization import CatalogTranslator
                    translator=CatalogTranslator(HANDLER/'thlib/ui/translations/ru.json')
                    try:
                        for language in ('en','ru'):
                            if language=='ru':
                                self.app.installTranslator(translator)
                                self.engine.retranslate()
                            for dark in (True,False):
                                self.theme.setProperty('dark',dark)
                                QTest.qWait(int(self.theme.property('motionMedium'))+20)
                                for width in (520,1000):
                                    details.resize(width,1080 if width==1000 else 620)
                                    QTest.qWait(30)
                                    self.assertLess(editor.mapToScene(QPointF()).y(),250)
                                    close=content.findChild(QQuickItem,'fileWorkspaceDetailsClose')
                                    self.assertLessEqual(close.mapToScene(QPointF(close.width(),close.height())).x(),width)
                                    self.assertEqual(content.property('draft'),'saved description')
                                    details.grabWindow().save(str(output/f'handler-changelist-{language}-{dark}-{width}.png'))
                    finally:
                        self.app.removeTranslator(translator)
                        self.engine.retranslate()
                    self.controller._data['change']={**self.controller.data['change'],'owner':'another-user'}
                    self.controller.stateChanged.emit()
                    self.assertFalse(content.property('editable'))
                    self.controller._data['change']={'code':'another-change'}
                    self.controller.stateChanged.emit()
                    self.assertEqual(content.property('changeCode'),change['code'])
                    self.assertFalse(content.property('sameChange'))
            finally:
                pool.exit()
                pool.deleteLater()
            self.assertFalse(self.warnings, self.warnings)
        finally:
            self.windows.close_window('file_changelist')
            details.deleteLater()

    def test_tools_file_state_menu_keeps_hidden_filter_accessible(self):
        def descendants(item):
            for child in item.childItems():
                yield child
                yield from descendants(child)
        tools=next(item for item in descendants(self.view) if item.property('text')=='Tools')
        self.click(tools)
        menu=self.view.findChild(QObject,'workspaceActionMenu')
        def choose(active, title):
            deadline=monotonic()+1
            while not active.property('opened') and monotonic()<deadline:
                QTest.qWait(10)
            self.assertTrue(active.property('opened'), active.property('actions').toVariant())
            QTest.qWait(250)  # Let the shared native popup finish its input guard.
            target=next(item for item in descendants(active.property('contentItem'))
                        if item.objectName()=='actionMenuPrimaryTarget'
                        and item.parentItem().property('modelData').toVariant().get('title')==title)
            self.assertTrue(target.isEnabled(),title)
            self.click(target,target.window())
        def submenu(parent):
            deadline=monotonic()+1
            result=parent.property('activeSubmenu')
            while not result and monotonic()<deadline:
                QTest.qWait(10)
                result=parent.property('activeSubmenu')
            if hasattr(result,'toQObject'):result=result.toQObject()
            self.assertIsNotNone(result)
            return result
        choose(menu, 'File state')
        filters=submenu(menu)
        choose(filters, 'Modified')
        deadline=monotonic()+1
        while self.controller.data['status_filter']!='Modified' and monotonic()<deadline:
            QTest.qWait(10)
        self.assertEqual(self.controller.data['status_filter'],'Modified')
        self.assertIsNone(self.controller._read_worker)
        self.assertFalse(self.controller.busy)
        self.resize(360,600)
        self.assertEqual(self.controller.data['status_filter'],'Modified')
        self.assertFalse(self.warnings,self.warnings)

    def test_hidden_file_inspector_does_not_schedule_background_requests(self):
        self.controller._data.update(active_tab='pending',file_focus={'stream':'main','path':'file.txt'})
        self.controller._queue_inspection()
        self.assertFalse(self.controller._inspection_timer.isActive())
        self.assertIsNone(self.controller._inspection_key)
        self.controller._data['active_tab']='files'
        self.controller._queue_inspection()
        self.assertTrue(self.controller._inspection_timer.isActive())
        self.controller._inspection_timer.stop()
