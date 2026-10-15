"""Capture the current Handler wizard using its native offline QML fixture."""
import importlib.util
import os
from pathlib import Path
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
handler = Path('D:/code/th_codex')
sys.path.insert(0, str(handler))
spec = importlib.util.spec_from_file_location('handler_duplicate_fixture', handler / 'tests/test_sobject_duplicate.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
from PySide6.QtGui import QFontDatabase
from PySide6.QtTest import QTest
from thlib.ui.icon_font import qml_icon_bindings

fixture.SObjectDuplicateQmlTests.setUpClass()
for path in [Path('C:/Windows/Fonts/segoeui.ttf'), Path('C:/Windows/Fonts/segoeuib.ttf'),
             *(handler / 'thlib/ui/assets/fonts').glob('*.ttf')]:
    if QFontDatabase.addApplicationFont(str(path)) < 0:
        raise RuntimeError('Cannot load reference font: %s' % path)
test = fixture.SObjectDuplicateQmlTests()
engine, theme_component, component, theme, controller, window_model, view, window, warnings = test._create(960)
try:
    for name, value in qml_icon_bindings(handler, engine).items():
        engine.rootContext().setContextProperty(name, value)
    output = Path(__file__).resolve().parents[1] / '.screenshots/handler-current'
    output.mkdir(parents=True, exist_ok=True)
    for step, name in enumerate(('fields', 'relations', 'snapshots', 'messages', 'review')):
        controller.set_step(step)
        QTest.qWait(300)
        path = output / ('duplicate-' + name + '.png')
        if not window.grabWindow().save(str(path)):
            raise RuntimeError('Cannot save Handler duplicate reference')
        print(path)
finally:
    window.close()
    view.setParentItem(None)
    view.deleteLater()
    theme.deleteLater()
    fixture.SObjectDuplicateQmlTests.app.processEvents()
