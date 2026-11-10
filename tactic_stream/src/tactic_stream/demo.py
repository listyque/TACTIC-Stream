"""Install the public demonstration on a new server through native operations."""
from datetime import date, timedelta
from hashlib import file_digest
import json
import os
from pathlib import Path
import secrets
from xmlrpc.client import Binary

from pyasm.common import Environment
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from tactic_stream.server.api import Api

ASSETS = (
    ('survey-drone', 'Survey Drone', 'Atmospheric reconnaissance vehicle'),
    ('landing-beacon', 'Landing Beacon', 'Guidance equipment for the landing sequence'),
    ('transit-pod', 'Transit Pod', 'Crew transport module'),
    ('orbital-relay', 'Orbital Relay', 'Communications tower and antenna array'),
    ('flight-suit', 'Flight Suit', 'Protective suit for exterior sequences'),
    ('surface-rover', 'Surface Rover', 'Utility vehicle for the desert set'),
)
PLUGINS = ('studio-review.zip', 'workspace-pulse.zip')


def verify_content(directory: Path) -> None:
    directory = directory.resolve()
    manifest = directory / 'manifest.json'
    if manifest.stat().st_size > 65536:
        raise ValueError('Demo content manifest is too large')
    document = json.loads(manifest.read_text(encoding='utf-8'))
    expected = {'assets/' + item[0] + '.png' for item in ASSETS} | {'plugins/' + name for name in PLUGINS}
    if (not isinstance(document, dict) or document.get('format') != 'tactic-stream-demo-1'
            or not isinstance(document.get('files'), dict) or set(document['files']) != expected):
        raise ValueError('Choose the complete TACTIC demonstration content')
    for relative, expected_hash in document['files'].items():
        path = directory / relative
        if not path.resolve().is_relative_to(directory) or path.is_symlink():
            raise ValueError('Demo content must remain inside its directory')
        with path.open('rb') as source:
            if file_digest(source, 'sha256').hexdigest() != expected_hash:
                raise ValueError('Demo content checksum mismatch: ' + relative)


def install(store: Store, login: str, password: str, directory: Path) -> dict:
    """Require an administrator and an empty installation; never replace a project."""
    directory = directory.resolve()
    verify_content(directory)
    api = Api(store)
    api.protocol = 'json'
    ticket = api.get_ticket(login, password)
    auth = dict(ticket=ticket, project='admin')
    marker = store.data_dir / 'demo-installed.json'
    accounts_file = store.data_dir / 'demo-accounts.json'

    def call(method, *args, **kwargs):
        return api.dispatch(method, (auth, *args), kwargs)

    def command(name, **values):
        return call('execute_cmd', name, values)['info']

    def publish(key, image, context='icon'):
        call('upload_file', image.name, Binary(image.read_bytes()))
        return call('simple_checkin', key, context, image.name, mode='upload',
                    create_icon=True, process=context.split('/')[0],
                    description='Orbit Studio demonstration publication')

    try:
        with request_context(RequestContext(store, login, 'admin')):
            api.auth.bind_security(login, ticket)
            if not Environment.get_security().is_admin():
                raise PermissionError('Administrator access is required to install demonstration projects')
        if marker.exists():
            return json.loads(marker.read_text(encoding='utf-8'))
        projects = call('query', 'sthpw/project')
        if any(row['code'] not in ('admin', 'sthpw') for row in projects) or accounts_file.exists():
            raise FileExistsError('Demo installation needs an empty server. Existing projects and accounts were preserved.')
        people = [('maya', 'Maya', 'Chen', 'artists'), ('leo', 'Leo', 'Martins', 'artists'),
                  ('nora', 'Nora', 'Kim', 'readers')]
        if any(row['login'] in {person[0] for person in people} for row in call('query', 'sthpw/login')):
            raise FileExistsError('A demonstration login already exists; no accounts were changed')
        for code, title, types in [('orbit', 'Orbit Studio', ['asset', 'shot', 'sequence']),
                                   ('atlas', 'Atlas Reference Library', ['asset'])]:
            command('tactic.command.CreateProjectCmd', project_code=code, project_title=title, project_stype=types)
        for group, access in [('artists', 'insert'), ('readers', 'view')]:
            rules = '<rules>'
            for project in ('orbit', 'atlas'):
                rules += '<rule group="project" code="' + project + '" access="allow"/>'
                types = [project + '/' + kind for kind in ('asset', 'shot', 'sequence')]
                types += ['studio/review', 'sthpw/task', 'sthpw/note', 'sthpw/snapshot', 'sthpw/file']
                rules += ''.join('<rule group="search_type" code="' + kind + '" project="' + project
                                 + '" access="' + access + '"/>' for kind in types)
                rules += '<rule group="process" process="*" project="' + project + '" access="allow"/>'
            rules += '</rules>'
            call('insert', 'sthpw/login_group', dict(code='demo_' + group, login_group='demo_' + group,
                description='Demonstration ' + group, access_rules=rules))
        accounts = []
        for user, first, last, group in people:
            user_password = secrets.token_urlsafe(18)
            call('insert', 'sthpw/login', dict(code=user, login=user, first_name=first, last_name=last,
                                             password=hash_password(user_password)))
            call('insert', 'sthpw/login_in_group', dict(login=user, login_group='demo_' + group))
            accounts.append(dict(login=user, password=user_password, role=group))
        counts = {}
        installed_plugins = {}
        for project, entries in [('orbit', ASSETS), ('atlas', ASSETS[::2])]:
            auth['project'] = project
            pipeline = project + '_asset'
            graph = '<pipeline>' + ''.join(
                '<process name="' + process + '" type="manual" xpos="' + str(60 + index * 220) + '" ypos="120"/>'
                for index, process in enumerate(('model', 'lookdev', 'review'))) + (
                '<connect from="model" to="lookdev"/><connect from="lookdev" to="review"/></pipeline>')
            call('insert', 'sthpw/pipeline', dict(code=pipeline, name='Asset production',
                search_type=project + '/asset', project_code=project, pipeline=graph))
            for index, process in enumerate(('model', 'lookdev', 'review')):
                call('insert', 'config/process', dict(code=project + '_' + process, process=process,
                    pipeline_code=pipeline, sort_order=index, workflow=json.dumps(dict(task_pipeline='task'))))
            for context in ('icon', 'publish/*'):
                call('insert', 'config/naming', dict(search_type=project + '/asset', snapshot_type='file',
                    context=context, latest_versionless=False,
                    dir_naming='{project.code}/assets/{sobject.code}/{snapshot.context}/v{snapshot.version}',
                    file_naming='{basefile}.{ext}'))
            assets = []
            for index, (filename, name, description) in enumerate(entries):
                asset = call('insert', project + '/asset', dict(code='ASSET_%03d' % (index + 1),
                    name=name, description=description, pipeline_code=pipeline))
                key = asset['__search_key__']
                assets.append(key)
                image = directory / 'assets' / (filename + '.png')
                publish(key, image)
                publish(key, image, 'publish/lookdev')
                if index == 0:
                    publish(key, image, 'publish/lookdev')
                for stage, process in enumerate(('model', 'lookdev', 'review')):
                    task = call('create_task', key, process, description=name + ' / ' + process,
                        bid_start_date=str(date.today() + timedelta(days=index + stage * 2)),
                        bid_end_date=str(date.today() + timedelta(days=index + stage * 2 + 3)),
                        bid_duration=3, assigned=('maya', 'leo', 'nora')[stage])
                    if isinstance(task, str):
                        task = json.loads(task) if task.startswith('{') else call('query', 'sthpw/task', [('code', task)])[0]
                    call('update', task['__search_key__'], dict(status='In Progress' if stage == 0 else 'Pending',
                                                               completion=60 if stage == 0 else 0))
                call('create_note', key, 'Review the silhouette and publish a new version when ready.', process='lookdev')
            counts[project] = dict(assets=len(assets), tasks=len(assets) * 3)
            if project == 'orbit':
                call('insert', 'orbit/sequence', dict(code='SEQ_010', name='Arrival', description='The expedition reaches the landing site.'))
                for index, name in enumerate(('Approach', 'Landing', 'First contact')):
                    shot = call('insert', 'orbit/shot', dict(code='SH_%03d' % ((index + 1) * 10), name=name,
                        description='Arrival sequence / ' + name))
                    call('create_task', shot['__search_key__'], 'animation', description=name + ' / blocking', assigned='maya',
                        bid_start_date=str(date.today()), bid_end_date=str(date.today() + timedelta(days=7)), bid_duration=7)
                counts[project].update(shots=3, sequences=1, tasks=counts[project]['tasks'] + 3)
            for filename in PLUGINS:
                if filename in installed_plugins:
                    document = command('tactic.ui.app.PluginManagerCmd', action='load', project_code=project,
                                       identity=installed_plugins[filename])
                else:
                    archive = directory / 'plugins' / filename
                    call('upload_file', filename, Binary(archive.read_bytes()))
                    document = command('tactic.ui.app.PluginManagerCmd', action='install', project_code=project, upload_file_name=filename)
                    installed_plugins[filename] = document['identity']
                command('tactic.ui.app.PluginManagerCmd', action='activate', project_code=project,
                        identity=document['identity'], expected_revision=document['revision'], confirmation=True)
            with request_context(RequestContext(store, login, project)):
                api.auth.bind_security(login, ticket)
                from tactic_stream.server.knowledge import knowledge_request
                knowledge_request('initialize', auth)
                body = ('# Welcome to ' + ('Orbit Studio' if project == 'orbit' else 'Atlas Reference Library') + '\n\n'
                    'Open Assets in Item View, expand Survey Drone and compare its two look-development versions. '
                    'Use Task Manager to see assignments, then open Workspace Pulse for the project dashboard.\n\n'
                    'Studio Review is an installed example plugin with editable records and an approval action. '
                    'The same project, files and permissions are available in TACTIC Handler.\n\n'
                    'Maya and Leo are artists. Nora has read-only project access. '
                    'Their generated passwords are in demo-accounts.json in the server data directory. '
                    'The administrator can change them in User Management.\n\n'
                    'These are fictional projects. You can edit them freely; a clean installation starts without them.')
                knowledge_request('save', dict(auth, document=dict(title='Start here', kind='article',
                    contentMarkdown=body, contentText=body, linkedSearchKeys=[assets[0]])))
        result = dict(format=1, projects=counts, accounts=[dict(login=row['login'], role=row['role']) for row in accounts],
                      plugins=list(PLUGINS))
        descriptor = os.open(accounts_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'w', encoding='utf-8') as output:
            json.dump(accounts, output, ensure_ascii=False, indent=2)
        with marker.open('x', encoding='utf-8') as output:
            json.dump(result, output, ensure_ascii=False, indent=2)
        return result
    finally:
        api.auth.logout(ticket)
