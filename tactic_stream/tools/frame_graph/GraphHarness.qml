import QtQuick
import QtQuick.Controls
import "file:///D:/grav/Tactic Stream/TH/thlib/ui/qml" as TH
import "file:///D:/grav/Tactic Stream/TH/thlib/ui/qml/tactic_frame" as Frame
import "model.mjs" as Model

ApplicationWindow {
    id: root
    visible: true; width: 1100; height: 740; color: theme.workspace
    property alias dark: theme.dark
    property string language: "en"
    property var graph: Model.initial()
    property var commands: []
    readonly property string stateJson: JSON.stringify({ui: canvas.ui, graph, commands})
    readonly property string sceneJson: JSON.stringify({body: canvas.node})
    function blur() {focusTarget.forceActiveFocus()}
    TH.Theme {id: theme; dark: true; clickAnimationsEnabled: false; hoverAnimationsEnabled: false; fadeAnimationsEnabled: false; popupAnimationsEnabled: false}
    Frame.FrameGraph {
        id: canvas
        anchors.fill: parent; theme: theme
        node: Object.assign({id: "testGraph", label: "Graph", width: root.width, height: root.height, language: root.language}, root.graph)
        onEvent: action => {root.commands = root.commands.concat([action.value]); root.graph = Model.apply(root.graph, action.value)}
    }
    Item {id: focusTarget}
}
