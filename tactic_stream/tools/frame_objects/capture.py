"""Production B08 presenters, archived native references and source-fresh evidence."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import zipfile
import subprocess

ROOT = Path(__file__).resolve().parents[2]
TH = Path("D:/code/th_codex")
OUT = Path(__file__).parent / "output"
REFERENCE = json.loads(
    (Path(__file__).parent / "reference.json").read_text(encoding="utf-8")
)
sys.path[:0] = [str(TH), str(ROOT / "tools/frame_admin")]
os.environ.update(
    QT_QPA_PLATFORM="offscreen",
    QT_QUICK_BACKEND="software",
    QT_QUICK_CONTROLS_STYLE="Basic",
)
from PySide6.QtCore import (
    QObject,
    Property,
    QUrl,
    QCoreApplication,
    QEvent,
    QPoint,
    QRect,
    Qt,
    Slot,
)
from PySide6.QtQml import QQmlEngine, QQmlComponent
from PySide6.QtQuick import QQuickItem, QQuickWindow
from PySide6.QtTest import QTest
from native_capture import snapshot, source_hashes, assert_icons
from tests.qt_application import gui_test_application
from tests.profile_ui_responsiveness import frame
from thlib.ui.icon_font import qml_icon_bindings
from thlib.ui.localization import CatalogTranslator
from thlib.ui.workspace_models.records import RecordListModel


from object_fixtures import Locale, FixtureController, fixtures


def capture(app, qml, fixture, original):
    engine = QQmlEngine()
    warnings = []
    engine.warnings.connect(
        lambda errors: warnings.extend(e.toString() for e in errors)
    )
    locale = Locale(fixture["language"])
    controller = FixtureController(fixture["model"])
    for name, value in dict(
        qml_icon_bindings(TH, app),
        localizationController=locale,
        watchFoldersController=controller,
        sobjectInfoController=controller,
        sobjectDeleteController=controller,
        communicationController=controller,
    ).items():
        engine.rootContext().setContextProperty(name, value)
    duplicate_controller = None
    if fixture["screen"] == "duplicate":
        from unittest.mock import patch
        from tests.test_sobject_duplicate import _Application
        from thlib.ui.sobject_duplicate import SObjectDuplicateController

        with patch("thlib.ui.sobject_duplicate.env_read_config", return_value={}):
            duplicate_controller = SObjectDuplicateController(_Application())
        duplicate_controller._analysis_ready(
            duplicate_controller._generation, fixture["model"]
        )
        duplicate_controller.set_step(fixture["model"]["step"])
        fixture = dict(fixture, model=dict(duplicate_controller.presentation))
        controller = duplicate_controller
        engine.rootContext().setContextProperty(
            "sobjectDuplicateController", controller
        )
        for key, value in dict(
            sobjectDuplicateRelationModel=controller.relations,
            sobjectDuplicateProcessModel=controller.processes,
            sobjectDuplicateFieldModel=controller.fields,
        ).items():
            engine.rootContext().setContextProperty(key, value)
    link_controller = None
    if fixture["screen"] == "links":
        from tests.test_sobject_link import _ready_controller, _SObject

        link_controller = _ready_controller(
            [_SObject("A", title="Hero Robot")] if fixture["state"] == "loaded" else [],
            [_SObject("B", title="Robot Arm")] if fixture["state"] == "loaded" else [],
        )
        link_controller._target_title = "Assets"
        link_controller._target_code = "cg/assets"
        link_controller._parent_title = "Workshop"
        link_controller._parent_type_title = "Scenes"
        link_controller._parent_code = "SCENE001"
        link_controller._available_total = link_controller.available_model.count
        link_controller._available_offset = link_controller.available_model.count
        model = dict(
            targetTitle="Assets",
            parentTitle="Workshop",
            subtitle="cg/assets → Scenes · SCENE001",
            direction="add",
            selectedCount=0,
            canTransfer=False,
            dirty=False,
            busy=False,
            saving=False,
            error="",
        )

        def rows(value):
            return [
                dict(
                    key=row["searchKey"],
                    **{
                        key: row[key]
                        for key in ("title", "subtitle", "previewUrl", "accent")
                        if key in row
                    },
                )
                for row in value._records
            ]

        fixture = dict(
            fixture,
            model=dict(
                model,
                available=rows(link_controller.available_model),
                linked=rows(link_controller.linked_model),
            ),
        )
        for key, value in dict(
            sobjectLinkController=link_controller,
            linkAvailableModel=link_controller.available_model,
            linkLinkedModel=link_controller.linked_model,
            linkCurrentModel=link_controller.linked_model,
        ).items():
            engine.rootContext().setContextProperty(key, value)
    hours_parent = hours_controller = None
    if original and fixture["screen"] == "inspector":
        from thlib.ui.work_hours import WorkHoursController

        hours_parent = QObject()
        hours_controller = WorkHoursController(hours_parent)
        hours_controller._task_code = "T1"
        hours_controller._summary_by_task["T1"] = fixture["model"].get("summary", {})
        engine.rootContext().setContextProperty("tasksController", controller)
        engine.rootContext().setContextProperty("workHoursController", hours_controller)
    editor_controller = None
    if original and fixture["screen"] == "editor":
        from thlib.ui.sobject_editor import SObjectEditorController
        from tests.test_sobject_editor import SObjectEditorQmlTests

        editor_controller = SObjectEditorController(lambda: {})
        editor_controller._title = fixture["model"]["title"]
        editor_controller._search_type = fixture["model"]["searchType"]
        editor_controller._batch_enabled = fixture["model"]["batchEnabled"]
        editor_controller._batch_count = 3
        editor_controller.model.replace(
            [
                SObjectEditorQmlTests._field("name", "string", "Hero Robot"),
                SObjectEditorQmlTests._field(
                    "description", "multiline", "Object description"
                ),
            ]
        )
        engine.rootContext().setContextProperty(
            "sobjectEditorController", editor_controller
        )
        engine.rootContext().setContextProperty(
            "sobjectFieldModel", editor_controller.model
        )
    models = []
    bindings = {
        "sobjectTaskStatusModel": "task_statuses",
        "sobjectTaskProcessModel": "task_processes",
        "sobjectTaskModel": "tasks",
        "sobjectParticipantModel": "participants",
        "sobjectNoteModel": "notes",
        "sobjectChildModel": "children",
        "sobjectChildTypeModel": "child_types",
        "sobjectSnapshotProcessModel": "snapshot_processes",
        "sobjectActivityModel": "activity",
        "sobjectDependencyModel": "groups",
    }
    for name, source in bindings.items():
        rows = fixture["model"].get(source, [])
        model = RecordListModel(tuple(rows[0]) if rows else (), rows)
        models.append(model)
        engine.rootContext().setContextProperty(name, model)
    user = RecordListModel(
        ("login", "displayName", "initials", "avatarUrl", "avatarColor"),
        [
            dict(
                login="admin",
                displayName="Administrator",
                initials="A",
                avatarUrl="",
                avatarColor="#437b70",
            )
        ],
    )
    models.append(user)
    engine.rootContext().setContextProperty("userListModel", user)
    translator = (
        CatalogTranslator(TH / "thlib/ui/translations/ru.json")
        if fixture["language"] == "ru"
        else None
    )
    if translator:
        app.installTranslator(translator)
    theme_component = QQmlComponent(engine, QUrl.fromLocalFile(str(qml / "Theme.qml")))
    theme = theme_component.createWithInitialProperties(
        dict(
            dark=fixture["dark"],
            styleName=fixture["style"],
            fadeAnimationsEnabled=False,
            hoverAnimationsEnabled=False,
            clickAnimationsEnabled=False,
            popupAnimationsEnabled=False,
        )
    )
    assert theme, [e.toString() for e in theme_component.errors()]
    screen = fixture["screen"]
    model = fixture["model"]
    name = {
        "description": "DescriptionEditor",
        "summary": "SnapshotSummary",
        "toolbar": "SnapshotBrowserToolbar",
        "watch": "WatchFolderEditorView",
        "field": "SObjectFieldFrame",
        "delete": "DeleteSObjectView",
        "report": "SObjectInfoView"
        if original
        else "features/objects/ObjectReportSurface",
        "duplicate": "DuplicateSObjectView",
        "editor": "SObjectFieldEditor"
        if original
        else "features/objects/ObjectEditorSurface",
        "inspector": "TaskInspector"
        if original
        else "features/objects/ObjectInspectorQuick"
        if fixture["state"] == "quick"
        else None,
        "note": None,
        "links": "LinkSObjectsView",
    }[screen]
    props = dict(theme=theme, width=fixture["width"], height=fixture["height"])
    if screen == "report":
        if original:
            props.update(width=fixture["width"] + 30, height=3000)
        else:
            props.update(
                model=model, part="header" if fixture["state"] == "header" else "page"
            )
    if screen in ("inspector", "editor") and not original:
        props["model"] = model
    if screen == "editor":
        if original:
            props.update(
                editorWindowId="capture",
                height=1400,
                width=fixture["width"] + (40 if model["part"] == "tools" else 0),
            )
        else:
            props["part"] = model["part"]
    if screen == "inspector" and original:
        props.update(controller=controller, width=fixture["width"] + 16, height=400)
    if screen == "description":
        props.update(
            value=model["value"],
            targetTitle=model["title"],
            targetKind=model["kind"],
            editing=model["editing"],
            pinned=model["pinned"],
            saving=model["saving"],
            dirty=model["dirty"],
            canSave=model["canSave"],
            editorEnabled=model["enabled"],
            errorText=model["error"],
        )
    elif screen == "summary":
        props.update(model)
    elif screen == "toolbar":
        props["controller"] = controller
    elif screen == "field":
        props.update(
            title=model["title"],
            fieldName=model["name"],
            description=model["description"],
            iconName=model["icon"],
            errorText=model["error"],
            requiredField=model["required"],
            readOnlyField=model["readOnly"],
        )
    if screen == "editor" and not original:
        code = 'import QtQuick\nimport "features/objects" as Objects\nimport "controls" as Controls\nObjects.ObjectEditorSurface { id:fixtureEditor; views:({batchCount:countPort}); Component{id:countPort; Controls.SpinBox{theme:fixtureEditor.theme;from:2;to:100;value:3}} }'
        component = QQmlComponent(engine)
        component.setData(
            code.encode(), QUrl.fromLocalFile(str(qml / "B08Fixture.qml"))
        )
    elif name:
        component = QQmlComponent(
            engine, QUrl.fromLocalFile(str(qml / (name + ".qml")))
        )
    elif original and screen == "note" and fixture["state"] != "header":
        from note_capture import reference

        code = reference(qml, fixture["state"])
        component = QQmlComponent(engine)
        component.setData(
            code.encode(), QUrl.fromLocalFile(str(qml / "B08NoteReference.qml"))
        )
        props["model"] = model
    elif screen == "note" and not original and model.get("part") == "body":
        component = QQmlComponent(
            engine, QUrl.fromLocalFile(str(qml / "features/objects/NoteBody.qml"))
        )
        props.update(model=model, controller=controller)
    elif original and screen == "note":
        source = (qml / "CommunicationView.qml").read_text(encoding="utf-8")
        author = source.index("id: authorLabel")
        start = source.rfind("RowLayout {", 0, author)
        end = start + len("RowLayout {")
        level = 1
        while level:
            if source[end] == "{":
                level += 1
            elif source[end] == "}":
                level -= 1
            end += 1
        fragment = source[start:end].replace(
            "RowLayout {", "RowLayout { anchors.fill:parent;", 1
        )
        code = (
            'import QtQuick\nimport QtQuick.Controls\nimport QtQuick.Layouts\nimport "controls" as Controls\nItem {id:root;required property var theme;required property var model; property var timelineRow:({author: model.author,authorDisplay:model.authorLabel,timePretty:model.time,timeSimple:model.fullTime,authorColor:model.authorColor,entryType:"note",index:0,body:""});property var bubbleHover:({hovered:true});property var messageOptionsMenu:({opened:false});property int messageMenuRow:-1;'
            + fragment
            + "}"
        )
        component = QQmlComponent(engine)
        component.setData(
            code.encode(), QUrl.fromLocalFile(str(qml / "B08NoteReference.qml"))
        )
        props["model"] = model
    else:
        module = "inspector" if screen == "inspector" else "note"
        part = (
            model.get("part", "header") if screen in ("inspector", "note") else "header"
        )
        code = (
            'import QtQuick\nimport "tactic_frame" as Frame\nimport "tactic_frame/features/objects/'
            + module
            + '.ui.mjs" as UI\nFrame.FrameView { required property var model; implicitHeight:scene.height || 28; scene:UI.'
            + part
            + '(model,width,typeof localizationController === "undefined" ? "en":localizationController.current_language) }'
        )
        component = QQmlComponent(engine)
        component.setData(
            code.encode(), QUrl.fromLocalFile(str(qml / "B08Fixture.qml"))
        )
        props["model"] = model
    view = component.createWithInitialProperties(props)
    assert view, [e.toString() for e in component.errors()]
    if screen == "field":
        # The card comparison supplies the same minimum-size value port as a real form.
        host = view.findChild(QObject, "sobjectFieldEditorHost_" + model["name"])
        assert host is not None
        port = QQuickItem(host)
        port.setHeight(theme.property("controlHeight"))
        port.setParentItem(host)
        models.append(port)
        app.processEvents()
    if screen == "field" or (screen in ("editor", "inspector", "note", "report") and not original):
        fixture = dict(fixture, height=max(1, int(view.implicitHeight())))
        view.setHeight(fixture["height"])
    window = QQuickWindow()
    window.resize(
        props["width"],
        props["height"]
        if original and screen in ("report", "editor", "inspector")
        else fixture["height"],
    )
    window.setColor(theme.property("background"))
    view.setParentItem(window.contentItem())
    window.show()
    try:
        crop = None
        if screen == "report" and original:
            frame(window)
            if fixture["state"] != "header":
                tabs = view.findChild(QObject, "sobjectInfoTabs")
                tabs.setProperty(
                    "currentIndex",
                    ("tasks", "notes", "children").index(fixture["model"]["page"]),
                )
            frame(window)
            item = view.findChild(
                QObject,
                "sobjectInfoPresentationHeader"
                if fixture["state"] == "header"
                else "sobjectInfoReportPages",
            )
            from PySide6.QtCore import QPointF

            point = item.mapToScene(QPointF())
            crop = QRect(
                round(point.x()),
                round(point.y()),
                round(item.width()),
                max(1, round(item.height())),
            )
        if screen == "inspector" and original:
            from PySide6.QtCore import QPointF
            from PySide6.QtQml import QQmlExpression

            frame(window)
            view.setHeight(view.implicitHeight())
            window.resize(props["width"], max(1, round(view.implicitHeight())))
            frame(window)
            names = {
                "quick": "taskInspectorTaskSurface",
                "related": "taskInspectorRelatedTasks",
                "workHours": "taskInspectorWorkHours",
            }
            if fixture["state"] == "context":
                expression = QQmlExpression(
                    QQmlEngine.contextForObject(view), view, "contextHeader"
                )
                item = expression.evaluate()[0]
                assert not expression.hasError(), expression.error().toString()
            else:
                item = view.findChild(QObject, names[fixture["state"]])
            point = item.mapToScene(QPointF())
            crop = QRect(
                round(point.x()),
                round(point.y()),
                round(item.width()),
                max(1, round(item.height())),
            )
        if screen == "editor" and original:
            from PySide6.QtCore import QPointF

            frame(window)
            if model["part"] == "tools":
                count = view.findChild(QObject, "sobjectEditorFieldCount").parentItem()
                setup = view.findChild(QObject, "sobjectBatchSetup")
                top = setup if model["batchEnabled"] else count
                point = top.mapToScene(QPointF())
                bottom = count.mapToScene(QPointF()).y() + count.height()
                crop = QRect(
                    round(point.x()),
                    round(point.y()),
                    round(top.width()),
                    round(bottom - point.y()),
                )
            else:
                item = view.findChild(
                    QObject,
                    "sobjectEditorHeader"
                    if model["part"] == "header"
                    else "sobjectEditorFooter",
                )
                point = item.mapToScene(QPointF())
                crop = QRect(
                    round(point.x()),
                    round(point.y()),
                    round(item.width()),
                    round(item.height()),
                )
        for _ in range(4):
            frame(window)
        if screen == "note" and (not original or fixture["state"] != "header"):
            view.setHeight(max(1, view.implicitHeight()))
            window.resize(fixture["width"], max(1, round(view.implicitHeight())))
            fixture = dict(fixture, height=max(1, round(view.implicitHeight())))
            frame(window)
        assert not warnings, warnings
        baseline_icon_errors = []
        if original:
            try:
                assert_icons(window)
            except AssertionError as error:
                baseline_icon_errors.append(str(error))
        else:
            assert_icons(window)
        filename = (
            "-".join(
                [
                    screen,
                    fixture["state"],
                    "original" if original else "native",
                    fixture["style"],
                    "dark" if fixture["dark"] else "light",
                    fixture["language"],
                    str(fixture["width"]),
                ]
            )
            + ".png"
        )
        pixels = window.grabWindow()
        assert (pixels.copy(crop) if crop else pixels).save(str(OUT / filename))
        measured = snapshot(window) if not original else {}
        aliases = {}
        if screen == "links" and not original:
            # Retain the public native SmoothListView names while measuring the same value ports.
            aliases = {
                "linkList_available": "linkObjectList-remove",
                "linkList_linked": "linkObjectList-add",
            }
            for common, native_name in aliases.items():
                if native_name in measured["boxes"]:
                    measured["boxes"][common] = measured["boxes"][native_name]
        return dict(
            fixture=fixture,
            image=filename,
            valuePortAliases=aliases,
            original=original,
            baselineIconErrors=baseline_icon_errors,
            referenceGeometry=snapshot(window, check_icons=False) if original else None,
            crop=dict(x=crop.x(), y=crop.y()) if crop else dict(x=0, y=0),
            **measured,
        )
    finally:
        window.close()
        view.setParentItem(None)
        view.deleteLater()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        if translator:
            app.removeTranslator(translator)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    archived = ROOT / ".tmp/frame_objects" / ("reference-" + REFERENCE["commit"][:12])
    if not (archived / "thlib/ui/qml/DescriptionEditor.qml").is_file():
        archived.mkdir(parents=True, exist_ok=True)
        packed = archived.parent / ("reference-" + REFERENCE["commit"][:12] + ".zip")
        with packed.open("wb") as output:
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(TH),
                    "archive",
                    "--format=zip",
                    REFERENCE["commit"],
                    "thlib/ui/qml",
                ],
                stdout=output,
                check=True,
            )
        with zipfile.ZipFile(packed) as archive:
            assert all(
                (archived / name).resolve().is_relative_to(archived.resolve())
                for name in archive.namelist()
            )
            archive.extractall(archived)
    app = gui_test_application()
    rows = []
    for original in (True, False):
        qml = (archived if original else TH) / "thlib/ui/qml"
        for fixture in fixtures(args.smoke):
            rows.append(capture(app, qml, fixture, original))
    names = [
        "thlib/ui/qml/" + name
        for name in (
            "DescriptionEditor.qml",
            "SnapshotSummary.qml",
            "SnapshotBrowserToolbar.qml",
            "SnapshotBrowser.qml",
            "SnapshotBrowserOptionsMenu.qml",
            "WatchFolderEditorView.qml",
            "SObjectFieldFrame.qml",
            "SObjectFieldGrid.qml",
            "SObjectInfoView.qml",
            "SObjectSnapshotTree.qml",
            "DeleteSObjectView.qml",
            "features/objects/DescriptionValue.qml",
            "features/objects/ObjectReportSurface.qml",
        )
    ]
    names += [
        "thlib/ui/" + name + ".py"
        for name in (
            "sobject_info",
            "sobject_delete",
            "sobject_duplicate",
            "sobject_editor",
            "sobject_link",
            "communication",
        )
    ]
    names += [
        "thlib/ui/qml/" + name + ".qml"
        for name in (
            "DuplicateSObjectView",
            "LinkSObjectsView",
            "LinkList",
            "SObjectFieldEditor",
            "CommunicationView",
            "TaskInspector",
            "WorkHoursSummary",
            "features/objects/ObjectEditorSurface",
            "features/objects/ObjectInspectorQuick",
            "features/objects/ObjectDependencyList",
            "features/objects/NoteBody",
            "features/objects/NoteEditDialog",
            "features/objects/NoteDeleteDialog",
            "controls/SearchField",
            "tactic_frame/core/FrameView",
        )
    ]
    names += ["thlib/ui/translations/ru.json"]
    shared, native = source_hashes(ROOT, TH, names)
    result = dict(
        smoke=args.smoke,
        captures=rows,
        shared=shared,
        nativeSources=native,
        driver=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        driverSources={
            path.relative_to(ROOT).as_posix(): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in (
                Path(__file__),
                Path(__file__).with_name("object_fixtures.py"),
                Path(__file__).with_name("reference.json"),
                Path(__file__).with_name("note_capture.py"),
            )
        },
        originalCommit=REFERENCE["commit"],
    )
    (OUT / "native.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Captured", len(rows), "B08 production/reference states; smoke:", args.smoke)


if __name__ == "__main__":
    main()
