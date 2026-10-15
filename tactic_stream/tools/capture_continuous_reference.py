"""Render and exercise the current Handler tree with isolated Qt fixtures."""
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
HANDLER = Path('D:/code/th_codex')
OUTPUT = ROOT / '.screenshots/continuous-current'


def main():
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    os.environ['QT_QUICK_BACKEND'] = 'software'
    os.environ['QT_SCALE_FACTOR'] = '1'
    sys.path.insert(0, str(HANDLER))
    from PySide6.QtCore import QObject, QPoint, QPointF, QUrl, Qt, Slot
    from PySide6.QtGui import QColor, QFontDatabase
    from PySide6.QtQml import QQmlComponent, QQmlEngine
    from PySide6.QtQuick import QQuickItem, QQuickWindow
    from PySide6.QtTest import QSignalSpy, QTest
    from tests.qt_application import gui_test_application
    from tests.test_workspace_result_item import WorkspaceResultItemTests, _WorkspaceAppController, _visual_child
    from thlib.ui.icon_font import qml_icon_bindings
    from thlib.ui.workspace_models.results import WorkspaceItemModel
    from thlib.ui.workspace_models.results_types import WorkspaceNode

    class Controller(_WorkspaceAppController):
        def __init__(self):
            super().__init__()
            self.toggles = []

        @Slot(str, result=str)
        def get_acronym(self, text):
            return 'EA'

        @Slot(str, result='QVariantList')
        def item_quick_actions(self, identity):
            return [action for action in super().item_quick_actions(identity) if action['command'] != 'open']

        @Slot(str, bool)
        def toggle_result_node_recursive(self, identity, recursive):
            self.toggles.append((identity, recursive))

        @Slot(str, int, result=bool)
        def handle_item_double_click(self, identity, modifiers):
            return False

    app = gui_test_application()
    engine = QQmlEngine()
    controller = Controller()
    context = engine.rootContext()
    context.setContextProperty('appController', controller)
    for name, value in qml_icon_bindings(HANDLER, engine).items():
        context.setContextProperty(name, value)
    for font in ('segoeui.ttf', 'seguisb.ttf', 'segoeuib.ttf'):
        QFontDatabase.addApplicationFont('C:/Windows/Fonts/' + font)
    qml = HANDLER / 'thlib/ui/qml'
    warnings = []
    engine.warnings.connect(lambda errors: warnings.extend(error.toString() for error in errors))
    theme_component = QQmlComponent(engine, QUrl.fromLocalFile(str(qml / 'Theme.qml')))
    theme = theme_component.createWithInitialProperties({'dark': True})
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(qml / 'WorkspaceResultItem.qml')))
    window = QQuickWindow()
    window.setColor(QColor(theme.property('workspace')))
    window.resize(1380, 600)
    items = []
    rows = [('sobject', 'Episode 01 — Arrival', '#6f94ea'), ('relation', 'Shot', '#dede6f'), ('relation', 'Assets', '#f25050')]
    rows += [('process', name, color) for name, color in zip(
        ['Сценарий', 'Сториборд', 'Лейаут', 'Озвучка', 'Анимация', 'Свет', 'Рендер', 'Композ', 'Звук', 'Публикация'],
        ['#b84e39', '#b6d456', '#b77f50', '#bc9c59', '#b7be32', '#5e3ba7', '#2da35f', '#247237', '#368a80', '#55cc28'])]
    OUTPUT.mkdir(parents=True, exist_ok=True)

    def settle():
        QTest.qWait(560)
        app.processEvents()

    def capture(name):
        settle()
        assert window.grabWindow().save(str(OUTPUT / ('handler-' + name + '.png')))

    def center(item):
        return item.mapToScene(QPointF(item.width() / 2, item.height() / 2)).toPoint()

    try:
        y = 0
        for index, (kind, title, accent) in enumerate(rows):
            controls = WorkspaceItemModel._controls_for(WorkspaceNode(
                node_id=str(index), node_type=kind, search_key='demo/asset?code=A',
                code='A', title=title, linkable_relation=title == 'Assets'))
            props = dict(index=index, nodeId=str(index), nodeType=kind, title=title, accent=accent,
                compactMode=False, width=1368, depth=0 if kind == 'sobject' else 1,
                expanded=kind == 'sobject', hasChildren=kind != 'process',
                childCount=2 if title == 'Shot' else 3 if title == 'Assets' else 0,
                tasks=1 if index in (0, 3) else 0, comments=1 if index in (0, 12) else 0,
                subtitle='Sample episode · Dialog' if kind == 'sobject' else '',
                progressItems=[dict(name='assets', label='0 / 3', color='#f25050')] if kind == 'sobject' else [],
                itemControls=controls, infoChips=[dict(text='120')] if kind == 'sobject' else [])
            item = component.createWithInitialProperties(WorkspaceResultItemTests.item_properties(theme, **props))
            if item is None:
                raise RuntimeError('\n'.join(error.toString() for error in component.errors()))
            item.setParentItem(window.contentItem())
            item.setX(6)
            item.setY(y)
            y += item.height() + 3
            items.append(item)
        window.resize(1380, int(y + 24))
        window.show()
        QTest.mouseMove(window, QPoint(700, 50))
        QTest.mouseMove(window, QPoint(700, int(y + 12)))
        capture('normal')
        QTest.mouseMove(window, QPoint(800, 50))
        capture('object-hover')
        title_item = items[0].findChild(QQuickItem, 'workspaceObjectTitle')
        QTest.mouseMove(window, center(title_item))
        capture('title-hover')
        save = _visual_child(items[0], 'workspaceInlineSaveAction')
        assert save and save.isVisible()
        QTest.mouseClick(window, Qt.LeftButton, pos=center(save))
        assert controller.item_actions[-1] == ('save', '0')
        relation = items[2]
        selection = QSignalSpy(relation.selectedRequested)
        QTest.mouseMove(window, QPoint(800, int(relation.y() + relation.height() / 2)))
        capture('relation-hover')
        QTest.mouseClick(window, Qt.LeftButton, pos=QPoint(800, int(relation.y() + relation.height() / 2)))
        assert selection.count() == 1 and not controller.toggles
        QTest.mouseDClick(window, Qt.LeftButton, pos=QPoint(800, int(relation.y() + relation.height() / 2)))
        assert controller.toggles[-1] == ('2', False)
        relation.setProperty('selected', True)
        capture('relation-selected')
        process = items[4]
        QTest.mouseMove(window, QPoint(800, int(process.y() + process.height() / 2)))
        capture('process-hover')
        QTest.mousePress(window, Qt.LeftButton, pos=QPoint(800, int(process.y() + process.height() / 2)))
        capture('process-pressed')
        QTest.mouseRelease(window, Qt.LeftButton, pos=QPoint(800, int(process.y() + process.height() / 2)))
        relation.setProperty('selected', False)
        process.setProperty('selected', True)
        QTest.mouseMove(window, QPoint(0, int(y + 12)))
        capture('process-selected')
        geometry = []
        for item in items:
            geometry.append(dict(title=item.property('title'), height=item.height(),
                surface_left=item.property('surfaceLeft'), controls=item.property('itemControls').toVariant()
                if hasattr(item.property('itemControls'), 'toVariant') else item.property('itemControls')))
        report = dict(geometry=geometry, clicks=controller.item_actions, toggles=controller.toggles,
            warnings=warnings, sources={str(path.relative_to(HANDLER)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in (qml / 'WorkspaceResultItem.qml', qml / 'ItemQuickActions.qml', qml / 'controls/ItemSurface.qml')})
        (OUTPUT / 'handler.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        states = [('normal', 'Обычное состояние'), ('object-hover', 'Наведение на объект'),
            ('title-hover', 'Наведение на заголовок'), ('relation-hover', 'Наведение на связь'),
            ('relation-selected', 'Выбранная связь'), ('process-hover', 'Наведение на процесс'),
            ('process-pressed', 'Нажатый процесс'), ('process-selected', 'Выбранный процесс')]
        panels = ''.join(f'<section data-state="{key}" hidden><h2>{label}</h2><div class="pair">' +
            ''.join(f'<figure><figcaption>{client}</figcaption><div class="frame"><img src="{prefix}-{key}.png" alt="{client}: {label}"></div></figure>'
                for client, prefix in [('ТХ — текущий QML', 'handler'), ('ТС — Chromium', 'web')]) + '</div></section>' for key, label in states)
        options = ''.join(f'<option value="{key}">{label}</option>' for key, label in states)
        gallery = '''<!doctype html><html lang="ru"><meta charset="utf-8"><title>Непрерывное дерево — ТХ / ТС</title>
<style>body{margin:20px;background:#1b1e20;color:#f6f8fa;font:15px Segoe UI,sans-serif}h1{font-size:22px}p{color:#aeb1b3;max-width:1100px}select,button{font:inherit;padding:8px;background:#383d40;color:inherit;border:1px solid #607d8b;border-radius:8px}button{margin-left:12px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:16px}figure{margin:0;min-width:0}figcaption{margin-bottom:8px}.frame{aspect-ratio:1380/536;overflow:hidden}img{width:100%;display:block}.actual .pair{grid-template-columns:1380px 1380px}.actual .frame{width:1380px;height:536px}a{color:#79a7bf}</style>
<h1>Непрерывное дерево — сравнение актуальных состояний</h1>
<p>Одинаковые данные Episode 01, ширина 1380 px и масштаб 100%. Слева — неизменённый WorkspaceResultItem.qml ТХ, запущенный через изолированный Qt-контроллер; справа — реальные клики в Chromium на временном сервере с cg.zip. Сравнивается первый эпизод. Repository Sync и Watch Folder присутствуют в оригинале ТХ и исключены из веба по согласованному объёму. Растеризация текста Qt и Chromium отличается.</p>
<select aria-label="Состояние дерева">''' + options + '''</select><button>Показать 1:1</button> <a href="handler.json">Исходники и измерения QML</a>''' + panels + '''
<script>const select=document.querySelector('select');function update(){for(const section of document.querySelectorAll('section'))section.hidden=section.dataset.state!==select.value}select.onchange=update;document.querySelector('button').onclick=function(){const actual=document.body.classList.toggle('actual');this.textContent=actual?'Уместить рядом':'Показать 1:1'};update()</script></html>'''
        (OUTPUT / 'index.html').write_text(gallery, encoding='utf-8')
        assert not warnings, warnings
        print('PASS: fresh Handler QML tree, hover/title actions, single/double click and press states')
    finally:
        window.close()
        for item in items:
            item.setParentItem(None)
            item.deleteLater()
        engine.deleteLater()
        window.deleteLater()
        app.processEvents()


if __name__ == '__main__':
    main()
