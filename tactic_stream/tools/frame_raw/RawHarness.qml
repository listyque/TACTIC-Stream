import QtQuick
import QtQuick.Controls
import "file:///D:/grav/Tactic Stream/TH/thlib/ui/qml" as TH

ApplicationWindow {
    id: root
    width: 1100; height: 740; visible: true
    color: theme.workspace
    property string language: "en"
    property alias dark: theme.dark
    readonly property var editor: administrationController.rawEditor
    readonly property string sceneJson: JSON.stringify({toolbar: raw.toolbarScene(width), body: raw.frameScene})
    readonly property string stateJson: JSON.stringify({ui: raw.ui, dirty: editor.dirty, uncertain: editor.uncertain, identity: editor.identity,
        rows: editor.rows.map(row => ({key: row.key == null ? null : row.key, texts: row.texts, modes: row.modes, deleted: row.deleted}))})
    function blur() {focusTarget.forceActiveFocus()}
    TH.Theme {id: theme; dark: true; clickAnimationsEnabled: false; hoverAnimationsEnabled: false; fadeAnimationsEnabled: false; popupAnimationsEnabled: false}
    TH.AdminRawDatabaseView {id: raw; anchors.fill: parent; theme: theme; controller: root.editor; language: root.language}
    Item {id: focusTarget}
}
