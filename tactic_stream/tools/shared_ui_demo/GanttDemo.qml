import QtQuick
import QtQuick.Controls
import "file:///D:/code/th_codex/thlib/ui/qml" as TH
import "file:///D:/code/th_codex/thlib/ui/qml/controls" as Controls
import "gantt.state.mjs" as State
import "gantt.ui.mjs" as UI

ApplicationWindow {
    id: root
    width: spec.viewport.width; height: spec.viewport.height
    visible: true; title: "Shared Gantt · native QML"; color: nativeTheme.workspace
    property var spec: ganttSpec
    property var fixture: ganttFixture
    property string language: demoLanguage
    property var palette: demoPalette
    property var demoState: State.initial(fixture)
    readonly property var scene: UI.scene(spec, fixture, demoState, width, height, palette, language)
    readonly property string sceneJson: State.stable(scene)
    function send(event) {demoState = State.transition(spec, fixture, demoState, event, width, height)}
    TH.Theme {id: nativeTheme; dark: demoDark; hoverAnimationsEnabled: false; clickAnimationsEnabled: false; popupAnimationsEnabled: false}
    Item {
        id: stage; anchors.fill: parent; focus: true
        Keys.onEscapePressed: root.send({type: "cancel"})
        Keys.onPressed: function(event) {
            if (event.key === Qt.Key_Z && (event.modifiers & Qt.ControlModifier)) {root.send({type: event.modifiers & Qt.ShiftModifier ? "redo" : "undo"}); event.accepted = true}
        }
        Repeater {
            model: root.scene.layers.length
            Item {
                id: layerItem
                required property int index
                readonly property var sceneLayer: root.scene.layers[index]
                objectName: "layer:" + sceneLayer.id
                x: sceneLayer.x; y: sceneLayer.y; width: sceneLayer.width; height: sceneLayer.height; clip: true
                Repeater {
                    model: layerItem.sceneLayer.nodes.length
                    Item {
                        id: nodeItem
                        required property int index
                        readonly property var node: layerItem.sceneLayer.nodes[index]
                        objectName: "node:" + node.id
                        x: node.x; y: node.y; width: node.width; height: node.height
                        activeFocusOnTab: (node.kind === "Label" && !!node.action) || !!node.keyAction
                        Accessible.ignored: !activeFocusOnTab
                        Accessible.role: Accessible.Button
                        Accessible.name: node.a11yLabel || node.text
                        Keys.onPressed: function(event) {
                            const codes = {}; codes[Qt.Key_Left] = "ArrowLeft"; codes[Qt.Key_Right] = "ArrowRight"; codes[Qt.Key_Home] = "Home"; codes[Qt.Key_End] = "End"
                            if (node.keyAction && codes[event.key]) {root.send(Object.assign({code: codes[event.key]}, node.keyAction)); event.accepted = true}
                            else if (node.action && (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || event.key === Qt.Key_Space)) {root.send(node.action); event.accepted = true}
                            else event.accepted = false
                        }
                        Loader {
                            anchors.fill: parent
                            sourceComponent: nodeItem.node.kind === "Button" ? buttonBrick : nodeItem.node.kind === "CheckBox" ? checkBrick : nodeItem.node.kind === "Label" ? labelBrick : rectangleBrick
                            Component {
                                id: rectangleBrick
                                Rectangle {objectName: "paint:" + nodeItem.node.id; color: nodeItem.node.background; border.color: nodeItem.node.border; border.width: nodeItem.node.border === "transparent" ? 0 : 1; radius: nodeItem.node.radius}
                            }
                            Component {
                                id: labelBrick
                                Label {
                                    objectName: "paint:" + nodeItem.node.id
                                    text: nodeItem.node.text; color: nodeItem.node.color
                                    font.family: nativeTheme.fontFamily; font.pointSize: nodeItem.node.fontSize * .75
                                    font.weight: nodeItem.node.bold ? Font.DemiBold : Font.Normal
                                    verticalAlignment: Text.AlignVCenter; horizontalAlignment: nodeItem.node.align === "center" ? Text.AlignHCenter : Text.AlignLeft
                                    elide: Text.ElideRight
                                }
                            }
                            Component {
                                id: buttonBrick
                                Controls.Button {
                                    objectName: "paint:" + nodeItem.node.id
                                    theme: nativeTheme; text: nodeItem.node.text; enabled: nodeItem.node.enabled; highlighted: nodeItem.node.highlighted
                                    font.pointSize: nodeItem.node.fontSize * .75
                                    onClicked: root.send(nodeItem.node.action)
                                }
                            }
                            Component {
                                id: checkBrick
                                Controls.CheckBox {
                                    objectName: "paint:" + nodeItem.node.id
                                    theme: nativeTheme; text: nodeItem.node.showLabel ? nodeItem.node.text : ""; checked: nodeItem.node.checked; padding: 0
                                    font.pointSize: nodeItem.node.fontSize * .75
                                    onToggled: root.send(nodeItem.node.action)
                                }
                            }
                        }
                        MouseArea {
                            id: pointer
                            anchors.fill: parent
                            enabled: (nodeItem.node.kind === "Label" || nodeItem.node.kind === "Rectangle") && !!(nodeItem.node.action || nodeItem.node.drag)
                            cursorShape: !nodeItem.node.drag ? Qt.PointingHandCursor : nodeItem.node.drag.mode === "start" || nodeItem.node.drag.mode === "end" ? Qt.SizeHorCursor : nodeItem.node.drag.mode === "progress" ? Qt.CrossCursor : Qt.OpenHandCursor
                            onPressed: function(mouse) {
                                if (nodeItem.activeFocusOnTab) nodeItem.forceActiveFocus(); else stage.forceActiveFocus()
                                if (!nodeItem.node.drag) return
                                const pt = mapToItem(stage, mouse.x, mouse.y)
                                root.send(Object.assign({type: "press", x: Math.round(pt.x), y: Math.round(pt.y)}, nodeItem.node.drag))
                            }
                            onPositionChanged: function(mouse) {if (pressed && root.demoState.drag) {const pt = mapToItem(stage, mouse.x, mouse.y); root.send({type: "pointer", x: Math.round(pt.x), y: Math.round(pt.y)})}}
                            onReleased: if (root.demoState.drag) root.send({type: "release"})
                            onCanceled: root.send({type: "cancel"})
                            onClicked: if (nodeItem.node.action) root.send(nodeItem.node.action)
                        }
                    }
                }
            }
        }
        WheelHandler {
            onWheel: function(event) {
                if (event.modifiers & Qt.ControlModifier) root.send({type: "zoom", factor: event.angleDelta.y > 0 ? 1.1 : 1 / 1.1, x: event.x})
                else root.send({type: "scroll", dx: event.modifiers & Qt.ShiftModifier ? -event.angleDelta.y : -event.angleDelta.x, dy: event.modifiers & Qt.ShiftModifier ? 0 : -event.angleDelta.y})
                event.accepted = true
            }
        }
    }
}
