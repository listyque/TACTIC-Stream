import QtQuick
import QtQuick.Controls
import "file:///D:/code/th_codex/thlib/ui/qml" as TH
import "file:///D:/code/th_codex/thlib/ui/qml/tactic_frame/features/administration/users/users.ui.mjs" as UI

ApplicationWindow {
    id: root
    width: 1100; height: 660; visible: true
    color: theme.workspace
    property string language: "en"
    property alias dark: theme.dark
    readonly property var editor: administrationController.usersEditor
    readonly property string sceneJson: JSON.stringify({toolbar: users.toolbarScene(width), body: UI.describe(users.frameModel, users.ui, width, height - 46, language)})
    readonly property string stateJson: JSON.stringify({ui: users.ui, dirty: editor.dirty, uncertain: editor.uncertain,
        draft: {login: editor.document.login || "", first_name: editor.document.first_name || "", groups: editor.document.groups || []}, identity: editor.identity})
    function blur() {focusTarget.forceActiveFocus()}
    TH.Theme {id: theme; dark: true; clickAnimationsEnabled: false; hoverAnimationsEnabled: false; fadeAnimationsEnabled: false; popupAnimationsEnabled: false}
    TH.AdminUsersView {id: users; anchors.fill: parent; theme: theme; controller: root.editor; language: root.language}
    Item {id: focusTarget}
}
