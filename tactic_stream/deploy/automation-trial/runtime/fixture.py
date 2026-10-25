"""Private native TS fixture process. It never imports Handler or connects to a real server."""
import json
from pathlib import Path
import sys

ROOT = Path('/work')


def main():
    from pyasm.search.storage import Store
    store = Store(ROOT/'server')
    if '--serve' in sys.argv:
        import uvicorn
        from tactic_stream.server.app import create_app
        uvicorn.run(create_app(store.data_dir, event_collector=False), host='127.0.0.1', port=8081,
                    log_level='error', access_log=False)
        return
    from pyasm.security.authenticator import hash_password
    from tactic_stream.server.api import Api
    request = json.loads((ROOT/'request.json').read_text())
    document = request['document']
    project = request['project']
    kind = document['search_type'] or document['entry_key'].rpartition('@')[0] or project+'/trial_object'
    namespace, name = kind.split('/', 1)
    if namespace in ('sthpw', 'config'):
        raise ValueError('Trial fixtures require a project SearchType, not a system/config type')
    store.initialize(hash_password('trial-only-password'))
    api = Api(store)
    api.protocol = 'json'
    ticket = api.get_ticket('admin', 'trial-only-password')
    auth = dict(ticket=ticket, project='admin')
    api.dispatch('execute_cmd', (auth, 'tactic.command.CreateProjectCmd',
                 dict(project_code=project, project_title='Isolated automation trial')))
    auth['project'] = project
    api.dispatch('execute_cmd', (auth, 'tactic.core.schema_commands.SearchTypeCreatorCmd',
                 dict(database=project, namespace=namespace, search_type_name=name, asset_title='Trial objects')))
    item = api.dispatch('insert', (auth, kind, dict(code='TRIAL001', name='Owned trial object')))
    entry = document['entry_key'].rpartition('@')[2] or 'trial_objects'
    from xml.etree import ElementTree as ET
    root = ET.Element('config')
    view = ET.SubElement(root, 'tactic_handler')
    element = ET.SubElement(view, 'element', name=entry, title='Trial objects')
    display = ET.SubElement(element, 'display', {'class':'LinkWdg'})
    ET.SubElement(display, 'search_type').text = kind
    ET.SubElement(display, 'view').text = 'table'
    api.dispatch('insert', (auth, 'config/widget_config', dict(search_type='SideBarWdg', view='tactic_handler',
                 priority=2000, login='', config=ET.tostring(root, encoding='unicode'))))
    command = 'tactic.ui.panel.handler_automation_cmd.HandlerAutomationCmd'
    def call(action, **values):
        return api.dispatch('execute_cmd', (auth, command, dict(action=action, project_code=project, **values)))['info']
    from uuid import uuid4
    preview = call('preview', document=document)
    draft = call('save_draft', document=document, expected_revision=preview['revision'], operation_id=str(uuid4()))
    applied = call('activate', draft_id=draft['draft_id'], draft_revision=draft['revision'],
                   expected_revision=call('read')['revision'], operation_id=str(uuid4()))
    state = call('read')
    (ROOT/'fixture.json').write_text(json.dumps(dict(project=project, ticket=ticket,
        search_key=item['__search_key__'], state=state, applied=applied)), encoding='utf-8')


if __name__ == '__main__':
    main()
