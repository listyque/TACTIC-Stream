import QtQuick
import QtQuick.Controls
import "file:///D:/grav/Tactic Stream/TH/thlib/ui/qml" as TH

ApplicationWindow {
 id:root
 visible:true;width:1100;height:740;color:theme.workspace
 property alias dark:theme.dark
 property string language:"en"
 readonly property string sceneJson:JSON.stringify({toolbar:types.toolbarScene(width),body:types.frameScene})
 readonly property string stateJson:JSON.stringify({ui:types.ui,dirty:types.controller.dirty,identity:types.controller.identity,document:normalized(types.controller.document)})
 function normalized(value){const result={};for(const key of ["title","description","color","columns","hasPipeline"])if(value[key]!==undefined)result[key]=value[key];result.removedColumns=value.removedColumns||[];return result}
 function blur(){focusTarget.forceActiveFocus()}
 TH.Theme {id:theme;dark:true;clickAnimationsEnabled:false;hoverAnimationsEnabled:false;fadeAnimationsEnabled:false;popupAnimationsEnabled:false}
 TH.AdminSearchTypesView {id:types;anchors.fill:parent;theme:theme;controller:searchTypesFixtureController;language:root.language;projectCode:"demo"}
 Item {id:focusTarget}
}
