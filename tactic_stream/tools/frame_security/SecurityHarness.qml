import QtQuick
import QtQuick.Controls
import "file:///D:/grav/Tactic Stream/TH/thlib/ui/qml" as TH
import "file:///D:/grav/Tactic Stream/TH/thlib/ui/qml/tactic_frame/features/administration/security/security.ui.mjs" as UI
import "file:///D:/grav/Tactic Stream/TH/thlib/ui/qml/tactic_frame/features/administration/security/security.state.mjs" as State

ApplicationWindow {
    id: root
    width: 1100; height: 660; visible: true
    color: theme.workspace
    property string language: "en"
    property alias dark: theme.dark
    readonly property var editor: administrationController.securityEditor
    readonly property string sceneJson: JSON.stringify({toolbar: security.toolbarScene(width), body: security.frameScene})
    readonly property string stateJson: {
        const ui = Object.assign({}, security.ui);delete ui.text;delete ui.baseline
        return JSON.stringify({ui, pending: State.pending(security.ui), dirty: editor.dirty, uncertain: editor.writeUncertain, group: editor.selectedGroup, selected: editor.selectedRule, attributes: editor.selectedAttributes})
    }
    function blur() {focusTarget.forceActiveFocus()}
    TH.Theme {id: theme; dark: true; clickAnimationsEnabled: false; hoverAnimationsEnabled: false; fadeAnimationsEnabled: false; popupAnimationsEnabled: false}
    TH.AdminSecurityView {id: security; anchors.fill: parent; theme: theme; controller: root.editor; language: root.language}
    Item {id: focusTarget}
}
