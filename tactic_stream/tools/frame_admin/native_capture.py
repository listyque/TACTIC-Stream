"""Real native input and visible-control measurements for Frame comparisons."""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtTest import QTest
from tests.test_sidebar_editor_qml import SidebarEditorQmlTests
from tests.profile_ui_responsiveness import frame


def value(data):
    return data.toVariant() if hasattr(data, 'toVariant') else data


def assert_icons(window):
    for item in SidebarEditorQmlTests.descendants(window.contentItem()):
        if item.objectName() == 'materialIconGlyph' and item.isVisible():
            assert any(item.property(field) for field in ('fontAwesomeName', 'materialName', 'catalogGlyph')), 'Unknown native icon: ' + str(item.parentItem().property('name'))


def controls(window):
    result = {}
    for item in SidebarEditorQmlTests.descendants(window.contentItem()):
        if not item.objectName() or not item.isVisible():
            continue
        box = item.mapRectToScene(QRectF(0, 0, item.width(), item.height()))
        parent, visible = item.parentItem(), True
        while parent:
            if parent.clip():
                clip = parent.mapRectToScene(QRectF(0, 0, parent.width(), parent.height()))
                if not box.intersects(clip):
                    visible = False
                    break
            parent = parent.parentItem()
        if visible:
            result[item.objectName()] = item
    return result


def click(window, item, settle=None):
    bounds = item.mapRectToScene(QRectF(0, 0, item.width(), item.height()))
    parent = item.parentItem()
    while parent:
        if parent.clip():
            bounds = bounds.intersected(parent.mapRectToScene(QRectF(0, 0, parent.width(), parent.height())))
        parent = parent.parentItem()
    bounds = bounds.intersected(QRectF(0, 0, window.width(), window.height()))
    assert not bounds.isEmpty(), 'Control is outside the visible viewport: ' + item.objectName()
    QTest.mouseClick(window, Qt.LeftButton, pos=bounds.center().toPoint())
    frame(settle or window)


def choose(window, item, selected):
    options = value(item.property('model'))
    target = next(index for index, option in enumerate(options) if option['value'] == selected)
    item.forceActiveFocus()
    for _ in range((target - item.property('currentIndex')) % len(options)):
        QTest.keyClick(window, Qt.Key_Down)
        frame(window)


def text(window, item, source):
    click(window, item)
    QTest.keyClick(window, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClick(window, Qt.Key_Backspace)
    for char in source:
        QTest.keyClick(window, Qt.Key_Return if char == '\n' else char)
        frame(window)


def snapshot(window):
    assert_icons(window)
    boxes, styles, interiors, frame_ids, fills = {}, {}, {}, [], {}
    for name, item in controls(window).items():
        box = item.mapRectToScene(QRectF(0, 0, item.width(), item.height()))
        boxes[name] = dict(x=box.x(), y=box.y(), width=box.width(), height=box.height())
        ancestor = item
        while ancestor:
            definition = value(ancestor.property('node'))
            if isinstance(definition, dict) and definition.get('id') == name:
                frame_ids.append(name)
                if definition.get('kind') == 'Label' and definition.get('wrap') and name.endswith('Description'):
                    content = item.property('contentHeight')
                    assert content is None or content <= item.height() + .5, f'Clipped description: {name}: {content} > {item.height()}'
                color = item.property('color')
                if definition.get('kind') == 'Box' and hasattr(color, 'alphaF'):
                    fills[name] = dict(color=color.name(), alpha=color.alphaF())
                break
            ancestor = ancestor.parentItem()
        if item.property('text') is not None and item.property('font') is not None:
            font, color = item.property('font'), item.property('color') or item.property('contentColor')
            styles[name] = dict(fontSize=font.pixelSize(), weight=font.weight(), color=color.name() if color is not None else '')
        if item.property('indicatorOffset') is not None:
            indicator = item.property('indicator')
            p = indicator.mapToScene(QPointF())
            interiors[name] = dict(x=p.x(), y=p.y(), width=indicator.width(), height=indicator.height())
    return dict(boxes=boxes, styles=styles, interiors=interiors, frameIds=frame_ids, fills=fills)


def source_hashes(repo, handler, names):
    import hashlib
    shared = {}
    for path in (repo / 'src/tactic_stream/shared_ui').rglob('*.mjs'):
        relative = path.relative_to(repo / 'src/tactic_stream/shared_ui')
        assert path.read_bytes() == (handler / 'thlib/ui/qml/tactic_frame' / relative).read_bytes(), 'Unsynchronized Frame module: ' + str(relative)
        shared[path.relative_to(repo / 'src/tactic_stream/shared_ui').as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    paths = (list((handler / 'thlib/ui/qml/tactic_frame').rglob('*.qml'))
             + list((handler / 'thlib/ui/qml/controls').glob('*.qml'))
             + [handler / 'thlib/ui/qml/Theme.qml'] + [handler / name for name in names])
    native = {str(path.relative_to(handler)).replace('\\', '/'): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    return shared, native
