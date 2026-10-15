import QtQuick
import QtQuick.Controls
import "file:///D:/code/th_codex/thlib/ui/qml" as TH
import "file:///D:/code/th_codex/thlib/ui/qml/tactic_frame" as Frame
import "file:///D:/code/th_codex/thlib/ui/qml/tactic_frame/features/administration/schema/schema_delete.ui.mjs" as UI
ApplicationWindow {
 id:root;visible:true;width:1100;height:740;color:theme.workspace
 property alias dark:theme.dark
 property string language:"en"
 readonly property var model:({identity:fixture.identity,schemaRevision:fixture.schemaRevision,metadata:fixture.metadata,canWrite:fixture.canWrite,busy:fixture.busy,deleting:fixture.deleting,uncertain:fixture.writeUncertain,error:fixture.error,confirmation:fixture.document.confirmation||""})
 readonly property string sceneJson:JSON.stringify(body.scene)
 readonly property string stateJson:JSON.stringify(model)
 TH.Theme{id:theme;dark:true;clickAnimationsEnabled:false;hoverAnimationsEnabled:false;fadeAnimationsEnabled:false;popupAnimationsEnabled:false}
 Frame.FrameView{id:body;anchors.fill:parent;theme:theme;scene:UI.describe(root.model,width,height,root.language);onEvent:action=>{if(action.type==='confirmation')fixture.set_field('confirmation',action.value)}}
}
