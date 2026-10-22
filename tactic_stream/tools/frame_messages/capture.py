"""Capture the pinned original and the production native communication controls."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import zipfile
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
TH = Path("D:/grav/Tactic Stream/TH")
OUT = ROOT / os.environ.get("MESSAGES_FRAME_OUTPUT", "tools/frame_messages/output")
REFERENCE = "a824d3ec3fa02653e9e9c9fe3da51c0cde11abc4"
sys.path[:0] = [str(TH), str(ROOT / "tools/frame_admin")]
os.environ.update(
    QT_QPA_PLATFORM="offscreen",
    QT_QUICK_BACKEND="software",
    QT_QUICK_CONTROLS_STYLE="Basic",
    QT_QPA_FONTDIR="C:/Windows/Fonts",
)
from PySide6.QtCore import QCoreApplication, QEvent, QUrl, QRectF, QPoint
from PySide6.QtQml import QQmlComponent, QQmlEngine, QQmlExpression
from PySide6.QtGui import QFont, QFontInfo
from PySide6.QtQuick import QQuickWindow
from PySide6.QtTest import QTest
from tests.qt_application import gui_test_application
from tests.profile_ui_responsiveness import frame
from tests.frame_messages_fixture import Fixture, Locale
from thlib.environment import env_mode
from thlib.ui.icon_font import qml_icon_bindings
from thlib.ui.localization import CatalogTranslator
from native_capture import snapshot, source_hashes, controls
from tests.test_notifications_qml import (
    _NotificationController,
    TOAST_ROLES,
    HISTORY_ROLES,
)
from tests.test_activity_feed_qml import _ActivityFeedController, ACTIVITY_ROLES
from thlib.ui.workspace_models.records import RecordListModel


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cases(smoke):
    variants = (
        [("md3", True, "en"), ("md3", False, "ru")]
        if smoke
        else [
            (style, dark, language)
            for style in ("md3", "material5", "fluent")
            for dark in (False, True)
            for language in ("en", "ru")
        ]
    )
    for style, dark, language in variants:
        for screen, width, height in [
            ("messages", 1000, 620),
            ("messages", 700, 520),
            ("create", 408, 508),
            ("members", 300, 380),
            ("search", 308, 130),
            ("edit", 460, 260),
            ("clear", 380, 180),
            ("delete", 380, 180),
            ("delete-message", 380, 150),
            ("forwarding", 420, 426),
            ("view-members", 278, 338),
            ("history", 368, 308),
            ("pin-history", 368, 308),
            ("files", 328, 378),
            ("reference", 340, 92),
            ("forward", 260, 100),
            ("calendar", 320, 390),
            ("toast", 390, 230),
            ("activity", 1000, 620),
            ("activity", 700, 520),
            ("event", 740, 180),
            ("event", 360, 220),
            ("notifications", 1000, 620),
            ("notifications", 420, 520),
        ]:
            yield dict(
                screen=screen,
                width=width,
                height=height,
                style=style,
                dark=dark,
                language=language,
            )


def evaluate(view, source):
    expression = QQmlExpression(QQmlEngine.contextForObject(view), view, source)
    result = expression.evaluate()
    assert not expression.hasError(), expression.error().toString()
    return result[0] if isinstance(result, tuple) else result


def capture(app, qml, case, original):
    engine = QQmlEngine()
    engine.addImportPath(str(qml))
    warnings = []
    engine.warnings.connect(
        lambda errors: warnings.extend(error.toString() for error in errors)
    )
    fixture = Fixture(case["language"])
    panel = case["screen"] in ("view-members", "history", "pin-history", "files")
    if panel:
        fixture.controller._conversation_id = "review"
        fixture.data["history"] = [
            dict(
                editedBy="admin",
                editedAt="2026-10-18 09:00",
                body="Lighting review before the latest change.\nSecond line.",
            ),
            dict(
                editedBy="reviewer", editedAt="2026-10-18 08:00", body="Earlier review"
            ),
        ]
        fixture.data["pinHistory"] = [
            dict(
                messageId="MSG001",
                pinnedBy="admin",
                pinnedAt="2026-10-18 09:00",
                body="Lighting review",
                summary="Lighting review",
            )
        ]
        fixture.data["messages"][-1]["__edit_history__"] = fixture.data["history"]
        if case["screen"] == "files":
            fixture.data["messages"][0]["__attachments__"] = [
                dict(
                    code="SNAP" + str(i),
                    context="publish",
                    __files__=[
                        dict(
                            code="FILE" + str(i),
                            file_name=name,
                            type="main",
                            st_size=12,
                        )
                    ],
                )
                for i, name in enumerate(["lighting.txt", "review.txt"])
            ]
        fixture.controller.messages.replace(fixture.records())
        fixture.controller._pin_history = fixture.data["pinHistory"]
    locale = Locale(case["language"])
    for name, value in dict(
        qml_icon_bindings(TH, app), **fixture.context(), localizationController=locale
    ).items():
        engine.rootContext().setContextProperty(name, value)
    feed_controller = _ActivityFeedController()
    activity = []
    for source in fixture.data["activity"]:
        record = {name: "" for name in ACTIVITY_ROLES}
        record.update(
            source,
            actorAvatar="",
            version="",
            hours=0,
            serverGenerated=False,
            timestampPretty=fixture.time_label,
        )
        activity.append(record)
    feed_model = RecordListModel(ACTIVITY_ROLES, activity)
    history_model = RecordListModel(
        HISTORY_ROLES,
        [
            dict(row, timestampPretty=fixture.time_label)
            for row in fixture.data["history"]
        ],
    )
    history_controller = _NotificationController()
    for name, value in dict(
        activityFeedController=feed_controller,
        activityFeedModel=feed_model,
        notificationController=history_controller,
        notificationHistoryModel=history_model,
        notificationGroupedHistoryModel=history_model,
    ).items():
        engine.rootContext().setContextProperty(name, value)
    translator = (
        CatalogTranslator(TH / "thlib/ui/translations/ru.json")
        if case["language"] == "ru"
        else None
    )
    if translator:
        app.installTranslator(translator)
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(qml / "Theme.qml")))
    theme = component.createWithInitialProperties(
        dict(
            dark=case["dark"],
            styleName=case["style"],
            fadeAnimationsEnabled=False,
            hoverAnimationsEnabled=False,
            clickAnimationsEnabled=False,
            popupAnimationsEnabled=False,
        )
    )
    assert theme, [error.toString() for error in component.errors()]
    screen = case["screen"]
    form = screen in (
        "create",
        "members",
        "search",
        "edit",
        "clear",
        "delete",
        "delete-message",
    )
    if screen in ("messages", "forwarding") or panel or (original and form):
        file = "MessagesView.qml"
    elif form:
        file = "features/messages/MessageForm.qml"
    else:
        file = {
            "forward": "MessageForwardPreview.qml",
            "reference": "MessageReplyPreview.qml",
            "calendar": "ActivityCalendarPopup.qml",
            "toast": "NotificationStack.qml"
            if original
            else "features/activity/NotificationToast.qml",
            "activity": "ActivityFeedView.qml",
            "event": "ActivityEventCard.qml",
            "notifications": "NotificationsView.qml",
        }[screen]
    window = QQuickWindow()
    window.resize(case["width"], case["height"])
    window.setColor(theme.property("surfaceContainerHigh"))
    properties = dict(
        theme=theme,
        width=case["width"],
        height=case["height"],
        parent=window.contentItem(),
    )
    if screen == "forwarding" or panel:
        properties.update(width=1000, height=620)
        window.resize(1000, 620)
        if screen == "forwarding":
            fixture.controller.toggle_forward_selection("MSG003")
    if screen == "event":
        properties.pop("height")
        allowed = (
            "kind",
            "actor",
            "actorLabel",
            "actorInitials",
            "actorColor",
            "timestamp",
            "timestampPretty",
            "timestampFull",
            "targetTitle",
            "targetType",
            "targetTypeTitle",
            "typeColor",
            "processColor",
            "process",
            "detail",
            "canOpen",
            "changes",
        )
        properties.update({name: activity[0][name] for name in allowed})
    if form and not original:
        properties.update(
            mode=screen,
            availableBodyHeight=case["height"],
            selectedLogins=["artist"],
            text="Lighting review" if screen != "search" else "lighting",
        )
    if screen in ("reference", "forward"):
        ref = fixture.data["reference"]
        properties.update(sender=ref["senderDisplay"], body=ref["body"])
        if screen == "forward":
            properties["attachmentCount"] = 2
        else:
            properties["dismissible"] = True
    if screen == "toast" and original:
        notifications = RecordListModel(
            TOAST_ROLES, [dict(fixture.data["toast"], dedupeKey="fixture")]
        )
        notification_controller = _NotificationController()
        notification_controller.model = notifications
        properties.update(
            controller=notification_controller, notifications=notifications
        )
    if screen == "toast" and not original:
        properties.update(
            record=fixture.data["toast"], replyText=fixture.data["toast"]["replyText"]
        )
    if screen == "calendar":
        window.resize(case["width"] + 20, case["height"] + 20)
        properties.update(
            width=case["width"] + 20,
            height=case["height"] + 20,
            parent=window.contentItem(),
            usePopupWindow=False,
            dayCounts=fixture.data["calendar"]["counts"],
            selectedDay=fixture.data["calendar"]["selected"],
            localeName="ru_RU" if case["language"] == "ru" else "en_US",
        )
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(qml / file)))
    view = component.createWithInitialProperties(properties)
    assert view, [error.toString() for error in component.errors()]
    crop = None
    if screen != "calendar":
        view.setParentItem(window.contentItem())
    window.show()
    try:
        for _ in range(5):
            frame(window)
        if panel:
            popup = {
                "view-members": "membersPopup",
                "history": "editHistoryPopup",
                "pin-history": "pinHistoryPopup",
                "files": "filesPopup",
            }[screen]
            if screen == "history":
                evaluate(
                    view, "selectedEditHistory=" + json.dumps(fixture.data["history"])
                )
            evaluate(
                view,
                "if ("
                + popup
                + ".usePopupWindow !== undefined) "
                + popup
                + ".usePopupWindow=false; "
                + popup
                + ".open()",
            )
            for _ in range(6):
                frame(window)
            crop = evaluate(view, popup + ".contentItem")
        elif screen == "forwarding":
            evaluate(view, "forwardDialog.open()")
            for _ in range(5):
                frame(window)
            crop = evaluate(view, "forwardDialog.contentItem")
        elif original and form:
            window.resize(case["width"] + 60, case["height"] + 60)
            view.setWidth(case["width"] + 60)
            view.setHeight(case["height"] + 60)
            popup = {
                "create": "conversationPopup",
                "members": "addMembersPopup",
                "search": "messageSearchPopup",
                "edit": "editMessageDialog",
                "clear": "clearNotesDialog",
                "delete": "deleteChatDialog",
                "delete-message": "deleteMessageDialog",
            }[screen]
            if screen == "create":
                evaluate(
                    view,
                    "selectedRecipients=['artist']; newChatTitle.text='Lighting review'",
                )
            elif screen == "edit":
                evaluate(view, "pendingEditBody='Lighting review'")
            evaluate(
                view,
                "if ("
                + popup
                + ".usePopupWindow !== undefined) "
                + popup
                + ".usePopupWindow = false; "
                + popup
                + ".open()",
            )
            for _ in range(5):
                frame(window)
            if screen == "members":
                evaluate(
                    view,
                    "editedMembers=['artist']; addMemberUsers.setSelection(editedMembers)",
                )
            elif screen == "search":
                evaluate(view, "messageSearchField.text='lighting'")
            for _ in range(3):
                frame(window)
            crop = evaluate(view, popup + ".contentItem")
        elif screen == "calendar":
            evaluate(view, "visibleMonth = new Date(2026,9,1); open()")
            for _ in range(5):
                frame(window)
            crop = view.property("contentItem")
        if screen == "toast" and original:
            crop = controls(window)["notificationCard"]
            controls(window)["notificationReplyField"].setProperty(
                "text", fixture.data["toast"]["replyText"]
            )
            frame(window)
        QTest.mouseMove(window, QPoint(window.width() - 1, window.height() - 1))
        frame(window)
        assert not warnings, "\n".join(warnings)
        measured = snapshot(
            SimpleNamespace(contentItem=lambda: crop) if crop else window
        )
        image = window.grabWindow()
        if crop:
            bounds = crop.mapRectToScene(QRectF(0, 0, crop.width(), crop.height()))
            for group in ("boxes", "interiors"):
                for box in measured[group].values():
                    box["x"] -= bounds.x()
                    box["y"] -= bounds.y()
            ratio = image.devicePixelRatio()
            image = image.copy(
                round(bounds.x() * ratio),
                round(bounds.y() * ratio),
                round(bounds.width() * ratio),
                round(bounds.height() * ratio),
            )
        name = (
            "-".join(
                [
                    screen,
                    "original" if original else "native",
                    case["style"],
                    "dark" if case["dark"] else "light",
                    case["language"],
                    str(case["width"]),
                ]
            )
            + ".png"
        )
        assert image.save(str(OUT / name))
        ports = {}
        for key, item in controls(window).items():
            if key in ("activitySentence", "messageBodyText"):
                ports[key] = dict(
                    text=item.property("text"),
                    font=item.property("font").toString(),
                    height=item.property("contentHeight"),
                )
        return dict(
            fixture=dict(case, model=fixture.data),
            original=original,
            image=name,
            ports=ports,
            **measured,
        )
    finally:
        window.close()
        view.deleteLater()
        window.deleteLater()
        fixture.close()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        if translator:
            app.removeTranslator(translator)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    archived = ROOT / ".tmp/b11/original"
    archive = ROOT / ".tmp/b11/original-handler.zip"
    with zipfile.ZipFile(archive) as reference:
        assert reference.comment.decode("ascii") == REFERENCE
        for name in reference.namelist():
            if name.startswith("thlib/ui/qml/") and not name.endswith("/"):
                assert (archived / name).read_bytes() == reference.read(name), (
                    "Modified original: " + name
                )
    names = [
        path.relative_to(TH).as_posix() for path in (TH / "thlib/ui/qml").rglob("*.qml")
    ] + [
        "thlib/ui/communication_feed.py",
        "thlib/ui/message_attachments.py",
        "tests/frame_messages_fixture.py",
        "tests/fixtures/frame_messages.json",
    ]
    shared, native = source_hashes(ROOT, TH, names)
    drivers = {
        p.relative_to(ROOT).as_posix(): digest(p)
        for p in Path(__file__).parent.iterdir()
        if p.suffix in (".py", ".json", ".vue", ".mjs", ".html")
    }
    app = gui_test_application()
    assert QFontInfo(QFont("Segoe UI")).family() == "Segoe UI", (
        "Missing native text font"
    )
    previous = env_mode.current_path
    rows = []
    with tempfile.TemporaryDirectory(prefix="frame-messages-") as isolated:
        env_mode.current_path = isolated
        try:
            for original in (True, False):
                for case in cases(args.smoke):
                    rows.append(
                        capture(
                            app,
                            (archived if original else TH) / "thlib/ui/qml",
                            case,
                            original,
                        )
                    )
                    print(
                        "Captured",
                        original,
                        case["screen"],
                        case["style"],
                        case["language"],
                        case["width"],
                        flush=True,
                    )
        finally:
            env_mode.current_path = previous
    assert (shared, native) == source_hashes(ROOT, TH, names), (
        "Sources changed during capture"
    )
    assert drivers == {name: digest(ROOT / name) for name in drivers}
    (OUT / "native.json").write_text(
        json.dumps(
            dict(
                reference=REFERENCE,
                archive=digest(archive),
                shared=shared,
                nativeSources=native,
                driverSources=drivers,
                scale=float(os.environ.get("QT_SCALE_FACTOR", "1")),
                captures=rows,
            ),
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
