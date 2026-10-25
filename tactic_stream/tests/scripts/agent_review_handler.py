"""Native editor review against a real test server; review does not run source."""
import argparse
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import Mock, patch

parser = argparse.ArgumentParser()
parser.add_argument('--handler-root', type=Path, required=True)
parser.add_argument('--fixture', type=Path, required=True)
args = parser.parse_args()
data = json.loads(args.fixture.read_text(encoding='utf-8'))
os.environ.update(QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software',
                  TACTIC_HANDLER_SETTINGS_DIR=str(args.fixture.parent/'private-native-settings'))
sys.path.insert(0, str(args.handler_root))
from PySide6.QtQuick import QQuickWindow
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QFontDatabase, QFont
from PySide6.QtTest import QTest
from tests import test_frame_script_tools as native
from tests.profile_ui_responsiveness import frame
from thlib.ui.script_editor import ScriptEditorController
from thlib import tactic_classes as tc
from thlib.side.client.tactic_client_lib import TacticServerStub
from thlib.environment import env_inst
from thlib.ui.icon_font import qml_icon_bindings

surface = native.ScriptToolsTests()
surface.setUpClass()
surface.setUp()
for name, value in qml_icon_bindings(native.QML.parents[2], surface.engine).items():
    surface.engine.rootContext().setContextProperty(name, value)
if os.name == 'nt':
    QFontDatabase.addApplicationFont(str(Path(os.environ['WINDIR'])/'Fonts/segoeui.ttf'))
    surface.app.setFont(QFont('Segoe UI'))
server = TacticServerStub(setup=False, server=data['server'], ticket=data['ticket'], project=data['project'])
with patch('thlib.ui.script_editor.env_read_config', return_value={}), patch('thlib.ui.script_editor.env_write_config'):
    editor = ScriptEditorController(None, Mock())
editor._project_code = lambda: data['project']
editor._write_settings = lambda: None
review = editor.agentDrafts
try:
    with patch.object(tc, 'server_start', return_value=server):
        view = surface.create(native.QML/'features/scripts/AgentDraftsView.qml',
            dict(theme=surface.theme, controller=review, width=1000, height=700))
        window = QQuickWindow()
        window.setColor(surface.theme.property('workspace'))
        window.resize(1000, 700)
        surface.windows.append(window)
        view.setParentItem(window.contentItem())
        window.show()
        window.requestActivate()
        def wait():
            deadline = time.monotonic()+30
            while review.model['busy'] and time.monotonic() < deadline:
                QTest.qWait(10)
            assert not review.model['busy'] and not review.model['error'], review.model
            frame(window)
        wait()
        for key in (Qt.Key_End, Qt.Key_Home):
            surface.item(view, 'agentDraftChoice').forceActiveFocus()
            QTest.keyClick(window, key)
            wait()
        index = next(i for i, row in enumerate(review.model['drafts']) if row['draft_id'] == data['draft_id'])
        for _ in range(index):
            surface.item(view, 'agentDraftChoice').forceActiveFocus()
            QTest.keyClick(window, Qt.Key_Down)
            wait()
        assert review.model['selected'] == data['draft_id'], review.model
        assert review.model['draft']['document']['source'].strip()
        assert not surface.warnings, surface.warnings
        if data.get('activate'):
            assert review.model['draft']['ready'], review.model
            checkbox = surface.item(view, 'agentDraftReviewed')
            point = checkbox.mapToScene(QPointF(12, checkbox.height()/2))
            QTest.mouseClick(window, Qt.LeftButton, pos=point.toPoint())
            frame(window)
            assert review.model['reviewed'], review.model
            surface.click(window, surface.item(view, 'agentDraftActivate'))
            assert review.model['confirming'], review.model
            surface.click(window, surface.item(view, 'agentDraftActivate'))
            wait()
            assert review.model['draft']['activated']
        assert window.grabWindow().save(data['screenshot'])
        assert not surface.warnings, surface.warnings
        print('Native editor source/report review and confirmed API activation passed; candidate code was not executed')
finally:
    surface.objects.reverse()
    surface.doCleanups()
    env_inst.server_pool.exit()
