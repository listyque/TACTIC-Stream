"""Opt-in real Codex/MCP acceptance on owned data; evidence stays outside Git."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
HANDLER = ROOT.parent.parent / 'TH'
OUT = None
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tests'), str(ROOT)]
os.environ.update(PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(ROOT / 'src'),
                  TACTIC_CONFIG_PATH='', TACTIC_TMP_CONFIG_PATH='')
from test_transport import Transport
from tactic_stream.server.api import Api
from tactic_stream.admin_agent import StreamConnection


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')


def report(message):
    print(message, flush=True)


def external(name, project, prompt, flags):
    args = ['-B', '-X', 'utf8', '-m', 'tactic_stream.admin_agent', '--server', Transport.url,
            '--project', project, '--stream-root', ROOT.as_posix(), '--handler-root', HANDLER.as_posix(), *flags]
    config = {'mcp_servers.tactic.command': Path(sys.executable).as_posix(),
              'mcp_servers.tactic.args': args, 'mcp_servers.tactic.cwd': ROOT.as_posix(),
              'mcp_servers.tactic.env_vars': ['TACTIC_AGENT_TICKET', 'PYTHONPATH', 'PYTHONUTF8'],
              'mcp_servers.tactic.required': True, 'mcp_servers.tactic.startup_timeout_sec': 30,
              'mcp_servers.tactic.tool_timeout_sec': 60,
              'mcp_servers.tactic.default_tools_approval_mode': 'approve', 'web_search': 'disabled',
              'project_doc_max_bytes': 0}
    command = [shutil.which('codex.cmd'), '-a', 'never', 'exec', '--ignore-user-config', '--ephemeral',
               '--skip-git-repo-check', '--sandbox', 'read-only', '--disable', 'shell_tool',
               '--disable', 'apps', '--disable', 'multi_agent', '--json', '-o', str(OUT / (name + '-answer.txt'))]
    for key, value in config.items():
        command += ['-c', key + '=' + json.dumps(value)]
    instruction = ('You are an external TACTIC administrator agent, not a source-code developer. '
                   'Use only tactic MCP tools. Discover capabilities, read ts.start and ts.model through '
                   'reference_read, and retrieve task-specific references as needed: ts.projects, ts.pages, '
                   'th.automation. After two similar failures, stop guessing and reread the complete task '
                   'recipe. Report an unavailable contract instead of inventing it. Do not read filesystem '
                   'or source, use a shell, use other services, or ask for credentials. The host supplies '
                   'the session privately. Follow native revision and idempotency contracts. Never claim '
                   'an execution or GUI test you cannot perform. The user has authorized the specified '
                   'writes on this disposable test server. Read back actual state. Record operation UUIDs '
                   'and result identities in your final concise report.\n\n' + prompt)
    (OUT / (name + '-request.txt')).write_text(instruction, encoding='utf-8')
    with tempfile.TemporaryDirectory(prefix='tactic-external-host-') as workspace:
        command += ['--cd', workspace, '-']
        with (OUT / (name + '-events.jsonl')).open('w', encoding='utf-8') as stdout, \
                (OUT / (name + '-stderr.txt')).open('w', encoding='utf-8') as stderr:
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=stdout, stderr=stderr,
                                       text=True, encoding='utf-8', env=dict(os.environ, TACTIC_AGENT_TICKET=ticket))
            try:
                process.communicate(instruction, timeout=900)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(10)
            if process.returncode:
                raise RuntimeError(f'External host failed in {name}; inspect private event/stderr evidence')
    events = [json.loads(line) for line in (OUT / (name + '-events.jsonl')).read_text(encoding='utf-8').splitlines()]
    assert events[-1]['type'] == 'turn.completed', events[-1]
    calls = [e['item'] for e in events if e['type'] == 'item.completed' and e['item']['type'] == 'mcp_tool_call']
    assert calls, f'No actual MCP calls in {name}'
    assert all(c['server'] == 'tactic' for c in calls)
    assert not any(e.get('item', {}).get('type') in ('command_execution', 'file_change') for e in events)
    report(f'{name}: real model completed, {len(calls)} MCP calls; {events[-1].get("usage", {})}')
    return calls


def rows(project, logical, **kwargs):
    value = Api(Transport.store).dispatch('query', (dict(ticket=ticket, project=project), logical), kwargs)
    return ast.literal_eval(value) if isinstance(value, str) else value


def insert(project, logical, values):
    return Api(Transport.store).dispatch('insert', (dict(ticket=ticket, project=project), logical, values))


def check_replay(calls, tool, count=1):
    operations = {}
    for call in calls:
        if call['tool'] == tool and call['status'] == 'completed':
            operations.setdefault(call['arguments']['operation_id'], []).append(call)
    repeated = [items for items in operations.values() if len(items) >= 2]
    assert len(repeated) == count, f'{tool}: missing actual identical retry'
    for items in repeated:
        assert all(item['arguments'] == items[0]['arguments'] for item in items)
        assert all(item['result']['structured_content'] == items[0]['result']['structured_content'] for item in items)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--handler-root', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    HANDLER = args.handler_root.resolve()
    OUT = args.output_dir.resolve()
    if any(repo == OUT or repo in OUT.parents for repo in (ROOT.parent, HANDLER)):
        parser.error('Private acceptance evidence must stay outside both repositories')
    OUT.mkdir(parents=True, exist_ok=False)
    if not shutil.which('codex.cmd') or not shutil.which('node'):
        parser.error('The installed Codex CLI and browser test runtime are required')
    Transport.setUpClass()
    try:
        ticket = Api(Transport.store).get_ticket('admin', 'private-test-password')
        report('Owned test server ready; normal 8081 server is untouched')
        external('01-project', 'one',
            'Create a new project agentfilm, title Night City. It needs sequences (sequence), shots (shot) '
            'and reusable assets (asset). Shots have an integer frames field, belong to one sequence, and '
            'can use several assets; assets can be reused in multiple shots. Build a native shot workflow '
            'layout -> animation -> compositing with statuses Waiting, Working, Approved. Publish naming '
            'must put shot files under project/shots/sequence-code/shot-code, named shot-code_v001.ext '
            '(native version padding, not a fixed 001). Create ordinary editable table navigation for '
            'the entities. Preview, create, inspect the actual configuration, export it as a reusable '
            'native template, then install it as new project agentfilmcopy titled Night City Copy. '
            'Preserve receipts. Do not populate operational records; the test host will do that next.',
            ['--allow-project-create'])
        connection = StreamConnection(Transport.url, 'one', ticket)
        state = connection.project_operation('read', target='agentfilm')
        copied = connection.project_operation('read', target='agentfilmcopy')
        save('01-native-project.json', state)
        save('01-native-copy.json', copied)
        assert state['registered'] and state['database_exists'] and copied['registered'] and copied['database_exists']
        assert set(state['entities']) == {'agentfilm/' + name for name in ('sequence', 'shot', 'asset', 'shot_asset')}
        assert 'frames' in state['columns']['agentfilm/shot']
        assert 'sequence_code' in state['columns']['agentfilm/shot']
        assert 'agentfilmcopy/shot' in copied['pipelines']
        from xml.etree import ElementTree as ET
        edges = [node.attrib for xml in state['schema'] for node in ET.fromstring(xml).findall('connect')]
        for child, parent, column in [('shot', 'sequence', 'sequence_code'),
                                      ('shot_asset', 'shot', 'shot_code'), ('shot_asset', 'asset', 'asset_code')]:
            assert any(edge.get('from') == 'agentfilm/' + child and edge.get('to') == 'agentfilm/' + parent
                       and edge.get('from_col') == column and edge.get('to_col') == 'code' for edge in edges)
        assert len(state['naming']) == len(copied['naming'])
        for field in ('layout', 'animation', 'compositing', 'Waiting', 'Working', 'Approved'):
            assert field in json.dumps(copied['workflows']), field
        report('Project and template installation read back through native API')
        insert('agentfilm', 'agentfilm/sequence', dict(code='SQ010', name='Opening'))
        for code, frames in [('SH010', 120), ('SH020', 80), ('SH030', 240)]:
            insert('agentfilm', 'agentfilm/shot', dict(code=code, name='Night flight ' + code,
                sequence_code='SQ010', frames=frames, pipeline_code='agentfilm/shot'))
        insert('agentfilm', 'agentfilm/asset', dict(code='ROBOT', name='Hero robot'))
        page_calls = external('02-naming-page', 'agentfilm',
            'On the existing shots, finish two requests. First update the publish naming rule: folder '
            'project-code/shots/parent-sequence-code/shot-code and filename shot-code_publish_v001.ext '
            '(real native version and original extension). Preview SH010 with input.exr, publish context, '
            'versions 1 and 2, save with revision check, repeat the exact same save with the same operation '
            'UUID to prove replay is safe, and read it back. Second create a page named long_shots titled '
            'Long shots, showing only shots with frames greater than 100, ordered by code ascending. '
            'Its table must have preview, code, name and frames columns; use a native workspace layout '
            'with results and the object inspector, and add native navigation. Preview matching rows, '
            'save and read back. Do not use scripts or custom widgets for these operations.',
            ['--allow-naming-save', '--allow-page-save'])
        check_replay(page_calls, 'ts_naming_save')
        save('02-native-naming.json', rows('agentfilm', 'config/naming'))
        configurations = rows('agentfilm', 'config/widget_config')
        save('02-native-pages.json', configurations)
        page_saves = [call for call in page_calls if call['tool'] == 'ts_page_save' and call['status'] == 'completed']
        assert len(page_saves) == 1, 'Agent did not save the requested page'
        saved_page = page_saves[0]['result']['structured_content']
        assert saved_page['workspace'] is not None
        page_fixture = OUT / 'page-fixture.json'
        page_fixture.write_text(json.dumps(dict(rows=configurations, saved=saved_page, project='agentfilm',
            title='Long shots', filter_column='frames', filter_value=100)), encoding='utf-8')
        result = subprocess.run([sys.executable, '-B', '-X', 'utf8', str(ROOT/'tests/scripts/agent_page_handler.py'),
            '--handler-root', str(HANDLER), '--fixture', str(page_fixture)], capture_output=True, text=True, encoding='utf-8', timeout=40)
        assert result.returncode == 0, result.stdout + result.stderr
        (OUT / '02-handler-page.txt').write_text(result.stdout + result.stderr, encoding='utf-8')
        result = subprocess.run([shutil.which('node'), 'tests/agent_pages.mjs', Transport.url, str(OUT), str(page_fixture)],
            cwd=ROOT/'frontend', env=dict(os.environ, PLAYWRIGHT_BROWSERS_PATH=str(ROOT/'.browser-cache')),
            capture_output=True, text=True, encoding='utf-8', timeout=90)
        (OUT / '02-browser-page.txt').write_text(result.stdout + result.stderr, encoding='utf-8')
        assert result.returncode == 0, result.stdout + result.stderr
        from tactic_client_lib import TacticServerStub
        client = TacticServerStub(setup=False, protocol='xmlrpc')
        client.set_server(Transport.url)
        client.set_project('agentfilm')
        client.set_ticket(ticket)
        insert('agentfilmcopy', 'agentfilm/sequence', dict(code='SQ010', name='Copy opening'))
        insert('agentfilmcopy', 'agentfilm/shot', dict(code='SH010', name='Copy flight', sequence_code='SQ010', pipeline_code='agentfilmcopy/shot'))
        client.set_project('agentfilmcopy')
        copy_source = Path(Transport.temp.name) / 'copy.exr'
        copy_source.write_bytes(b'owned template checkin')
        copy_snapshot = client.simple_checkin('agentfilm/shot?project=agentfilmcopy&code=SH010', 'publish', str(copy_source), mode='upload', create_icon=False)
        copy_files = rows('agentfilmcopy', 'sthpw/file', filters=[['snapshot_code', copy_snapshot['code']]])
        assert [row['file_name'] for row in copy_files] == ['SH010_v001.exr'], copy_files
        assert copy_files[0]['relative_dir'] == 'agentfilmcopy/shots/SQ010/SH010', copy_files
        save('02-template-checkin.json', dict(snapshot=copy_snapshot, files=copy_files))
        client.set_project('agentfilm')
        source = Path(Transport.temp.name) / 'input.exr'
        source.write_bytes(b'owned external agent checkin')
        snapshots = [client.simple_checkin('agentfilm/shot?project=agentfilm&code=SH010', 'publish',
            str(source), mode='upload', create_icon=False) for _ in range(2)]
        files = rows('agentfilm', 'sthpw/file', filters=[['project_code', 'agentfilm']])
        save('02-native-checkin.json', dict(snapshots=snapshots, files=files))
        assert {f['file_name'] for f in files} >= {'SH010_publish_v001.exr', 'SH010_publish_v002.exr'}, files
        report('Real SDK check-in produced both naming versions')
        validator = Path(Transport.temp.name) / 'validator.py'
        validator.write_text('import pathlib, sys\nraise SystemExit(7 if pathlib.Path(sys.argv[1]).name == "blocked.bin" else 0)\n', encoding='utf-8')
        marker = Path(Transport.temp.name) / 'after.txt'
        after = Path(Transport.temp.name) / 'after.py'
        after.write_text('import pathlib, sys\npathlib.Path(sys.argv[1]).write_text(sys.argv[2], encoding="utf-8")\n', encoding='utf-8')
        draft_calls = external('03-automation-drafts', 'agentfilm',
            'Prepare and save inactive drafts for three TH actions; DO NOT activate. Before each shot '
            'check-in, validate every file with this program argv: ' + json.dumps([str(Path(sys.executable)), str(validator), '{file}']) +
            '. Nonzero exit blocks publication. After successful shot check-in, run argv: ' +
            json.dumps([str(Path(sys.executable)), str(after), str(marker), '{result_search_key}']) +
            '. Use the existing native program helper with timeouts, not shell execution. Third: on '
            'the shots table shelf, add a button Selected shots that opens a native modal Frame window '
            'listing the selected shot keys, using the shipped Frame showcase helper and captured '
            'TACTIC_SCRIPT_KWARGS selection. Inspect the real entry key rather than guessing. Read the '
            'TH automation and Frame script references. Save the three drafts and report their IDs, '
            'exact source, and proposed bindings for host review. Do not claim execution or activate.',
            ['--allow-automation-draft'])
        drafts = []
        for call in draft_calls:
            if call['tool'] == 'th_automation_save_draft' and call['status'] == 'completed':
                value = call['result']['structured_content']
                drafts.append(dict(code=value['draft_id'], document=json.dumps(value['document'])))
        assert len(drafts) == 3, drafts
        save('03-drafts-for-review.json', drafts)
        review_hash = hashlib.sha256((OUT/'03-drafts-for-review.json').read_bytes()).hexdigest()
        report('REVIEW REQUIRED: inspect exact source/bindings in 03-drafts-for-review.json; put this SHA-256 in review-approved.txt: ' + review_hash)
        deadline = time.monotonic() + 1800
        while not ((OUT / 'review-approved.txt').is_file() and (OUT/'review-approved.txt').read_text(encoding='utf-8').strip() == review_hash):
            if time.monotonic() > deadline:
                raise TimeoutError('Exact source review was not completed')
            time.sleep(1)
        activation_calls = external('04-automation-activate', 'agentfilm',
            'The host has reviewed and authorized exactly these three inactive drafts on this owned '
            'test project: ' + ', '.join(row['code'] for row in drafts) +
            '. Read their exact source and revisions, then activate each with a fresh dependency revision '
            'and its own operation UUID. Repeat each identical activation once to prove safe replay, '
            'then read actual hooks and shelves. Do not edit source or create additional actions. '
            'The independent host will execute real native TH checks; do not claim those yourself.',
            ['--allow-automation-activate'])
        check_replay(activation_calls, 'th_automation_activate', count=3)
        state = StreamConnection(Transport.url, 'agentfilm', ticket).command('automation', 'read')
        save('04-native-automation.json', state)
        # The independent native probe consumes the model-authored saved scripts and real configuration.
        shelf = next(row for row in drafts if json.loads(row['document'])['kind'] == 'shelf')
        button = next((preset, button) for preset in state['shelves'] for button in preset['configuration']['buttons']
                      if button['id'] == shelf['code'])
        fixture = Path(Transport.temp.name) / 'handler-automation.json'
        from urllib.parse import urlsplit
        fixture.write_text(json.dumps(dict(ticket=ticket, server=urlsplit(Transport.url).netloc,
            project='agentfilm', search_key='agentfilm/shot?project=agentfilm&code=SH010',
            entry_key=json.loads(shelf['document'])['entry_key'], marker=str(marker),
            shelf_view=button[0]['view'], button_id=shelf['code'], screenshot=str(OUT/'native-modal.png'))), encoding='utf-8')
        probe = ROOT / 'tests/scripts/agent_automation_handler.py'
        result = subprocess.run([sys.executable, '-B', '-X', 'utf8', str(probe), '--handler-root', str(HANDLER),
            '--fixture', str(fixture)], cwd=HANDLER, env=dict(os.environ, PYTHONPATH=str(HANDLER)),
            capture_output=True, text=True, encoding='utf-8', timeout=90)
        (OUT / '05-native-handler.txt').write_text(result.stdout + result.stderr, encoding='utf-8')
        assert result.returncode == 0, result.stdout + result.stderr
        report('All real external-agent scenarios and independent native Handler checks completed')
    finally:
        Transport.tearDownClass()
        report('Owned test server stopped and private runtime data removed')
