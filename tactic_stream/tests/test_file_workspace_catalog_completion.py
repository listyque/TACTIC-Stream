"""Native callbacks, real graph provenance, bounded trees and physical paths."""
from pathlib import Path
from unittest.mock import patch
import threading
import unittest
from pyasm.command import Trigger
from pyasm.common import Container
from pyasm.search import Search, SearchType
from test_file_project import FileProjectFixture
from test_file_workspace_completion import FileWorkspaceCompletionTest


class DynamicVersionTrigger(Trigger):
    paths = []

    def execute(self):
        row = self.get_caller()
        self.paths.append(row.get_json_value('data')['path'])
        if len(self.paths) == 1:
            trigger = SearchType.create('sthpw/trigger')
            trigger.set_value('event', 'insert|file_project/version|number', temp=True)
            trigger.set_value('mode', 'same process,same transaction', temp=True)
            trigger.set_value('class_name', 'test_file_workspace_catalog_completion.LateColumnTrigger', temp=True)
            Trigger.append_static_trigger(trigger)


class LateColumnTrigger(Trigger):
    counts = []

    def execute(self):
        self.counts.append(Search('file_project/version').get_count())


class FileWorkspaceCatalogCompletionTest(FileWorkspaceCompletionTest):
    def test_catalog_and_graph_real_qml_narrow_theme_and_restart_preferences(self):
        from PySide6.QtCore import QUrl, QCoreApplication, QEvent
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtQml import QQmlEngine, QQmlComponent
        from PySide6.QtQuick import QQuickWindow
        from PySide6.QtTest import QTest
        from thlib.ui.file_workspace import FileWorkspaceController,initial_state
        from test_handler_file_workspace_ui import Application,HANDLER,QML,qml_icon_bindings
        from thlib.side.client.tactic_client_lib.file_transfer import FileTransferClient
        self.publish({'a':b'graph base'})
        self.call('create_stream',code='dev',depot='main',parent='main')
        app=Application();controller=FileWorkspaceController(app);controller._enabled=True
        engine=QQmlEngine();warnings=[]
        engine.warnings.connect(lambda errors:warnings.extend(error.toString() for error in errors))
        for name,value in qml_icon_bindings(HANDLER,engine).items():engine.rootContext().setContextProperty(name,value)
        theme_component=QQmlComponent(engine,QUrl.fromLocalFile(str(QML/'Theme.qml')))
        theme=theme_component.createWithInitialProperties({'dark':True})
        component=QQmlComponent(engine,QUrl.fromLocalFile(str(QML/'FileWorkspaceView.qml')))
        view=component.createWithInitialProperties({'theme':theme,'controller':controller})
        self.assertIsNotNone(view,str(component.errors()))
        window=QQuickWindow();view.setParentItem(window.contentItem());window.show()
        try:
            with self.http() as url:
                client=FileTransferClient(url,self.token,'files')
                for source in ('workspaces','streams','depots','stream_graph','storage'):
                    tab=next(row for row in controller.view_presets if row.get('source')==source)
                    controller._data['tabs'].append(tab);controller._data['active_tab']=tab['id']
                    controller._data=controller._execute(client,controller.data,Path(self.temp.name)/'catalog-cache','catalog_page',{'source':source},threading.Event())
                    controller.stateChanged.emit();QTest.qWait(30)
                    for dark in (True,False):
                        theme.setProperty('dark',dark)
                        for width in (1280,360):
                            window.resize(width,720);view.setWidth(width);view.setHeight(720);QTest.qWait(40)
                            self.assertLessEqual(view.childrenRect().width(),width+1)
                            self.assertGreater(view.height(),0)
                    if source=='stream_graph':
                        self.assertEqual(len(controller.data['graph_nodes']),2)
                        controller.set_value('graph_zoom',1.4)
                        controller._capture_view();controller._save_tabs()
                        from thlib.environment import env_read_config
                        saved=env_read_config(unique_id=controller._tabs_key(),filename='tabs',long_abs_path=True)
                        self.assertEqual(saved['tab_states'][tab['id']]['graph_zoom'],1.4)
                self.assertFalse(warnings,warnings)
        finally:
            controller.shutdown();window.close()
            for value in (view,controller,theme,component,theme_component,engine,window,app):value.deleteLater()
            QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)

    def test_native_dynamic_callbacks_keep_per_file_work_and_sequential_visibility(self):
        DynamicVersionTrigger.paths=[];LateColumnTrigger.counts=[]
        self.api.dispatch('insert',(self.ticket,'config/trigger',{'code':'dynamic-version',
            'event':'insert|file_project/version|data','class_name':'test_file_workspace_catalog_completion.DynamicVersionTrigger',
            'mode':'same process,same transaction'}))
        change=self.change();blob=self.upload(change)
        self.call('edit',change=change,edit_revision=0,chunk='dynamic',operations=[{'path':path,'blob':blob} for path in ['a','b','c']])
        self.assertEqual(DynamicVersionTrigger.paths,['a','b','c'])
        self.assertEqual(LateColumnTrigger.counts,[1,2,3])

    def test_read_submitted_change_files_uses_native_catalog(self):
        change=self.publish({'a.txt':b'actual submitted bytes'})
        page=self.call('inspect_change_files',change=change,limit=1)
        self.assertEqual([row['path'] for row in page['items']],['a.txt'])
        self.assertEqual(page['info']['state'],'submitted')
        branch=self.call('create_stream',code='read-branch',depot='main',parent='main')
        page=self.call('inspect_change_files',change=branch['baseline_change'],limit=1)
        self.assertEqual(page['items'][0]['file']['sha256'],page['items'][0]['base']['sha256'])
        self.assertEqual(page['info']['waiting_uploads'],0)

    def test_stream_graph_uses_real_branch_and_merge_changes_and_rejects_stale_page(self):
        from test_file_change import FileChangeTest
        base=self.publish({'a':b'base'})
        self.call('create_stream',code='branch',depot='main',parent='main')
        graph=self.call('stream_graph')
        self.assertEqual(graph['edges'],[{'source':'main','target':'branch','kind':'branch','change':base}])
        changed=self.publish({'b':b'new'})
        self.call('create_workspace',code='branch-work',stream='branch',local_root='D:/test/branch')
        draft=self.call('create_change',workspace='branch-work')['code']
        job=self.call('merge_begin',change=draft,source_stream='main',edit_revision=0,request_id='merge')
        while True:
            job=self.call('integration_next',change=draft,integration=job['integration'],edit_revision=job['edit_revision'],after=job['after'],request_id='next-'+str(job['after']))
            if job['complete']:break
        self.call('integration_finish',change=draft,integration=job['integration'],edit_revision=job['edit_revision'],request_id='finish')
        self.call('submit',change=draft)
        result=self.call('stream_graph')
        self.assertIn({'source':'main','target':'branch','kind':'merge','change':changed},result['edges'])
        with self.assertRaisesRegex(ValueError,'Graph changed'):
            self.call('stream_graph',heads=graph['heads'])
        with self.assertRaises(ValueError):
            self.call('stream_graph',edge_after='../1/x')

    def test_restore_seeks_deep_off_page_directories_without_paging_siblings(self):
        from thlib.ui.file_workspace import FileWorkspaceController,initial_state
        from thlib.ui.file_workspace_tree_state import restore_directories,trim_tree,TREE_LIMIT
        from thlib.side.client.tactic_client_lib.file_transfer import FileTransferClient
        root=Path(self.temp.name)/'root';cache=Path(self.temp.name)/'tree-cache';cache.mkdir()
        change=self.change();blob=self.upload(change)
        paths=['folder%04d/x' % index for index in range(350)]+['zzzz/deep/leaf.txt']
        self.call('edit',change=change,edit_revision=0,chunk='folders',operations=[{'path':path,'blob':blob} for path in paths]);self.call('submit',change=change)
        state=initial_state();state.update(workspace='work',root=str(root),stream='main',depot_expanded=['stream/main','path/main/zzzz/','path/main/zzzz/deep/'])
        with self.http() as url:
            client=FileTransferClient(url,self.token,'files')
            FileWorkspaceController._execute(client,state,cache,'refresh',{},threading.Event())
        self.assertIn('path/main/zzzz/deep/leaf.txt',{row['id'] for row in state['depot_tree']})
        self.assertLess(len(state['depot_tree']),220)
        tree=[{'id':'stream/main','depth':1}]+[{'id':str(index),'depth':2} for index in range(TREE_LIMIT+200)]
        self.assertTrue(trim_tree(tree,str(TREE_LIMIT+199)));self.assertEqual(len(tree),TREE_LIMIT)
        self.assertEqual(tree[-1]['id'],str(TREE_LIMIT+199))

    def test_physical_deep_unicode_and_empty_directory_index(self):
        from thlib.side.client.tactic_client_lib.file_workspace import reconcile_workspace,workspace_files,local_browse
        from thlib.side.client.tactic_client_lib.file_transfer import FileTransferClient
        root=Path(self.temp.name)/'deep'
        directory=root
        for index in range(12):directory=directory/('Каталог_%02d_—_日本語'%index)
        directory.mkdir(parents=True);file=directory/'long name — 空.txt';file.write_bytes(b'physical unicode content')
        (directory/'Empty — 空').mkdir()
        self.assertGreater(len(str(file)),260)
        self.assertEqual(list(workspace_files(root)),[file])
        with self.http() as url:
            reconcile_workspace(FileTransferClient(url,self.token,'files'),'work',root,Path(self.temp.name)/'local.sqlite')
        page=local_browse(Path(self.temp.name)/'local.sqlite',directory.relative_to(root).as_posix()+'/')
        self.assertEqual({row['kind'] for row in page['items']},{'file','directory'})
