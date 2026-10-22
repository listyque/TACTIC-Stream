import QtQuick
import QtQuick.Controls
import "file:///D:/grav/Tactic Stream/TH/thlib/ui/qml" as TH
import "file:///D:/grav/Tactic Stream/TH/thlib/ui/qml/tactic_frame/features/administration/groups/groups.ui.mjs" as UI
import "file:///D:/grav/Tactic Stream/TH/thlib/ui/qml/tactic_frame/features/administration/groups/groups.state.mjs" as State

ApplicationWindow {
    id: root
    width: 1100; height: 660; visible: true
    title: "Tactic Frame · production Groups · QML"
    color: theme.workspace
    property string language: "en"
    property alias dark: theme.dark
    readonly property string sceneJson: JSON.stringify({toolbar: groups.toolbarScene(width), body: UI.describe(groups.frameModel, groups.ui, width, height - 46, language)})
    readonly property string stateJson: JSON.stringify({ui: groups.ui, dirty: administrationController.dirty, uncertain: administrationController.groupUncertain,
        draft: {code: administrationController.draft.code || "", name: administrationController.draft.name || "", description: administrationController.draft.description || ""}, memberCount: administrationController.memberCount})
    function resetUi() {groups.ui = State.initial()}
    function setQuery(value) {groups.dispatch({type: "query", value: value})}
    function blur() {focusTarget.forceActiveFocus()}
    TH.Theme {
        id: theme; dark: true
        clickAnimationsEnabled: false; hoverAnimationsEnabled: false
        fadeAnimationsEnabled: false; popupAnimationsEnabled: false
    }
    TH.SecurityGroupsView {
        id: groups; anchors.fill: parent; theme: theme
        controller: administrationController
        groupsModel: administrationGroupModel; membersModel: administrationMemberModel
        language: root.language
    }
    Item {id: focusTarget}
}
