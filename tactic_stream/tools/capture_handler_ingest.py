"""Fresh Handler ingest QML reference, using its own offline test controller."""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
root = Path(__file__).resolve().parents[1]
handler = Path('D:/code/th_codex')
sys.path.insert(0, str(handler))
spec = importlib.util.spec_from_file_location('handler_ingest_fixture', handler / 'tests/test_ingest_files.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
from PySide6.QtCore import QEventLoop, QTimer, QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtGui import QGuiApplication, QFontDatabase

app = QGuiApplication.instance() or QGuiApplication([])
for path in [Path('C:/Windows/Fonts/segoeui.ttf'), Path('C:/Windows/Fonts/segoeuib.ttf'),
             * (handler / 'thlib/ui/assets/fonts').glob('*.ttf')]:
    if QFontDatabase.addApplicationFont(str(path)) < 0:
        raise RuntimeError('Cannot load reference font: %s' % path)
application = fixture._Application()
controller = fixture.IngestFilesController(application)
controller._parent_title = 'Первый'
controller._target_title = 'Collection'
controller._target_search_type = 'contract/collection'
controller._replace_rules([dict(code='browser_rule', title='Browser ingest rule', data=dict(ignore='.tmp'))])
controller._selected_rule_id = 'browser_rule'
controller._replace_rules([dict(code='browser_rule', title='Browser ingest rule', data=dict(ignore='.tmp'))])
engine = QQmlEngine()
engine.addImportPath(str(fixture.QML))
from thlib.ui.icon_font import qml_icon_bindings
for name, value in qml_icon_bindings(handler, engine).items():
    engine.rootContext().setContextProperty(name, value)
for name, obj in dict(ingestFilesController=controller, ingestFileModel=controller.files,
                     ingestRuleModel=controller.rules, windowModel=application.window_model).items():
    engine.rootContext().setContextProperty(name, obj)
theme_component = QQmlComponent(engine, QUrl.fromLocalFile(str(fixture.QML / 'Theme.qml')))
theme = theme_component.createWithInitialProperties(dict(dark=True))
component = QQmlComponent(engine, QUrl.fromLocalFile(str(fixture.QML / 'IngestFilesView.qml')))
view = component.createWithInitialProperties(dict(theme=theme))
if view is None:
    raise RuntimeError('\n'.join(error.toString() for error in component.errors()))
window = QQuickWindow()
try:
    with tempfile.TemporaryDirectory() as directory:
        paths = []
        for name in ('BrowserIngest.txt', 'Ignored.tmp'):
            path = Path(directory) / name
            path.write_bytes(b'fixture')
            paths.append(str(path))
        controller._add_local_paths(paths)
        window.resize(960, 560)
        view.setParentItem(window.contentItem())
        view.setProperty('width', 960)
        view.setProperty('height', 560)
        window.show()
        loop = QEventLoop()
        QTimer.singleShot(700, loop.quit)
        loop.exec()
        output = root / '.screenshots/handler-current/ingest-files.png'
        if not window.grabWindow().save(str(output)):
            raise RuntimeError('Cannot save Handler ingest reference')
        print(output)
finally:
    window.close()
    view.setParentItem(None)
    view.deleteLater()
    theme.deleteLater()
    app.processEvents()
