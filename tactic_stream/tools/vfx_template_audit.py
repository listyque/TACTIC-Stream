"""Exercise every registered VFX type and saved view in an isolated project."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import zipfile
from xml.etree import ElementTree as ET

from pyasm.search import Search
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from tactic_stream.server.api import Api
from tactic_stream.server.interface import read_interface, read_form
from tactic_stream.server.result_items import read_result_items
from tactic_stream.server.table_cells import read_table_cells
from tools.file_project_delivery import ROOT


def audit(output):
    sys.path.insert(0, str(ROOT / 'tests'))
    from test_vfx_relationships import exercise

    with tempfile.TemporaryDirectory(prefix='vfx-audit-') as directory:
        store = Store(Path(directory))
        store.initialize(hash_password('plugin-test-password'))
        core = exercise(store, 'vfx_audit')
        api = Api(store)
        api.protocol = 'json'
        token = api.get_ticket('admin', 'plugin-test-password')
        project = 'vfx_audit_ok'
        auth = dict(ticket=token, project=project)
        with zipfile.ZipFile(ROOT.parent / 'legacy/src/install/start/templates/vfx-1.0.0.zip') as archive:
            types = [node.get('code') for node in ET.fromstring(archive.read('vfx/manifest.xml')).findall('search_type')]
        report = dict(template='vfx-1.0.0-stream.1', scope='SQLite / administrator / isolated generated records',
                      excluded_by_user=['Maya', 'applets'], core=core, types=[], views=[])
        with request_context(RequestContext(store, 'admin', project)):
            api.auth.bind_security('admin', token)
            configs = Search('config/widget_config').get_sobjects()
            for stype in types:
                entry = dict(search_type=stype)
                report['types'].append(entry)
                try:
                    search = Search(stype)
                    records = search.get_sobjects()
                    if not records:
                        columns = search.get_columns()
                        values = {field: 'AUDIT' for field in ('code', 'name') if field in columns}
                        created = api.dispatch('insert', (auth, stype, values))
                        records = [Search.get_by_search_key(created['__search_key__'])]
                        entry['insert'] = 'passed'
                    else:
                        entry['insert'] = 'core fixture'
                    entry['query'] = 'passed'
                    key = records[0].get_search_key()
                    try:
                        read_result_items(stype, [key], dict(kind='children'))
                        entry['tree'] = 'passed'
                    except Exception as error:
                        entry['tree'] = dict(error=type(error).__name__, message=str(error))
                    views = {'table', 'edit'} | {row.get_value('view') for row in configs if row.get_value('search_type') == stype}
                    for view in sorted(views):
                        row = dict(search_type=stype, view=view)
                        report['views'].append(row)
                        if view in ('definition', 'edit_definition', 'color', 'tab_config_render') or ':' in view or 'filter' in view or view.startswith('search_'):
                            row['status'] = 'configuration; not a table/form scenario'
                            continue
                        try:
                            if view == 'edit':
                                form = read_form(stype, view, search_key=key)
                                row.update(status='form loaded; save not exercised', fields=[item['name'] for item in form['fields']])
                                continue
                            definition = read_interface(stype, view)
                            cells = read_table_cells(stype, view, [key])[key]
                            row['element_count'] = len(definition['table']['elements'])
                            row['unsupported'] = [dict(name=item['name'], display=item['display'], action=item['action'])
                                                  for item in definition['table']['elements'] if not item['cell']['supported']]
                            row['errors'] = {name: cell['error'] for name, cell in cells.items() if cell.get('error')}
                            row['status'] = 'gaps' if row['unsupported'] or row['errors'] else 'cells passed; GUI actions not exercised'
                            if not row['element_count']:
                                row['status'] = 'no table columns; GUI not exercised'
                        except Exception as error:
                            row.update(status='failed', error=type(error).__name__, message=str(error))
                except Exception as error:
                    entry.update(query='failed', error=type(error).__name__, message=str(error))
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    result = audit(parser.parse_args().output)
    print(json.dumps(dict(types=len(result['types']), views=len(result['views']),
                          gaps=sum(row['status'] in ('gaps', 'failed') for row in result['views']))))
