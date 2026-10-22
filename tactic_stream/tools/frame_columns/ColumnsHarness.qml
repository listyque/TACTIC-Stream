import QtQuick
import QtQuick.Controls
import "file:///D:/grav/Tactic Stream/TH/thlib/ui/qml" as TH

ApplicationWindow {
    id: root
    width: 1100; height: 740; visible: true
    color: theme.workspace
    property string language: "en"
    property alias dark: theme.dark
    property bool canWrite: true
    readonly property string sceneJson: JSON.stringify({toolbar: columns.toolbarScene(width), body: columns.frameScene})
    readonly property string stateJson: JSON.stringify({ui: columns.ui, dirty: columns.catalogDirty, identity: columns.selectedCatalogIdentity, xml: columns.catalogXmlText})
    function blur() {focusTarget.forceActiveFocus()}
    TH.Theme {id: theme; dark: true; clickAnimationsEnabled: false; hoverAnimationsEnabled: false; fadeAnimationsEnabled: false; popupAnimationsEnabled: false}
    TH.ColumnsEditorView {id: columns; objectName: "columnsFramePage"; anchors.fill: parent; theme: theme; language: root.language; projectCode: "demo"; canWrite: root.canWrite}
    Item {id: focusTarget}
}
