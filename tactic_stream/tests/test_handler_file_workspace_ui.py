"""Real Handler QML and worker signals against an owned Stream HTTP server."""
import os
import logging
import json
from pathlib import Path
import sys
import threading
from time import monotonic
import unittest
from unittest.mock import patch
from test_file_project import FileProjectFixture
import test_file_transfer as transfers

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_QUICK_BACKEND', 'software')
os.environ.setdefault('QSG_RENDER_LOOP', 'basic')
os.environ.setdefault('QT_QUICK_CONTROLS_STYLE', 'Material')
os.environ.setdefault('QT_QPA_FONTDIR', 'C:/Windows/Fonts')
sys.path.insert(0, 'D:/code/th_codex')

from PySide6.QtCore import QCoreApplication, QEvent, QObject, QPointF, QUrl, Signal, Qt, QMetaObject
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine, qmlClearTypeRegistrations
from PySide6.QtQuick import QQuickItem, QQuickWindow
from PySide6.QtTest import QSignalSpy, QTest
from thlib.ui.file_workspace import FileWorkspaceController, initial_state
from thlib.side.client.tactic_client_lib.file_transfer import FileTransferClient
from thlib.ui.icon_font import qml_icon_bindings
from thlib.ui.localization import CatalogTranslator
from thlib.pool import ThreadsPool
from thlib.environment import env_inst, env_mode, env_server

HANDLER = Path('D:/code/th_codex')
QML = HANDLER / 'thlib/ui/qml'


class DebugRecorder:
    stacktrace = ''

    def log(self, _level, _message, **values):
        self.stacktrace = values.get('stacktrace', '')


class Application(QObject):
    project_changed = Signal(str, str)
    server_state_changed = Signal()
    signing_out = Signal()
    project_state_changed = Signal()
    current_project_code = 'files'

    def __init__(self):
        super().__init__()
        self.errors = []
        self.debug_log = DebugRecorder()

    @property
    def stacktrace(self):
        return self.debug_log.stacktrace

    def _report_error_payload(self, payload, _group):
        self.errors.append(str(payload))

    def open_window(self, _name):
        pass


class HandlerFileWorkspaceUiTest(FileProjectFixture, unittest.TestCase):
    http = transfers.FileTransferTest.http
    client = transfers.FileTransferTest.client
    context = transfers.FileTransferTest.context

    @classmethod
    def setUpClass(cls):
        logging.getLogger().setLevel(logging.WARNING)
        cls.app = QGuiApplication.instance() or QGuiApplication([])
        cls.app.setFont(QFont('Segoe UI', 10))

    @classmethod
    def tearDownClass(cls):
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        qmlClearTypeRegistrations()

    def setUp(self):
        FileProjectFixture.setUp(self)
        scope = patch.object(env_mode, 'current_path', self.temp.name)
        scope.start()
        self.addCleanup(scope.stop)

    def test_expanded_changelist_selects_and_checks_out_a_file_on_the_next_page(self):
        change = self.call('create_change', workspace='work', description='Paged files')
        blob = self.upload(change['code'], b'new paged content')
        self.call('edit', change=change['code'], edit_revision=0, chunk='paged', operations=[
            {'path': f'files/{index:04d}.txt', 'blob': blob} for index in range(201)])
        change = self.call('status', change=change['code'])
        other = self.call('create_change', workspace='work', description='Other change')
        state = initial_state()
        state.update(workspace='work', stream='main', changes=[change, other], change=other)
        fixture = self

        class Client:
            def rpc(self, action, **kwargs):
                return fixture.call(action, **kwargs)

        client = Client()
        cache = Path(self.temp.name) / 'controller-cache'
        cancelled = threading.Event()
        for action in ('toggle_change', 'more_change'):
            FileWorkspaceController._execute(client, state, cache, action, {'change': change['code']}, cancelled)
        self.assertEqual(len(state['change_children'][change['code']]['items']), 201)
        FileWorkspaceController._execute(client, state, cache, 'select_change',
            {'change': change['code'], 'path': 'files/0200.txt', 'selected': True}, cancelled)

        self.assertEqual(state['selected'], ['files/0200.txt'])
        self.assertEqual(len(state['change_children'][change['code']]['items']), 201)
        FileWorkspaceController._execute(client, state, cache, 'checkout', {'mode': 'exclusive'}, cancelled)
        held = self.call('locks', stream='main', paths=['files/0200.txt', 'files/0000.txt'])['items']
        holders = {item['path']: item['holders'][0] for item in held}
        self.assertEqual(holders['files/0200.txt']['mode'], 'exclusive')
        self.assertEqual(holders['files/0200.txt']['change'], change['code'])
        self.assertEqual(holders['files/0000.txt']['mode'], 'ordinary')
        self.call('edit', change=change['code'], edit_revision=state['change']['edit_revision'],
            chunk='concurrent', operations=[{'path': 'files/0000.txt', 'blob': blob}])
        with self.assertRaisesRegex(ValueError, 'Changelist changed'):
            FileWorkspaceController._execute(client, state, cache, 'select_change',
                {'change': change['code'], 'path': 'files/0000.txt', 'selected': True}, cancelled)

    def test_expanding_stale_change_reads_latest_but_more_and_writes_remain_pinned(self):
        change=self.call('create_change',workspace='work')
        blob=self.upload(change['code'],b'folder content')
        self.call('edit',change=change['code'],edit_revision=0,chunk='folder',operations=[
            {'path':f'folder/{index:04d}.txt','blob':blob} for index in range(201)])
        state=initial_state()
        state.update(workspace='work',stream='main',change=change,changes=[change])
        fixture=self
        class Client:
            def rpc(self,action,**kwargs):return fixture.call(action,**kwargs)
        cache=Path(self.temp.name)/'cache'
        FileWorkspaceController._execute(Client(),state,cache,'toggle_change',{'change':change['code']},threading.Event())
        self.assertEqual(state['change']['edit_revision'],1)
        self.assertEqual(state['changes'][0]['opened_files'],201)
        self.assertEqual(len(state['change_children'][change['code']]['items']),200)
        self.call('edit',change=change['code'],edit_revision=1,chunk='concurrent',operations=[{'path':'new.txt','blob':blob}])
        with self.assertRaisesRegex(ValueError,'revision conflict'):
            FileWorkspaceController._execute(Client(),state,cache,'more_change',{'change':change['code']},threading.Event())
        with self.assertRaisesRegex(ValueError,'revision conflict'):
            self.call('checkout',change=change['code'],edit_revision=1,request_id='stale',paths=['folder/0000.txt'])
        FileWorkspaceController._execute(Client(),state,cache,'toggle_change',{'change':change['code']},threading.Event())
        FileWorkspaceController._execute(Client(),state,cache,'toggle_change',{'change':change['code']},threading.Event())
        self.assertEqual(state['change']['edit_revision'],2)

    def test_depot_pointer_does_not_serialize_retained_tabs_or_start_write(self):
        application=Application();controller=FileWorkspaceController(application);controller._enabled=True
        archived=[{'path':f'folder/file{index:05d}.txt','file':{'sha256':'a'*64,'size':1234}} for index in range(8000)]
        controller._data.update(tab_states={'files':{'rows':archived}},change_children={'archived':{'items':archived}},
            depot_tree=[{'id':f'path/main/folder{index}/','kind':'directory','name':f'folder{index}',
                         'stream':'main','directory':f'folder{index}/','depth':0,'expanded':False} for index in range(200)])
        controller.stateChanged.emit()
        pool=ThreadsPool(1);pool.start();engine=QQmlEngine();warnings=[]
        engine.warnings.connect(lambda items:warnings.extend(item.toString() for item in items))
        for name,value in qml_icon_bindings(HANDLER,engine).items():engine.rootContext().setContextProperty(name,value)
        theme_component=QQmlComponent(engine,QUrl.fromLocalFile(str(QML/'Theme.qml')))
        theme=theme_component.createWithInitialProperties({'dark':True})
        component=QQmlComponent(engine,QUrl.fromLocalFile(str(QML/'FileWorkspaceView.qml')))
        view=component.createWithInitialProperties({'theme':theme,'controller':controller})
        self.assertIsNotNone(view,str(component.errors()))
        window=QQuickWindow();view.setParentItem(window.contentItem());window.resize(1280,800);view.setWidth(1280);view.setHeight(800);window.show()
        def find(item,caption):
            if item.property('caption')==caption:return item
            for child in item.childItems():
                value=find(child,caption)
                if value is not None:return value
        elapsed=[]
        try:
            def no_requests(*args,**kwargs):raise AssertionError('Pending selection must not request files')
            def client_factory(*args,**kwargs):return FileTransferClient(*args,rpc=no_requests,**kwargs)
            with patch.object(env_inst,'server_pool',pool),patch.object(env_inst,'commit_pool',pool),patch.object(env_mode,'current_path',self.temp.name),patch.object(env_server,'get_server',return_value='http://127.0.0.1:1'),patch.object(env_server,'get_ticket',return_value='test-only'),patch.object(env_server,'get_user',return_value='admin'),patch('thlib.ui.file_workspace.FileTransferClient',side_effect=client_factory),patch('thlib.side.client.tactic_client_lib.file_transfer.FileTransferClient',side_effect=client_factory):
                QTest.qWait(30)
                for index in range(5):
                    QTest.qWait(30)
                    item=find(view,'folder0');self.assertIsNotNone(item)
                    point=item.mapToScene(QPointF(item.width()/2,item.height()/2)).toPoint()
                    start=monotonic();QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,point);elapsed.append((monotonic()-start)*1000)
                    deadline=monotonic()+5
                    while (controller.busy or controller._read_worker) and monotonic()<deadline:QTest.qWait(10)
                    self.assertEqual(controller.data['tree_selection'],'path/main/folder0/')
                print('DEPOT_POINTER_MS',','.join(f'{value:.2f}' for value in elapsed))
                self.assertFalse(controller.busy)
                self.assertEqual(controller.log_model.count(),0)
                self.assertTrue('tab_states' not in view.property('state'),'Private tab snapshots must not cross the Qt state boundary')
                QTest.keyClick(window,Qt.Key_Down)
                self.assertEqual(controller.data['tree_selection'],'path/main/folder1/')
                blocked=view.findChild(QObject,'workspaceDropBlocked')
                from thlib.ui.file_workspace_files import WORKSPACE_DROP_MESSAGE
                for width in (1280,360):
                    window.resize(width,800);view.setWidth(width);QTest.qWait(20)
                    controller.dropRejected.emit(WORKSPACE_DROP_MESSAGE);QTest.qWait(30)
                    self.assertTrue(blocked.property('opened'))
                    ok=view.findChild(QQuickItem,'workspaceDropBlockedOk')
                    self.assertEqual(ok.property('text'),'OK')
                    self.assertLess(ok.width(),blocked.property('width')/2)
                    directory=Path(__file__).resolve().parents[1]/'.screenshots/file-workspace';directory.mkdir(parents=True,exist_ok=True)
                    window.grabWindow().save(str(directory/f'handler-outside-drop-{width}.png'))
                    blocked.accept();QTest.qWait(20)
                window.resize(1280,800);view.setWidth(1280);QTest.qWait(30)
                controller._data.update(change={'code':'synthetic','number':11,'owner':'admin','workspace':'work','state':'pending','opened_files':2},
                    selection_scope='changes',selection_ids=['one','two'],selected=['a.txt','b.txt'],selection_records={
                        'one':{'path':'a.txt','kind':'file','parent':'synthetic','change_state':'pending','owner':'admin','workspace':'work'},
                        'two':{'path':'b.txt','kind':'file','parent':'foreign','change_state':'pending','owner':'admin','workspace':'work'}})
                controller.stateChanged.emit();QTest.qWait(20)
                menu_button=view.findChild(QQuickItem,'fileActionsButton')
                point=menu_button.mapToScene(QPointF(menu_button.width()/2,menu_button.height()/2)).toPoint()
                QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,point);QTest.qWait(20)
                menu=view.findChild(QObject,'workspaceActionMenu')
                entries=menu.property('actions').toVariant()
                edits=next(group for group in entries if group.get('title')=='Changelist edits')
                move=next(item for item in edits['children'] if item['command']=='move_files')
                self.assertFalse(move['enabled']);self.assertIn('current owned pending',move['status'])
                menu.close();QTest.qWait(250)
                controller._data.update(selection_ids=[],selection_records={},selected=[])
                controller.stateChanged.emit();QTest.qWait(20)
                # Real menu dispatch opens the nonempty-change choice without a mutation.
                menu_button=view.findChild(QQuickItem,'changelistActionsButton')
                point=menu_button.mapToScene(QPointF(menu_button.width()/2,menu_button.height()/2)).toPoint()
                QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,point);QTest.qWait(250)
                self.assertTrue(menu.property('opened'));self.assertTrue(any(item.get('command')=='delete_change' for item in menu.property('actions').toVariant()),menu.property('actions').toVariant())
                def descendants(item):
                    for child in item.childItems():yield child;yield from descendants(child)
                delete=next(item for item in descendants(menu.property('contentItem')) if item.objectName()=='actionMenuPrimaryTarget' and item.parentItem().property('modelData').toVariant().get('command')=='delete_change')
                point=delete.mapToScene(QPointF(delete.width()/2,delete.height()/2)).toPoint()
                QTest.mouseClick(delete.window(),Qt.LeftButton,Qt.NoModifier,point);QTest.qWait(250)
                choice=view.findChild(QObject,'workspaceNonemptyDelete');self.assertTrue(choice.property('opened'))
                for width in (360,1280):
                    window.resize(width,800);view.setWidth(width);QTest.qWait(20)
                    for name in ('workspaceMoveAllFiles','workspaceRevertAllFiles'):
                        button=view.findChild(QQuickItem,name)
                        self.assertGreater(button.width(),0)
                        self.assertGreaterEqual(button.mapToScene(QPointF()).x(),0)
                        self.assertLessEqual(button.mapToScene(QPointF(button.width(),button.height())).x(),width)
                    window.grabWindow().save(str(directory/f'handler-nonempty-change-{width}.png'))
                QTest.keyClick(window,Qt.Key_Escape);QTest.qWait(20)
                self.assertFalse(choice.property('opened'));self.assertFalse(controller.busy)
                self.assertFalse(warnings,warnings)
        finally:
            controller.shutdown();pool.exit();window.close();view.setParentItem(None);view.deleteLater();window.deleteLater();controller.deleteLater();application.deleteLater();theme.deleteLater();engine.deleteLater();pool.deleteLater()
            QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)

    def test_local_workspace_drop_opens_paths_without_any_upload(self):
        root=Path(self.temp.name)/'local';(root/'art/docs/private').mkdir(parents=True)
        (root/'art/docs/new.txt').write_bytes(b'new local file')
        (root/'art/docs/private/skip.txt').write_bytes(b'excluded local file')
        (root/'outside.txt').write_bytes(b'unselected file')
        self.call('create_workspace',code='mapped',stream='main',local_root=root.as_posix(),mappings=[
            {'stream':'main','source':'assets/...','target':'art/...','writable':True},
            {'stream':'main','source':'assets/docs/private/...','target':'art/docs/private/...','exclude':True}])
        change=self.call('create_change',workspace='mapped')
        state=initial_state();state.update(workspace='mapped',stream='main',root=root.as_posix(),changes=[change])
        payload=json.dumps({'project':'files','workspace':'mapped','scope':'workspace','rows':[
            {'kind':'directory','path':'art/docs/','directory':'art/docs/','stream':'main'},
            {'kind':'file','path':'art/docs/new.txt','stream':'main'}]})
        with self.http(worker=True) as url:
            client=FileTransferClient(url,self.token,'files');original=client.rpc;calls=[]
            def rpc(action,**kwargs):calls.append(action);return original(action,**kwargs)
            client.rpc=rpc
            FileWorkspaceController._execute(client,state,Path(self.temp.name)/'cache','drop_files',
                {'target':change['code'],'project':'files','payload':payload},threading.Event())
        self.assertEqual(calls.count('checkout'),1)
        self.assertNotIn('transfer_begin',calls)
        self.assertNotIn('upload_begin',calls)
        self.assertFalse(self.call('transfer_tasks')['items'])
        self.assertEqual(self.call('status',change=change['code'])['state'],'pending')
        self.assertEqual(self.call('list',stream='main')['files'],0,'Adding local files does not submit the changelist')
        self.assertEqual([row['path'] for row in self.call('change_files',change=change['code'])['items']],['assets/docs/new.txt'])
        self.assertIsNone(self.call('change_files',change=change['code'])['items'][0]['file'])
        self.assertEqual(state['change_children'][change['code']]['items'][0]['local_status'],'added')
        self.assertEqual((root/'art/docs/new.txt').read_bytes(),b'new local file')
        self.assertEqual((root/'art/docs/private/skip.txt').read_bytes(),b'excluded local file')

    def test_local_files_view_drop_and_explorer_keep_existing_workspace_path(self):
        root=Path(self.temp.name)/'local';(root/'docs/deep').mkdir(parents=True)
        file=root/'docs/deep/new.txt';file.write_bytes(b'local bytes')
        state=initial_state();state.update(workspace='work',stream='main',root=root.as_posix())
        with self.http(worker=True) as url:
            client=FileTransferClient(url,self.token,'files')
            for origin in ('files','explorer'):
                change=self.call('create_change',workspace='work');state['changes']=[change]
                values={'target':change['code'],'project':'files'}
                if origin=='files':values['payload']=json.dumps({'project':'files','workspace':'work','scope':'files','source':'local',
                    'rows':[{'kind':'file','path':'docs/deep/new.txt','local_path':'docs/deep/new.txt'}]})
                else:values['urls']=[QUrl.fromLocalFile(str(file)).toString()]
                FileWorkspaceController._execute(client,state,Path(self.temp.name)/'cache','drop_files',values,threading.Event())
                self.assertEqual([row['path'] for row in self.call('change_files',change=change['code'])['items']],['docs/deep/new.txt'])
                self.assertIsNone(self.call('change_files',change=change['code'])['items'][0]['file'])
                self.assertFalse(self.call('transfer_tasks')['items'])
        self.assertEqual(file.read_bytes(),b'local bytes');self.assertFalse((root/'new.txt').exists())

    def test_explorer_folder_drop_uses_workspace_mappings_for_all_nested_files(self):
        from thlib.side.client.tactic_client_lib.file_transfer import FileTransferClient
        root=Path(self.temp.name)/'mapped-local'
        self.call('create_workspace',code='mapped',stream='main',local_root=root.as_posix(),
            mappings=[{'stream':'main','source':'assets/...','target':'art/...','writable':True}])
        change=self.call('create_change',workspace='mapped')
        outside=root/'art/outside'
        (outside/'deep').mkdir(parents=True)
        (outside/'one.txt').write_bytes(b'fresh one')
        (outside/'deep/two.txt').write_bytes(b'fresh nested')
        state=initial_state();state.update(workspace='mapped',stream='main',root=root.as_posix(),change=change)
        with self.http(worker=True) as url:
            client=FileTransferClient(url,self.token,'files')
            FileWorkspaceController._execute(client,state,Path(self.temp.name)/'cache','drop_files',
                {'target':change['code'],'urls':[QUrl.fromLocalFile(str(outside)).toString()],'prefix':'art/','project':'files'},threading.Event())
        rows=self.call('change_files',change=change['code'])['items']
        self.assertEqual({row['path'] for row in rows},{'assets/outside/one.txt','assets/outside/deep/two.txt'})
        self.assertEqual((root/'art/outside/deep/two.txt').read_bytes(),b'fresh nested')

    def test_outside_and_mixed_workspace_drops_are_rejected_before_rpc_or_copy(self):
        from copy import deepcopy
        from thlib.ui.file_workspace_files import WORKSPACE_DROP_MESSAGE
        root=Path(self.temp.name)/'workspace';root.mkdir()
        inside=root/'inside.txt';inside.write_bytes(b'kept')
        outside=Path(self.temp.name)/'outside.txt';outside.write_bytes(b'external')
        sibling=Path(self.temp.name)/'workspace-other';sibling.mkdir()
        sibling_file=sibling/'neighbor.txt';sibling_file.write_bytes(b'neighbor')
        change=self.call('create_change',workspace='work')
        state=initial_state();state.update(workspace='work',stream='main',root=str(root),change=change,
            recovery={'available':True},connection_state='offline')
        class Client:
            def rpc(self,*args,**kwargs):raise AssertionError('Rejected drop must not query the server')
            def upload(self,*args,**kwargs):raise AssertionError('Rejected drop must not upload')
        cache=Path(self.temp.name)/'unused-cache'
        for sources in ([outside],[inside,outside],[sibling_file]):
            urls=[QUrl.fromLocalFile(str(path)).toString() for path in sources]
            result=FileWorkspaceController._execute(Client(),deepcopy(state),cache,'drop_files',
                {'target':change['code'],'project':'files','urls':urls},threading.Event())
            self.assertEqual(result['drop_rejected'],WORKSPACE_DROP_MESSAGE)
            self.assertEqual(result['operation_notice']['level'],'WARNING')
            self.assertEqual(result['recovery'],{'available':True})
            self.assertEqual(result['connection_state'],'offline')
        self.assertEqual(list(cache.iterdir()),[])
        self.assertEqual(list(root.iterdir()),[inside]);self.assertEqual(inside.read_bytes(),b'kept')
        self.assertEqual(outside.read_bytes(),b'external')
        self.assertEqual(self.call('change_files',change=change['code'])['items'],[])

    def test_files_inspector_real_selection_preview_and_narrow_layout(self):
        root=Path(self.temp.name)/'inspector-workspace';root.mkdir()
        (root/'note.txt').write_text('server content',encoding='utf-8')
        change=self.call('create_change',workspace='work')
        blob=self.upload(change['code'],b'server content')
        self.call('edit',change=change['code'],edit_revision=0,chunk='content',operations=[{'path':path,'blob':blob} for path in ('note.txt','second.txt','nested/child.txt')])
        self.call('submit',change=change['code'])
        pending=self.call('create_change',workspace='work')
        self.call('checkout',change=pending['code'],paths=['note.txt'],mode='exclusive')
        application=Application();controller=FileWorkspaceController(application);controller._enabled=True
        controller._data.update(workspace='work',root=root.as_posix(),stream='main',active_tab='files',view='depot',
                                rows=[{'path':'note.txt','stream':'main','kind':'file'}])
        pool=ThreadsPool(2);pool.start()
        engine=QQmlEngine();warnings=[]
        engine.warnings.connect(lambda items:warnings.extend(item.toString() for item in items))
        for name,value in qml_icon_bindings(HANDLER,engine).items():engine.rootContext().setContextProperty(name,value)
        theme_component=QQmlComponent(engine,QUrl.fromLocalFile(str(QML/'Theme.qml')))
        theme=theme_component.createWithInitialProperties({'dark':True})
        component=QQmlComponent(engine,QUrl.fromLocalFile(str(QML/'FileWorkspaceView.qml')))
        view=component.createWithInitialProperties({'theme':theme,'controller':controller})
        self.assertIsNotNone(view,str(component.errors()))
        window=QQuickWindow();window.setColor(theme.property('workspace'));view.setParentItem(window.contentItem());window.resize(1280,800);view.setWidth(1280);view.setHeight(800);window.show()
        def find(item,name):
            if item.objectName()==name:return item
            for child in item.childItems():
                value=find(child,name)
                if value is not None:return value
        def wait_inspection():
            deadline=monotonic()+5
            while (controller.data['inspection_busy'] or not controller.data['inspection'].get('path')) and monotonic()<deadline:
                QTest.qWait(10);threading.Event().wait(.01)
            self.assertFalse(controller.data['inspection_busy'])
            self.assertEqual(controller.data['inspection_error'],'')
        try:
            with self.http() as url,patch.object(env_inst,'commit_pool',pool),patch.object(env_inst,'server_pool',pool),patch.object(env_inst,'local_pool',pool),patch.object(env_mode,'current_path',self.temp.name),patch.object(env_server,'get_server',return_value=url),patch.object(env_server,'get_ticket',return_value=self.token),patch.object(env_server,'get_user',return_value='admin'),patch.object(env_server,'get_proxy',return_value={'enabled':False}):
                controller.action('refresh',{})
                deadline=monotonic()+5
                while (controller.busy or controller._read_worker is not None) and monotonic()<deadline:
                    QTest.qWait(10);threading.Event().wait(.01)
                self.assertFalse(controller.busy)
                self.assertEqual(controller.data['error'],'')
                controller.select_row('files',controller.row_identity(controller.data['rows'][0]),0)
                wait_inspection()
                info=controller.data['inspection']
                self.assertEqual(info['workspace_location'],(root/'note.txt').as_posix())
                self.assertEqual(info['holders'][0]['workspace'],'work')
                self.assertEqual(info['holders'][0]['mode'],'exclusive')
                inspector=find(view,'workspaceFileInspector');self.assertTrue(inspector.isVisible())
                def items(item):
                    yield item
                    for child in item.childItems():yield from items(child)
                button=next(item for item in items(inspector) if item.property('text')=='Preview' and item.metaObject().indexOfSignal('clicked()')>=0)
                point=button.mapToScene(QPointF(button.width()/2,button.height()/2)).toPoint()
                QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,point)
                wait_inspection()
                self.assertEqual(controller.data['active_tab'],'files')
                self.assertEqual(controller.data['inspection']['preview']['text'],'server content')
                for width in (1280,360):
                    window.resize(width,600);view.setWidth(width);view.setHeight(600);QTest.qWait(30)
                    self.assertGreater(inspector.height(),0)
                    self.assertLessEqual(inspector.mapToScene(QPointF(inspector.width(),inspector.height())).y(),600)
                window.resize(1280,800);view.setWidth(1280);view.setHeight(800);QTest.qWait(30)
                directory=Path(__file__).resolve().parents[1]/'.screenshots/file-workspace';directory.mkdir(parents=True,exist_ok=True)
                window.grabWindow().save(str(directory/'handler-stage2-preview.png'))
                # The History tab follows file selection; a pinned tab keeps its file.
                controller._data['depot_tree']=[{'id':name,'path':name,'stream':'main','kind':'file','depth':0,'name':name} for name in ('note.txt','second.txt')]
                controller.stateChanged.emit()
                def wait_read():
                    deadline=monotonic()+5
                    while controller._read_worker is not None and monotonic()<deadline:
                        QTest.qWait(10);threading.Event().wait(.01)
                controller.select_row('depot','note.txt',0)
                wait_read()
                self.assertEqual([row['path'] for row in controller.data['rows']],['note.txt','second.txt'])
                self.assertTrue(find(view,'workspaceFile_note.txt').property('selected'))
                with patch.object(controller,'_start_read',wraps=controller._start_read) as read:
                    controller.select_row('depot','second.txt',0x04000000)
                    read.assert_not_called()
                wait_read()
                self.assertEqual({row['path'] for row in controller.data['rows']},{'note.txt','second.txt'})
                self.assertTrue(find(view,'workspaceFile_second.txt').property('selected'))
                controller.open_view('pending');wait_read()
                pending_rows=controller.data['rows'][:]
                controller.select_row('depot','second.txt',0)
                self.assertEqual(controller.data['active_tab'],'pending')
                self.assertEqual(controller.data['rows'],pending_rows)
                controller.open_view('files');wait_read()
                self.assertEqual([row['path'] for row in controller.data['rows']],['note.txt','second.txt'])
                from thlib.side.client.tactic_client_lib.file_workspace import reconcile_workspace
                (root/'local-only.txt').write_text('not uploaded',encoding='utf-8')
                (root/'nested').mkdir();(root/'nested/child.txt').write_text('local nested',encoding='utf-8')
                reconcile_workspace(FileTransferClient(url,self.token,'files'),'work',root,Path(controller.data['local_cache']))
                controller._data['workspace_tree']=[{'id':'local-note','path':'note.txt','stream':'main','kind':'file','depth':0,'name':'note.txt'}]
                controller.select_row('workspace','local-note',0);wait_read()
                self.assertEqual([row['path'] for row in controller.data['rows']],['local-only.txt','note.txt'])
                self.assertTrue(find(view,'workspaceFile_note.txt').property('selected'))
                controller.set_value('inspector_tab','details');wait_inspection()
                translator=CatalogTranslator(HANDLER/'thlib/ui/translations/ru.json')
                try:
                    for language in ('en','ru'):
                        if language=='ru':self.app.installTranslator(translator);engine.retranslate()
                        for dark in (True,False):
                            theme.setProperty('dark',dark)
                            for width in (700,1600):
                                window.resize(width,1000);view.setWidth(width);view.setHeight(1000);QTest.qWait(100)
                                wait_inspection()
                                self.assertTrue(find(view,'workspaceFile_note.txt').property('selected'))
                                self.assertEqual(controller.data['inspection']['path'],'note.txt')
                                window.grabWindow().save(str(directory/f'handler-files-{language}-{dark}-{width}.png'))
                finally:
                    self.app.removeTranslator(translator);engine.retranslate()
                controller._data['workspace_tree'].insert(0,{'id':'workspace/work','kind':'workspace','directory':'','stream':'main','depth':0,'name':'work'})
                controller.select_row('workspace','workspace/work',0);wait_read()
                self.assertEqual(controller.data['file_focus'],{})
                self.assertEqual(controller.data['inspection'],{})
                self.assertEqual([row['path'] for row in controller.data['rows']],['local-only.txt','note.txt'])
                self.assertFalse(find(view,'workspaceFile_note.txt').property('selected'))
                controller.configure_tab({'id':'fixed-files','preset':'files','title':'Fixed files','source':'depot','prefix':'note.txt'})
                wait_read()
                controller.select_row('depot','second.txt',0)
                self.assertEqual([row['path'] for row in controller.data['rows']],['note.txt'])
                controller.open_view('files');wait_read()
                controller.select_row('depot','note.txt',0);wait_read()
                controller.open_view('history')
                def history_loaded(path):
                    deadline=monotonic()+5
                    while controller._read_worker is not None and monotonic()<deadline:
                        QTest.qWait(10);threading.Event().wait(.01)
                    self.assertEqual(controller.data['history_path'],path)
                    self.assertEqual([row['path'] for row in controller.data['history']],[path])
                history_loaded('note.txt')
                controller.select_row('depot','second.txt',0)
                history_loaded('second.txt')
                controller.configure_tab({'id':'pinned-history','preset':'history','title':'Pinned history','pinned':True})
                history_loaded('second.txt')
                controller.select_row('depot','note.txt',0)
                self.assertEqual(controller.data['history_path'],'second.txt')
                self.assertEqual(controller.data['history'][0]['path'],'second.txt')
                window.grabWindow().save(str(directory/'handler-history-selection.png'))
                self.assertFalse(warnings,warnings)
        finally:
            controller.shutdown();pool.exit();window.close();view.deleteLater();controller.deleteLater();theme.deleteLater();component.deleteLater();theme_component.deleteLater();engine.deleteLater();pool.deleteLater();window.deleteLater();application.deleteLater()
            QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)

    def test_read_view_during_operation_preserves_progress_and_selection(self):
        change=self.call('create_change',workspace='work')
        blob=self.upload(change['code'],b'content')
        self.call('edit',change=change['code'],edit_revision=0,chunk='content',operations=[{'path':'live.txt','blob':blob}])
        self.call('submit',change=change['code'])
        application=Application();controller=FileWorkspaceController(application);controller._enabled=True
        controller._data.update(workspace='work',stream='main',root=self.temp.name,change={},description='')
        pool=ThreadsPool(2);pool.start();started=threading.Event();release=threading.Event()
        original=FileWorkspaceController._execute
        def execute(client,state,cache,action,values,cancelled):
            if action=='upload':
                client.progress({'state':'uploading','bytes_done':5,'bytes_total':10,'total_known':True})
                started.set()
                if not release.wait(10):raise TimeoutError('test operation release')
                state['progress']={'state':'complete','bytes_done':10,'bytes_total':10,'total_known':True}
                return state
            return original(client,state,cache,action,values,cancelled)
        def until(predicate):
            deadline=monotonic()+5
            while not predicate() and monotonic()<deadline:
                QTest.qWait(10);threading.Event().wait(.005)
            self.assertTrue(predicate())
        try:
            with self.http() as url,patch.object(env_inst,'commit_pool',pool),patch.object(env_inst,'server_pool',pool),patch.object(env_inst,'local_pool',pool),patch.object(env_mode,'current_path',self.temp.name),patch.object(env_server,'get_server',return_value=url),patch.object(env_server,'get_ticket',return_value=self.token),patch.object(env_server,'get_user',return_value='admin'),patch.object(env_server,'get_proxy',return_value={'enabled':False}),patch.object(controller,'_execute',side_effect=execute):
                controller.action('upload',{})
                until(started.is_set)
                controller.open_view('files')
                until(lambda:controller._read_worker is None and bool(controller.data['rows']))
                self.assertTrue(controller.busy)
                self.assertEqual(controller.data['active_tab'],'files')
                self.assertEqual(controller.data['progress']['bytes_done'],5)
                row=controller.data['rows'][0]
                controller.select_row('files',controller.row_identity(row),0)
                release.set()
                until(lambda:not controller.busy)
                QTest.qWait(20)
                until(lambda:not controller.busy)
                self.assertEqual(controller.data['active_tab'],'files')
                self.assertEqual(controller.data['selected'],['live.txt'])
                self.assertEqual(controller.data['progress']['state'],'complete')
                # Selection can also change during a write without navigating to another view.
                started.clear();release.clear()
                controller.action('upload',{})
                until(started.is_set)
                row=controller.data['rows'][0]
                controller.select_row('files',controller.row_identity(row),0x04000000)
                controller.remember_scroll('files',73)
                self.assertEqual(controller.data['selected'],[])
                self.assertEqual(controller.data['scroll']['files'],73)
                release.set();until(lambda:not controller.busy)
                self.assertEqual(controller.data['selected'],[])
                self.assertEqual(controller.data['scroll']['files'],73)
        finally:
            release.set();controller.shutdown();pool.exit();controller.deleteLater();pool.deleteLater();application.deleteLater()
            QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)

    def test_external_comparison_empty_deleted_side_and_failed_copy_cleanup(self):
        import io
        import sys
        from hashlib import sha256
        from types import SimpleNamespace
        from thlib.ui.file_workspace_compare import external_compare
        cache=Path(self.temp.name)/'compare-cache';cache.mkdir()
        state={'comparison':{'left':{'path':'deleted.txt','deleted':True,'size':0},
                             'right':{'path':'new.txt','size':3,'sha256':sha256(b'new').hexdigest()},
                             'left_selector':{'path':'deleted.txt'},'right_selector':{'path':'new.txt'}}}
        client=SimpleNamespace(open=lambda *args,**kwargs:io.BytesIO(b'new'),progress=lambda event:None)
        application={'application':QUrl.fromLocalFile(sys.executable).toString()}
        with patch('thlib.ui.file_workspace_compare.subprocess.Popen') as launch:
            external_compare(client,state,cache,application,threading.Event())
            args=launch.call_args.args[0]
            self.assertEqual(Path(args[1]).read_bytes(),b'')
            self.assertEqual(Path(args[2]).read_bytes(),b'new')
        previous=set(cache.iterdir())
        client.open=lambda *args,**kwargs:io.BytesIO(b'bad')
        with self.assertRaisesRegex(ValueError,'revision changed'):
            external_compare(client,state,cache,application,threading.Event())
        self.assertEqual(set(cache.iterdir()),previous)

    def test_shelf_target_preview_then_unshelve_copies_selected_source(self):
        from thlib.side.client.tactic_client_lib.file_transfer import FileTransferClient
        change=self.call('create_change',workspace='work')
        blob=self.upload(change['code'],b'shelf bytes')
        self.call('edit',change=change['code'],edit_revision=0,chunk='file',operations=[{'path':'shelved.txt','blob':blob}])
        shelf=self.call('shelve',change=change['code'],edit_revision=1,request_id='shelf')
        self.call('revert',change=change['code'],edit_revision=1,request_id='revert')
        state=initial_state();state.update(workspace='work',stream='main',change=shelf)
        with self.http() as url:
            client=FileTransferClient(url,self.token,'files')
            state=FileWorkspaceController._execute(client,state,Path(self.temp.name)/'cache','prepare_unshelve',{'creating':True,'description':'destination'},threading.Event())
            self.assertNotEqual(state['change']['code'],shelf['code'])
            self.assertEqual(state['review_request']['shelf'],shelf['code'])
            self.assertEqual([row['path'] for row in state['review']['items']],['shelved.txt'])
            preview=state['review']
            state=FileWorkspaceController._execute(client,state,Path(self.temp.name)/'cache','unshelve_begin',
                {'shelf':shelf['code'],'review_revision':preview['edit_revision'],'preview_head_revision':preview['preview_head_revision'],'preview_source_root':preview['preview_source_root']},threading.Event())
            rows=client.rpc('change_files',change=state['change']['code'])['items']
            self.assertEqual([row['path'] for row in rows],['shelved.txt'])
            self.assertEqual(client.rpc('inspect_change',change=shelf['code'])['state'],'shelved')

    def test_reconcile_selected_add_edit_delete_rename_keeps_unselected_local_file(self):
        from thlib.side.client.tactic_client_lib.file_transfer import FileTransferClient
        from thlib.side.client.tactic_client_lib.file_workspace import reconcile_workspace,local_page
        change=self.call('create_change',workspace='work')
        operations=[]
        for path,data in [('old.txt',b'old'),('deleted.txt',b'delete'),('edited.txt',b'base'),('unchanged.txt',b'same')]:
            operations.append({'path':path,'blob':self.upload(change['code'],data)})
        self.call('edit',change=change['code'],edit_revision=0,chunk='seed',operations=operations)
        self.call('submit',change=change['code'])
        root=Path(self.temp.name)/'reconcile';cache=Path(self.temp.name)/'reconcile-cache';cache.mkdir()
        with self.http(worker=True) as url,patch.object(env_mode,'current_path',self.temp.name):
            client=FileTransferClient(url,self.token,'files')
            client.download('work',root)
            (root/'old.txt').rename(root/'renamed.txt');(root/'deleted.txt').unlink()
            (root/'edited.txt').write_bytes(b'edited');(root/'added.txt').write_bytes(b'added')
            (root/'unselected.txt').write_bytes(b'keep local')
            state=initial_state();state.update(workspace='work',stream='main',root=root.as_posix())
            state=FileWorkspaceController._execute(client,state,cache,'reconcile',{},threading.Event())
            self.assertEqual(state['active_tab'],'reconcile')
            self.assertEqual(state['view'],'local')
            self.assertNotIn('unchanged.txt',{row['path'] for row in state['rows']})
            self.assertFalse([task for task in client.rpc('transfer_tasks')['items'] if task['kind']=='upload'])
            rows=[row for row in state['rows'] if row['path']!='unselected.txt']
            state.update(rows=rows,
                selection_scope='files',selection_ids=[row['path'] for row in rows],selection_records={row['path']:row for row in rows},selected=[row['path'] for row in rows])
            state=FileWorkspaceController._execute(client,state,cache,'target_files',
                {'operation':'apply_reconcile','creating':True,'description':'selected'},threading.Event())
            entries={row['path']:row for row in client.rpc('change_files',change=state['change']['code'])['items']}
            self.assertEqual(set(entries),{'old.txt','renamed.txt','deleted.txt','edited.txt','added.txt'})
            self.assertEqual(entries['renamed.txt']['action'],'move/add')
            self.assertEqual(entries['deleted.txt']['action'],'delete')
            self.assertIsNone(entries['added.txt']['file'])
            self.assertEqual(entries['edited.txt']['action'],'checkout')
            self.assertFalse([task for task in client.rpc('transfer_tasks')['items'] if task['kind']=='upload'])
            self.assertEqual((root/'unselected.txt').read_bytes(),b'keep local')

    def test_revision_worker_scopes_depot_selection_while_files_view_is_local(self):
        from thlib.side.client.tactic_client_lib.file_transfer import FileTransferClient
        for content in (b'first',b'second'):
            change=self.call('create_change',workspace='work')
            blob=self.upload(change['code'],content)
            self.call('edit',change=change['code'],edit_revision=0,chunk='files',operations=[
                {'path':'docs/deep/file.txt','blob':blob},{'path':'outside.txt','blob':blob}])
            self.call('submit',change=change['code'])
        root=Path(self.temp.name)/'local'
        cache=Path(self.temp.name)/'controller-cache';cache.mkdir()
        state=initial_state()
        state.update(workspace='work',stream='main',root=str(root),view='local',selection_scope='depot',
            context_row={'kind':'directory','stream':'main','directory':'docs/deep/'})
        with self.http() as url:
            client=FileTransferClient(url,self.token,'files')
            FileWorkspaceController._execute(client,state,cache,'get_revision',{'scope':'folder','file_revision':1},threading.Event())
            self.assertEqual((root/'docs/deep/file.txt').read_bytes(),b'first')
            self.assertFalse((root/'outside.txt').exists())
            state.update(selection_scope='depot',selection_ids=['depot-file'],selected=['docs/deep/file.txt'],
                selection_records={'depot-file':{'kind':'file','stream':'main','path':'docs/deep/file.txt'}})
            FileWorkspaceController._execute(client,state,cache,'sync_selected',{},threading.Event())
            self.assertEqual((root/'docs/deep/file.txt').read_bytes(),b'second')
            self.assertFalse((root/'outside.txt').exists())

    def test_workspace_switch_keeps_work_and_tasks_but_rejects_old_view_state(self):
        from copy import deepcopy
        from hashlib import sha256
        from thlib.ui.file_workspace import local_page
        first=Path(self.temp.name)/'first-root';second=Path(self.temp.name)/'second-root'
        first.mkdir();(first/'keep.txt').write_bytes(b'local edit')
        self.call('update_workspace',workspace='work',view_revision=0,request_id='root',local_root=str(first))
        self.call('create_workspace',code='second',stream='main',local_root=str(second))
        self.call('switch_workspace',workspace='work',revision=0,request_id='first')
        pending=self.call('create_change',workspace='work',description='saved')
        task=self.call('transfer_begin',kind='download',workspace='work',client_root=str(first))['task']
        original_task=self.call('transfer_status',task=task)
        old=initial_state()
        old.update(workspace='work',stream='main',root=str(first),view='local',change=pending,description='unsaved')
        cache=Path(self.temp.name)/'cache'/'previous';cache.mkdir(parents=True)
        with self.http() as url,patch.object(env_mode,'current_path',self.temp.name),patch.object(env_server,'get_user',return_value='admin'),patch.object(env_inst,'projects',{}):
            client=FileTransferClient(url,self.token,'files')
            for action in ('preview_workspace_switch','choose_workspace'):
                with self.assertRaisesRegex(ValueError,'Save the changelist description'):
                    FileWorkspaceController._execute(client,deepcopy(old),cache,action,{'workspace':'second','revision':1},threading.Event())
            self.assertEqual(client.rpc('workspace_active')['workspace'],'work')
            old.update(description='saved',selected=['keep.txt'],selection_ids=['old-file'],selection_scope='files',
                selection_records={'old-file':{'path':'keep.txt','stream':'main'}},file_focus={'path':'keep.txt','stream':'main'},
                history=[{'path':'keep.txt'}],rows=[{'path':'keep.txt'}],scroll={'files':99},local_dirty=True,
                progress={'state':'downloading','task':task})
            preview=FileWorkspaceController._execute(client,deepcopy(old),cache,'preview_workspace_switch',{'workspace':'second'},threading.Event())
            self.assertTrue(preview['switch_preview']['token'])
            self.assertEqual(preview['workspace'],'work')
            self.assertEqual(preview['switch_preview']['pending_changes'],1)
            self.assertEqual(preview['switch_preview']['active_transfer'],task)
            from urllib.error import HTTPError
            with self.assertRaisesRegex(HTTPError,'revision conflict'):
                FileWorkspaceController._execute(client,deepcopy(old),cache,'choose_workspace',{'workspace':'second','revision':0},threading.Event())
            self.assertEqual(client.rpc('workspace_active')['workspace'],'work')
            with patch('thlib.side.client.tactic_client_lib.file_workspace.local_page',wraps=local_page) as page:
                switched=FileWorkspaceController._execute(client,deepcopy(old),cache,'choose_workspace',{'workspace':'second','revision':1},threading.Event())
            identity=sha256((url+'\0admin\0files\0second\0'+str(second)).encode()).hexdigest()
            self.assertEqual(page.call_args.args[0],cache.parent/identity/'local.sqlite')
            self.assertEqual(switched['rows'],[])
            app=Application();controller=FileWorkspaceController(app)
            try:
                controller._data=old
                controller._data['tab_states']={'files':{'rows':[{'path':'keep.txt'}],'change':pending,'description':'saved',
                    'selected':['keep.txt'],'selection_ids':['old-file'],'scroll':{'files':99},'name_filter':'retained'}}
                controller._write_view_context=('pending','change','',pending['code'])
                controller._write_selection={key:deepcopy(old[key]) for key in ('selected','selection_ids')}
                controller._result((switched,controller._generation))
                self.assertEqual(controller.data['workspace'],'second')
                for key in ('selected','selection_ids','rows','history'):
                    self.assertEqual(controller.data[key],[])
                for key in ('change','inspection','file_focus','progress','scroll'):
                    self.assertEqual(controller.data[key],{})
                self.assertFalse(controller.data['local_dirty'])
                self.assertEqual(controller.data['tab_states']['files']['name_filter'],'retained')
                self.assertEqual(controller.data['tab_states']['files']['rows'],[])
                self.assertEqual(controller.data['tab_states']['files']['selection_ids'],[])
                controller._data['selected']=['new-workspace-selection']
                with patch.object(controller,'action'):
                    controller.activate_tab('files')
                self.assertEqual(controller.data['rows'],[])
                self.assertEqual(controller.data['change'],{})
                self.assertEqual(controller.data['selected'],[])
            finally:
                controller.shutdown();controller.deleteLater();app.deleteLater()
            self.assertEqual(client.rpc('status',change=pending['code'])['state'],'pending')
            self.assertEqual(client.rpc('transfer_status',task=task),original_task)
            self.assertEqual((first/'keep.txt').read_bytes(),b'local edit')

    def test_pointer_range_context_menu_and_file_move_against_native_api(self):
        from PySide6.QtCore import QMimeData, QPoint
        from PySide6.QtGui import QDragEnterEvent, QDropEvent
        from thlib import tactic_classes as tc
        from copy import deepcopy
        import json

        published=self.call('create_change',workspace='work')
        folder_blob=self.upload(published['code'],b'folder contents')
        self.call('edit',change=published['code'],edit_revision=0,chunk='folder',operations=[
            {'path':'docs/first.txt','blob':folder_blob},{'path':'docs/deep/second.txt','blob':folder_blob}])
        self.call('submit',change=published['code'])
        source = self.call('create_change',workspace='work',description='Source')
        target = self.call('create_change',workspace='work',description='Target')
        blob = self.upload(source['code'])
        self.call('edit',change=source['code'],edit_revision=0,chunk='ui',operations=[
            {'path':name,'blob':blob} for name in ('a.txt','b.txt','c.txt')])
        source = self.call('status',change=source['code'])
        root=Path(self.temp.name)/'drop-workspace';root.mkdir()
        outside=root/'external — 外部.txt';outside.write_bytes(b'fresh Explorer import')
        pool=ThreadsPool(1);pool.start()
        application=Application();engine=QQmlEngine();warnings=[]
        engine.warnings.connect(lambda items:warnings.extend(item.toString() for item in items))
        for name,value in qml_icon_bindings(HANDLER,engine).items():engine.rootContext().setContextProperty(name,value)
        component=QQmlComponent(engine,QUrl.fromLocalFile(str(QML/'Theme.qml')))
        while component.isLoading():QTest.qWait(5)
        theme=component.createWithInitialProperties({'dark':True})
        self.assertIsNotNone(theme,str(component.errors()))
        QQmlEngine.setObjectOwnership(theme,QQmlEngine.CppOwnership)
        theme.setParent(engine)
        window=QQuickWindow();view=controller=None
        try:
            with (self.http(worker=True) as url,patch.object(env_inst,'projects',{'files':tc.Project({'code':'files','type':'file_project'})}),
                  patch.object(env_inst,'commit_pool',pool),patch.object(env_inst,'server_pool',pool),patch.object(env_mode,'current_path',self.temp.name),
                  patch.object(env_server,'get_server',return_value=url),patch.object(env_server,'get_ticket',return_value=self.token),
                  patch.object(env_server,'get_user',return_value='admin'),patch.object(env_server,'get_proxy',return_value={'enabled':False})):
                controller=FileWorkspaceController(application)
                fixture=self
                class Client:
                    def rpc(self,action,**kwargs):return fixture.call(action,**kwargs)
                state=initial_state();state.update(workspace='work',stream='main',change=source,description='Source',
                    changes=[source,target],targets=[source,target],root=root.as_posix(),depots=self.call('depots')['items'],streams=self.call('streams')['items'])
                FileWorkspaceController._depot_roots(state)
                FileWorkspaceController._depot_branch(Client(),state,'stream/main')
                FileWorkspaceController._change_branch(Client(),state,source['code'])
                controller._data=state;controller.stateChanged.emit()
                component=QQmlComponent(engine,QUrl.fromLocalFile(str(QML/'FileWorkspaceView.qml')))
                while component.isLoading():QTest.qWait(5)
                view=component.createWithInitialProperties({'theme':theme,'controller':controller})
                self.assertIsNotNone(view,str(component.errors()))
                view.setParentItem(window.contentItem());view.setWidth(1280);view.setHeight(800)
                window.resize(1280,800);window.show();QTest.qWait(30)
                def find(item,name):
                    if item.objectName()==name:return item
                    for child in item.childItems():
                        found=find(child,name)
                        if found:return found
                def file(name):return find(view,'workspaceChangeFile:'+source['code']+'/'+name)
                def click(item,button=Qt.LeftButton,modifiers=Qt.NoModifier):
                    self.assertIsNotNone(item)
                    point=item.mapToScene(QPointF(160,item.height()/2)).toPoint()
                    QTest.mouseMove(window,point)
                    QTest.mouseClick(window,button,modifiers,point);QTest.qWait(30)
                click(file('a.txt'));click(file('c.txt'),modifiers=Qt.ControlModifier)
                self.assertEqual(controller.data['selected'],['a.txt','c.txt'])
                click(file('c.txt'),Qt.RightButton)
                self.assertEqual(controller.data['selected'],['a.txt','c.txt'])
                menu=view.findChild(QObject,'workspaceActionMenu')
                deadline=monotonic()+2
                while not menu.property('opened') and monotonic()<deadline:QTest.qWait(10)
                self.assertTrue(menu.property('opened'),str(warnings));menu.close()
                revert=[row for row in menu.property('actions').toVariant() if row.get('command')=='revert_files']
                self.assertEqual(len(revert),1)
                self.assertTrue(revert[0]['enabled'],revert[0])
                self.assertNotIn('children',revert[0])
                deadline=monotonic()+2
                while menu.property('visible') and monotonic()<deadline:QTest.qWait(10)
                click(file('a.txt'));click(file('c.txt'),modifiers=Qt.ShiftModifier)
                self.assertEqual(controller.data['selected'],['a.txt','b.txt','c.txt'])
                target_row=find(view,'workspaceTreeRow:'+target['code'])
                point=target_row.mapToScene(QPointF(160,target_row.height()/2)).toPoint()
                mime=QMimeData();payload=controller.drag_payload('changes',source['code']+'/a.txt')['application/x-tactic-file-workspace']
                mime.setData('application/x-tactic-file-workspace',payload.encode())
                entered=QDragEnterEvent(point,Qt.MoveAction,mime,Qt.LeftButton,Qt.NoModifier)
                QCoreApplication.sendEvent(window,entered)
                self.assertEqual(target_row.property('dragFeedback'),'')
                self.assertIn('Move 3 files',target_row.property('dragCaption'))
                confirm=view.findChild(QObject,'workspaceDropConfirm')
                from PySide6.QtGui import QDragLeaveEvent
                QCoreApplication.sendEvent(window,QDragLeaveEvent())
                original_payload=payload
                invalid=json.loads(payload);invalid['rows'][0]['stream']='different-stream'
                mime.setData('application/x-tactic-file-workspace',json.dumps(invalid).encode())
                QCoreApplication.sendEvent(window,QDragEnterEvent(point,Qt.MoveAction,mime,Qt.LeftButton,Qt.NoModifier))
                QTest.qWait(20);self.assertIn('one changelist stream',target_row.property('dragFeedback'))
                QCoreApplication.sendEvent(window,QDropEvent(QPointF(point),Qt.MoveAction,mime,Qt.LeftButton,Qt.NoModifier))
                QTest.qWait(20);self.assertFalse(confirm.property('opened'))
                QCoreApplication.sendEvent(window,QDragLeaveEvent())
                mime.setData('application/x-tactic-file-workspace',original_payload.encode())
                QCoreApplication.sendEvent(window,QDragEnterEvent(point,Qt.MoveAction,mime,Qt.LeftButton,Qt.NoModifier))
                dropped=QDropEvent(QPointF(point),Qt.MoveAction,mime,Qt.LeftButton,Qt.NoModifier)
                QCoreApplication.sendEvent(window,dropped);QTest.qWait(20)
                confirm=view.findChild(QObject,'workspaceDropConfirm')
                self.assertTrue(confirm.property('opened'))
                confirm.accept()
                finished=threading.Event()
                controller._worker.result.connect(lambda *_args:finished.set(),Qt.DirectConnection)
                controller._worker.error.connect(lambda *_args:finished.set(),Qt.DirectConnection)
                deadline=monotonic()+15
                while (controller.busy or controller._read_worker is not None) and monotonic()<deadline:
                    QTest.qWait(10)
                    finished.wait(.01)
                self.assertFalse(controller.busy,f'{controller.data["progress"]}; target={self.call("change_files",change=target["code"])["items"]}; errors={application.errors}')
                self.assertEqual(controller.data['error'],'')
                self.assertEqual(self.call('change_files',change=source['code'])['items'],[])
                self.assertEqual(len(self.call('change_files',change=target['code'])['items']),3)
                target_row=find(view,'workspaceTreeRow:'+target['code'])
                point=target_row.mapToScene(QPointF(160,target_row.height()/2)).toPoint()
                folder_mime=QMimeData()
                folder_payload=controller.drag_payload('depot','path/main/docs/')['application/x-tactic-file-workspace']
                self.assertEqual(json.loads(folder_payload)['rows'][0]['kind'],'directory')
                folder_mime.setData('application/x-tactic-file-workspace',folder_payload.encode())
                QCoreApplication.sendEvent(window,QDragEnterEvent(point,Qt.CopyAction,folder_mime,Qt.LeftButton,Qt.NoModifier))
                QCoreApplication.sendEvent(window,QDropEvent(QPointF(point),Qt.CopyAction,folder_mime,Qt.LeftButton,Qt.NoModifier))
                QTest.qWait(20)
                self.assertTrue(confirm.property('opened'))
                self.assertIn('Open selected files for editing',find(confirm.property('contentItem'),'workspaceDropDescription').property('text'))
                confirm.accept()
                deadline=monotonic()+15
                while (controller.busy or controller._read_worker is not None) and monotonic()<deadline:
                    QTest.qWait(10)
                    threading.Event().wait(.005)
                self.assertFalse(controller.busy)
                self.assertEqual(controller.data['error'],'')
                checked={row['path'] for row in self.call('change_files',change=target['code'])['items']}
                self.assertTrue({'docs/first.txt','docs/deep/second.txt'}<=checked)
                self.assertEqual(controller.data['progress']['files_done'],2)
                self.assertEqual((root/'docs/deep/second.txt').read_bytes(),b'folder contents')
                (root/'docs/deep/second.txt').write_bytes(b'edited locally')
                from thlib.side.client.tactic_client_lib.file_workspace import watched_changes
                changes_now=watched_changes(Path(controller.data['local_cache']),root,['docs/deep/second.txt'])
                controller._local_changed(controller._watch_generation,changes_now)
                changed=next(row for row in controller.data['change_tree'] if row.get('path')=='docs/deep/second.txt')
                self.assertEqual(changed['local_status'],'modified')
                QTest.qWait(20)
                edited=find(view,'workspaceChangeFile:'+target['code']+'/docs/deep/second.txt')
                self.assertIsNotNone(edited)
                with patch('os.startfile') if os.name=='nt' else patch('subprocess.Popen') as opened:
                    QTest.mouseDClick(window,Qt.LeftButton,Qt.NoModifier,edited.mapToScene(QPointF(160,edited.height()/2)).toPoint())
                    deadline=monotonic()+15
                    while (controller.busy or controller._read_worker is not None) and monotonic()<deadline:QTest.qWait(10)
                    self.assertTrue(opened.called,'Double click opens the pending local file for editing')
                # Keep the original missing-copy Explorer regression after materialization coverage.
                (root/'docs/deep/second.txt').unlink()
                (root/'docs/first.txt').unlink()
                (root/'docs/deep').rmdir()
                (root/'docs').rmdir()
                if target['code'] not in controller.data['expanded_changes']:
                    controller.action('toggle_change',{'change':target['code']})
                    deadline=monotonic()+15
                    while (controller.busy or controller._read_worker is not None) and monotonic()<deadline:QTest.qWait(10)
                reveal_id=target['code']+'/docs/deep/second.txt'
                controller.select_row('changes',reveal_id,0,True)
                controller._data['selection_records'][reveal_id]['local_status']='missing'
                controller._data['error']='Previous operation error'
                controller.stateChanged.emit()
                QTest.qWait(30)
                missing_file=find(view,'workspaceChangeFile:'+reveal_id)
                click(missing_file,Qt.RightButton)
                self.assertEqual(controller.data['selection_ids'],[reveal_id])
                menu=view.findChild(QObject,'workspaceActionMenu')
                deadline=monotonic()+2
                while not menu.property('opened') and monotonic()<deadline:QTest.qWait(5)
                def items(item):
                    for child in item.childItems():
                        yield child
                        yield from items(child)
                reveal=next(item for item in items(menu.property('contentItem')) if item.objectName()=='actionMenuPrimaryTarget' and item.isVisible() and item.parentItem().property('modelData').toVariant().get('command')=='reveal_local')
                self.assertTrue(reveal.isEnabled(),'A missing local copy must not disable Show in Explorer')
                self.assertGreaterEqual(reveal.window().height(),reveal.mapToScene(QPointF(0,reveal.height())).y(),'The menu must not be clipped to its anchor row height')
                with patch('subprocess.Popen') as launched:
                    triggered=QSignalSpy(menu.triggered)
                    QTest.qWait(30)
                    reveal_point=reveal.mapToScene(QPointF(reveal.width()/2,reveal.height()/2)).toPoint()
                    QTest.mouseMove(reveal.window(),reveal_point)
                    QTest.mouseClick(reveal.window(),Qt.LeftButton,Qt.NoModifier,reveal_point)
                    deadline=monotonic()+3
                    while not triggered.count() and monotonic()<deadline:QTest.qWait(10)
                    self.assertGreater(triggered.count(),0,'Show in Explorer must dispatch from the actual menu')
                    deadline=monotonic()+15
                    while (controller.busy or controller._read_worker is not None) and monotonic()<deadline:QTest.qWait(10)
                    self.assertFalse(controller.busy)
                    self.assertTrue(launched.called,f'progress={controller.data["progress"]}, error={controller.data["error"]}')
                    self.assertEqual(launched.call_args.args[0],['explorer.exe' if os.name=='nt' else 'xdg-open',str(root)])
                self.assertEqual(controller.data['error'],'')
                notice=controller.log_model.get(controller.log_model.rowCount()-1)
                self.assertEqual(notice['level'],'INFO')
                self.assertIn('nearest existing folder',notice['message'])
                self.assertNotIn('operation_notice',controller.data)
                self.assertFalse((root/'docs').exists())
                target_row=find(view,'workspaceTreeRow:'+target['code'])
                point=target_row.mapToScene(QPointF(160,target_row.height()/2)).toPoint()
                imported=QMimeData();imported.setUrls([QUrl.fromLocalFile(str(outside))])
                QCoreApplication.sendEvent(window,QDragEnterEvent(point,Qt.CopyAction,imported,Qt.LeftButton,Qt.NoModifier))
                QCoreApplication.sendEvent(window,QDropEvent(QPointF(point),Qt.CopyAction,imported,Qt.LeftButton,Qt.NoModifier))
                self.assertFalse(confirm.property('opened'),'Workspace Explorer drops must start without confirmation')
                finished.clear()
                if controller._worker:
                    controller._worker.result.connect(lambda *_args:finished.set(),Qt.DirectConnection)
                    controller._worker.error.connect(lambda *_args:finished.set(),Qt.DirectConnection)
                deadline=monotonic()+20
                while (controller.busy or controller._read_worker is not None) and monotonic()<deadline:QTest.qWait(10);finished.wait(.01)
                self.assertFalse(controller.busy);self.assertEqual(controller.data['error'],'',application.stacktrace)
                self.assertEqual((root/outside.name).read_bytes(),outside.read_bytes())
                self.assertIn(outside.name,[row['path'] for row in self.call('change_files',change=target['code'])['items']])
                rejected_file=Path(self.temp.name)/'outside-workspace.txt';rejected_file.write_bytes(b'not imported')
                before_revision=self.call('status',change=target['code'])['edit_revision']
                target_row=find(view,'workspaceTreeRow:'+target['code'])
                point=target_row.mapToScene(QPointF(160,target_row.height()/2)).toPoint()
                rejected_mime=QMimeData();rejected_mime.setUrls([QUrl.fromLocalFile(str(outside)),QUrl.fromLocalFile(str(rejected_file))])
                QCoreApplication.sendEvent(window,QDragEnterEvent(point,Qt.CopyAction,rejected_mime,Qt.LeftButton,Qt.NoModifier))
                QCoreApplication.sendEvent(window,QDropEvent(QPointF(point),Qt.CopyAction,rejected_mime,Qt.LeftButton,Qt.NoModifier))
                blocked=view.findChild(QObject,'workspaceDropBlocked')
                deadline=monotonic()+5
                while not blocked.property('opened') and monotonic()<deadline:QTest.qWait(10)
                self.assertTrue(blocked.property('opened'));self.assertFalse(confirm.property('opened'))
                self.assertEqual(controller.data['error'],'')
                self.assertFalse((root/rejected_file.name).exists())
                self.assertEqual(self.call('status',change=target['code'])['edit_revision'],before_revision)
                ok=find(blocked.property('contentItem'),'workspaceDropBlockedOk')
                QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,ok.mapToScene(QPointF(ok.width()/2,ok.height()/2)).toPoint())
                QTest.qWait(30);self.assertFalse(blocked.property('opened'))
                from thlib.ui.file_workspace_files import execute_files
                from thlib.ui.file_workspace_interaction import file_identity
                trash_state=deepcopy(controller.data);trash_state['selection_scope']='files'
                local_row=next(row for row in trash_state['rows'] if row['path']==outside.name)
                identity=file_identity(local_row,trash_state)
                trash_state['selection_ids']=[identity];trash_state['selection_records']={identity:local_row}
                from PySide6.QtCore import QFile
                with patch.object(QFile,'moveToTrash',return_value=False),self.assertRaisesRegex(OSError,'Trash'):
                    execute_files(Client(),trash_state,Path(self.temp.name)/'trash-cache','delete_local',{},threading.Event())
                self.assertTrue((root/outside.name).exists())
                execute_files(Client(),trash_state,Path(self.temp.name)/'trash-cache','delete_local',{},threading.Event())
                self.assertFalse((root/outside.name).exists())
                self.assertIn(outside.name,[row['path'] for row in self.call('change_files',change=target['code'])['items']],'Local Trash never deletes server history')
                for code in list(controller.data['expanded_changes']):
                    controller.action('toggle_change',{'change':code})
                    deadline=monotonic()+15
                    while (controller.busy or controller._read_worker is not None) and monotonic()<deadline:QTest.qWait(10)
                QTest.qWait(30)
                tree=find(view,'workspaceChangelistTree')
                blank=tree.mapToScene(QPointF(150,tree.height()*.7)).toPoint()
                QTest.mouseClick(window,Qt.RightButton,Qt.NoModifier,blank);QTest.qWait(30)
                menu=view.findChild(QObject,'workspaceActionMenu')
                deadline=monotonic()+2
                while not menu.property('opened') and monotonic()<deadline:QTest.qWait(10)
                if not menu.property('opened'):
                    window.grabWindow().save(str(Path(__file__).resolve().parents[1]/'.test-tmp/stage3-blank-menu.png'))
                self.assertTrue(menu.property('opened'),f"Right click on empty Pending area: tab={controller.data['active_tab']} visible={tree.isVisible()} height={tree.height()} point={blank} contentY={tree.property('contentY')}")
                candidates=lambda:[item for item in items(menu.property('contentItem')) if item.objectName()=='actionMenuPrimaryTarget' and item.isVisible() and item.parentItem().property('modelData').toVariant().get('command')=='create_change']
                deadline=monotonic()+2
                while not candidates() and monotonic()<deadline:QTest.qWait(10)
                self.assertTrue(candidates(),f"Menu actions={menu.property('actions')}; expanded={controller.data['expanded_changes']}; warnings={warnings}")
                create=candidates()[0]
                before={row['code'] for row in self.call('changes',workspace='work')['items']}
                triggered=QSignalSpy(menu.triggered);QTest.qWait(30)
                create_point=create.mapToScene(QPointF(create.width()/2,create.height()/2)).toPoint()
                QTest.mouseMove(create.window(),create_point)
                QTest.mouseClick(create.window(),Qt.LeftButton,Qt.NoModifier,create_point)
                deadline=monotonic()+3
                while not triggered.count() and monotonic()<deadline:QTest.qWait(10)
                self.assertGreater(triggered.count(),0,'New changelist dispatches from its actual menu')
                deadline=monotonic()+15
                while (controller.busy or controller._read_worker is not None) and monotonic()<deadline:QTest.qWait(10)
                self.assertFalse(controller.busy);self.assertEqual(controller.data['error'],'')
                self.assertNotIn(controller.data['change']['code'],before)
                self.assertGreater(controller.data['change']['number'],0)
                tab=find(view,'workspaceViewTab:files')
                close=tab.mapToScene(QPointF(tab.width()-20,tab.height()/2)).toPoint()
                QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,close);QTest.qWait(30)
                self.assertFalse(any(row['id']=='files' for row in controller.data['tabs']),'Close tab works with a real pointer click')
                screenshots=Path(__file__).resolve().parents[1]/'.screenshots/file-workspace';screenshots.mkdir(parents=True,exist_ok=True)
                window.grabWindow().save(str(screenshots/'handler-stage1.png'))
                self.assertEqual(warnings,[])
        finally:
            if controller:controller.shutdown()
            pool.exit();window.close()
            if view:view.setParentItem(None);view.deleteLater()
            if controller:controller.deleteLater()
            component.deleteLater();engine.deleteLater();application.deleteLater();pool.deleteLater();window.deleteLater()
            QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)

    def test_cached_file_project_renders_real_dock_and_maximize_button(self):
        from thlib import tactic_classes as tc
        from thlib.ui.workspace_models.docks import DockPanelModel
        application = Application()
        with patch.object(env_inst, 'projects', {'files':tc.Project({'code':'files','type':'file_project'})}):
            controller = FileWorkspaceController(application)
        self.assertTrue(controller.enabled)
        docks = DockPanelModel({})
        docks.show_panel('commit_queue')
        docks.place_panel('commit_queue','results','center')
        docks.show_panel('snapshot')
        engine = QQmlEngine()
        warnings = []
        engine.warnings.connect(lambda items: warnings.extend(item.toString() for item in items))
        for name, value in qml_icon_bindings(HANDLER, engine).items():
            engine.rootContext().setContextProperty(name, value)
        engine.rootContext().setContextProperty('fileWorkspaceController', controller)
        engine.rootContext().setContextProperty('dockModel', docks)
        component = QQmlComponent(engine)
        component.setData(b'''import QtQuick
Item {
    id:sceneHost
    property bool windowResizeActive:false
    property bool dockDragActive:false
    Theme { id:uiTheme;dark:true }
    Component { id:queue;CommitWorkspaceView { theme:uiTheme } }
    Component { id:empty;Item {} }
    Repeater {
        model:dockModel
        delegate:DockPanel {
            required property bool panelVisible
            host:sceneHost;theme:uiTheme
            modelVisible:panelVisible && stackActive;panelOpen:modelVisible
            contentComponent:kind === "commit_queue" ? queue : empty
        }
    }
}''', QUrl.fromLocalFile(str(QML/'owned-file-dock.qml')))
        view = component.create()
        self.assertIsNotNone(view, str(component.errors()))
        window = QQuickWindow()
        view.setParentItem(window.contentItem())
        window.resize(1280,800);view.setWidth(1280);view.setHeight(800);window.show()

        def find(item,name):
            if item.objectName()==name:return item
            for child in item.childItems():
                found=find(child,name)
                if found is not None:return found

        try:
            QTest.qWait(40)
            files=find(view,'fileWorkspaceView')
            self.assertIsNotNone(files)
            for _ in range(3):
                application.server_state_changed.emit()
                QTest.qWait(10)
                self.assertTrue(controller.enabled)
                self.assertIs(find(view,'fileWorkspaceView'), files,
                    'Connection notifications must preserve the loaded file workspace')
            panel=find(view,'dockPanel_commit_queue')
            self.assertTrue(panel.isVisible())
            self.assertLess(panel.width(),view.width())
            button=find(view,'fileWorkspaceMaximize')
            self.assertIsNotNone(button)
            for maximized in (True,False):
                point=button.mapToScene(QPointF(button.width()/2,button.height()/2)).toPoint()
                QTest.mouseMove(window,point);QTest.qWait(20)
                QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,point)
                QTest.qWait(200)
                if docks.maximizedPanelId != ('commit_queue' if maximized else ''):
                    window.grabWindow().save(str(Path(__file__).resolve().parents[1]/'.screenshots/file-workspace/handler-dock-failure.png'))
                self.assertEqual(docks.maximizedPanelId, 'commit_queue' if maximized else '',
                    f'panel={panel.width()} files={files.width()} button={button.width()}x{button.height()} visible={button.isVisible()} enabled={button.isEnabled()} position={point}')
                if maximized:self.assertEqual(panel.width(),view.width())
                else:self.assertLess(panel.width(),view.width())
            from unittest.mock import Mock
            from contextlib import redirect_stdout
            import io
            application.debug_log = Mock()
            pool = ThreadsPool(1)
            pool.start()
            output = io.StringIO()
            def blocked(_client, state, *_args):
                state['progress'] = {'state':'blocked','reason':'local_modified_or_untracked',
                                     'path':'D:/workspace/shots/SH010/layout.txt'}
                state['operation_blocked'] = True
                return state
            def wait_operation():
                deadline = monotonic() + 5
                while (controller.busy or controller._read_worker is not None) and monotonic() < deadline:
                    QTest.qWait(5)
                    threading.Event().wait(.005)
                self.assertFalse(controller.busy)
                QTest.qWait(20)
            try:
                with (patch.object(env_inst,'commit_pool',pool),patch.object(env_inst,'server_pool',pool),
                      patch.object(env_mode,'current_path',self.temp.name),
                      redirect_stdout(output)):
                    with patch.object(controller,'_execute',side_effect=blocked):
                        controller.action('get_latest', {})
                        wait_operation()
                    self.assertEqual(controller.data['progress']['state'],'blocked')
                    self.assertEqual(controller.log_model.get(1)['level'],'WARNING')
                    self.assertIn('not overwritten', controller.log_model.get(1)['message'])
                    self.assertEqual(application.errors, [])
                    application.debug_log.log.assert_not_called()
                    log=find(view,'fileWorkspaceLog')
                    self.assertIsNotNone(log)
                    def log_messages(item):
                        result=[item.property('text')] if item.objectName()=='fileWorkspaceLogMessage' else []
                        for child in item.childItems():
                            result.extend(log_messages(child))
                        return result
                    messages=log_messages(log)
                    self.assertTrue(any('layout.txt' in message for message in messages), messages)
                    with patch.object(controller,'_execute',side_effect=RuntimeError('Unexpected test failure')):
                        controller.action('refresh', {})
                        wait_operation()
                    self.assertEqual(application.errors, [])
                    self.assertIn('RuntimeError: Unexpected test failure', application.debug_log.log.call_args.kwargs['stacktrace'])
                    self.assertEqual(controller.log_model.get(3)['level'],'ERROR')
                    with patch.object(controller,'_execute',side_effect=lambda _client,state,*_:state):
                        controller.action('refresh', {})
                        wait_operation()
                    self.assertEqual(controller.log_model.get(5)['message'],'Completed')
                    controller.copy_log()
                    self.assertIn('layout.txt', self.app.clipboard().text())
                    controller.clear_log()
                    self.assertEqual(controller.log_model.rowCount(),0)
                    def disk_blocked(_client,state,*_args):
                        state['progress']={'state':'blocked','reason':'insufficient_disk_space','path':'D:/workspace',
                                           'required_bytes':2048,'available_bytes':512}
                        state['operation_blocked']=True
                        return state
                    application.debug_log.reset_mock()
                    with patch.object(controller,'_execute',side_effect=disk_blocked):
                        controller.action('get_latest',{})
                        wait_operation()
                    self.assertEqual(controller.log_model.get(1)['level'],'WARNING')
                    self.assertIn('free disk space',controller.log_model.get(1)['message'])
                    self.assertEqual(controller.data['progress']['required_bytes'],2048)
                    application.debug_log.log.assert_not_called()
                    switch=files.findChild(QObject,'workspaceSwitchDialog')
                    with patch.object(controller,'action') as action:
                        controller._data['switch_preview']={'token':'first-switch','previous':'one','workspace':'two','revision':7}
                        controller.stateChanged.emit();QTest.qWait(30)
                        self.assertTrue(switch.property('opened'))
                        QTest.keyClick(window,Qt.Key_Escape);QTest.qWait(30)
                        self.assertFalse(switch.property('opened'))
                        action.assert_not_called()
                        controller._data['switch_preview']['token']='second-switch'
                        controller.stateChanged.emit();QTest.qWait(30)
                        self.assertTrue(switch.property('opened'))
                        switch.accept()
                        action.assert_called_once_with('choose_workspace',{'workspace':'two','revision':7})
                    controller.clear_log()
                    for index in range(1001):
                        controller._log('INFO', str(index))
                    self.assertEqual(controller.log_model.rowCount(),1000)
                    self.assertEqual(controller.log_model.get(0)['message'],'1')
                    controller.clear_log()
                self.assertNotIn('Traceback',output.getvalue())
            finally:
                pool.exit()
                pool.deleteLater()
            self.assertEqual(sorted(set(warnings)), [], '\n'.join(sorted(set(warnings))[:12]))
            output=Path(__file__).resolve().parents[1]/'.screenshots/file-workspace/handler-docked.png'
            window.grabWindow().save(str(output))
        finally:
            controller.shutdown();window.close();view.setParentItem(None)
            for item in (view,window,controller,application,component,engine,docks):item.deleteLater()
            QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)

    def test_bootstrap_and_ping_preserve_file_project_until_sign_out(self):
        from thlib import tactic_classes as tc
        from thlib.ui.controller import ApplicationController

        project = tc.Project({'code': 'files', 'type': 'file_project'})
        project.get_all_search_types([], [], '', [])
        application = controller = None
        try:
            with (patch.object(env_mode, 'current_path', self.temp.name),
                  patch.object(env_inst, 'projects', {'files': project}),
                  patch.object(env_inst, 'current_project', None),
                  patch.object(env_inst, 'logins', {}),
                  patch.object(env_inst, 'exit_pools'),
                  patch.object(env_server, 'get_server_presets', return_value={})):
                application = ApplicationController()
                controller = FileWorkspaceController(application)
                application._bootstrap_request_id = 'file-mode-bootstrap'
                with patch.object(controller, 'action'):
                    application._async_bootstrap_result((
                        [project], 'Admin', 'files', 'Files', [], project,
                        True, 'file-mode-bootstrap'))
                self.assertTrue(controller.enabled,
                    'Connected notification must not undo file-project selection')
                controller._data.update(workspace='work', selected=['local.txt'])
                generation = controller._generation
                for state, message in (('online', 'Pong'), ('error', 'Connection lost'),
                                       ('connecting', 'Reconnecting'), ('online', 'Connected')):
                    application._set_server_state(state, message)
                    self.assertTrue(controller.enabled)
                    self.assertEqual(controller.data['workspace'], 'work')
                    self.assertEqual(controller.data['selected'], ['local.txt'])
                    self.assertEqual(controller._generation, generation)
                application.open_window('commit_queue')
                self.assertTrue(application.dock_model.is_panel_presented('commit_queue'))
                self.assertFalse(application.window_model.is_window_visible('commit_queue'))
                application.signing_out.emit()
                self.assertFalse(controller.enabled)
                self.assertEqual(controller.data['workspace'], '')
                self.assertTrue(controller._cancel.is_set())
        finally:
            with (patch.object(env_mode, 'current_path', self.temp.name),
                  patch.object(env_inst, 'exit_pools')):
                if controller:
                    controller.shutdown()
                    controller.deleteLater()
                if application:
                    application.shutdown()
                    application.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)

    def test_sync_local_conflict_returns_blocked_before_reconcile(self):
        from thlib.side.client.tactic_client_lib.file_transfer import FileTransferClient
        change = self.call('create_change', workspace='work')
        blob = self.upload(change['code'], b'published layout')
        self.call('edit', change=change['code'], edit_revision=0, chunk='publish',
                  operations=[{'path':'shots/SH010/layout.txt','blob':blob}])
        self.call('submit', change=change['code'])
        root = Path(self.temp.name) / 'workspace'
        target = root / 'shots/SH010/layout.txt'
        target.parent.mkdir(parents=True)
        target.write_bytes(b'local untracked edits')
        state = initial_state()
        state.update(workspace='work',stream='main',root=root.as_posix())
        with self.http() as url, patch('thlib.ui.file_workspace.reconcile_workspace') as reconcile:
            client = FileTransferClient(url,self.token,'files')
            result = FileWorkspaceController._execute(client,state,Path(self.temp.name)/'cache',
                                                       'get_latest',{},threading.Event())
            self.assertTrue(result['operation_blocked'])
            self.assertEqual(result['progress']['state'],'blocked')
            self.assertEqual(result['progress']['path'],target.as_posix())
            self.assertEqual(target.read_bytes(),b'local untracked edits')
            reconcile.assert_not_called()

    def test_handler_latest_selected_file_after_stopped_workspace_sync(self):
        change=self.call('create_change',workspace='work')
        blob=self.upload(change['code'],b'server bytes')
        self.call('edit',change=change['code'],edit_revision=0,chunk='files',operations=[
            {'path':'a.txt','blob':blob},{'path':'b.txt','blob':blob}])
        self.call('submit',change=change['code'])
        root=Path(self.temp.name)/'local';root.mkdir();(root/'a.txt').write_bytes(b'local changes')
        state=initial_state();state.update(workspace='work',stream='main',root=root.as_posix(),view='depot')
        with self.http() as url:
            client=FileTransferClient(url,self.token,'files')
            FileWorkspaceController._execute(client,state,Path(self.temp.name)/'cache','get_latest',{},threading.Event())
            stopped=state['progress']['task'];self.assertTrue(state.pop('operation_blocked'))
            state.update(rows=[{'path':'b.txt','kind':'file','stream':'main'}],selected=['b.txt'])
            FileWorkspaceController._execute(client,state,Path(self.temp.name)/'cache','sync_selected',{},threading.Event())
            self.assertEqual(client.rpc('transfer_status',task=stopped)['state'],'cancelled')
            self.assertIsNone(client.rpc('workspace_status',workspace='work')['active_sync'])
        self.assertEqual((root/'a.txt').read_bytes(),b'local changes')
        self.assertEqual((root/'b.txt').read_bytes(),b'server bytes')

    def test_native_qml_upload_submit_have_history_and_small_layout(self):
        root = Path(self.temp.name) / 'sources'
        root.mkdir()
        (root / 'fresh.txt').write_bytes(b'native GUI fresh content')
        self.call('create_workspace', code='gui', stream='main', local_root=root.as_posix())
        self.call('switch_workspace', workspace='gui', revision=0, request_id='gui')
        application = Application()
        controller = FileWorkspaceController(application)
        controller._enabled = True
        pool = ThreadsPool(1)
        pool.start()
        engine = QQmlEngine()
        warnings = []
        engine.warnings.connect(lambda items: warnings.extend(item.toString() for item in items))
        for name, value in qml_icon_bindings(HANDLER, engine).items():
            engine.rootContext().setContextProperty(name, value)
        theme_component = QQmlComponent(engine, QUrl.fromLocalFile(str(QML / 'Theme.qml')))
        theme = theme_component.createWithInitialProperties({'dark': True})
        component = QQmlComponent(engine, QUrl.fromLocalFile(str(QML / 'FileWorkspaceView.qml')))
        view = component.createWithInitialProperties({'theme': theme, 'controller': controller})
        self.assertIsNotNone(view, '\n'.join(error.toString() for error in component.errors()))
        window = QQuickWindow()
        window.setColor(theme.property('workspace'))
        view.setParentItem(window.contentItem())
        window.resize(1280, 900)
        view.setWidth(1280)
        view.setHeight(900)
        window.show()

        def action(name, values=None):
            if name in ('submit','shelve'):
                action('review_change',{'operation':name})
                values={**(values or {}),'review_revision':controller.data['review']['edit_revision']}
            if name:
                controller.action(name, values or {})
            finished=threading.Event()
            if controller._worker:
                controller._worker.result.connect(lambda *_args:finished.set(),Qt.DirectConnection)
                controller._worker.error.connect(lambda *_args:finished.set(),Qt.DirectConnection)
            deadline = monotonic() + 40
            while (controller.busy or controller._read_worker is not None) and monotonic() < deadline:
                QTest.qWait(10)
                finished.wait(.01)
            self.assertFalse(controller.busy, f'{name}: {controller.data["progress"]}; {controller.data["error"]}')
            self.assertEqual(controller.data['error'], '', name)

        def click(item):
            point = item.mapToScene(QPointF(item.width() / 2, item.height() / 2))
            QTest.mouseMove(item.window(), point.toPoint())
            QTest.qWait(20)
            QTest.mouseClick(item.window(), Qt.LeftButton, Qt.NoModifier, point.toPoint())
            QTest.qWait(250)

        def tree_item(name):
            def find(item):
                if item.objectName() == name:
                    return item
                for child in item.childItems():
                    result = find(child)
                    if result is not None:
                        return result
            deadline = monotonic() + 2
            item = find(view)
            while item is None and monotonic() < deadline:
                QTest.qWait(5)
                item = find(view)
            if item is None:
                output = Path(__file__).resolve().parents[1] / '.screenshots/file-workspace/handler-tree-failure.png'
                window.grabWindow().save(str(output))
            self.assertIsNotNone(item, f'{name}: rows={controller.data["depot_tree"]}; model={controller.depot_model.rowCount()}; warnings={warnings}')
            return item

        def children(item):
            for child in item.childItems():
                yield child
                yield from children(child)

        def menu_command(button, command):
            click(tree_item(button))
            menu = view.findChild(QObject, 'workspaceActionMenu')
            self.assertTrue(menu.property('opened'),str(warnings))
            groups={'checkout_ordinary':'Checkout','checkout_exclusive':'Checkout','remove_files':'Changelist edits','move_files':'Changelist edits','rename_file':'Changelist edits','file_history':'Inspect / revisions','revision_selected':'Inspect / revisions'}
            active=menu
            if command in groups:
                group=next(item for item in children(menu.property('contentItem'))
                    if item.objectName()=='actionMenuPrimaryTarget' and item.parentItem().property('modelData').toVariant().get('title')==groups[command])
                click(group)
                deadline=monotonic()+2
                while not menu.property('activeSubmenu') and monotonic()<deadline:QTest.qWait(5)
                active=menu.property('activeSubmenu')
                if hasattr(active,'toQObject'):active=active.toQObject()
                self.assertIsNotNone(active)
                while not active.property('opened') and monotonic()<deadline:QTest.qWait(5)
            target = next(item for item in children(active.property('contentItem'))
                          if item.objectName() == 'actionMenuPrimaryTarget'
                          and item.parentItem().property('modelData').toVariant().get('command') == command)
            self.assertTrue(target.isEnabled())
            triggered=QSignalSpy(menu.triggered)
            if command in groups or command == 'new_tab':
                target.forceActiveFocus(Qt.PopupFocusReason)
                QTest.keyClick(target.window(),Qt.Key_Return);QTest.qWait(250)
            else:
                click(target)
            self.assertGreater(triggered.count(),0,f'{command}; submenu={active.property("opened")}')
            destination = view.findChild(QObject, 'workspaceTargetDialog')
            if command.startswith('checkout_') and destination:
                deadline=monotonic()+2
                while not destination.property('opened') and monotonic()<deadline:QTest.qWait(5)
                self.assertTrue(destination.property('opened'))
                destination.accept()
            return menu

        try:
            with self.http(worker=True) as url, patch.object(env_inst, 'commit_pool', pool), patch.object(env_inst,'server_pool',pool), patch.object(env_mode, 'current_path', self.temp.name), patch.object(env_server, 'get_server', return_value=url), patch.object(env_server, 'get_ticket', return_value=self.token), patch.object(env_server, 'get_user', return_value='admin'), patch.object(env_server, 'get_proxy', return_value={'enabled': False}):
                action('refresh')
                self.assertEqual(controller.data['workspace'], 'gui')
                QTest.qWait(30)
                button = tree_item('newChangelistButton')
                self.assertIsNotNone(button)
                point = button.mapToScene(QPointF(button.width() / 2, button.height() / 2))
                QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, point.toPoint())
                action(None)
                self.assertTrue(controller.data['change'].get('code'))
                with patch.object(application, 'open_window') as opened:
                    menu_command('changelistActionsButton', 'change_details')
                    opened.assert_called_once_with('file_changelist')
                from thlib.ui.workspace_models.windows import FloatingWindowModel
                window_model = FloatingWindowModel({})
                engine.rootContext().setContextProperty('windowModel', window_model)
                details_component = QQmlComponent(engine, QUrl.fromLocalFile(str(QML/'FileWorkspaceChangelistView.qml')))
                details = details_component.createWithInitialProperties({'theme':theme, 'controller':controller, 'windowId':'file_changelist'})
                self.assertIsNotNone(details, str(details_component.errors()))
                details_window = QQuickWindow()
                details_window.setTransientParent(window)
                details_window.setFlags(Qt.Dialog)
                details_window.setModality(Qt.WindowModal)
                details_window.resize(600,540)
                details.setParentItem(details_window.contentItem());details.setWidth(600);details.setHeight(540)
                details_window.show();QTest.qWait(30)
                try:
                    action(None)
                    details_window.requestActivate();QTest.qWait(30)
                    edit = next(item for item in children(details) if item.objectName()=='fileWorkspaceDetailsEdit')
                    self.assertTrue(edit.property('enabled'))
                    QTest.mouseClick(details_window,Qt.LeftButton,Qt.NoModifier,edit.mapToScene(QPointF(edit.width()/2,edit.height()/2)).toPoint())
                    field = next(item for item in children(details) if item.objectName()=='fileWorkspaceChangelistDescription')
                    self.assertFalse(field.property('readOnly'))
                    QMetaObject.invokeMethod(field,'focusEditor')
                    for char in 'menu change':
                        QTest.keyClick(details_window, Qt.Key(ord(char.upper())))
                    self.assertEqual(field.property('text'), 'menu change')
                    save = next(item for item in children(details) if item.objectName()=='fileWorkspaceDetailsSave')
                    QTest.mouseClick(details_window,Qt.LeftButton,Qt.NoModifier,save.mapToScene(QPointF(save.width()/2,save.height()/2)).toPoint())
                    action(None)
                    self.assertEqual(controller.data['change']['description'], 'menu change')
                finally:
                    details_window.close()
                    for value in (details,details_window,details_component,window_model):value.deleteLater()
                controller.configure_tab({'title':'Local changes','preset':'files','source':'local'})
                action(None)
                action('reconcile')
                self.assertEqual(controller.data['rows'][0]['local_status'], 'added')
                action('drop_files',{'target':controller.data['change']['code'],'project':'files','urls':[QUrl.fromLocalFile(str(root/'fresh.txt')).toString()]})
                controller.open_view('pending')
                action(None)
                controller.set_value('view', 'change')
                action('files')
                controller.select_file('fresh.txt', True)
                menu_command('fileActionsButton', 'checkout_exclusive')
                action(None)
                self.assertEqual(controller.data['locks']['main\0fresh.txt'][0]['mode'], 'exclusive')
                action('shelve')
                action('submit')
                controller.open_view('submitted');action(None)
                tree_change = self.call('create_change', workspace='gui', description='Directory tree')
                tree_blob = self.upload(tree_change['code'], b'tree content')
                self.call('edit', change=tree_change['code'], edit_revision=0, chunk='tree', operations=[
                    {'path': path, 'blob': tree_blob} for path in ['assets/characters/hero.ma', 'assets/props/tool.ma', 'shots/Шот 01/layout.ma']])
                self.call('submit', change=tree_change['code'])
                action('refresh')
                click(tree_item('workspaceDisclosure:stream/main'))
                action(None)
                self.assertTrue(any(row.get('name') == 'assets' for row in controller.data['depot_tree']))
                click(tree_item('workspaceDisclosure:path/main/assets/'))
                action(None)
                directory_row = tree_item('workspaceTreeRow:path/main/assets/characters/')
                directory_row.forceActiveFocus()
                QTest.keyClick(window, Qt.Key_Right)
                action(None)
                self.assertTrue(any(row.get('path') == 'assets/characters/hero.ma' for row in controller.data['depot_tree']))
                resets = QSignalSpy(controller.depot_model.modelReset)
                controller._progress(controller._generation, {'state': 'complete'})
                QTest.qWait(5)
                self.assertEqual(resets.count(), 0)
                self.assertIs(tree_item('workspaceTreeRow:path/main/assets/characters/'), directory_row)
                signal = directory_row.metaObject().method(directory_row.metaObject().indexOfSignal('activated()'))
                activated = QSignalSpy(directory_row, signal)
                click(tree_item('workspaceTreeRow:path/main/assets/characters/'))
                action(None)
                self.assertEqual(activated.count(), 1)
                self.assertEqual(controller.data['files_prefix'],'assets/characters/')
                self.assertNotEqual(controller.data['active_tab'],'files')
                controller.open_view('files');action(None)
                self.assertEqual([row['path'] for row in controller.data['rows']], ['assets/characters/hero.ma'])
                disclosure = tree_item('workspaceDisclosure:path/main/assets/')
                point = disclosure.mapToScene(QPointF(disclosure.width() / 2, disclosure.height() / 2)).toPoint()
                device = QTest.createTouchDevice()
                QTest.touchEvent(window, device).press(0, point, window).commit()
                QTest.touchEvent(window, device).release(0, point, window).commit()
                QTest.qWait(50)
                action(None)
                self.assertFalse(any(row.get('path') == 'assets/characters/hero.ma' for row in controller.data['depot_tree']))
                selected_change = controller.data['change']['code']
                controller.open_view('submitted');action(None)
                controller.set_value('view', 'change')
                controller.set_value('prefix', '')
                QTest.qWait(20)
                changelist_tree = view.findChild(QObject, 'workspaceChangelistTree')
                depot_tree = tree_item('workspaceDepotTree')
                self.assertGreater(changelist_tree.mapToScene(QPointF()).x(), depot_tree.mapToScene(QPointF()).x() + depot_tree.width())
                click(tree_item('workspaceDisclosure:' + selected_change))
                action(None)
                self.assertNotIn(selected_change, controller.data['expanded_changes'])
                click(tree_item('workspaceDisclosure:' + selected_change))
                action(None)
                self.assertIn(selected_change, controller.data['expanded_changes'])
                self.assertTrue(any(row.get('parent') == selected_change and row.get('path') == 'fresh.txt' for row in controller.data['change_tree']))
                change_file = tree_item('workspaceChangeFile:' + selected_change + '/fresh.txt')
                checkbox = next(item for item in children(change_file) if item.property('checkState') is not None)
                click(checkbox)
                action(None)
                self.assertEqual(controller.data['selected'], ['fresh.txt'])
                action('select_change', {'change': selected_change})
                self.assertEqual(controller.data['prefix'], '')
                action('toggle_depot', {'id': 'path/main/assets/'})
                action('toggle_depot', {'id': 'path/main/assets/characters/'})
                controller.configure_tab({'title':'Local changes','preset':'files','source':'local'});action(None)
                action('get_latest')
                self.assertEqual(next(row for row in controller.data['rows'] if row['path'] == 'fresh.txt')['local_status'], 'clean')
                (root / 'fresh.txt').write_bytes(b'local modification')
                action('reconcile')
                self.assertEqual(next(row for row in controller.data['rows'] if row['path'] == 'fresh.txt')['local_status'], 'modified')
                action('history', {'path': 'fresh.txt', 'stream': 'main'})
                revision = controller.data['history'][0]
                action('preview', {'path': revision['path'], 'stream': revision['stream'], 'published_change': revision['change']})
                self.assertEqual(controller.data['preview'], 'native GUI fresh content')
                action('compare',{'mode':'local_head','path':'fresh.txt','stream':'main'})
                self.assertIn('-native GUI fresh content',controller.data['comparison']['text'])
                self.assertIn('+local modification',controller.data['comparison']['text'])
                action('compare',{'mode':'local_have','path':'fresh.txt','stream':'main'})
                self.assertIn('-native GUI fresh content',controller.data['comparison']['text'])
                self.assertIn('+local modification',controller.data['comparison']['text'])
                controller.open_view('submitted');action(None)
                controller.set_value('view', 'change')
                action('files')
                action('toggle_change', {'change': tree_change['code']})
                QTest.mouseMove(window, QPointF(5, 5).toPoint())
                QTest.qWait(20)
                for width in (1280, 760, 360):
                    window.resize(width, 800)
                    view.setWidth(width)
                    view.setHeight(800)
                    QTest.qWait(30)
                    self.assertLessEqual(view.childrenRect().width(), width + 1)
                    output = Path(__file__).resolve().parents[1] / '.screenshots/file-workspace'
                    output.mkdir(parents=True, exist_ok=True)
                    window.grabWindow().save(str(output / ('handler-' + str(width) + '.png')))
                self.assertEqual(application.errors, [])
                self.assertEqual(sorted(set(warnings)), [])
                menu_command('workspaceViewsButton','new_tab')
                tab_editor=view.findChild(QObject,'workspaceTabEditor')
                deadline=monotonic()+2
                while not tab_editor.property('opened') and monotonic()<deadline:QTest.qWait(5)
                self.assertTrue(tab_editor.property('opened'))
                title=next(item for item in children(tab_editor.property('contentItem')) if item.objectName()=='workspaceTabTitle')
                title.forceActiveFocus()
                for character in 'UI history':QTest.keyClick(window,character)
                preset=next(item for item in children(tab_editor.property('contentItem')) if item.objectName()=='workspaceTabPreset')
                preset.forceActiveFocus()
                QTest.keyClick(window,Qt.Key_Home)
                for _ in range(3):QTest.keyClick(window,Qt.Key_Down)
                QTest.keyClick(window,Qt.Key_Return)
                tab_editor.accept();action(None)
                custom=next(tab for tab in controller.data['tabs'] if tab['title']=='UI history')
                self.assertEqual(custom['kind'],'history')
                self.assertEqual(controller.data['active_tab'],custom['id'])
                controller.move_tab(-1)
                self.assertIn(custom,controller.data['tabs'])
                controller.close_tab(custom['id']);action(None)
                self.assertNotIn(custom,controller.data['tabs'])
                controller.open_view('files'); action(None)
                controller.set_value('view','local'); controller.set_value('prefix',''); action('files')
                controller.select_loaded('files',False)
                controller.select_file('fresh.txt',True)
                self.assertTrue(controller.data['selection_ids'])
                window.resize(1280,900);view.setWidth(1280);QTest.qWait(20)
                menu_command('fileActionsButton','revision_selected')
                revision_dialog=view.findChild(QObject,'workspaceGetRevisionDialog')
                self.assertTrue(revision_dialog.property('opened'))
                self.assertEqual(revision_dialog.property('scope'),'selection')
                self.assertFalse(revision_dialog.property('force'))
                revision_dialog.setProperty('selector','file_revision')
                revision_dialog.setProperty('value','1')
                QTest.qWait(30)
                force=next(item for item in children(revision_dialog.property('contentItem')) if item.objectName()=='workspaceRevisionForce')
                click(force)
                output=Path(__file__).resolve().parents[1]/'.screenshots/file-workspace'
                output.mkdir(parents=True,exist_ok=True)
                window.grabWindow().save(str(output/'handler-get-revision-click.png'))
                self.assertTrue(revision_dialog.property('force'),f'visible={force.isVisible()}, size={force.width(),force.height()}, scene={force.mapToScene(QPointF())}, checked={force.property("checked")}')
                for width in (520,1280):
                    window.resize(width,900);view.setWidth(width);QTest.qWait(10)
                    self.assertLessEqual(revision_dialog.property('width'),width)
                    output=Path(__file__).resolve().parents[1]/'.screenshots/file-workspace'
                    output.mkdir(parents=True,exist_ok=True)
                    window.grabWindow().save(str(output/f'handler-get-revision-{width}.png'))
                revision_dialog.accept();action(None)
                self.assertEqual((root/'fresh.txt').read_bytes(),b'native GUI fresh content')
                original_root=controller.data['root']
                controller.set_value('setup',True)
                controller.set_value('mappings',json.dumps([{'stream':'main','source':'...','target':'...','writable':True}]))
                QTest.qWait(40)
                def mapping_field(item):
                    if item.objectName()=='workspaceMappingSource:0':return item
                    for child in item.childItems():
                        found=mapping_field(child)
                        if found:return found
                source_field=mapping_field(window.contentItem())
                self.assertIsNotNone(source_field)
                click(source_field)
                self.app.clipboard().setText('assets/...')
                QTest.keyClick(window,Qt.Key_A,Qt.ControlModifier)
                QTest.keyClick(window,Qt.Key_V,Qt.ControlModifier);QTest.qWait(20)
                self.assertEqual(json.loads(controller.data['mappings'])[0]['source'],'assets/...')
                self.assertTrue(source_field.hasActiveFocus(),'Editing mappings retains keyboard focus')
                action('workspace_preview',{'paths':[{'stream':'main','path':'assets/example.txt'}]})
                self.assertEqual(controller.data['mapping_preview']['items'][0]['local_path'],'example.txt')
                controller.set_value('root','D:/cancelled-draft')
                controller.set_value('setup',False);QTest.qWait(30)
                self.assertEqual(controller.data['root'],original_root)
                self.assertEqual(sorted(set(warnings)),[])
        finally:
            controller.shutdown()
            pool.exit()
            pool.deleteLater()
            window.close()
            view.setParentItem(None)
            view.deleteLater()
            window.deleteLater()
            controller.deleteLater()
            application.deleteLater()
            component.deleteLater()
            theme.deleteLater()
            theme_component.deleteLater()
            engine.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
            QTest.qWait(10)

    def test_search_tabs_read_managed_records_with_stale_or_missing_client_metadata(self):
        from thlib import tactic_classes as tc
        from thlib.ui.controllers.search_runtime import SearchRuntimeMixin
        from thlib.side.client.tactic_client_lib.tactic_server_stub import TacticServerStub
        from xmlrpc.client import Fault
        from tactic_stream.server.search_configuration import search_configuration_request

        project = tc.Project({'code': 'files', 'name': 'Files', 'type': 'file_project'})
        project.get_all_search_types([], [], '', [])
        artist = transfers.FileTransferTest.writer(self)
        self.call('create_depot', code='second')
        with (self.http() as url,
              patch.object(env_mode, 'current_path', self.temp.name)):
            stub = TacticServerStub(server=url, project='files', ticket=self.token, protocol='xmlrpc')
            with stub.server, patch.object(tc, 'server_start', return_value=stub):
                for projects in ({'files': project}, {}):
                    with self.subTest(projects=bool(projects)), patch.object(env_inst, 'projects', projects):
                        if projects:
                            objects, info, _stype = SearchRuntimeMixin._query_sobjects(
                                'file_project/depot', 'files', (), [], 1, 1, bypass_cache=True)
                        else:
                            objects, info = tc.get_sobjects('file_project/depot', project_code='files',
                                limit=1, offset=1, include_total_count=False, include_progress=True)
                            objects = list(objects.values())
                        self.assertEqual([item.get_code() for item in objects], ['second'])
                        self.assertEqual(info['total_sobjects_query_count'], 2)
                        self.assertIsNone(info['total_sobjects_count'])
                        objects, info = tc.get_sobjects('file_project/depot', project_code='files',
                            filters=[['code', '=', 'main']], include_snapshots=False)
                        self.assertEqual([item.get_code() for item in objects.values()], ['main'])
                        self.assertEqual(info['total_sobjects_query_count'], 1)
                        hydrated, payload = tc.get_sobjects('file_project/depot', project_code='files',
                            filters=[['code', '=', 'main']], compressed_return=False,
                            include_info=False, return_payload=True)
                        self.assertEqual([item.get_code() for item in hydrated.values()], ['main'])
                        self.assertEqual(payload['sobjects_list'][0]['code'], 'main')
                        self.assertIsNone(payload['total_sobjects_query_count'])
                from pyasm.biz.file_project import TABLES
                with patch.object(env_inst, 'projects', {'files': project}):
                    for kind in TABLES:
                        with self.subTest(kind=kind):
                            objects, info, _stype = SearchRuntimeMixin._query_sobjects(
                                'file_project/' + kind, 'files', (), [], 20, 0, bypass_cache=True)
                            self.assertIsInstance(objects, list)
                            self.assertIsInstance(info['total_sobjects_query_count'], int)
                with self.assertRaises(Fault) as denied:
                    tc.get_sobjects('file_project/depot?project=admin', project_code='files')
                self.assertNotEqual(denied.exception.faultCode, 200)
            stub = TacticServerStub(server=url, project='files', ticket=artist['ticket'], protocol='xmlrpc')
            with stub.server, patch.object(tc, 'server_start', return_value=stub), patch.object(env_inst, 'projects', {'files': project}):
                with patch.object(stub, 'execute_python_script', wraps=stub.execute_python_script) as query:
                    with self.assertRaises(Fault) as denied:
                        SearchRuntimeMixin._query_sobjects('file_project/depot', 'files', (), [], 20, 0, bypass_cache=True)
                    query.assert_called_once()
                self.assertEqual(denied.exception.faultCode, 403)
            with self.context():
                page = search_configuration_request('query', {
                    'search_type': 'file_project/depot', 'limit': 1, 'offset': 1, 'include_total': True})
                self.assertEqual([row['code'] for row in page['records']], ['second'])
                self.assertEqual(page['total'], 2)

    def test_real_project_selection_keeps_search_metadata_and_opens_file_dock(self):
        from thlib import tactic_classes as tc
        from thlib.ui.controller import ApplicationController

        project = tc.Project({'code': 'files', 'name': 'Files', 'type': 'file_project'})
        classic = tc.Project({'code': 'classic', 'name': 'Classic', 'type': 'cg'})
        classic.get_all_search_types([], [], '', [])
        pool = ThreadsPool(1)
        pool.start()
        application = controller = None
        errors = []
        try:
            with (self.http() as url,
                  patch.object(env_mode, 'current_path', self.temp.name),
                  patch.object(env_inst, 'projects', {'files': project, 'classic': classic}),
                  patch.object(env_inst, 'current_project', None),
                  patch.object(env_inst, 'logins', {}),
                  patch.object(env_inst, 'commit_pool', pool),
                  patch.object(env_inst, 'server_pool', pool),
                  patch.object(env_inst, 'exit_pools'),
                  patch.object(env_server, 'get_server_presets', return_value={}),
                  patch.object(env_server, 'get_server', return_value=url),
                  patch.object(env_server, 'get_ticket', return_value=self.token),
                  patch.object(env_server, 'get_user', return_value='admin'),
                  patch.object(env_server, 'get_proxy', return_value={'enabled': False})):
                application = ApplicationController()
                controller = FileWorkspaceController(application)
                with (patch.object(application, 'open_window'),
                      patch.object(application, '_report_error_payload', side_effect=lambda *args: errors.append(args))):
                    from thlib.side.client.tactic_client_lib.tactic_server_stub import TacticServerStub
                    stub = TacticServerStub(server=url,project='files',ticket=self.token,protocol='xmlrpc')
                    with stub.server, patch.object(tc, 'server_start', return_value=stub):
                        prepared = application._prepare_project_selection('files', 'Files')
                        policy = project.get_stypes()['file_project/depot'].get_info()['__record_read__']
                        self.assertTrue(policy['available'])
                        self.assertTrue(policy['readonly'])
                        objects, info = tc.get_sobjects('file_project/depot', project_code='files',
                                                       limit=2, include_snapshots=False)
                        self.assertEqual([item.get_code() for item in objects.values()], ['main'])
                        self.assertEqual(info['total_sobjects_query_count'],1)
                        table = tc.get_table_layout('file_project/depot',
                            search_keys=[item.get_search_key() for item in objects.values()], project_code='files')
                        self.assertTrue(table['columns'])
                    application._apply_cached_project_shell(*prepared)
                    application._apply_selected_project(*prepared)
                    finished=threading.Event()
                    if controller._worker:
                        controller._worker.result.connect(lambda *_args:finished.set(),Qt.DirectConnection)
                        controller._worker.error.connect(lambda *_args:finished.set(),Qt.DirectConnection)
                    deadline = monotonic() + 20
                    while (controller.busy or controller._read_worker is not None) and monotonic() < deadline:
                        QTest.qWait(10)
                        finished.wait(.01)
                    self.assertFalse(controller.busy)
                    self.assertEqual(errors, [])
                    self.assertEqual(controller.data['error'], '')
                    self.assertTrue(controller.enabled)
                    self.assertIn('main', [row['code'] for row in controller.data['streams']])
                    self.assertTrue(controller.data['depots'])
                    self.assertEqual(application.navigation_model.rowCount(), 0)
                    self.assertEqual(application._sessions, {})
                    application._apply_selected_project('classic', 'Classic', [], classic)
                    self.assertFalse(controller.enabled)
                    self.assertEqual(application.current_project_code, 'classic')
        finally:
            with (patch.object(env_mode, 'current_path', self.temp.name),
                  patch.object(env_inst, 'exit_pools')):
                if controller:
                    controller.shutdown()
                    controller.deleteLater()
                if application:
                    application.shutdown()
                    application.deleteLater()
            pool.exit()
            pool.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)

    def test_qml_english_russian_and_light_dark_keep_selection(self):
        application = Application()
        controller = FileWorkspaceController(application)
        controller._enabled = True
        change = self.call('create_change', workspace='work', description='Server label')
        controller._data.update(change=change, changes=[change], workspace='work', root='D:/work/niki_friends', stream='main',
                                workspaces=[{'code':'work'}], streams=[{'code':'main'}], description='Server label',
                                rows=[{'path': 'src/local.txt', 'local_status': 'modified', 'server_status': 'current', 'number':2}]
                                + [{'path':'scenes/shot_%04d.ma' % i,'local_status':'clean','server_status':'current','number':1} for i in range(199)],
                                selected=['src/local.txt'])
        controller._data['change_children'] = {change['code']: {'items': controller._data['rows']}}
        controller._data['expanded_changes'] = [change['code']]
        controller._tree(controller._data)
        controller.stateChanged.emit()
        engine = QQmlEngine()
        warnings = []
        engine.warnings.connect(lambda items: warnings.extend(item.toString() for item in items))
        for name, value in qml_icon_bindings(HANDLER, engine).items():
            engine.rootContext().setContextProperty(name, value)
        theme_component = QQmlComponent(engine, QUrl.fromLocalFile(str(QML / 'Theme.qml')))
        theme = theme_component.createWithInitialProperties({'dark': True})
        component = QQmlComponent(engine, QUrl.fromLocalFile(str(QML / 'FileWorkspaceView.qml')))
        view = component.createWithInitialProperties({'theme': theme, 'controller': controller})
        self.assertIsNotNone(view, str(component.errors()))
        window = QQuickWindow()
        view.setParentItem(window.contentItem())
        translator = CatalogTranslator(HANDLER / 'thlib/ui/translations/ru.json')
        try:
            for language in ('en', 'ru'):
                if language == 'ru':
                    self.app.installTranslator(translator)
                    engine.retranslate()
                for dark in (True, False):
                    theme.setProperty('dark', dark)
                    window.setColor(theme.property('workspace'))
                    for width in (1280, 360):
                        window.resize(width, 800)
                        view.setWidth(width)
                        view.setHeight(800)
                        window.show()
                        QTest.qWait(30)
                        self.assertLessEqual(view.childrenRect().width(), width + 1)
                        for item in view.findChildren(QQuickItem):
                            if item.property('contentColor') is not None and item.isVisible():
                                self.assertLessEqual(item.width(), width - 24, str(item.property('text')))
                        self.assertEqual(controller.data['selected'], ['src/local.txt'])
                        output = Path(__file__).resolve().parents[1] / '.screenshots/file-workspace'
                        output.mkdir(parents=True, exist_ok=True)
                        window.grabWindow().save(str(output / ('handler-%s-%s-%s.png' % (language, 'dark' if dark else 'light', width))))
            self.assertEqual(sorted(set(warnings)), [])
            controller._data.update(setup=True, busy=False)
            controller.stateChanged.emit()
            QTest.qWait(30)
            controller._data.update(busy=True, progress={'state': 'waiting'})
            controller.stateChanged.emit()
            QTest.qWait(30)
            stop = next(item for item in view.findChildren(QQuickItem)
                        if item.isVisible() and item.property('text') in ('Stop waiting', 'Прекратить ожидание'))
            self.assertTrue(stop.isEnabled())
            QTest.mouseClick(window, Qt.LeftButton, pos=stop.mapToScene(QPointF(stop.width() / 2, stop.height() / 2)).toPoint())
            self.assertTrue(controller._cancel.is_set())
            controller._data.update(busy=False, setup=False)
            controller.stateChanged.emit()
        finally:
            self.app.removeTranslator(translator)
            controller.shutdown()
            window.close()
            view.setParentItem(None)
            view.deleteLater()
            window.deleteLater()
            controller.deleteLater()
            application.deleteLater()
            component.deleteLater()
            theme.deleteLater()
            theme_component.deleteLater()
            engine.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
            QTest.qWait(10)

