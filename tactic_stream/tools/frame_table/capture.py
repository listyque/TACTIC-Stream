"""Capture production Table View and inline editors against the B06 checkpoint."""

import hashlib
import json
import os
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HANDLER = Path("D:/code/th_codex")
OUT = Path(__file__).parent / "output"
sys.path[:0] = [str(HANDLER), str(ROOT / "tools/frame_admin")]
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

from native_capture import snapshot, source_hashes
from PySide6.QtCore import (
    Property,
    QCoreApplication,
    QEvent,
    QObject,
    QPoint,
    QPointF,
    QUrl,
    Slot,
    Qt,
)
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtTest import QTest
from tests.profile_ui_responsiveness import frame
from tests.qt_application import gui_test_application
from tests.test_columns_table_view import _TableColumns, _TableController, _visual_items
from thlib.ui.icon_font import qml_icon_bindings
from thlib.ui.localization import CatalogTranslator
from thlib.ui.workspace_models.records import RecordListModel
from thlib.ui.workspace_models.results import WorkspaceItemModel
from thlib.ui.workspace_models.results_types import WorkspaceNode

DATA = json.loads(
    (ROOT / "reports/table-view-2026-10-14/fixture.json").read_text(encoding="utf-8")
)
VALUES = json.loads(
    (ROOT / "tests/fixtures/frame_table_values.json").read_text(encoding="utf-8")
)


class Locale(QObject):
    def __init__(self, language):
        super().__init__()
        self.language = language

    @Property(str, constant=True)
    def current_language(self):
        return self.language


class Columns(_TableColumns):
    def __init__(self):
        super().__init__()
        self._columns = []
        for index, column in enumerate(DATA["definition"]["table"]["elements"]):
            descriptor = column["cell"]
            self._columns.append(
                dict(
                    row=index,
                    name=column["name"],
                    label=column["title"],
                    width=int(column["attributes"]["width"]),
                    hideOrder=int(column["attributes"].get("th_hide_order", 0)),
                    kind=descriptor["kind"],
                    dataType=DATA["definition"]["columns"]
                    .get(descriptor["field"], {})
                    .get("data_type", ""),
                    sortable=descriptor["sortable"],
                    editable=descriptor.get("editable", False),
                    displayOptions=column["display"]["options"],
                )
            )

    @Slot(str, int, result="QVariantMap")
    def row_cells(self, key, revision):
        return DATA["cells"].get(key, {})


class Controller(_TableController):
    @Slot(str, str, result="QVariantList")
    def process_count_actions(self, node_id, panel):
        if panel != "notes":
            return []
        values = DATA["cells"][node_id]["notes"]["processes"]
        return [
            dict(
                title=value["label"] or value["process"],
                process=value["process"],
                badgeCount=value["count"],
                accent=value["accent"],
            )
            for value in values
        ]


def reference():
    target = ROOT / ".tmp/b07/reference"
    with zipfile.ZipFile(ROOT / ".tmp/b07/handler-before.zip") as archive:
        for name in archive.namelist():
            path = target / name
            assert path.resolve().is_relative_to(target.resolve())
            if name.endswith("/"):
                continue
            raw = archive.read(name)
            if path.exists():
                assert path.read_bytes() == raw
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
    return target / "thlib/ui/qml"


def capture(fixture, qml, original):
    app = gui_test_application()
    engine = QQmlEngine()
    warnings = []
    engine.warnings.connect(
        lambda items: warnings.extend(item.toString() for item in items)
    )
    locale = Locale(fixture["language"])
    engine.rootContext().setContextProperty("localizationController", locale)
    for name, value in qml_icon_bindings(HANDLER, app).items():
        engine.rootContext().setContextProperty(name, value)
    translator = None
    if fixture["language"] == "ru":
        translator = CatalogTranslator(HANDLER / "thlib/ui/translations/ru.json")
        app.installTranslator(translator)
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(qml / "Theme.qml")))
    theme = component.createWithInitialProperties(
        dict(
            dark=fixture["dark"],
            styleName=fixture["style"],
            fadeAnimationsEnabled=False,
            hoverAnimationsEnabled=False,
            clickAnimationsEnabled=False,
            popupAnimationsEnabled=False,
        )
    )
    assert theme, component.errors()
    model = WorkspaceItemModel()
    controller = Controller()
    columns = Columns()
    identities = {}
    for row in DATA["cells"].values():
        for cell in row.values():
            for task in cell.get("tasks", []):
                identity = task.get("assignedIdentity")
                if identity:
                    identities[identity["login"]] = identity
    users = RecordListModel(
        ("login", "initials", "avatarUrl", "avatarColor"), list(identities.values())
    )
    keep = [component, theme, locale, model, controller, columns, users]
    if fixture["screen"] == "table":
        model.replace_nodes(
            [
                WorkspaceNode(
                    node_id=row["__search_key__"],
                    node_type="sobject",
                    search_key=row["__search_key__"],
                    code=row["code"],
                    title=row["name"],
                    values=row,
                    accent=DATA["accent"],
                    comments=4,
                    tasks=2,
                )
                for row in DATA["records"]
            ]
        )
        controller._selected = [DATA["records"][2]["__search_key__"]]
        component = QQmlComponent(
            engine, QUrl.fromLocalFile(str(qml / "SearchResultTable.qml"))
        )
        view = component.createWithInitialProperties(
            dict(
                theme=theme,
                controller=controller,
                columnsController=columns,
                resultModel=model,
                userModel=users,
                presentationActive=True,
                width=fixture["width"],
                height=fixture["height"],
            )
        )
    elif fixture["screen"] == "append":
        from thlib.ui.table.file_append import SnapshotAppendController
        from types import SimpleNamespace
        owner = SnapshotAppendController(SimpleNamespace())
        owner._model.update(fixture['model'])
        owner._add_records([dict(path=row['name'], title=row['name'], size=row['size']) for row in fixture['files']])
        owner.files.replace([dict(row,canRemove=not owner.busy) for row in owner.files.records()])
        keep.append(owner)
        component = QQmlComponent(engine, QUrl.fromLocalFile(str(qml / 'features/table/SnapshotAppendView.qml')))
        view = component.createWithInitialProperties(dict(theme=theme, owner=owner,
            width=fixture['width'], height=fixture['height']))
    elif fixture["screen"] == "checkout":
        from thlib.ui.table.file_checkout import SnapshotCheckoutController
        from types import SimpleNamespace
        from unittest.mock import Mock
        owner = SnapshotCheckoutController(SimpleNamespace(repository_sync=Mock(), window_model=Mock()))
        owner._state.update(fixture['model'])
        owner._snapshot = dict(code='S7',version=7,context='publish/reference')
        owner._records = [dict(row) for row in fixture['files']]
        owner._selected = 'F1'
        owner._rebuild()
        keep.append(owner)
        component = QQmlComponent(engine, QUrl.fromLocalFile(str(qml / 'features/table/SnapshotCheckoutView.qml')))
        view = component.createWithInitialProperties(dict(theme=theme, owner=owner,
            width=fixture['width'],height=fixture['height']))
    elif fixture["screen"] == "nested":
        from tests.test_table_nested import Scope
        scope = Scope()
        scope.state = fixture['model']
        keep.append(scope)
        component = QQmlComponent(engine, QUrl.fromLocalFile(str(qml / 'features/table/NestedTableView.qml')))
        view = component.createWithInitialProperties(dict(theme=theme, controller=controller,
            columnsController=columns, userModel=users, services=None, administration=None, scope=scope,
            width=fixture['width'], height=fixture['height']))
    elif fixture['screen'] == 'parent':
        from tests.test_table_parent_group import ParentResponses
        owner = ParentResponses()
        owner._open = False
        keep.append(owner)
        component = QQmlComponent(engine, QUrl.fromLocalFile(str(qml / 'features/table/ParentGroupView.qml')))
        view = component.createWithInitialProperties(dict(theme=theme, owner=owner, state=fixture['model'],
            width=fixture['width'], height=fixture['height']))
    elif fixture['screen'] == 'parent-group':
        component = QQmlComponent(engine, QUrl.fromLocalFile(str(qml / 'features/table/ParentGroupHeader.qml')))
        view = component.createWithInitialProperties(dict(theme=theme, model=fixture['model'], editable=True,
            width=fixture['width'], height=fixture['height']))
    elif fixture['screen'] == 'dependencies':
        from tests.test_table_dependencies import DependencyResponses
        owner = DependencyResponses(fixture['data'], fixture['mode'])
        keep.append(owner)
        component = QQmlComponent(engine, QUrl.fromLocalFile(str(qml / 'features/table/DependenciesView.qml')))
        view = component.createWithInitialProperties(dict(theme=theme, owner=owner, model=fixture['data']['seed'],
            width=fixture['width'], height=fixture['height']))
    elif fixture["screen"] == "cell":
        value = fixture["value"]
        component = QQmlComponent(
            engine, QUrl.fromLocalFile(str(qml / "TacticTableCellDisplay.qml"))
        )
        view = component.createWithInitialProperties(
            dict(
                theme=theme,
                controller=controller,
                columnsController=columns,
                userModel=users,
                nodeId=DATA["records"][0]["__search_key__"],
                kind=value["kind"],
                cell=value["cell"],
                textValue=value["cell"].get("text", ""),
                columnIndex=1,
                previewActive=False,
                previewUrl="",
                previewRevealed=False,
                title="Value",
                accent=DATA["accent"],
                comments=0,
                tasks=0,
                displayOptions={},
                width=fixture["width"],
                height=fixture["height"],
            )
        )
    else:
        component = QQmlComponent(
            engine, QUrl.fromLocalFile(str(qml / "features/table/ValueEditor.qml"))
        )
        view = component.createWithInitialProperties(
            dict(
                theme=theme,
                descriptor=fixture["descriptor"],
                mode=fixture["mode"],
                width=fixture["width"],
                count=2,
                height=fixture["height"],
            )
        )
    keep.append(component)
    assert view, [item.toString() for item in component.errors()]
    window = QQuickWindow()
    window.resize(fixture["width"], fixture["height"])
    popup_editor = fixture['screen'] == 'inline' and fixture['mode'] in ('multiline', 'tags', 'date', 'datetime', 'color')
    window.setColor(theme.property("surfaceContainerHigh" if popup_editor else "background"))
    view.setParentItem(window.contentItem())
    window.show()
    try:
        frame(window)
        if fixture['screen'] == 'dependencies' and fixture['mode'] == 'expanded':
            item = next(item for item in _visual_items(view) if item.objectName() == 'dependencyExpand_root_0')
            point = item.mapToScene(QPointF(item.width()/2,item.height()/2)).toPoint()
            QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, point)
            frame(window)
        QTest.mouseMove(window, QPoint(window.width() + 30, window.height() + 30))
        QCoreApplication.sendEvent(window, QEvent(QEvent.Leave))
        if fixture["screen"] == "table":
            window.contentItem().forceActiveFocus()
        frame(window)
        assert not warnings, warnings
        name = (
            "-".join(
                [
                    fixture["screen"],
                    fixture.get("mode", fixture.get("value", {}).get("name", "")),
                    "original" if original else "native",
                    fixture["style"],
                    "dark" if fixture["dark"] else "light",
                    fixture["language"],
                    str(fixture["width"]),
                ]
            )
            + ".png"
        )
        assert window.grabWindow().save(str(OUT / name))
        result = dict(fixture=fixture, original=original, image=name)
        if fixture['screen'] == 'append':
            result['enabled'] = {item.objectName():item.isEnabled() for item in _visual_items(view)
                if item.objectName() in ('objectCheckinFileRemove_0','objectCheckinChooseFiles','objectCheckinSubmit')}
        if fixture['screen'] == 'checkout':
            result['enabled'] = {item.objectName():item.isEnabled() for item in _visual_items(view)
                if item.objectName() in ('snapshotCheckoutDownload','snapshotCheckoutClose','snapshotCheckoutFile_F1')}
        if not original:
            result.update(snapshot(window))
        if fixture.get('value', {}).get('name') == 'object_summary':
            result['summaryText'] = {}
            for index, entry in enumerate(fixture['value']['cell']['summary']):
                name = 'tableSummaryText_' + str(index)
                item = next(item for item in _visual_items(view) if item.objectName() == name and item.property('text') is not None)
                assert item.isVisible() and item.property('paintedWidth') > 0, 'Missing visible summary text: ' + name
                result['summaryText'][name] = item.property('text')
        if fixture['screen'] == 'nested':
            result['embeddedText'] = {}
            for item in _visual_items(view):
                text = item.property('text')
                if text not in ('Robot 0', 'Configured nested table') or item.property('paintedHeight') is None:
                    continue
                point = item.mapToScene(QPointF())
                record = dict(x=point.x() + float(item.property('leftPadding') or 0),
                    centerY=point.y() + item.height() / 2,
                    fontSize=item.property('font').pixelSize(), weight=item.property('font').weight())
                previous = result['embeddedText'].get(text)
                if previous is None or record['centerY'] < previous['centerY']:
                    result['embeddedText'][text] = record
        result["table"] = {
            item.objectName(): dict(
                x=item.mapToScene(QPointF(0, 0)).x(),
                y=item.mapToScene(QPointF(0, 0)).y(),
                width=item.width(),
                height=item.height(),
            )
            for item in _visual_items(view)
            if item.objectName()
            in ("tableHeaderSurface", "tableCellPreview", "tableColumnHeaderLabel_name")
        }
        result["paint"] = {
            name: theme.property(name).name()
            for name in (
                "surfaceContainer",
                "surfaceContainerLow",
                "secondaryText",
                "contentSelection",
            )
        }
        result['background'] = theme.property('surfaceContainerHigh').name() if fixture['screen'] in ('append','checkout') else window.color().name()
        if fixture['screen'] == 'checkout' and fixture['mode'] == 'busy':
            progress = next(item for item in _visual_items(view)
                if 'ProgressBar' in item.metaObject().className() and item.property('theme') is not None)
            background = progress.property('background')
            point = background.mapToScene(QPointF())
            fill = progress.property('contentItem').property('color')
            track = background.property('color')
            assert fill == theme.property('action')
            assert abs(track.alphaF() - 0.25) < 0.005
            result['progress'] = dict(value=progress.property('position'),
                fill=list(fill.getRgb()), track=list(track.getRgb()),
                bounds=dict(x=point.x(), y=point.y(), width=background.width(), height=background.height()))
        result["completionTracks"] = [
            dict(
                x=item.mapToScene(QPointF()).x(),
                y=item.mapToScene(QPointF()).y(),
                width=item.width(),
                height=item.height(),
            )
            for item in _visual_items(view)
            if item.objectName() == "tableCellCompletionTrack"
            and 0 <= item.mapToScene(QPointF()).y() < fixture["height"]
        ]
        return result
    finally:
        window.close()
        view.setParentItem(None)
        view.deleteLater()
        window.deleteLater()
        if translator:
            app.removeTranslator(translator)
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    archived = reference()
    names = [
        "thlib/ui/qml/" + name + ".qml"
        for name in (
            "SearchResultTable",
            "SearchResultTableHeader",
            "TacticTableCellDisplay",
            "TacticTaskCell",
            "TacticTaskCards",
            "TacticTableActionCell",
            "TacticTableInlineEditor",
            "TacticCompletionCell",
            "TacticStructuredTableCell",
            "TableViewPresetMenu",
        )
    ]
    names += [
        "thlib/ui/qml/features/table/" + name + ".qml"
        for name in ("ValueEditor", "TaskSummaryCell", "ValueFieldsCell", "MessageCell", "ServiceCell", "ServiceDialogs", "DocumentView", "NestedTableView", "SnapshotAppendView", "SnapshotCheckoutView", "DependenciesView")
    ]
    names += [
        "tests/test_columns_table_view.py",
        "tests/test_frame_table.py",
        "thlib/ui/workspace_models/results.py",
        "thlib/tactic_table_widgets.py",
        "thlib/tactic_query.py",
        "thlib/ui/table/services.py",
        "thlib/ui/table/scripts.py",
        "thlib/ui/table/script_worker.py",
        "thlib/ui/table/requests.py",
        "thlib/ui/table/nested.py",
        "tests/test_table_nested.py",
        "tests/test_table_append.py",
        "tests/test_table_checkout.py",
        "thlib/ui/table/file_append.py",
        "thlib/ui/table/file_checkout.py",
        "thlib/repository_download.py",
        "thlib/tactic_classes.py",
        "thlib/ui/qml/features/table/runtime/client_api.js",
        "thlib/ui/qml/features/table/runtime/table_action_runtime.js",
        "thlib/ui/translations/ru.json",
    ]
    names += ['thlib/ui/table/dependencies.py', 'thlib/ui/table/requests.py', 'tests/test_table_dependencies.py',
        'thlib/ui/table/parent_group.py', 'tests/test_table_parent_group.py', 'thlib/ui/workspace_models/results_organization.py']
    shared, native = source_hashes(ROOT, HANDLER, names)
    captures = []
    for style in ("md3", "fluent", "material5"):
        for dark in (False, True):
            for language in ("en", "ru"):
                parent = json.loads((ROOT/'tests/fixtures/frame_table_parent.json').read_text(encoding='utf-8'))
                for width in (288, 800):
                    for mode, model in parent['models'].items():
                        fixture = dict(screen='parent', mode=mode, width=width, height=480,
                            style=style, dark=dark, language=language, model=model)
                        captures.append(capture(fixture, HANDLER/'thlib/ui/qml', False))
                    for closed in (False, True):
                        fixture = dict(screen='parent-group', mode='closed' if closed else 'open', width=width, height=64,
                            style=style, dark=dark, language=language, model=dict(cell=parent['cell'],count=3,closed=closed))
                        captures.append(capture(fixture, HANDLER/'thlib/ui/qml', False))
                for width in (320, 800):
                    for mode in ('tree','expanded','empty','error'):
                        fixture = dict(screen='dependencies', mode=mode, width=width, height=440,
                            style=style,dark=dark,language=language,
                            data=json.loads((ROOT/'tests/fixtures/frame_table_dependencies.json').read_text(encoding='utf-8')))
                        captures.append(capture(fixture,HANDLER/'thlib/ui/qml',False))
                for width in (360, 800, 1496):
                    fixture = dict(
                        screen="table",
                        width=width,
                        height=420,
                        style=style,
                        dark=dark,
                        language=language,
                    )
                    captures.append(capture(fixture, archived, True))
                    captures.append(capture(fixture, HANDLER / "thlib/ui/qml", False))
                for width in (320, 800):
                    fixture = dict(screen='nested', mode='scope', width=width, height=320, style=style, dark=dark, language=language,
                        model=json.loads((ROOT / 'tests/fixtures/frame_table_nested.json').read_text(encoding='utf-8')))
                    captures.append(capture(fixture, HANDLER / 'thlib/ui/qml', False))
                for value in VALUES:
                    fixture = dict(
                        screen="cell",
                        value=value,
                        width=280,
                        height=118 if value["name"] == "object_summary" else 102 if value["name"] == "object_connections" else 90 if value["name"] in ("legacy_tasks","custom_layout","drop_links") else 58,
                        style=style,
                        dark=dark,
                        language=language,
                    )
                    captures.append(capture(fixture, HANDLER / "thlib/ui/qml", False))
                for width in (360, 760):
                    for state in ('ready', 'loading', 'error', 'unknown', 'discard'):
                        fixture = dict(screen='append', mode=state, width=width, height=700,
                            style=style, dark=dark, language=language,
                            model=dict(append=True, ready=state!='loading', busy=state=='loading',
                                appendUncertain=state=='unknown', discard=state=='discard', error='Choose a valid file type' if state=='error' else '',
                                process='publish', context='publish/reference', fileType='reference', keepFileName=True,
                                count=2, processes=[dict(value='publish',label='publish')]),
                            files=[dict(name='reference.txt',size=1024),dict(name='preview.png',size=4096)])
                        captures.append(capture(fixture, HANDLER / 'thlib/ui/qml', False))
                for width in (360,760):
                    for state in ('ready','loading','error','busy','empty'):
                        files = [dict(token='F1',title='scene.ma',fileType='main',bytes=1024,selected=True,enabled=state!='busy'),
                            dict(token='F2',title='reference.txt',fileType='reference',bytes=4096,selected=False,enabled=state!='busy')]
                        if state in ('loading','error','empty'):
                            files=[]
                        fixture = dict(screen='checkout',mode=state,width=width,height=560,
                            style=style,dark=dark,language=language,
                            model=dict(ready=state in ('ready','busy','empty'),loading=state=='loading',busy=state=='busy',
                                error='File Offline' if state=='error' else '',message='',progress=0.4 if state=='busy' else 0,
                                context='publish/reference',count=len(files)),files=files)
                        captures.append(capture(fixture,HANDLER/'thlib/ui/qml',False))
                for mode in (
                    "text",
                    "multiline",
                    "select",
                    "bool",
                    "date",
                    "datetime",
                    "color",
                    "tags",
                ):
                    value = (
                        True
                        if mode == "bool"
                        else "2030-05-01T12:30"
                        if mode in ("date", "datetime")
                        else "#4a8197"
                        if mode == "color"
                        else "Production asset"
                    )
                    fixture = dict(
                        screen="inline",
                        mode=mode,
                        width=360,
                        height=336
                        if mode == "multiline"
                        else 154
                        if mode == "tags"
                        else 84
                        if mode in ("date", "datetime", "color")
                        else 40,
                        descriptor=dict(
                            fieldValue=value,
                            fieldName="Description" if mode == "multiline" else "Value",
                            fieldOptions=[
                                dict(
                                    value="Production asset", label="Production asset"
                                ),
                                dict(value="Other", label="Other"),
                            ],
                        ),
                        style=style,
                        dark=dark,
                        language=language,
                    )
                    captures.append(capture(fixture, HANDLER / "thlib/ui/qml", False))
    assert (shared, native) == source_hashes(ROOT, HANDLER, names)
    result = dict(
        status="captured",
        reference="Tracked pre-B07 Handler B06; already includes earlier Frame migrations",
        referenceCommit=(ROOT / ".tmp/b07/handler-head.txt").read_text().strip(),
        sha256=shared,
        nativeSources=native,
        driverSources={
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in (
                "tools/frame_table/capture.py",
                "tools/frame_table/TableFixture.vue",
                "tests/fixtures/frame_table_values.json",
                "tests/fixtures/frame_table_nested.json",
                "tests/fixtures/frame_table_dependencies.json",
                "tests/fixtures/frame_table_parent.json",
                "reports/table-view-2026-10-14/fixture.json",
            )
        },
        data=DATA,
        captures=captures,
    )
    (OUT / "native.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Captured", len(captures), "table and inline states")


if __name__ == "__main__":
    main()
