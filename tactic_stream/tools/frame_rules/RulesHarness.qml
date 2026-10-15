import QtQuick
import QtQuick.Controls
import "file:///D:/code/th_codex/thlib/ui/qml" as TH
ApplicationWindow {
 id:root;visible:true;width:1100;height:740;color:theme.workspace
 property alias dark:theme.dark
 property string language:"en"
 readonly property string sceneJson:JSON.stringify({toolbar:layout.toolbarScene(width),body:layout.frameScene})
 readonly property string stateJson:JSON.stringify({ui:layout.ui,document:fixture.document,dirty:fixture.dirty,uncertain:fixture.writeUncertain})
 function send(event){layout.dispatch(event)}
 function blur(){target.forceActiveFocus()}
 TH.Theme{id:theme;dark:true;clickAnimationsEnabled:false;hoverAnimationsEnabled:false;fadeAnimationsEnabled:false;popupAnimationsEnabled:false}
 TH.AdminProcessRulesView{id:layout;anchors.fill:parent;theme:theme;controller:fixture;language:root.language}
 Item{id:target}
}
