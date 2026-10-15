"""Owned QML probe for the reported Reconcile Ctrl+A hang."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QT_QUICK_BACKEND','software')
os.environ.setdefault('QSG_RENDER_LOOP','basic')
import json
from pathlib import Path
import time
from unittest.mock import patch
import test_handler_file_workspace_ui as native
from PySide6.QtCore import QUrl, QObject, QMetaObject, Qt, QCoreApplication, QEvent, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtTest import QTest
from thlib.ui.file_workspace import FileWorkspaceController
from thlib.environment import env_inst,env_mode,env_server

app=QGuiApplication.instance() or QGuiApplication([])
with patch.object(env_inst,'projects',{}),patch.object(env_mode,'current_path',os.environ['TEMP']),patch.object(env_server,'get_user',lambda:'admin'):
    application=native.Application();controller=FileWorkspaceController(application)
    controller._data.update(tabs=[{'id':'reconcile','kind':'files','title':'Reconcile','source':'local','icon':'file','reconcile_only':True}],active_tab='reconcile',view='local',workspace='work',stream='main',change={'code':'source','number':1,'description':'','state':'pending','owner':'admin','stream':'main','workspace':'work'},targets=[{'code':'target','number':2,'description':'','state':'pending','owner':'admin','stream':'main','workspace':'work'}],rows=[{'path':f'local/{index:04d}.txt','local_status':'modified' if index%2 else 'added','reconcile_action':'edit' if index%2 else 'add','server_status':'untracked','stream':'main','kind':'file','size':100} for index in range(1000)])
    engine=QQmlEngine();warnings=[]
    engine.warnings.connect(lambda rows:warnings.extend(row.toString() for row in rows))
    for name,value in native.qml_icon_bindings(native.HANDLER,engine).items():engine.rootContext().setContextProperty(name,value)
    tc=QQmlComponent(engine,QUrl.fromLocalFile(str(native.QML/'Theme.qml')));theme=tc.createWithInitialProperties({'dark':True})
    component=QQmlComponent(engine,QUrl.fromLocalFile(str(native.QML/'FileWorkspaceView.qml')))
    view=component.createWithInitialProperties({'theme':theme,'controller':controller})
    assert view is not None,str(component.errors())
    window=QQuickWindow();view.setParentItem(window.contentItem());window.resize(1280,900);view.setWidth(1280);view.setHeight(900);window.show();QTest.qWait(100)
    files=view.findChild(QObject,'workspaceFiles');QMetaObject.invokeMethod(files,'forceActiveFocus')
    timings=[];ticks=[];timer=QTimer();timer.setInterval(10);timer.timeout.connect(lambda:ticks.append(time.perf_counter()));timer.start()
    target=view.findChild(QObject,'workspaceTargetDialog');preview=target.findChild(QObject,'workspaceTargetPreview')
    for _ in range(3):
        before=time.perf_counter();QTest.keyClick(window,Qt.Key_A,Qt.ControlModifier);elapsed=time.perf_counter()-before
        assert elapsed<2,elapsed
        timings.append(elapsed)
        assert len(controller.data['selection_ids'])==1000
        assert controller.data['selection_query'] is None
        assert preview.property('count')==0,'Hidden preview must not build selected rows'
        QTest.qWait(20)
    target.setProperty('operation','apply_reconcile');target.setProperty('sourceChange','source')
    before=time.perf_counter();QMetaObject.invokeMethod(target,'open');QTest.qWait(30)
    assert time.perf_counter()-before<2
    assert target.property('targetStream')=='main'
    assert preview.property('count')==1000
    assert len(controller.data['selection_ids'])==1000
    QMetaObject.invokeMethod(target,'close');QTest.qWait(250)
    assert preview.property('count')==0
    assert len(controller.data['selection_ids'])==1000
    QMetaObject.invokeMethod(files,'forceActiveFocus');QTest.keyClick(window,Qt.Key_Escape)
    assert controller.data['selection_ids']==[]
    controller.set_value('name_filter','local/00');controller.set_value('status_filter','Modified');QTest.qWait(20)
    QMetaObject.invokeMethod(files,'forceActiveFocus');QTest.keyClick(window,Qt.Key_A,Qt.ControlModifier)
    assert len(controller.data['selection_ids'])==50
    assert all(row['local_status']=='modified' and row['path'].startswith('local/00') for row in controller.data['selection_records'].values())
    assert ticks
    timer.stop()
    assert not warnings,warnings
    print(json.dumps({'ctrlASeconds':timings,'loaded':1000,'filtered':50,'preview':1000,'heartbeat':len(ticks)}),flush=True)
    controller.shutdown();window.close()
    for value in (view,window,controller,application,theme,component,tc,engine):value.deleteLater()
    QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)
