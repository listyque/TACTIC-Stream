"""Exercise the public native sizing facade against its historical values."""
import json
import os
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine, QQmlExpression

ROOT = Path(__file__).resolve().parents[2]
app = QGuiApplication.instance() or QGuiApplication([])
engine = QQmlEngine()
warnings = []
engine.warnings.connect(lambda errors: warnings.extend(error.toString() for error in errors))
component = QQmlComponent(engine, QUrl.fromLocalFile('D:/code/th_codex/thlib/ui/qml/shell/windows/WindowSizing.qml'))
assert component.isReady(), component.errors()
policy = component.create()
reference = json.loads((ROOT / 'frontend/tests/fixtures/window_sizing.json').read_text(encoding='utf-8'))
checks = 0
for name, cases in reference.items():
    for kind, expected in cases.items():
        expression = QQmlExpression(engine.rootContext(), policy, name + '(' + json.dumps(kind) + ')')
        actual, undefined = expression.evaluate()
        assert not expression.hasError() and not undefined, expression.error().toString()
        assert actual == expected, (name, kind, actual, expected)
        checks += 1
assert not warnings, warnings
print('Native window/dock sizing facade:', checks, 'original values passed')
