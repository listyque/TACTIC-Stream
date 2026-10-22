"""Exercise the pre-Frame administration and its shipped native replacement.

The tracked archive is the original reference, not the later working-tree backup.
Frame-to-Vue measurements remain in the existing per-domain capture suites.
"""

import argparse
import copy
import hashlib
import html
import importlib.util
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
TH = Path("D:/grav/Tactic Stream/TH")
HERE = Path(__file__).resolve().parent
OUT = HERE / "output/original"
REFERENCE = ROOT / "tools/frame_foundation/reference/thlib/ui/qml"
ARCHIVE = (
    ROOT.parent
    / "backups/2026-10-15_103116_before_shared_ui_foundation/TH_git_HEAD_reference.zip"
)
SCREENS = (
    "groups",
    "users",
    "security",
    "types",
    "schema",
    "workflow",
    "rules",
    "columns",
    "sidebar",
    "naming",
)


def extract_reference():
    with zipfile.ZipFile(ARCHIVE) as archive:
        sources = {}
        legacy_controller = archive.read("thlib/ui/columns_editor.py")
        (REFERENCE.parent / "columns_editor.py").parent.mkdir(
            parents=True, exist_ok=True
        )
        (REFERENCE.parent / "columns_editor.py").write_bytes(legacy_controller)
        sources["thlib/ui/columns_editor.py"] = hashlib.sha256(
            legacy_controller
        ).hexdigest()
        for name in archive.namelist():
            if not name.startswith("thlib/ui/qml/") or name.endswith("/"):
                continue
            relative = Path(name).relative_to("thlib/ui/qml")
            assert ".." not in relative.parts
            data = archive.read(name)
            target = REFERENCE / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists() or target.read_bytes() != data:
                target.write_bytes(data)
            sources[name] = hashlib.sha256(data).hexdigest()
    return sources


def capture(screen, quick):
    os.environ.update(
        QT_QPA_PLATFORM="offscreen",
        QT_QUICK_BACKEND="software",
        QSG_RENDER_LOOP="basic",
        QT_FONT_DPI="96",
    )
    sys.path[:0] = [str(TH), str(HERE)]
    from native_capture import click, controls, snapshot, source_hashes, text
    from PySide6.QtCore import QCoreApplication, QEvent, QPointF, QUrl
    from PySide6.QtGui import QFontDatabase
    from PySide6.QtQml import QQmlComponent, QQmlEngine
    from tests.profile_ui_responsiveness import frame
    from tests.test_admin_users_ui import AdminUsersUiTests
    from tests.test_administration_qml import AdministrationQmlTests
    from tests.test_sidebar_editor_qml import SidebarEditorQmlTests

    AdministrationQmlTests.setUpClass()
    for name in ("segoeui.ttf", "seguisb.ttf"):
        QFontDatabase.addApplicationFont("C:/Windows/Fonts/" + name)
    sources = source_hashes(ROOT, TH, ["thlib/ui/administration.py"])
    driver_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    rows = []
    for original in (True, False):
        for dark, language, width in (
            ((True, "en", 1100),)
            if quick
            else (
                (dark, language, width)
                for dark in (True, False)
                for language in ("en", "ru")
                for width in (1100, 1600)
            )
        ):
            test = (
                AdminUsersUiTests() if screen == "users" else AdministrationQmlTests()
            )
            test.setUp()
            fixture = test.fixture
            app = fixture.app
            if language == "en":
                app.removeTranslator(fixture.translator)
            engine = QQmlEngine()
            warnings = []
            engine.warnings.connect(
                lambda errors: warnings.extend(error.toString() for error in errors)
            )
            context = engine.rootContext()
            for name in (
                "appController",
                "projectModel",
                "sidebarEditorController",
                "columnsEditorController",
                "userController",
                "administrationController",
                "administrationGroupModel",
                "administrationMemberModel",
            ):
                context.setContextProperty(
                    name, fixture.engine.rootContext().contextProperty(name)
                )
            for name, value in SidebarEditorQmlTests.icons.items():
                context.setContextProperty(name, value)
            context.setContextProperty(
                "localizationController", {"current_language": language}
            )
            controller, component_name, properties = prepare(
                screen, test, context, original
            )
            qml = REFERENCE if original else TH / "thlib/ui/qml"
            if not original and screen == "columns":
                properties += 'projectCode:"demo";'
            elif original and screen == "columns":
                properties += 'workspaceMode:"catalog";catalogScope:"all";'
            source = (
                'import QtQuick\nimport QtQuick.Controls\nimport "'
                + qml.as_uri()
                + '" as TH\n'
                "ApplicationWindow { visible:true; width:"
                + str(width)
                + "; height:900; color:theme.workspace;"
                "TH.Theme {id:theme; dark:"
                + str(dark).lower()
                + ";clickAnimationsEnabled:false;hoverAnimationsEnabled:false;fadeAnimationsEnabled:false;popupAnimationsEnabled:false}"
                "TH."
                + component_name
                + ' {id:page;objectName:"referencePage";anchors.fill:parent;theme:theme;'
                + properties
                + "}}"
            )
            component = QQmlComponent(engine)
            component.setData(source.encode(), QUrl())
            window = None
            try:
                assert component.isReady(), [e.toString() for e in component.errors()]
                window = component.create()
                assert window
                frame(window)

                def save(phase):
                    frame(window)
                    name = f"{screen}-{'original' if original else 'frame'}-{'dark' if dark else 'light'}-{language}-{width}-{phase}.png"
                    assert window.grabWindow().save(str(OUT / name))
                    document = (
                        controller.draft
                        if screen == "groups"
                        else controller.selectedRule
                        if screen == "naming"
                        else controller.document
                        if hasattr(controller, "document")
                        else None
                    )
                    fields = sorted(
                        {
                            item.objectName()
                            for item in SidebarEditorQmlTests.descendants(
                                window.contentItem()
                            )
                            if item.isVisible()
                            and item.objectName().startswith("adminProcessField_")
                        }
                    )
                    rows.append(
                        dict(
                            screen=screen,
                            original=original,
                            dark=dark,
                            language=language,
                            width=width,
                            phase=phase,
                            image=name,
                            document=copy.deepcopy(document),
                            processFields=fields,
                            referenceWarnings=list(warnings),
                            **snapshot(window, check_icons=False),
                        )
                    )

                def press(name):
                    named = controls(window)
                    assert name in named, (screen, original, name, sorted(named))
                    click(window, named[name])

                def page(selector, value, old_selector=None, old_value=None):
                    prefix = (old_selector or selector) if original else selector
                    target = (old_value or value) if original else value
                    names = controls(window)
                    for name in (
                        prefix + "_" + target,
                        "segmentedButtonSegment_" + target,
                    ):
                        if name in names:
                            press(name)
                            return
                    raise AssertionError(
                        (screen, original, prefix, target, sorted(names))
                    )

                save("initial")
                if screen == "groups":
                    page("securityGroupEditorTabs", "details")
                    save("details")
                    text(
                        window,
                        controls(window)["securityGroupDescription"],
                        "Reference group",
                    )
                    assert test.admin.draft["description"] == "Reference group"
                    save("draft")
                elif screen == "users":
                    text(
                        window,
                        controls(window)["adminUserField_email"],
                        "reference@example.test",
                    )
                    assert controller.document["email"] == "reference@example.test"
                    page("adminUserEditorTabs", "account")
                    save("account")
                    page("adminUserEditorTabs", "groups")
                    save("groups")
                elif screen == "security":
                    for value in (
                        "link",
                        "gear_menu",
                        "search_type",
                        "process",
                        "tasks",
                        "sobject",
                        "sobject_column",
                        "builtin",
                        "search_filter",
                        "technical",
                    ):
                        press("adminSecurityTab_" + value)
                        save(value)
                elif screen == "types":
                    if not original:
                        press("adminSearchType_demo/asset")
                    for value, old in (
                        ("summary", "entity_summary"),
                        ("workflow", "entity_workflows"),
                        ("details", "entity_details"),
                        ("fields", "entity_fields"),
                    ):
                        page("searchTypePages", value, old_value=old)
                        save(value)
                    page("searchTypePages", "details", old_value="entity_details")
                    text(
                        window,
                        controls(window)["adminSearchTypeTitle"],
                        "Reference assets",
                    )
                    assert controller.document["title"] == "Reference assets"
                    save("draft")
                elif screen in ("schema", "workflow"):
                    controller.select_node(
                        "demo/asset" if screen == "schema" else "model"
                    )
                    save("node")
                    if screen == "workflow":
                        for kind in (
                            "manual",
                            "approval",
                            "action",
                            "condition",
                            "hierarchy",
                            "dependency",
                            "progress",
                            "status",
                        ):
                            controller.set_attribute("type", kind)
                            frame(window)
                            text(
                                window,
                                controls(window)["adminProcessDescription"],
                                "Reference " + kind,
                            )
                            assert controller.processDescription == "Reference " + kind
                            save("process-" + kind)
                        controller.set_attribute("type", "manual")
                        page(
                            "adminProcessPages", "native_json", old_value="native_json"
                        )
                        save("process-json")
                    controller.select_edge(0)
                    save("edge")
                    if screen == "workflow":
                        press("adminEditPipeline")
                        save("pipeline")
                    page("adminGraphPages", "technical")
                    save("technical")
                elif screen == "rules":
                    for action in (
                        "task_status",
                        "parent_status",
                        "task_create",
                        "task_date",
                        "custom_script",
                        "python_class",
                    ):
                        controller.set_rule_field("action", action)
                        save("action-" + action)
                    for value in ("notifications", "naming", "objects"):
                        page(
                            "adminDependencyPages",
                            "notification" if value == "notifications" else value,
                            old_value=value,
                        )
                        save(value)
                elif screen == "columns":
                    prefix = "definitionCatalogRow_" if original else "definitionRow_"
                    press(
                        next(
                            name for name in controls(window) if name.startswith(prefix)
                        )
                    )
                    save("catalog")
                elif screen == "sidebar":
                    save("selected")
                elif screen == "naming":
                    press("namingRule_N1")
                    save("selected")
                    if original:
                        button = next(
                            item
                            for item in SidebarEditorQmlTests.descendants(
                                window.contentItem()
                            )
                            if item.inherits("QQuickAbstractButton")
                            and item.property("text")
                            == QCoreApplication.translate(
                                "NamingEditorView", "Advanced fields"
                            )
                        )
                        parent = button.parentItem()
                        while parent:
                            if parent.inherits("QQuickFlickable"):
                                parent.setProperty(
                                    "contentY",
                                    max(
                                        0,
                                        min(
                                            parent.property("contentHeight")
                                            - parent.height(),
                                            parent.property("contentY")
                                            + button.mapToItem(parent, QPointF()).y()
                                            - 8,
                                        ),
                                    ),
                                )
                            parent = parent.parentItem()
                        frame(window)
                        click(window, button)
                    else:
                        page("namingPages", "advanced")
                    save("advanced")
                if original and screen == "columns":
                    assert all(
                        'ColumnsEditorView.qml:724:25: QML Label: Binding loop detected for property "text"'
                        in warning
                        for warning in warnings
                    ), warnings
                else:
                    assert not warnings, warnings
            finally:
                if window:
                    window.close()
                    window.deleteLater()
                engine.deleteLater()
                QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
                test.doCleanups()
    assert sources == source_hashes(ROOT, TH, ["thlib/ui/administration.py"]), (
        "Sources changed during original comparison"
    )
    assert driver_hash == hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), (
        "Comparison driver changed during capture"
    )
    (OUT / (screen + ".json")).write_text(
        json.dumps(
            dict(
                sha256=sources[0],
                nativeSources=sources[1],
                driverSha256=driver_hash,
                captures=rows,
            ),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(screen, len(rows), "original/native Frame states passed", flush=True)


def prepare(screen, test, context, original):
    """Use existing production controllers and isolated test records in both hosts."""
    from PySide6.QtCore import Slot
    from tests.test_columns_table_view import _Application, _SType
    from tests.test_sidebar_editor_qml import SidebarEditorQmlTests
    from thlib.ui.admin.process_rules import ProcessRulesEditor
    from thlib.ui.columns_editor import ColumnsEditorController
    from thlib.ui.naming_editor import (
        _BOOLEAN_FIELDS,
        _DATA_FIELDS,
        NamingEditorController,
    )

    admin = test.admin
    properties = "controller:referenceController;"
    if screen == "groups":
        admin.select_group("G0")
        controller, name = admin, "SecurityGroupsView"
        properties += "groupsModel:administrationGroupModel;membersModel:administrationMemberModel;"
    elif screen == "users":
        controller, name = test.editor, "AdminUsersView"
    elif screen == "security":
        controller, name = admin.securityEditor, "AdminSecurityView"
    elif screen == "types":
        controller, name = admin.typesEditor, "AdminSearchTypesView"
        controller._catalog[0]["label"] = "Assets"
        controller._metadata.update(
            table="asset",
            database="demo",
            projectLocal=True,
            tableAvailable=True,
            summary=dict(
                total=230, active=215, retired=15, fields=3, pipelines=1, processes=2
            ),
            relationships=[
                dict(
                    schema="demo",
                    relationship="code",
                    type="hierarchy",
                    **{"from": "demo/asset", "to": "demo/shot"},
                )
            ],
            hasPipeline=True,
            pipelines=[
                dict(
                    identity="demo/assets",
                    label="Asset workflow",
                    description="Model and review",
                    shared=False,
                    processCount=2,
                )
            ],
            columns={
                "code": {"data_type": "varchar"},
                "description": {"data_type": "text"},
                "duration": {"data_type": "integer"},
            },
        )
        controller._document_loaded()
        properties += 'projectCode:"demo";'
    elif screen in ("schema", "workflow"):
        controller = admin.schemaEditor if screen == "schema" else admin.workflowEditor
        name = "AdminGraphView"
    elif screen == "rules":
        controller = ProcessRulesEditor(
            SimpleNamespace(can_manage_tools=True, debug_log=None),
            SimpleNamespace(),
            None,
        )
        controller._project = "demo"
        controller._identity = "PR1"
        controller._loaded = controller._can_write = True
        controller._metadata = dict(
            process="model",
            pipeline="demo/assets",
            searchType="demo/asset",
            sourceStatuses=["Pending", "Complete"],
            processes=[],
            outputs=["publish"],
            scriptPaths=[],
            naming=[dict(context="publish", directory="assets", file="main")],
            items=[dict(key="demo/asset?code=A1", label="Asset one")],
            itemCount=1,
            itemOffset=0,
        )
        controller.add_rule("trigger")
        controller._original = copy.deepcopy(controller.document)
        name = "AdminProcessRulesView"
    elif screen == "columns":
        if original:
            spec = importlib.util.spec_from_file_location(
                "thlib.ui._original_columns", REFERENCE.parent / "columns_editor.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            ColumnsEditorController = module.ColumnsEditorController

        class ReferenceColumns(ColumnsEditorController):
            # Original QML predates the project argument; reads use the same seeded catalog.
            @Slot()
            def load_definition_catalog(self):
                pass

            @Slot()
            def begin_session(self):
                pass

        application = _Application(_SType())
        controller = ReferenceColumns(application)
        arguments = [
            "demo",
            application.stype.project,
            application.stype.project.views.config_dict,
        ]
        if not original:
            arguments.append({"demo/asset": "Assets"})
        controller._set_definition_catalog(*arguments)
        controller.load_definition_catalog = lambda *_: None
        context.setContextProperty("columnsEditorController", controller)
        context.setContextProperty("columnsEditorModel", controller.model)
        name, properties = "ColumnsEditorView", ""
    elif screen == "sidebar":
        fixture = SidebarEditorQmlTests()
        fixture.setUp()
        test.addCleanup(fixture.doCleanups)
        controller = fixture.controller
        context.setContextProperty("sidebarEditorController", controller)
        context.setContextProperty("sidebarEntryModel", controller.entries)
        context.setContextProperty(
            "sidebarSecurityGroupModel", controller.security_groups
        )
        name, properties = "SidebarEditorView", ""
    elif screen == "naming":
        controller = NamingEditorController(
            SimpleNamespace(can_manage_tools=True, debug_log=None),
            SimpleNamespace(currentObject={}),
            None,
        )
        controller._target = dict(
            projectCode="demo", searchType="demo/asset", title="Assets"
        )
        controller._type_mode = True
        controller._project_data = {"code": "demo"}
        document = {
            field: False if field in _BOOLEAN_FIELDS else "" for field in _DATA_FIELDS
        }
        document.update(
            search_type="demo/asset",
            context="publish",
            checkin_type="strict",
            dir_naming="{project.code}/{sobject.code}",
            file_naming="{sobject.name}_v{version}.{ext}",
        )
        controller._records = [
            controller._normalize_record(
                dict(
                    document,
                    code="N1",
                    __search_key__="config/naming?project=demo&code=N1",
                )
            )
        ]
        controller._select(0)
        context.setContextProperty("namingEditorController", controller)
        context.setContextProperty("namingEditorModel", controller.model)
        name, properties = "NamingEditorView", ""
    else:
        raise AssertionError(screen)
    context.setContextProperty("referenceController", controller)
    return controller, name, properties


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--screen", choices=SCREENS)
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    reference = extract_reference()
    if args.screen:
        capture(args.screen, args.quick)
        return
    for screen in SCREENS:
        subprocess.run(
            [
                sys.executable,
                "-B",
                "-X",
                "utf8",
                __file__,
                "--screen",
                screen,
                *(["--quick"] if args.quick else []),
            ],
            check=True,
        )
    captures = []
    for screen in SCREENS:
        result = json.loads((OUT / (screen + ".json")).read_text(encoding="utf8"))
        assert (
            result["driverSha256"]
            == hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        ), "Changed original comparison driver"
        captures.extend(result["captures"])
    result = dict(
        archive=str(ARCHIVE),
        archiveSha256=hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(),
        referenceSources=reference,
        captures=captures,
        quick=args.quick,
    )
    pairs = []
    for row in captures:
        if not row["original"]:
            continue
        current = next(
            other
            for other in captures
            if not other["original"]
            and all(
                other[key] == row[key]
                for key in ("screen", "dark", "language", "width", "phase")
            )
        )
        assert current["document"] == row["document"], (
            row["screen"],
            row["phase"],
            "Original and Frame drafts differ after the same input",
        )
        assert set(row["processFields"]) <= set(current["processFields"]), (
            row["phase"],
            "Missing process fields",
            set(row["processFields"]) - set(current["processFields"]),
        )
        title = f"{row['screen']} · {row['phase']} · {row['language']} · {'dark' if row['dark'] else 'light'} · {row['width']}"
        pairs.append(
            "<details><summary>"
            + html.escape(title)
            + '</summary><div><figure><figcaption>Original Handler</figcaption><img loading="lazy" src="'
            + row["image"]
            + '"></figure><figure><figcaption>Frame Handler</figcaption><img loading="lazy" src="'
            + current["image"]
            + '"></figure></div></details>'
        )
    (OUT / "index.html").write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8"><title>Administration · original reference</title><style>body{background:#202426;color:#eee;font:15px Segoe UI;margin:24px}details{margin:12px 0}details>div{display:flex;gap:12px}figure{margin:0;width:50%}img{width:100%}summary{cursor:pointer}</style><h1>Administration: original → Frame</h1><p>Tracked pre-Frame Handler fa3f594. Actual native controls and input. These are review pairs, not zero-pixel-difference claims. Raw database and Layout Editor have no matching page in this archive; their production paths are covered by the paired suites.</p>'
        + "".join(pairs),
        encoding="utf8",
    )
    (OUT / "results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf8"
    )
    print(len(pairs), "original/native Frame review pairs")


if __name__ == "__main__":
    main()
