"""Independent native page editor with the real dashboard renderer; no network."""

import copy, json, os, sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
TH = Path("D:/grav/Tactic Stream/TH")
OUT = Path(os.environ.get("TACTIC_CANVAS_CAPTURE", ROOT / ".screenshots/page-editor"))
OUT.mkdir(parents=True, exist_ok=True)
sys.path[:0] = [str(TH), str(ROOT / "tools/frame_admin")]
os.environ.update(
    QT_QPA_PLATFORM="offscreen",
    QT_QUICK_BACKEND="software",
    QSG_RENDER_LOOP="basic",
    QT_FONT_DPI="96",
)
from PySide6.QtCore import QObject, Property, QUrl, QCoreApplication, QEvent
from PySide6.QtQml import QQmlEngine, QQmlComponent
from tests.qt_application import gui_test_application
from tests.profile_ui_responsiveness import frame
from tests.test_custom_layout import Services
from tests.test_layout_editor import Pool
from thlib.environment import env_inst
from thlib.ui.admin.dashboard import DashboardEditor
from thlib.ui.icon_font import qml_icon_bindings
from native_capture import snapshot, source_hashes


class Application(QObject):
    @Property(str, constant=True)
    def server_url(self):
        return ""


class Preview(QObject):
    def __init__(self, owner):
        super().__init__()
        self._owner = owner

    @Property(QObject, constant=True)
    def services(self):
        return self._owner

    @Property(QObject, constant=True)
    def owner(self):
        return self._owner

    @Property(QObject, constant=True)
    def items(self):
        return None


document = dict(
    name="review",
    title="Review",
    blocks=[
        dict(
            kind="column",
            height=240,
            padding=[8, 12, 8, 12],
            children=[
                dict(
                    kind="text",
                    title="Status",
                    text="Project status",
                    height=60,
                    padding=[4, 8, 4, 8],
                )
            ],
        )
    ],
)
compiled = dict(
    title="Review",
    layoutNodes=[
        dict(
            kind="group",
            height=240,
            editorPath=[0],
            padding=[8, 12, 8, 12],
            children=[
                dict(
                    kind="text",
                    text="Project status",
                    height=60,
                    padding=[4, 8, 4, 8],
                    editorPath=[0, 0],
                )
            ],
        )
    ],
    targetSearchKey="sthpw/project?code=demo",
)
source = dict(
    searchType="demo/asset",
    fields=[dict(value="amount", label="Amount", dataType="integer")],
    tableViews=[dict(value="table", label="Table")], itemViews=[], records=[],
)
fixtures = dict(layout=dict(document=document, compiled=compiled), data=dict(
    document=dict(name="review", title="Review", blocks=[dict(kind="column", height=240, children=[
        dict(kind="metric", title="Assets", search_type="demo/asset", filters=[
            dict(column="amount", relation="!=", value=None)])])]),
    compiled=dict(title="Review", targetSearchKey="sthpw/project?code=demo", layoutNodes=[
        dict(kind="group", height=240, editorPath=[0], children=[
            dict(kind="metric", text="Assets", value=4, editorPath=[0, 0])])]),
))
app = gui_test_application()
env_inst.server_pool = Pool()
icons = qml_icon_bindings(TH, app)
captures = []
sources = source_hashes(
    ROOT,
    TH,
    [
        "thlib/ui/qml/features/administration/layouts/PageLayoutEditorView.qml",
        "thlib/ui/qml/features/administration/layouts/CanvasSelection.qml",
        "thlib/ui/qml/features/table/CustomLayoutView.qml",
    ],
)
from itertools import product
for scenario, mode in product(["layout", "data"], ["dark", "light"]):
    for language in ["en", "ru"]:
        for width in [1400, 850]:
            host = DashboardEditor(
                SimpleNamespace(can_manage_tools=True, debug_log=None)
            )
            host._project = "demo"
            host._can_write = True
            host._identity = "review"
            host._catalog = [dict(identity="review", label="review")]
            document, compiled = fixtures[scenario]["document"], fixtures[scenario]["compiled"]
            host._document = copy.deepcopy(document)
            host._original = copy.deepcopy(document)
            owner = Services(copy.deepcopy(compiled))
            preview = Preview(owner)
            application = Application()
            host._metadata = dict(
                checkedDocument=copy.deepcopy(document),
                previewOwner=preview,
                application=application,
                searchTypes=[dict(value="demo/asset", label="Assets", projectOwned=True)],
                dataSource=copy.deepcopy(source),
            )
            engine = QQmlEngine()
            warnings = []
            engine.warnings.connect(
                lambda errors: warnings.extend(e.toString() for e in errors)
            )
            for key, value in icons.items():
                engine.rootContext().setContextProperty(key, value)
            engine.rootContext().setContextProperty("fixture", host)
            component = QQmlComponent(engine)
            component.setData(
                (
                    'import QtQuick\nimport QtQuick.Controls\nimport "'
                    + (TH / "thlib/ui/qml").as_uri()
                    + '" as TH\nApplicationWindow {id:root;visible:true;width:1400;height:740;color:theme.workspace;property string language:"en";property alias dark:theme.dark;function selectPanel(value){if(editor.ui.preview !== (value==="preview"))editor.dispatch({type:"preview"});if(value!=="preview"){editor.dispatch({type:"panel",value});editor.dispatch({type:"select",key:"0.0"})}}TH.Theme{id:theme;clickAnimationsEnabled:false;hoverAnimationsEnabled:false;fadeAnimationsEnabled:false;popupAnimationsEnabled:false}TH.PageLayoutEditorView{id:editor;anchors.fill:parent;theme:theme;controller:fixture;language:root.language}}'
                ).encode(),
                QUrl(),
            )
            assert component.isReady(), [e.toString() for e in component.errors()]
            window = component.createWithInitialProperties(
                dict(width=width, height=740, dark=mode == "dark", language=language)
            )
            assert window
            try:
                for panel in (["properties"] if scenario == "data" else ["canvas", "properties", "preview"]):
                    window.selectPanel(panel)
                    frame(window)
                    if host._source_worker is not None:
                        host._source_worker.result.emit(copy.deepcopy(source))
                        frame(window)
                    name = f"page-{scenario}-{mode}-{language}-{width}-{panel}.png"
                    assert window.grabWindow().save(str(OUT / name))
                    captures.append(
                        dict(
                            mode=mode,
                            language=language,
                            width=width,
                            height=740,
                            panel=panel,
                            fixture=scenario,
                            image=name,
                            **snapshot(window),
                        )
                    )
                assert not warnings, warnings
            finally:
                window.close()
                window.deleteLater()
                engine.deleteLater()
                host.shutdown()
                QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
(OUT / "page-native.json").write_text(
    json.dumps(
        dict(
            fixtures=fixtures,
            source=source,
            captures=captures,
            sha256=sources[0],
            nativeSources=sources[1],
        ),
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)
print(f"Captured {len(captures)} native page editor states")
