"""Fresh reference rendered by the original Handler QML, without editing Handler."""
import os
from pathlib import Path
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_QUICK_BACKEND', 'software')
os.environ.setdefault('QT_SCALE_FACTOR', '1')
ROOT = Path(__file__).resolve().parents[1]
HANDLER = Path('D:/grav/Tactic Stream/TH')
sys.path.insert(0, str(HANDLER))
from PySide6.QtCore import QUrl, Slot, QPoint, QObject
from PySide6.QtGui import QColor, QFontDatabase
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtTest import QTest
from tests.qt_application import gui_test_application
from tests.test_workspace_result_item import WorkspaceResultItemTests, _WorkspaceAppController
from thlib.ui.icon_font import fontawesome_assets, material_design_icon_assets


class Controller(_WorkspaceAppController):
    @Slot(str, result=str)
    def get_acronym(self, text):
        return 'EA'


app = gui_test_application()
for font in ('segoeui.ttf', 'seguisb.ttf', 'segoeuib.ttf'):
    QFontDatabase.addApplicationFont(str(Path('C:/Windows/Fonts') / font))
engine = QQmlEngine()
controller = Controller()
context = engine.rootContext()
context.setContextProperty('appController', controller)
solid, solid_font, regular, regular_font = fontawesome_assets(HANDLER)
material, material_font = material_design_icon_assets(HANDLER, complete=True)
for name, value in dict(fontAwesomeSolidGlyphs=solid, fontAwesomeSolidFontFamily=solid_font,
        fontAwesomeRegularGlyphs=regular, fontAwesomeRegularFontFamily=regular_font,
        materialDesignIconGlyphs=material, materialDesignIconFontFamily=material_font).items():
    context.setContextProperty(name, value)
qml = HANDLER / 'thlib/ui/qml'
theme_component = QQmlComponent(engine, QUrl.fromLocalFile(str(qml / 'Theme.qml')))
theme = theme_component.createWithInitialProperties({'dark': True})
component = QQmlComponent(engine, QUrl.fromLocalFile(str(qml / 'WorkspaceResultItem.qml')))
window = QQuickWindow()
window.setColor(QColor(theme.property('workspace')))
window.resize(1380, 550)
items = []
rows = [('sobject', 'Episode 01 — Arrival', '#6f94ea'), ('relation', 'Shot', '#dede6f'), ('relation', 'Assets', '#f25050')]
rows += [('process', name, color) for name, color in zip(
    ['Сценарий', 'Сториборд', 'Лейаут', 'Озвучка', 'Анимация', 'Свет', 'Рендер', 'Композ', 'Звук', 'Публикация'],
    ['#b84e39', '#b6d456', '#b77f50', '#bc9c59', '#b7be32', '#5e3ba7', '#2da35f', '#247237', '#368a80', '#55cc28'])]
y = 0
try:
    for index, (kind, title, accent) in enumerate(rows):
        props = dict(index=index, nodeId=str(index), nodeType=kind, title=title, accent=accent,
            compactMode=False, width=1366, depth=0 if kind == 'sobject' else 1, expanded=kind == 'sobject',
            hasChildren=kind != 'process', childCount=2 if title == 'Shot' else 3 if title == 'Assets' else 0,
            tasks=1 if index in (0, 3) else 0, comments=1 if index in (0, 12) else 0,
            subtitle='Sample episode · Dialog' if kind == 'sobject' else '',
            progressItems=[dict(name='assets', label='0 / 3', color='#f25050')] if kind == 'sobject' else [],
            infoChips=[dict(text='120')] if kind == 'sobject' else [])
        item = component.createWithInitialProperties(WorkspaceResultItemTests.item_properties(theme, **props))
        if item is None:
            raise RuntimeError('\n'.join(error.toString() for error in component.errors()))
        item.setParentItem(window.contentItem())
        item.setX(6)
        item.setY(y)
        y += item.height() + 3
        items.append(item)
    window.resize(1380, int(y))
    window.show()
    QTest.mouseMove(window, QPoint(0, int(y) + 10))
    for item in items:
        item.findChild(QObject, 'workspaceItemSurface').setProperty('hovered', False)
    QTest.qWait(250)
    path = ROOT / '.screenshots/handler-result-tree-reference.png'
    assert window.grabWindow().save(str(path))
    print(path.as_posix())
finally:
    window.close()
    for item in items:
        item.setParentItem(None)
        item.deleteLater()
    engine.deleteLater()
    window.deleteLater()
    app.processEvents()
