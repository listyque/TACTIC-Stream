"""Exercise native authoring and RPC lifecycles before replacing WebEngine."""
import ast,copy,importlib.util,json,os,sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[2];TH=Path('D:/code/th_codex')
os.environ.update(QT_QPA_PLATFORM='offscreen',QT_QUICK_BACKEND='software',QT_FONT_DPI='96');sys.path[:0]=[str(TH),str(ROOT/'tools/frame_admin')]
from PySide6.QtCore import QObject,Signal,QUrl,QPointF,QCoreApplication,QEvent,Qt
from PySide6.QtGui import QFont,QFontDatabase
from PySide6.QtQml import QQmlEngine,QQmlComponent
from PySide6.QtTest import QTest
from tests.qt_application import gui_test_application
from tests.profile_ui_responsiveness import frame
from tests.test_sidebar_editor_qml import SidebarEditorQmlTests
from thlib.environment import env_inst,env_server
from thlib import tactic_classes as tc
from thlib.ui.icon_font import qml_icon_bindings
from native_capture import controls,click,text,choose,snapshot
from thlib.ui import layout_editor as module
xml='<config><!--custom--><cards_example layout="sobject-layout" columns="12" collection="grid"><element name="title" title="Title" row="1" column="1" span="12" custom="kept"><display class="title"><bind>node.title</bind></display></element><extension value="kept"/></cards_example></config>'
blank='<config><blank layout="sobject-layout" columns="12" collection="grid"/></config>'
templates=[dict(name=name,xml=blank) for name in ('blank','continuous','cards','table')]
class Worker(QObject):
 result=Signal(object);error=Signal(object)
 def __init__(self,operation):super().__init__();self.operation=operation;self.cancelled=False
 def start(self):
  try:self.result.emit(self.operation())
  except Exception as error:self.error.emit(({'exception':error,'stacktrace':''},self))
 def cancel(self):self.cancelled=True
class Pool:
 is_stopped=False
 def __init__(self):self.workers=[]
 def add_task(self,operation):worker=Worker(operation);self.workers.append(worker);return worker
class Api:
 def __init__(self):self.xml=xml;self.revision='R1';self.calls=[];self.unknown=False
 def configuration(self):return dict(revision=self.revision,sources=[dict(id=1,xml=self.xml,priority=0)],layers=[],views=['cards_example'],layout_views=['cards_example'],layout_templates=templates,resolved={'configured':True})
 def execute(self,_function,arguments,**kwargs):
  self.calls.append(copy.deepcopy(arguments));assert kwargs['project']=='demo';assert kwargs['server'] is server
  if arguments['action']=='read':return dict(configuration=self.configuration(),sampleItems=[dict(kind='object',title='Asset',record={'name':'Asset','__search_key__':'demo/asset?code=A1'},note_count=2,task_count=3)],sampleError='')
  assert arguments['revision']==self.revision
  if arguments['action']=='preview':return dict(interface={'table':{'item_layout':dict(elements=[],columns=12,collection='grid',flow='grid')}},diff='fixture diff')
  self.xml=arguments['xml'];self.revision='R2'
  if self.unknown:raise TimeoutError('unacknowledged write')
  return self.configuration()
server=object();stype=SimpleNamespace(get_code=lambda:'demo/asset',get_info=lambda:{'title':'Assets'});project=SimpleNamespace(stypes={'demo/asset':stype},get_stypes=Mock(side_effect=AssertionError('Do not discover metadata on the UI thread')))
app=gui_test_application();app.setFont(QFont('Segoe UI',10))
for name in ('segoeui.ttf','seguisb.ttf'):QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)
icons=qml_icon_bindings(TH,app)
