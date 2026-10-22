"""Native QML demo; uses Handler controls and the same screen/logic as Vue."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
TH = Path('D:/grav/Tactic Stream/TH')
screen = json.loads((HERE/'screen.json').read_text(encoding='utf-8'))
parser = argparse.ArgumentParser()
parser.add_argument('--capture', action='store_true')
parser.add_argument('--language', choices=('en','ru'), default='ru')
parser.add_argument('--mode', choices=('dark','light'), default='dark')
parser.add_argument('--width', type=int, default=520)
args = parser.parse_args()
if args.capture:
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['QT_QUICK_BACKEND'] = 'software'
os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
os.environ['QT_FONT_DPI'] = '96'
from PySide6.QtCore import QPoint, QPointF, QUrl, Qt, QObject
from PySide6.QtGui import QGuiApplication, QFont, QColor, QFontDatabase, QFontInfo
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
sys.path.insert(0, str(TH))
from thlib.ui.icon_font import qml_icon_bindings


def leaves(node):
    if node['kind'] in ('Row', 'Column'):
        return [leaf for child in node['children'] for leaf in leaves(child)]
    if node['kind'] not in ('Label', 'TextField', 'CheckBox', 'Button'):
        raise ValueError('Unsupported brick: ' + node['kind'])
    return [node]


def source(mode='dark', language='en'):
    parts = [f'''import QtQuick
import QtQuick.Controls
import "{(TH/'thlib/ui/qml').as_uri()}" as TH
import "{(TH/'thlib/ui/qml/controls').as_uri()}" as Controls
import "logic.mjs" as Logic
ApplicationWindow {{
 id: root; width:{screen['viewport']['width']}; height:{screen['viewport']['height']}; visible:true; title:"Shared UI skeleton demo"; color:theme.workspace
 property var spec: {json.dumps(screen,ensure_ascii=False)}
 property string language: "{language}"
 property var demoState: Logic.initial(spec)
 readonly property var boxes: Logic.layout(spec,width)
 readonly property var model: Logic.present(spec,demoState,language)
 function send(event) {{demoState=Logic.transition(spec,demoState,event)}}
 TH.Theme {{id:theme; objectName:"demoTheme"; dark:{str(mode=='dark').lower()}; hoverAnimationsEnabled:false; clickAnimationsEnabled:false; popupAnimationsEnabled:false}}
 Item {{id:stage; objectName:"demoStage"; anchors.fill:parent; focus:true
''']
    for node in leaves(screen['layout']):
        kind = node['kind']; key = node['id']; model = f'root.model["{key}"]'; box = f'root.boxes["{key}"]'
        widget = 'Label' if kind == 'Label' else 'Controls.' + kind
        parts.append(f'{widget} {{ objectName:"{key}"; x:{box}.x; y:{box}.y; width:{box}.width; height:{box}.height;')
        parts.append(f'font.family:theme.fontFamily; font.pointSize:root.spec.typography.{node.get("role","body")}*0.75;')
        if kind != 'Label':
            parts.append(f'theme:theme; enabled:{model}.enabled;')
        if kind == 'Label':
            color = 'theme.secondaryText' if node.get('muted') else 'theme.primaryText'
            parts.append(f'text:{model}.text; color:{model}.error ? theme.error : {color}; verticalAlignment:Text.AlignVCenter; elide:Text.ElideRight; font.weight:Font.{"DemiBold" if node.get("role")=="title" else "Normal"};')
        elif kind == 'TextField':
            parts.append(f'text:{model}.value; onTextEdited:root.send({{type:"change",field:"{node["field"]}",value:text}});')
        elif kind == 'CheckBox':
            parts.append(f'text:{model}.text; checked:{model}.value; padding:0; onToggled:root.send({{type:"change",field:"{node["field"]}",value:checked}});')
        elif kind == 'Button':
            parts.append(f'text:{model}.text; highlighted:{str(node.get("highlighted",False)).lower()}; onClicked:root.send({{type:"{node["action"]}"}});')
        parts.append('}')
    return '\n'.join(parts) + '\n}}'


app = QGuiApplication([])
for name in ('segoeui.ttf','seguisb.ttf'):
    QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)
app.setFont(QFont('Segoe UI', 9))
engine = QQmlEngine()
for name,value in qml_icon_bindings(TH,engine).items():
    engine.rootContext().setContextProperty(name,value)
OUT = HERE/'output'; OUT.mkdir(exist_ok=True)
palettes = {}; captures = []


def item(window, name):
    return window.findChild(QQuickItem,name)


def click(window, name):
    control = item(window,name)
    point = control.mapToScene(QPointF(control.width()/2,control.height()/2))
    QTest.mouseClick(window,Qt.LeftButton,pos=point.toPoint());QTest.qWait(30)


def name_text(window, value):
    click(window,'name');QTest.keyClick(window,Qt.Key_A,Qt.ControlModifier)
    QTest.keyClick(window,Qt.Key_Backspace)
    for char in value:
        QTest.keyClick(window,char)
    QTest.qWait(30)


def state(window):
    return window.property('demoState').toVariant()


def capture(window, mode, language, phase, width):
    # Remove input focus and hover for comparable baseline snapshots.
    item(window,'demoStage').forceActiveFocus()
    QTest.mouseMove(window,QPoint(width-5,window.height()-5));QTest.qWait(40)
    name=f'qml-{mode}-{language}-{width}-{phase}.png'
    assert window.grabWindow().save(str(OUT/name))
    geometry={}; styles={}; texts={}
    for node in leaves(screen['layout']):
        control=item(window,node['id']);point=control.mapToScene(QPointF(0,0))
        geometry[node['id']]={'x':point.x(),'y':point.y(),'width':control.width(),'height':control.height()}
        font=control.property('font')
        color=control.property('contentColor') if node['kind']=='Button' else control.property('contentItem').property('color') if node['kind']=='CheckBox' else control.property('color')
        styles[node['id']]={'fontSize':QFontInfo(font).pixelSize(),'fontWeight':int(font.weight()),'color':color.name(QColor.HexRgb)}
        texts[node['id']]=control.property('text')
    captures.append({'mode':mode,'language':language,'width':width,'phase':phase,'image':name,'geometry':geometry,'layout':window.property('boxes').toVariant(),'styles':styles,'texts':texts,'state':state(window)})


if not args.capture:
    component=QQmlComponent(engine);component.setData(source(args.mode,args.language).encode(),QUrl.fromLocalFile(str(HERE/'Demo.qml')))
    window=component.create();assert window,[error.toString() for error in component.errors()]
    window.resize(args.width,screen['viewport']['height'])
    sys.exit(app.exec())

for mode in ('dark','light'):
    for language in ('en','ru'):
        for width in (520,320):
            component=QQmlComponent(engine)
            generated=source(mode,language)
            (OUT/'Demo.generated.qml').write_text(generated,encoding='utf-8')
            component.setData(generated.encode(),QUrl.fromLocalFile(str(HERE/'Demo.qml')))
            window=component.create();assert window,[error.toString() for error in component.errors()]
            try:
                window.resize(width,screen['viewport']['height']);window.requestActivate();QTest.qWait(100)
                theme=window.findChild(QObject,'demoTheme')
                roles=['workspace','surfaceContainerHigh','primaryText','secondaryText','action','selectedText','outline','outlineVariant','disabledText','rowHover','selected','error']
                palettes[mode]={role:theme.property(role).name(QColor.HexRgb) for role in roles}
                capture(window,mode,language,'initial',width)
                assert not item(window,'apply').isEnabled()
                name_text(window,'');click(window,'apply')
                assert state(window)['error']=='Name is required'
                capture(window,mode,language,'error',width)
                name_text(window,'Pipeline B');click(window,'enabled');click(window,'apply')
                assert state(window)['saved']=={'name':'Pipeline B','enabled':False}
                assert state(window)['saves']==1
                capture(window,mode,language,'saved',width)
                name_text(window,'Draft');click(window,'reset')
                assert state(window)['draft']==state(window)['saved']
                capture(window,mode,language,'reset',width)
            finally:
                window.close();window.deleteLater();app.processEvents()
(HERE/'palettes.json').write_text(json.dumps(palettes,indent=2)+'\n',encoding='utf-8')
(OUT/'qml-measurements.json').write_text(json.dumps({'captures':captures,'sources':{name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in ['screen.json','logic.mjs']}},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'native':'Qt Quick, no WebEngine','captures':len(captures),'interaction_cases':8}))
