"""Opt-in native request input through real XML-RPC and an external host."""
import argparse
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--handler-root', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--server', required=True)
args = parser.parse_args()
os.environ.update(QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software')
sys.path.insert(0, str(args.handler_root))
from PySide6.QtQuick import QQuickWindow
from PySide6.QtTest import QTest
from tests.test_agent_request import Application
from tests.test_frame_script_tools import ScriptToolsTests, QML
from tests.profile_ui_responsiveness import frame
from thlib.ui.agent_request import AgentRequestController
from thlib.side.client.tactic_client_lib import TacticServerStub
from thlib.environment import env_inst
from thlib.ui.icon_font import qml_icon_bindings

surface = ScriptToolsTests()
surface.setUpClass()
surface.setUp()
for name, value in qml_icon_bindings(QML.parents[2], surface.engine).items():
    surface.engine.rootContext().setContextProperty(name, value)
app = Application()
app.current_project_code = 'agentfilm'
app.section.entry_key = 'agentfilm/shot@shot_list'
app.section.search_type = 'agentfilm/shot'
app.keys = ['agentfilm/shot?project=agentfilm&code=SH010']
controller = AgentRequestController(app, env_inst.server_pool)
server = TacticServerStub(setup=False, server=args.server, ticket=os.environ['TACTIC_TEST_TICKET'], project='agentfilm')
try:
    with patch('thlib.tactic_classes.server_start', return_value=server):
        controller.open()
        view = surface.create(QML/'features/scripts/AgentRequestView.qml',
            dict(theme=surface.theme, controller=controller, width=1000, height=650))
        window = QQuickWindow()
        window.resize(1000, 650)
        view.setParentItem(window.contentItem())
        surface.windows.append(window)
        window.show()
        window.requestActivate()

        def wait(predicate, seconds=30):
            deadline = time.monotonic()+seconds
            while not predicate():
                if time.monotonic()>deadline:
                    raise RuntimeError('Native request timed out: '+str(controller.model))
                QTest.qWait(20)
            assert not controller.model['error'], controller.model
            frame(window)

        wait(lambda: not controller._in_flight and bool(controller.model['hosts']))
        surface.fill(window, surface.item(view,'agentRequestPrompt'),
            'Read the captured context and selected objects. Reply with captured client, project, page, view and selected object codes. Do not change any data or configuration.')
        surface.click(window,surface.item(view,'agentRequestSend'))
        wait(lambda: controller.model['request'].get('status') in ('completed','failed','interrupted'),180)
        request = controller.model['request']
        assert request['status']=='completed', request
        assert request['document']['context']['client']=='TH'
        assert request['document']['context']['project']=='agentfilm'
        assert request['document']['context']['search_keys']==app.keys
        assert request['document']['allow_changes'] is False
        assert 'SH010' in request['answer'] and 'TH' in request['answer'], request['answer']
        args.output.write_text(json.dumps(request,ensure_ascii=False,indent=2),encoding='utf-8')
        assert not surface.warnings, surface.warnings
        print('Real native QML input -> XML-RPC -> external model -> native answer passed; read-only task')
finally:
    controller._timer.stop()
    env_inst.exit_pools()
    controller.deleteLater()
    app.deleteLater()
    surface.doCleanups()
