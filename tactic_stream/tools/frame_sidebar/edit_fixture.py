"""Exercise Stream's real sidebar draft endpoint without persistence or a server."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch
from tactic_stream.server import sidebar_editor as sidebar

catalog = json.loads((Path(__file__).parent / 'output/catalog.json').read_text())
groups = [SimpleNamespace(get_data=lambda row=row: row) for row in catalog['groupRecords']]
with patch.object(sidebar, '_require_admin'), patch.object(sidebar, '_groups', return_value=groups), patch.object(sidebar.Project, 'get_project_code', return_value='demo'):
    for line in sys.stdin:
        try:
            request = json.loads(line)
            result = sidebar.sidebar_request('edit', request)
            print(json.dumps(dict(result=result)), flush=True)
        except (ValueError, TypeError) as error:
            print(json.dumps(dict(error=str(error))), flush=True)
