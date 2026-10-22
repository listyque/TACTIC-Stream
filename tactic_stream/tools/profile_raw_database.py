"""Measure real Handler raw-page presentation with fixture or saved response data."""
import argparse
import copy
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, 'D:/grav/Tactic Stream/TH')
from tests.test_raw_database import RawDatabaseQmlTests
from tests.profile_ui_responsiveness import frame
from tests.test_sidebar_editor_qml import SidebarEditorQmlTests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--page', type=Path, help='Saved raw load response; data remains local')
    args = parser.parse_args()
    RawDatabaseQmlTests.setUpClass()
    fixture = RawDatabaseQmlTests()
    fixture.setUp()
    try:
        editor = fixture.editor
        if args.page:
            page = json.loads(args.page.read_text(encoding='utf-8'))
            page = page.get('result', page)
            editor._identity = page['identity']
            editor._metadata = page['metadata']
            editor._document = page['document']
            columns = page['metadata']['columns']
        else:
            columns = [dict(name=f'column_{index}', type='TEXT', readonly=False) for index in range(12)]
            editor._metadata.update(columns=columns, total=100)
            editor._document = dict(offset=0, rows=[dict(key=[index], revision=str(index), values={column['name']: f'value {index}' for column in columns}) for index in range(50)])
        count = len(editor.rows)
        fixture.fixture.window.resize(1400, 940)
        start = time.perf_counter()
        editor._document_loaded()
        editor.stateChanged.emit()
        frame(fixture.fixture.window)
        load = time.perf_counter() - start
        editor._metadata['offset'] += count
        editor._document = copy.deepcopy(editor._document)
        editor._document['offset'] = editor._metadata['offset']
        for index, row in enumerate(editor.rows):
            row['key'] = [editor._metadata['offset'] + index]
            name = columns[0]['name']
            row['values'][name] = editor._metadata['offset'] + index
        start = time.perf_counter()
        editor._document_loaded()
        editor.stateChanged.emit()
        frame(fixture.fixture.window)
        page = time.perf_counter() - start
        start = time.perf_counter()
        editor.set_cell(0, columns[0]['name'], '"edited"')
        frame(fixture.fixture.window)
        edit = time.perf_counter() - start
        cells = [item for item in SidebarEditorQmlTests.descendants(fixture.fixture.window.contentItem()) if item.objectName().startswith('rawCell_')]
        print(json.dumps(dict(rows=count, columns=len(columns), createdCells=len(cells),
            createdMenus=sum(cell.property('contextMenu') is not None for cell in cells),
            loadSeconds=round(load, 3), pageSeconds=round(page, 3), editSeconds=round(edit, 3))), flush=True)
        assert not fixture.fixture.fixture.warnings, fixture.fixture.fixture.warnings
    finally:
        fixture.doCleanups()


if __name__ == '__main__':
    main()
