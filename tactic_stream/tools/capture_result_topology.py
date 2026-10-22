"""Render current Handler model/QML against the owned CG fixture's native records."""
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
HANDLER = Path('D:/grav/Tactic Stream/TH')
OUTPUT = ROOT / '.screenshots/continuous-topology'


def main():
    os.environ.update(QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software', QT_SCALE_FACTOR='1')
    sys.path.insert(0, str(HANDLER))
    from PySide6.QtCore import QPoint, QUrl, Slot
    from PySide6.QtGui import QColor, QFontDatabase
    from PySide6.QtQml import QQmlComponent, QQmlEngine
    from PySide6.QtQuick import QQuickWindow
    from PySide6.QtTest import QTest
    from tests.qt_application import gui_test_application
    from tests.test_workspace_result_item import WorkspaceResultItemTests, _WorkspaceAppController
    from thlib import tactic_classes as tc
    from thlib.ui.icon_font import qml_icon_bindings
    from thlib.ui.workspace_models.results import WorkspaceItemModel
    from thlib.ui.workspace_models.results_types import WorkspaceNode
    from thlib.global_functions import gen_acronym

    class Controller(_WorkspaceAppController):
        @Slot(str, result=str)
        def get_acronym(self, text):
            return gen_acronym(text)

    data = json.loads((OUTPUT / 'native.json').read_text(encoding='utf-8'))
    app = gui_test_application()
    project = tc.Project(data['project'])
    project.get_all_search_types(data['stypes'], data['pipelines'], data['schema'], data['views'])
    objects = {}
    for record in data['objects']:
        source = tc.SObject(copy.deepcopy(record), project)
        source.init_snapshots(copy.deepcopy(record['__snapshots__']))
        objects[source.get_code()] = source
    arm, metal = objects['DEMO_ARM'], objects['DEMO_TEX_METAL']
    # Handler resolves category labels for the main search, but nested relation
    # records only carry their raw category and configured literal select labels.
    metal.info.pop('__category_labels__', None)
    model = WorkspaceItemModel()
    root = WorkspaceNode(node_id='arm', node_type='sobject', code=arm.get_code(), search_key=arm.get_search_key(),
        title=arm.get_title(), subtitle=model._sobject_subtitle(arm.get_stype(), arm.info),
        accent=arm.get_stype().get_stype_color(fmt='hex'), expanded=True, has_children=True, source=arm,
        chips=model._build_info_items(arm.get_stype(), arm.info))
    model._roots = [root]
    model._register_tree(root)

    def counts(source, *_args):
        stypes = {}
        for relation in source.get_stype().get_schema().children:
            target = relation.get('from')
            count = len(data['related'].get(source.get_code() + ':' + target, []))
            stypes[relation.get('instance_type') or target] = count
        return dict(notes={}, tasks={}, stypes=stypes)

    def related(source, child_stype=None, **_kwargs):
        codes = data['related'][source.get_code() + ':' + child_stype.get_code()]
        return [objects[code] for code in codes if code in objects]

    with patch.object(tc, 'server_start', side_effect=AssertionError('Capture must not connect to a user server')), \
            patch.object(tc, 'get_notes_count', counts), patch.object(tc.SObject, 'get_related_sobjects', related), \
            patch.object(tc.SObject, 'update_snapshots', lambda *_args, **_kwargs: None), \
            patch.object(tc.File, 'get_full_abs_path', lambda source: source.info['__fixture_path__']), \
            patch.object(model, '_checkin_option', return_value=False):
        model._load_root(root)
        assert root.children[0].node_type == 'snapshot' and root.children[0].title == 'Robot Arm.md'
        texture = next(node for node in root.children if node.node_type == 'relation' and node.code == 'cg/texture')
        model._load_relation(texture)
        texture.expanded = True
        child = texture.children[0]
        model._load_root(child)
        child.expanded = True
        assert [node.title for node in child.children] == ['Icon', 'Attachment', 'Publish']
        assert child.subtitle == 'Sample texture'
        assert [chip['text'] for chip in child.chips] == ['DEMO_CAT_MAT', 'Diffuse']

    engine = QQmlEngine()
    controller = Controller()
    engine.rootContext().setContextProperty('appController', controller)
    for name, value in qml_icon_bindings(HANDLER, engine).items():
        engine.rootContext().setContextProperty(name, value)
    for font in ('segoeui.ttf', 'seguisb.ttf', 'segoeuib.ttf'):
        QFontDatabase.addApplicationFont('C:/Windows/Fonts/' + font)
    qml = HANDLER / 'thlib/ui/qml'
    theme_component = QQmlComponent(engine, QUrl.fromLocalFile(str(qml / 'Theme.qml')))
    theme = theme_component.createWithInitialProperties({'dark': True})
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(qml / 'WorkspaceResultItem.qml')))
    window = QQuickWindow()
    window.setColor(QColor(theme.property('workspace')))
    window.resize(1380, 760)
    items = []

    def rows(node):
        return [node] + [child for branch in node.children for child in (rows(branch) if branch.expanded else [branch])]

    try:
        y = 0
        for index, node in enumerate(rows(root)):
            props = dict(index=index, nodeId=node.node_id, nodeType=node.node_type, searchKey=node.search_key,
                itemCode=node.code, title=node.title, subtitle=node.subtitle, accent=node.accent, depth=node.depth,
                parentId=node.parent_id, expanded=node.expanded, hasChildren=node.has_children, childCount=node.child_count,
                context=node.context, version=node.version, author=node.author, repository=node.repository,
                repositoryColor=node.repository_color, isLatest=node.is_latest, isVersionless=node.is_versionless,
                filePath=node.file_path, fileExists=bool(node.file_path and Path(node.file_path).is_file()),
                fileSize=node.file_size, timestamp=node.timestamp, timestampPretty=node.timestamp_pretty,
                timestampSimple=node.timestamp_simple, infoChips=node.chips, itemControls=model._controls_for(node),
                compactMode=False, width=1368)
            item = component.createWithInitialProperties(WorkspaceResultItemTests.item_properties(theme, **props))
            assert item is not None, [error.toString() for error in component.errors()]
            item.setParentItem(window.contentItem()); item.setY(y)
            y += item.height() + 3
            items.append(item)
        window.resize(1380, int(y + 12)); window.show()
        QTest.mouseMove(window, QPoint(1378, int(y + 10))); QTest.qWait(600); app.processEvents()
        assert window.grabWindow().save(str(OUTPUT / 'handler-texture.png'))
        report = dict(rows=[dict(kind=node.node_type, title=node.title, depth=node.depth) for node in rows(root)],
            limits='Current Handler schema/SObject/process/model/QML; count and relation queries supplied from owned native fixture; no live user Handler connection.',
            sources={str(path.relative_to(HANDLER)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in (qml / 'WorkspaceResultItem.qml', HANDLER / 'thlib/ui/workspace_models/results_loading.py')})
        (OUTPUT / 'handler.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print('PASS: current Handler native model publish ordering and type-recursion filtering; QML capture')
    finally:
        window.close()
        for item in items:
            item.deleteLater()
        app.processEvents()


if __name__ == '__main__':
    main()
