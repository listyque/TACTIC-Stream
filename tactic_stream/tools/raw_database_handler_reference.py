"""Capture the real Handler raw editor on the browser check's same private fixture."""
import argparse
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    sys.path.insert(0, 'D:/grav/Tactic Stream/TH')
    from tests.test_raw_database import RawDatabaseQmlTests
    from tests.profile_ui_responsiveness import frame

    RawDatabaseQmlTests.setUpClass()
    fixture = RawDatabaseQmlTests()
    fixture.setUp()
    try:
        window = fixture.fixture.window
        native = fixture.fixture.fixture
        native.app.removeTranslator(native.translator)
        native.engine.retranslate()
        fixture.editor.rows[0]['values'].update(id=2, value='created')
        fixture.editor._document_loaded()
        fixture.editor.stateChanged.emit()
        window.resize(1400, 940)
        frame(window)
        cell = fixture.fixture.item('rawCell_0_value')
        header = fixture.fixture.item('rawTableHeadings')
        print('Raw geometry:', json.dumps(dict(rowHeight=cell.parentItem().height(), headerHeight=header.height(),
            columnWidth=cell.parentItem().width(), inputWidth=cell.width(), inputHeight=cell.height())))
        print('Raw controls:', json.dumps({name: dict(width=fixture.fixture.item(name).width(), height=fixture.fixture.item(name).height())
            for name in ('rawWarning', 'rawNewRow', 'rawExportCsv', 'rawDropTable')}))
        window.grabWindow().save(str(args.output))
        if fixture.fixture.fixture.warnings:
            raise AssertionError(fixture.fixture.fixture.warnings)
    finally:
        fixture.doCleanups()


if __name__ == '__main__':
    main()
