"""Read saved server configuration through the real independent TH consumers."""
import argparse
import json
from pathlib import Path
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--handler-root', type=Path, required=True)
parser.add_argument('--fixture', type=Path, required=True)
args = parser.parse_args()
sys.path.insert(0, str(args.handler_root))

from thlib.environment import env_mode
env_mode.current_path = str(args.fixture.parent / 'handler-state')
from thlib import tactic_classes as tc
from thlib.ui.models import NavigationModel
from thlib.ui.workspace_layout_presets import layout_configuration_from_xml

data = json.loads(args.fixture.read_text(encoding='utf8'))
project = tc.Project(dict(code=data.get('project', 'one'), title='Agent page test'))
project.stypes = {}
project.views = tc.ViewsConfig(data['rows'], project=project)
login = tc.Login(dict(code='admin', login='admin'), [], [])
entry = next(row for row in NavigationModel.build_project_entries(project, login)
             if row.title == data.get('title', 'Review shots'))
saved = data['saved']
assert entry.table_view == saved['view']
assert entry.view_mode == 'table'
assert entry.search_view == saved['search']['view']
assert entry.layout_preset == saved['workspace']['view']
assert entry.filter_records and entry.filter_records[0]['column'] == data.get('filter_column', 'code')
assert str(entry.filter_records[0]['value']) == str(data.get('filter_value', 'A'))
layout = next(row for row in data['rows'] if row['view'] == entry.layout_preset)
assert layout_configuration_from_xml(layout['config'], entry.layout_preset) == saved['workspace']['configuration']
print('TH native navigation, table-view selection, filter decoding and dock configuration passed')
