"""Archived note render fragments; the original window/controller stays untouched."""


def block(source, start):
    opening = source.index("{", start)
    end = opening + 1
    depth = 1
    while depth:
        if source[end] == "{":
            depth += 1
        elif source[end] == "}":
            depth -= 1
        end += 1
    return source[start:end]


def reference(qml, state):
    source = (qml / "CommunicationView.qml").read_text(encoding="utf-8")
    if state in ("edit", "delete"):
        dialog = block(
            source,
            source.rfind(
                "Controls.Dialog {",
                0,
                source.index(
                    "id: editMessageDialog" if state == "edit" else "id: deleteDialog"
                ),
            ),
        )
        start = dialog.index("contentItem: ") + len("contentItem: ")
        content = block(dialog, start)
        if state == "edit":
            content = content.replace(
                "id: editMessageText", "id: editMessageText; text:root.model.text"
            )
    else:
        text_start = source.index("MessageBodyText {")
        status = source.rfind(
            "RowLayout {",
            0,
            source.index(
                'visible: timelineRow.entryType === "status"', text_start - 2000
            ),
        )
        status = block(source, status)
        text = block(source, text_start)
        previews_start = source.index("ColumnLayout {", text_start)
        previews = block(source, previews_start)
        files = block(source, source.index("Controls.ResponsiveFlow {", previews_start))
        content = "ColumnLayout {spacing:6;" + status + text + previews + files + "}"
    return (
        """import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "controls" as Controls
Item {id:root;required property var theme;required property var model;
property var timelineRow:model;implicitHeight:content.implicitHeight;
"""
        + content.replace("{", "{id:content;width:root.width;", 1)
        + "}"
    )
