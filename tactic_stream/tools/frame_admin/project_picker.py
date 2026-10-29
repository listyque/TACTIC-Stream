"""Native project picker input and fresh counterpart geometry captures."""

import argparse, json, os, sys
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--handler-root", type=Path, required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[2]
out = root / "tools/frame_admin/output/projects"
out.mkdir(parents=True, exist_ok=True)
os.environ.update(
    QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software", QT_FONT_DPI="96"
)
sys.path[:0] = [str(args.handler_root), str(Path(__file__).parent)]
from PySide6.QtCore import QObject, QPointF, Qt, QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtGui import QFontDatabase
from PySide6.QtTest import QTest
from tests.test_sidebar_editor_qml import SidebarEditorQmlTests as Fixture
from tests.profile_ui_responsiveness import frame
from native_capture import snapshot, click, source_hashes

Fixture.setUpClass()
for name in ("segoeui.ttf", "seguisb.ttf"):
    QFontDatabase.addApplicationFont("C:/Windows/Fonts/" + name)
model = json.loads(
    (Path(__file__).parent / "project_picker.json").read_text(encoding="utf-8")
)
native_names = [
    "thlib/ui/qml/features/administration/AdminProjectPicker.qml",
    "thlib/ui/qml/features/administration/AdministrationView.qml",
    "thlib/ui/qml/tactic_frame/core/FrameView.qml",
    "thlib/ui/qml/controls/ItemPreview.qml",
]
initial_sources = source_hashes(root, args.handler_root, native_names)
captures = []
for dark in (True, False):
    for language in ("en", "ru"):
        for width, height in ((1100, 760), (360, 640)):
            engine = QQmlEngine()
            warnings = []
            engine.warnings.connect(
                lambda errors: warnings.extend(e.toString() for e in errors)
            )
            for name, value in Fixture.icons.items():
                engine.rootContext().setContextProperty(name, value)
            component = QQmlComponent(
                engine,
                QUrl.fromLocalFile(
                    str(args.handler_root / "tests/qml/AdminProjectPickerHarness.qml")
                ),
            )
            window = component.createWithInitialProperties(
                dict(
                    data=model, language=language, width=width, height=height, dark=dark
                )
            )
            assert window, [e.toString() for e in component.errors()]
            try:
                frame(window)
                window.requestActivate()
                frame(window)
                picker = next(
                    i
                    for i in Fixture.descendants(window.contentItem())
                    if i.objectName() == "administrationProjectPickerControl"
                )
                trigger = next(
                    i
                    for i in Fixture.descendants(picker)
                    if i.objectName() == "administrationProjectSelector"
                )
                click(window, trigger)
                frame(window)
                popup = picker.findChild(QObject, "administrationProjectPopup")
                assert popup.property("opened")
                content = popup.property("contentItem")
                popup_window = content.window()
                frame(popup_window)
                search = next(
                    i
                    for i in Fixture.descendants(content)
                    if i.objectName() == "administrationProjectSearch"
                )
                for phase in ("open", "filtered", "empty"):
                    if phase != "open":
                        search.forceActiveFocus()
                        QTest.keyClick(popup_window, Qt.Key_A, Qt.ControlModifier)
                        for char in "city" if phase == "filtered" else "no_match":
                            QTest.keyClick(popup_window, char)
                        frame(popup_window)
                    data = snapshot(popup_window)
                    origin = content.mapToScene(QPointF())
                    for box in data["boxes"].values():
                        box["x"] -= origin.x()
                        box["y"] -= origin.y()
                    popup_window.grabWindow().save(
                        str(out / f"qml-{dark}-{language}-{width}-{phase}.png")
                    )
                    captures.append(
                        dict(
                            dark=dark,
                            language=language,
                            width=width,
                            height=height,
                            phase=phase,
                            **data,
                        )
                    )
                search.forceActiveFocus()
                QTest.keyClick(popup_window, Qt.Key_A, Qt.ControlModifier)
                for char in "city_template":
                    QTest.keyClick(popup_window, char)
                frame(popup_window)
                QTest.keyClick(popup_window, Qt.Key_Down)
                frame(popup_window)
                QTest.keyClick(popup_window, Qt.Key_Return)
                frame(window)
                assert window.property("data").toVariant()["project"] == "city_template"
                assert not popup.property("opened")
                click(window, trigger)
                frame(window)
                window.setProperty("data", dict(model, locked=True))
                frame(window)
                assert not popup.property("opened") and not trigger.isEnabled()
                assert not warnings, warnings
            finally:
                window.close()
                window.deleteLater()
                engine.deleteLater()
assert initial_sources == source_hashes(root, args.handler_root, native_names), (
    "Sources changed during native capture"
)
shared, native = initial_sources
(out / "qml.json").write_text(
    json.dumps(
        dict(sha256=shared, nativeSources=native, captures=captures),
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)
print(
    f"Native picker: {len(captures)} captures; code search, keyboard selection, lock guards passed"
)
