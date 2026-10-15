"""Whole Workflow page: independent original TH and current Frame TH."""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
TH = Path('D:/code/th_codex')
HERE = Path(__file__).resolve().parent
OUT = HERE / 'output/administration'
OUT.mkdir(parents=True, exist_ok=True)
os.environ.update(QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software', QSG_RENDER_LOOP='basic')
sys.path[:0] = [str(TH), str(ROOT / 'tools/frame_admin')]
from PySide6.QtCore import QPointF, QUrl
from PySide6.QtQml import QQmlComponent
from tests.test_administration_qml import AdministrationQmlTests
from tests.profile_ui_responsiveness import frame
from native_capture import controls, snapshot


def main():
    AdministrationQmlTests.setUpClass()
    fixture = AdministrationQmlTests()
    fixture.setUp()
    editor = fixture.admin.workflowEditor
    editor._catalog = list(editor.metadata['pipelines'])
    editor.catalogChanged.emit()
    fixture.admin.select_section('workflow')
    fixture.fixture.engine.rootContext().setContextProperty('localizationController', {'current_language': 'ru'})
    (OUT / 'fixture.json').write_text(json.dumps(dict(document=editor.document, metadata=editor.metadata,
        identity=editor.identity, catalog=editor.catalog, revision='isolated-reference', canWrite=editor.canWrite)), encoding='utf-8')
    rows = []
    try:
        for original in (True, False):
            qml = HERE / 'reference/thlib/ui/qml' if original else TH / 'thlib/ui/qml'
            assert qml.is_dir(), 'Run reference_graph.py to extract the independent original first'
            component = QQmlComponent(fixture.fixture.engine)
            component.setData(('import QtQuick\nimport QtQuick.Controls\nimport "' + qml.as_uri() + '" as TH\n'
                'ApplicationWindow{visible:true;width:1600;height:900;color:theme.workspace;'
                'TH.Theme{id:theme;dark:true;clickAnimationsEnabled:false;hoverAnimationsEnabled:false;fadeAnimationsEnabled:false;popupAnimationsEnabled:false}'
                'TH.AdministrationView{anchors.fill:parent;theme:theme}}').encode(), QUrl())
            assert component.isReady(), [error.toString() for error in component.errors()]
            window = component.create()
            assert window
            try:
                for width in (1100, 1600):
                    window.setWidth(width)
                    frame(window)
                    named = controls(window)
                    library = named['adminWorkflowList' if original else 'adminWorkflowCatalogPanel']
                    graph = named['schemaCanvas' if original else 'adminGraphCanvas'] if 'schemaCanvas' in named else named.get('adminGraphCanvas')
                    library_right = library.mapToScene(QPointF(library.width(), 0)).x()
                    assert library_right < 300, ('Workflow library must remain in the left navigation', original, library_right)
                    if graph:
                        assert library_right < graph.mapToScene(QPointF()).x()
                    image = ('original' if original else 'frame') + '-' + str(width) + '.png'
                    assert window.grabWindow().save(str(OUT / image))
                    rows.append(dict(original=original, width=width, image=image, **snapshot(window)))
            finally:
                window.close()
                window.deleteLater()
        assert fixture.fixture.warnings == [], fixture.fixture.warnings
    finally:
        fixture.doCleanups()
    (OUT / 'native.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Original and Frame whole Workflow pages: left library at two widths passed')


if __name__ == '__main__':
    main()
