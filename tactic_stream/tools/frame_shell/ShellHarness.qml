import QtQuick
import QtQuick.Controls
import "file:///D:/code/th_codex/thlib/ui/qml" as TH
import "file:///D:/code/th_codex/thlib/ui/qml/tactic_frame" as Frame
import "file:///D:/code/th_codex/thlib/ui/qml/tactic_frame/features/administration/administration.ui.mjs" as UI
import "file:///D:/code/th_codex/thlib/ui/qml/tactic_frame/features/administration/administration.state.mjs" as State
ApplicationWindow {
 id:root;visible:true;width:1100;height:740;color:theme.workspace
 property alias dark:theme.dark
 property string language:"en"
 property var model:({section:'types',project:'demo',projects:[{value:'demo',label:'Demo'}],locked:false,busy:false,drafts:[]})
 property var ui:State.initial()
 readonly property string sceneJson:JSON.stringify(body.scene)
 readonly property string stateJson:JSON.stringify({model,ui})
 function send(event){const result=State.transition(ui,model,event);ui=result.ui;for(const command of result.commands){if(command.type==='section')model=Object.assign({},model,{section:command.value})}}
 TH.Theme{id:theme;dark:true;clickAnimationsEnabled:false;hoverAnimationsEnabled:false;fadeAnimationsEnabled:false;popupAnimationsEnabled:false}
 Component{id:port;Item{}}
 Frame.FrameView{id:body;anchors.fill:parent;theme:theme;scene:UI.describe(root.model,root.ui,width,height,root.language);models:({sections:UI.sections});describeRow:(list,record)=>UI.row(list,record,root.model,root.ui,root.language);views:({toolbar:port,content:port});onEvent:action=>root.send(action)}
}
