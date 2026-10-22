"""Owned Windows pointer/drag cancellation and desktop launch boundaries."""
import argparse
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests'),'D:/grav/Tactic Stream/TH']


def native_drag():
    os.environ['QT_QPA_PLATFORM']='windows'
    os.environ.setdefault('QT_QUICK_CONTROLS_STYLE','Material')
    from PySide6.QtCore import QUrl,QPoint,QEvent,QCoreApplication,Qt
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlEngine,QQmlComponent
    from PySide6.QtQuick import QQuickWindow
    from PySide6.QtTest import QTest,QSignalSpy
    from thlib.ui.icon_font import qml_icon_bindings
    app=QGuiApplication.instance() or QGuiApplication([])
    engine=QQmlEngine();warnings=[]
    engine.warnings.connect(lambda rows:warnings.extend(row.toString() for row in rows))
    handler=Path('D:/grav/Tactic Stream/TH');qml=handler/'thlib/ui/qml'
    for name,value in qml_icon_bindings(handler,engine).items():engine.rootContext().setContextProperty(name,value)
    theme_component=QQmlComponent(engine,QUrl.fromLocalFile(str(qml/'Theme.qml')))
    theme=theme_component.createWithInitialProperties({'dark':True})
    component=QQmlComponent(engine)
    component.setData(b'''import QtQuick
import "."
FileWorkspaceTreeRow {
    property bool began:false
    property int outcome:-1
    Drag.onDragStarted:began=true
    Drag.onDragFinished:action=>outcome=action
}''',QUrl.fromLocalFile(str(qml/'OwnedPlatformProbe.qml')))
    source=component.createWithInitialProperties({'theme':theme,'row':{'id':'owned/source','kind':'directory','depth':0,'path':'owned/'},'caption':'Owned drag source','dragData':{'application/x-tactic-file-workspace':'{"scope":"depot","path":"owned/"}'}})
    target_component=QQmlComponent(engine,QUrl.fromLocalFile(str(qml/'FileWorkspaceTreeRow.qml')))
    target=target_component.createWithInitialProperties({'theme':theme,'row':{'id':'owned/target','kind':'change','depth':0,'number':1},'caption':'Owned drop target','acceptsDrop':True})
    assert source and target, str(component.errors())+str(target_component.errors())
    window=QQuickWindow();window.setFlags(window.flags()|Qt.WindowStaysOnTopHint);window.setTitle('TACTIC owned native drag test');window.resize(700,240)
    window.setColor(theme.property('workspace'))
    source.setParentItem(window.contentItem());source.setX(20);source.setY(30);source.setWidth(300);source.setHeight(40)
    source.setProperty('focused',True)
    target.setParentItem(window.contentItem());target.setX(370);target.setY(120);target.setWidth(300);target.setHeight(40)
    dropped=QSignalSpy(target.dropped);window.show();window.requestActivate();QTest.qWait(150)
    pressed=QSignalSpy(source.selectedByUser);drag_requested=QSignalSpy(source.dragRequested)
    directory=ROOT/'.screenshots/file-workspace';directory.mkdir(parents=True,exist_ok=True)
    window.grabWindow().save(str(directory/'owned-native-drag.png'))
    user=ctypes.windll.user32;handle=int(window.winId())
    user.GetForegroundWindow.restype=wintypes.HWND
    user.GetWindowThreadProcessId.argtypes=(wintypes.HWND,ctypes.POINTER(wintypes.DWORD))
    user.ShowWindow.argtypes=(wintypes.HWND,ctypes.c_int)
    user.SetForegroundWindow.argtypes=(wintypes.HWND,)
    user.WindowFromPoint.argtypes=(wintypes.POINT,)
    user.WindowFromPoint.restype=wintypes.HWND
    user.ClientToScreen.argtypes=(wintypes.HWND,ctypes.POINTER(wintypes.POINT))
    user.PostMessageW.argtypes=(wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM)
    user.GetWindowDpiAwarenessContext.argtypes=(wintypes.HWND,)
    user.GetWindowDpiAwarenessContext.restype=wintypes.HANDLE
    user.SetThreadDpiAwarenessContext.argtypes=(wintypes.HANDLE,)
    user.SetThreadDpiAwarenessContext.restype=wintypes.HANDLE
    class MouseInput(ctypes.Structure):
        _fields_=[('dx',wintypes.LONG),('dy',wintypes.LONG),('data',wintypes.DWORD),('flags',wintypes.DWORD),('time',wintypes.DWORD),('extra',ctypes.c_size_t)]
    class InputUnion(ctypes.Union):
        _fields_=[('mouse',MouseInput)]
    class Input(ctypes.Structure):
        _fields_=[('type',wintypes.DWORD),('value',InputUnion)]
    user.SendInput.argtypes=(wintypes.UINT,ctypes.POINTER(Input),ctypes.c_int)
    assert ctypes.sizeof(Input)==40
    def button(flags):
        value=Input(0,InputUnion(mouse=MouseInput(0,0,0,flags,0,0)))
        if user.SendInput(1,ctypes.byref(value),ctypes.sizeof(value))!=1:
            raise RuntimeError('Native pointer input was rejected by this desktop session')
    dpi_context=user.GetWindowDpiAwarenessContext(handle)
    user.ShowWindow(handle,5);user.SetForegroundWindow(handle);QTest.qWait(150)
    original=wintypes.POINT();user.GetCursorPos(ctypes.byref(original))
    def physical(x,y):
        previous=user.SetThreadDpiAwarenessContext(dpi_context)
        try:
            point=wintypes.POINT(round(x*window.devicePixelRatio()),round(y*window.devicePixelRatio()))
            assert user.ClientToScreen(handle,ctypes.byref(point))
            return QPoint(point.x,point.y)
        finally:
            if previous:user.SetThreadDpiAwarenessContext(previous)
    start=physical(130,50);end=physical(500,140)
    failure=[];input_state={};finished=threading.Event()
    def foreground_owned():
        process=wintypes.DWORD();user.GetWindowThreadProcessId(user.GetForegroundWindow(),ctypes.byref(process))
        return process.value==os.getpid()
    def input_sequence():
        previous=user.SetThreadDpiAwarenessContext(dpi_context)
        try:
            process=wintypes.DWORD()
            user.GetWindowThreadProcessId(user.WindowFromPoint(wintypes.POINT(start.x(),start.y())),ctypes.byref(process))
            assert process.value==os.getpid(),f'Pointer target did not belong to the test; no input sent (visible={bool(user.IsWindowVisible(handle))}, window={window.geometry()}, ratio={window.devicePixelRatio()}, point={start}, target_pid={process.value}, test_pid={os.getpid()})'
            user.SetCursorPos(start.x(),start.y());button(0x0002)
            input_state['pressed']=True
            time.sleep(.15)
            input_state['left_down']=bool(user.GetAsyncKeyState(1)&0x8000)
            if not input_state['left_down']:
                raise RuntimeError('Native pointer input is unavailable in this test session; run this probe in an interactive desktop.')
            for step in range(1,9):
                x,y=start.x()+(end.x()-start.x())*step//8,start.y()+(end.y()-start.y())*step//8
                user.GetWindowThreadProcessId(user.WindowFromPoint(wintypes.POINT(x,y)),ctypes.byref(process))
                assert process.value==os.getpid(),'Pointer target changed; test stopped'
                user.SetCursorPos(x,y)
                time.sleep(.035)
            assert user.PostMessageW(handle,0x0100,0x1B,0)
            assert user.PostMessageW(handle,0x0101,0x1B,0)
            time.sleep(.1)
        except Exception as error:failure.append(str(error))
        finally:
            if input_state.get('pressed'):
                try:button(0x0004)
                except RuntimeError as error:failure.append(str(error))
            if previous:user.SetThreadDpiAwarenessContext(previous)
            finished.set()
    thread=threading.Thread(target=input_sequence);thread.start()
    try:
        deadline=time.monotonic()+8
        while (not finished.is_set() or source.property('outcome')==-1) and not failure and time.monotonic()<deadline:QTest.qWait(20)
        thread.join(timeout=2)
        assert not thread.is_alive() and not failure,failure
        assert source.property('began'),f'Native source drag did not begin: {input_state}, selections={pressed.count()}, requests={drag_requested.count()}'
        assert source.property('outcome')==0,'Escape did not return IgnoreAction'
        assert dropped.count()==0,'Cancelled drag reached a drop handler'
        assert not warnings,warnings
        return {'native_pointer_drag':True,'escape_cancelled':True,'drops_after_escape':dropped.count()}
    finally:
        current=wintypes.POINT();user.GetCursorPos(ctypes.byref(current))
        if (current.x,current.y)==(end.x(),end.y()):user.SetCursorPos(original.x,original.y)
        window.close()
        for value in (source,target,theme,component,target_component,theme_component,engine,window):value.deleteLater()
        QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)


def desktop_launches():
    from thlib.ui.file_workspace import initial_state
    from thlib.ui.file_workspace_files import execute_files
    with tempfile.TemporaryDirectory(prefix='tactic-owned-desktop-') as directory:
        root=Path(directory);file=root/('Owned '+uuid.uuid4().hex+' — 空.txt');file.write_bytes(b'Owned desktop application test. No edits.')
        state=initial_state();identity='workspace-path/'+file.name
        state.update(root=str(root),workspace='owned',view='local',selection_scope='workspace',
            selection_ids=[identity],selection_records={identity:{'path':file.name,'kind':'file','workspace':True}})
        env={**os.environ,'TACTIC_OWNED_FOLDER':str(root),'TACTIC_OWNED_FILE':file.name}
        def shell(script):
            result=subprocess.run(['powershell','-NoProfile','-Command',script],env=env,capture_output=True,text=True,timeout=10)
            if result.returncode:raise RuntimeError('Owned desktop probe failed')
            return result.stdout.strip()
        count=shell("$shell=New-Object -ComObject Shell.Application; @($shell.Windows() | Where-Object { $_.LocationURL -and ([Uri]$_.LocationURL).LocalPath.TrimEnd('\\') -eq $env:TACTIC_OWNED_FOLDER }).Count")
        assert count=='0','Owned test folder was already open'
        execute_files(None,state,root/'cache','reveal_local',{},threading.Event())
        deadline=time.monotonic()+5;visible=False
        try:
            while time.monotonic()<deadline:
                count=shell("$shell=New-Object -ComObject Shell.Application; @($shell.Windows() | Where-Object { $_.LocationURL -and ([Uri]$_.LocationURL).LocalPath.TrimEnd('\\') -eq $env:TACTIC_OWNED_FOLDER }).Count")
                if count!='0':visible=True;break
                time.sleep(.1)
            assert visible,'Explorer did not expose the owned folder in this desktop session'
        finally:
            shell("$shell=New-Object -ComObject Shell.Application; @($shell.Windows()) | Where-Object { $_.LocationURL -and ([Uri]$_.LocationURL).LocalPath.TrimEnd('\\') -eq $env:TACTIC_OWNED_FOLDER } | ForEach-Object { $_.Quit() }")
        size=wintypes.DWORD(2048);executable=ctypes.create_unicode_buffer(size.value)
        code=ctypes.windll.shlwapi.AssocQueryStringW(0,2,'.txt',None,executable,ctypes.byref(size))
        default_checked=False
        if code==0 and Path(executable.value).name.lower()=='notepad.exe' and shell("@(Get-Process Notepad -ErrorAction SilentlyContinue).Count")=='0':
            execute_files(None,state,root/'cache','open_local',{},threading.Event())
            deadline=time.monotonic()+5
            while time.monotonic()<deadline:
                count=shell("@(Get-Process Notepad -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle.Contains($env:TACTIC_OWNED_FILE) }).Count")
                if count=='1':default_checked=True;break
                time.sleep(.1)
            shell("Get-Process Notepad -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle.Contains($env:TACTIC_OWNED_FILE) } | ForEach-Object { [void]$_.CloseMainWindow() }")
            assert default_checked,'Owned Notepad document did not appear'
        assert file.read_bytes()==b'Owned desktop application test. No edits.'
        return {'explorer_owned_folder':visible,'default_application_checked':default_checked,
                'default_application_guard':'Only Notepad with no existing process is launched; other associations are preserved.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path);parser.add_argument('--mode',choices=('drag','desktop'),default='drag');args=parser.parse_args()
    if os.name!='nt':raise SystemExit('Windows qualification requires Windows')
    result=native_drag() if args.mode=='drag' else desktop_launches()
    text=json.dumps(result,indent=2)
    if args.output:args.output.write_text(text+'\n',encoding='utf-8')
    print(text)
