"""Capture production search controls against the archived pre-B06 Handler."""

import hashlib
import io
import json
import os
from pathlib import Path
import sys
import subprocess
import tarfile
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
HANDLER = Path("D:/grav/Tactic Stream/TH")
sys.path[:0] = [str(HANDLER), str(ROOT / "tools/frame_admin")]
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Material")

from PySide6.QtCore import QCoreApplication, QEvent, QObject, QPoint, Property, QUrl
from PySide6.QtGui import QColor
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtTest import QTest
from tests.qt_application import gui_test_application
from tests.profile_ui_responsiveness import frame
from tests.test_workspace_result_item import (
    WorkspaceResultItemTests,
    _WorkspaceAppController,
)
from tests.test_process_menu_latency import ProcessMenuLatencyTests
from thlib.ui.filter_editor import FilterEditorController
from thlib.ui.icon_font import qml_icon_bindings
from thlib.ui.localization import CatalogTranslator
from native_capture import snapshot, source_hashes

OUT = Path(__file__).resolve().parent / "output"
REFERENCE_COMMIT = "533507ad37843089c2bb921ba4d37cadfb3249a5"
CURRENT = HANDLER / "thlib/ui/qml"


def original_reference():
    """Read the known checkpoint; never overwrite an edited reference file."""
    reference = ROOT / ".tmp/frame_search_reference" / REFERENCE_COMMIT
    assert reference.resolve().is_relative_to(ROOT.resolve())
    archive = subprocess.check_output(
        [
            "git",
            "-C",
            str(HANDLER),
            "archive",
            "--format=tar",
            REFERENCE_COMMIT,
            "thlib/ui/qml",
        ]
    )
    sources = {}
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as stream:
        for member in stream.getmembers():
            if member.isdir():
                continue
            assert member.isfile(), member.name
            target = reference / member.name
            assert target.resolve().is_relative_to(reference.resolve()), member.name
            content = stream.extractfile(member).read()
            if target.exists():
                assert target.read_bytes() == content, "Reference was edited: " + str(
                    target
                )
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
            sources[member.name] = hashlib.sha256(content).hexdigest()
    return reference / "thlib/ui/qml", sources


class Locale(QObject):
    def __init__(self, language):
        super().__init__()
        self.language = language

    @Property(str, constant=True)
    def current_language(self):
        return self.language


def data(screen, width, language, dark, style):
    card = screen.startswith("card")
    is_snapshot = "snapshot" in screen
    key = "sthpw/snapshot?code=SNAP001" if is_snapshot else "demo/asset?code=ASSET001"
    node = dict(
        id=key,
        kind="snapshot" if is_snapshot else "object",
        title="robot_model.ma" if is_snapshot else "Firetruck",
        subtitle="Approved production model",
        depth=0,
        hasChildren=True,
        expanded=True,
        record=dict(
            __search_key__=key,
            name="Firetruck",
            context="model/main",
            description="Approved production model",
        ),
        task_count=2,
        note_count=3,
        accent="#607d8b",
        branches=[],
        info_items=[],
        progress_items=[],
    )
    if is_snapshot:
        node["record"].update(version=1, repo="main")
        node["snapshot_display"] = dict(
            title="robot_model.ma",
            version="v001",
            repository="main",
            author="admin",
            exists=True,
            latest=True,
        )
    rows = [
        dict(
            column="name",
            columnTitle="name",
            relation="EQI",
            value="robot",
            rowEnabled=True,
            operator="begin",
            isDefault=True,
            relations=[
                dict(value="EQI", label="Contains"),
                dict(value="=", label="Is"),
            ],
        ),
        dict(
            column="description",
            columnTitle="description",
            relation="EQI",
            value="production",
            rowEnabled=False,
            operator="and",
            isDefault=False,
            relations=[
                dict(value="EQI", label="Contains"),
                dict(value="=", label="Is"),
            ],
        ),
    ]
    model = dict(
        count=50,
        total=178,
        range="1–50",
        mode="pages",
        page=1,
        pageCount=4,
        pageSize=50,
        hasNext=True,
        hasPrevious=False,
        busy=False,
        canCreate=True,
        capabilities={},
    )
    if screen == "tags":
        model = dict(busy=False, count=8, selected=1, search="")
    elif screen == "quick":
        model = dict(
            busy=False, loaded=True, count=2, personalized=True, disabled=False
        )
    elif screen == "visibility":
        model = dict(valid=True, dirty=True)
    return dict(
        screen=screen,
        viewportWidth=max(800, width),
        width=212 if card else width,
        height=244
        if card
        else 100
        if screen == "row"
        else 84
        if screen == "snapshot"
        else 58
        if screen == "footer"
        else 90
        if screen == "tags"
        else (138 if width < (460 if language == "ru" else 404) else 48)
        if screen == "visibility"
        else 36
        if screen == "quick"
        else 600,
        node=node if screen in ("row", "snapshot", "card", "card_snapshot") else None,
        rows=rows,
        columns=[
            dict(value=value, label=value) for value in ("name", "description", "code")
        ],
        presets=[dict(view="link_search:assets:demo/asset", title="Production assets")],
        model=model,
        language=language,
        dark=dark,
        style=style,
    )


def capture(fixture, qml, original, case):
    app = gui_test_application()
    engine = QQmlEngine()
    warnings = []
    engine.warnings.connect(
        lambda errors: warnings.extend(error.toString() for error in errors)
    )
    locale = Locale(fixture["language"])
    engine.rootContext().setContextProperty("localizationController", locale)
    for name, value in qml_icon_bindings(HANDLER, app).items():
        engine.rootContext().setContextProperty(name, value)
    translator = None
    if fixture["language"] == "ru":
        translator = CatalogTranslator(HANDLER / "thlib/ui/translations/ru.json")
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
    assert theme, theme_component.errors()
    theme.setParent(engine)
    controller = _WorkspaceAppController()
    engine.rootContext().setContextProperty("appController", controller)
    width, height = fixture["width"], fixture["height"]
    components, owners = [theme_component], [controller, locale]
    if fixture["node"]:
        card = fixture["screen"].startswith("card")
        node = fixture["node"]
        props = dict(
            nodeType="snapshot" if node["kind"] == "snapshot" else "sobject",
            title=node["title"],
            subtitle=node["subtitle"],
            searchKey=node["id"],
            hasChildren=True,
            tasks=2,
            comments=3,
            width=width,
            height=height,
        )
        if node["kind"] == "snapshot":
            props.update(
                process="model/main",
                version="v001",
                repository="main",
                author="admin",
                isLatest=True,
            )
        else:
            props.update(status="")
        source = "WorkspaceCard.qml" if card else "WorkspaceResultItem.qml"
        properties = (
            WorkspaceResultItemTests.card_properties
            if card
            else WorkspaceResultItemTests.item_properties
        )(theme, **props)
        if not card:
            properties.update(depth=0, compactMode=False, fileExists=True)
        component = QQmlComponent(engine, QUrl.fromLocalFile(str(qml / source)))
        view = component.createWithInitialProperties(properties)
    elif fixture["screen"] == "advanced":
        state = case.controller.workspace_state
        state.filter_column_model.replace(fixture["columns"])
        state.filter_model.replace(
            [
                {
                    key: value
                    for key, value in row.items()
                    if key not in ("columnTitle", "relations")
                }
                for row in fixture["rows"]
            ]
        )
        editor = FilterEditorController(
            lambda: state.filter_model._records,
            lambda: state.filter_column_model._records,
            lambda *_: [
                dict(value="EQI", label="Contains"),
                dict(value="=", label="Is"),
            ],
            lambda message: (_ for _ in ()).throw(AssertionError(message)),
        )
        editor.presets.replace(
            [dict(view="link_search:assets:demo/asset", title="Production assets")]
        )
        for name, value in dict(
            appController=case.controller,
            filterModel=state.filter_model,
            filterColumnModel=state.filter_column_model,
            advancedFilterSuggestionModel=state.advanced_filter_suggestion_model,
            filterEditorController=editor,
            filterPresetModel=editor.presets,
        ).items():
            engine.rootContext().setContextProperty(name, value)
        owners.append(editor)
        component = QQmlComponent(
            engine, QUrl.fromLocalFile(str(qml / "AdvancedSearchView.qml"))
        )
        view = component.createWithInitialProperties(
            dict(theme=theme, width=width, height=height)
        )
    else:
        module, expression = {
            "footer": (
                "footer",
                "UI.describe(Object.assign({},model,{countWidth:countMetrics.advanceWidth}),width,height,language)",
            ),
            "tags": ("popups", "UI.tagHeader(model,width,language)"),
            "quick": ("popups", "UI.quickHeader(model,width,language)"),
            "visibility": ("visibility", "UI.footer(model,width,language)"),
        }[fixture["screen"]]
        component = QQmlComponent(engine)
        component.setData(
            f'''import QtQuick
import "{CURRENT.as_uri()}/tactic_frame" as Frame
import "{CURRENT.as_uri()}/tactic_frame/features/search/{module}.ui.mjs" as UI
Item {{
    id: captureRoot
    required property var theme
    required property var model
    required property string language
    TextMetrics {{ id:countMetrics; text: UI.countText ? UI.countText(captureRoot.model,captureRoot.width,captureRoot.language) : ""; font.family:captureRoot.theme.fontFamily; font.pixelSize:14; font.hintingPreference:Font.PreferVerticalHinting }}
    Frame.FrameView {{ anchors.fill:parent; theme:parent.theme; scene:{expression} }}
}}'''.encode(),
            QUrl.fromLocalFile(str(OUT / "SearchCapture.qml")),
        )
        view = component.createWithInitialProperties(
            dict(
                theme=theme,
                model=fixture["model"],
                language=fixture["language"],
                width=width,
                height=height,
            )
        )
    components.append(component)
    assert view, [error.toString() for error in component.errors()]
    window = QQuickWindow()
    window.resize(width, height)
    window.setColor(theme.property("surfaceContainerLow"))
    view.setParentItem(window.contentItem())
    window.show()
    try:
        frame(window)
        QTest.mouseMove(window, QPoint(width + 30, height + 30))
        QCoreApplication.sendEvent(window, QEvent(QEvent.Leave))
        frame(window)
        app.processEvents()
        assert not warnings, warnings
        image = window.grabWindow()
        assert not image.isNull()
        name = f"{fixture['screen']}-{'original' if original else 'native'}-{fixture['style']}-{'dark' if fixture['dark'] else 'light'}-{fixture['language']}-{width}.png"
        assert image.save(str(OUT / name))
        result = dict(fixture=fixture, image=name, original=original)
        if not original:
            result.update(snapshot(window))
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
    original, original_sources = original_reference()
    OUT.mkdir(parents=True, exist_ok=True)
    names = [
        "thlib/ui/qml/" + name + ".qml"
        for name in (
            "AdvancedSearchView",
            "SearchPresetBar",
            "SearchWorkspaceView",
            "WorkspaceResultItem",
            "WorkspaceCard",
            "SearchResultMenus",
            "SearchResultSurface",
            "TagCloudPopup",
            "SearchQuickFilterPopup",
            "QuickFilterEditorView",
            "ProcessFilterEditorView",
        )
    ]
    names += [
        str(path.relative_to(HANDLER)).replace("\\", "/")
        for path in (CURRENT / "features/search").glob("*.qml")
    ]
    names += [
        "tests/test_process_menu_latency.py",
        "tests/test_workspace_result_item.py",
    ]
    sha256, native = source_hashes(ROOT, HANDLER, names)
    driver_sources = {
        "tools/frame_search/capture.py": hashlib.sha256(
            Path(__file__).read_bytes()
        ).hexdigest()
    }
    ProcessMenuLatencyTests.setUpClass()
    case = ProcessMenuLatencyTests()
    case.setUp()
    stype = SimpleNamespace(
        get_code=lambda: "demo/asset", get_column_data_type=lambda _: "text"
    )
    captures = []
    try:
        with patch.object(case.controller, "_active_stype", return_value=stype):
            for style in ("md3", "fluent", "material5"):
                for dark in (False, True):
                    for language in ("en", "ru"):
                        for width in (360, 800):
                            for screen in (
                                "advanced",
                                "row",
                                "snapshot",
                                "card",
                                "card_snapshot",
                                "footer",
                                "tags",
                                "quick",
                                "visibility",
                            ):
                                # Fixed-size cards need only one capture per theme/language.
                                if width == 800 and screen.startswith("card"):
                                    continue
                                fixture = data(screen, width, language, dark, style)
                                if screen in (
                                    "advanced",
                                    "row",
                                    "snapshot",
                                    "card",
                                    "card_snapshot",
                                ):
                                    captures.append(
                                        capture(fixture, original, True, case)
                                    )
                                captures.append(capture(fixture, CURRENT, False, case))
    finally:
        case.doCleanups()
    assert (sha256, native) == source_hashes(ROOT, HANDLER, names), (
        "Sources changed during capture"
    )
    assert (
        driver_sources["tools/frame_search/capture.py"]
        == hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    )
    result = dict(
        status="captured",
        reference="Tracked Handler HEAD before B06; later Frame baseline, not the pre-Frame original",
        referenceCommit=REFERENCE_COMMIT,
        originalSources=original_sources,
        driverSources=driver_sources,
        sha256=sha256,
        nativeSources=native,
        captures=captures,
    )
    (OUT / "native.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Captured", len(captures), "production search states", flush=True)


if __name__ == "__main__":
    main()
