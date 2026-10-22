import QtQuick
import QtQuick.Controls
import "file:///D:/grav/Tactic Stream/TH/thlib/ui/qml" as TH
ApplicationWindow {
 id:root;visible:true;width:1100;height:740;color:theme.workspace
 property alias dark:theme.dark
 property string language:"en"
 readonly property string sceneJson:JSON.stringify({toolbar:editor.toolbarScene(width),body:editor.frameScene})
 readonly property string stateJson:JSON.stringify({ui:editor.ui,dirty:editor.controller.dirty,identity:editor.controller.identity,selected:editor.controller.selectedNodes,primary:editor.controller.selectedNode,edge:editor.controller.selectedEdge,attributes:editor.controller.selectedAttributes,settings:editor.controller.processSettings})
 function send(action){editor.dispatch(action)}
 function blur(){focusTarget.forceActiveFocus()}
 TH.Theme{id:theme;dark:true;clickAnimationsEnabled:false;hoverAnimationsEnabled:false;fadeAnimationsEnabled:false;popupAnimationsEnabled:false}
 TH.AdminGraphView{id:editor;anchors.fill:parent;theme:theme;controller:graphFixture;language:root.language}
 Item{id:focusTarget}
}
