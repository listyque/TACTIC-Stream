import QtQuick
import QtQuick.Controls
import "file:///D:/grav/Tactic Stream/TH/thlib/ui/qml" as TH

ApplicationWindow {
    id: root
    width: 1100; height: 740; visible: true
    color: theme.workspace
    property string language: "en"
    property alias dark: theme.dark
    readonly property string sceneJson: JSON.stringify({toolbar: sidebar.toolbarScene(width), body: sidebar.frameScene})
    readonly property string stateJson: JSON.stringify({ui: sidebar.ui, dirty: sidebar.controller.dirty, selected: sidebar.controller.selectedRow, entry: sidebar.controller.selectedEntry.name || ""})
    function blur() {focusTarget.forceActiveFocus()}
    TH.Theme {id: theme; dark: true; clickAnimationsEnabled: false; hoverAnimationsEnabled: false; fadeAnimationsEnabled: false; popupAnimationsEnabled: false}
    TH.SidebarEditorView {id: sidebar; objectName: "sidebarFramePage"; anchors.fill: parent; theme: theme; language: root.language}
    Item {id: focusTarget}
}
