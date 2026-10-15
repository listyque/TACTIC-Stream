"""Refresh the static API inventory; this does not claim runtime parity."""
import ast
import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
HANDLER = ROOT.parent.parent / 'th_codex'
OUT = ROOT / 'src/tactic_stream/compatibility'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contracts-output', type=Path, help='Write source-level UnsupportedContract guards; not coverage')
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT / 'src'))
    from tactic_stream.server.api import SUPPORTED_METHODS
    path = OUT / 'api_manifest.json'
    manifest = json.loads(path.read_text(encoding='utf-8'))
    calls = {}
    for source in (HANDLER / 'thlib').rglob('*.py'):
        if 'side' in source.relative_to(HANDLER).parts:
            continue
        try:
            tree = ast.parse(source.read_text(encoding='utf-8-sig'))
        except (SyntaxError, UnicodeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in manifest['methods']:
                calls.setdefault(node.func.attr, []).append({
                    'file': source.relative_to(HANDLER).as_posix(), 'line': node.lineno,
                    'receiver': ast.unparse(node.func.value),
                    'positional_arguments': len(node.args), 'keywords': [item.arg for item in node.keywords]})
    stub_path = HANDLER / 'thlib/side/client/tactic_client_lib/tactic_server_stub.py'
    stub = ast.parse(stub_path.read_text(encoding='utf-8-sig'))
    owner = next(node for node in stub.body if isinstance(node, ast.ClassDef) and node.name == 'TacticServerStub')
    clients = {}
    for method in owner.body:
        if isinstance(method, ast.FunctionDef):
            rpc = sorted({node.func.attr for node in ast.walk(method) if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute) and ast.unparse(node.func.value) == 'self.server'})
            if rpc:
                clients[method.name] = rpc
    manifest['handler_call_candidates'] = calls
    manifest['handler_xmlrpc_call_sites'] = {name: matching for name, candidates in calls.items()
        if name in clients and (matching := [call for call in candidates
            if call['receiver'] in ('server', 'api') or call['receiver'].startswith('server_start(')])}
    manifest['handler_client_rpc_methods'] = clients
    manifest['handler_source_sha256'] = hashlib.sha256((HANDLER / 'thlib/tactic_query.py').read_bytes()).hexdigest()
    reasons = {'set_palette': 'Native request-local Palette stack restored; it is not a browser appearance setting.', 'get_widget': 'Native HTML rendering retained for migrated Widget classes. Administrator access required. Full old HTML shell excluded by user on 2026-10-11; missing widget classes and Help library fail explicitly.', 'get_column_widgets': 'Native nested HTML cells retained for migrated column widgets, including the original first insertion-row and single-key behavior. Full interactive TableLayout shell and grouped/hierarchical HTML excluded by user on 2026-10-11.', 'set_application_state': 'Native top_layout XML/WidgetSettings persistence restored. Nested options are retained; this does not change browser workspace layouts.', 'execute_js_script': 'Original JsCmd/custom_script lookup and JS client API restored on synchronous QuickJS-NG, replacing obsolete PyV8. Administrator-only; API rights, transactions and rollback retained. Browser/DCC/Python object interoperability and asynchronous execution are excluded.'}
    reasons.update({
        'insert': 'Native SObject writes and dictionary info propagation to ApiClientCmd restored; info is command metadata, not stored object fields. Type/column/parent policy and domain write limits remain.',
        'update': 'Native single/list writes and dictionary info propagation restored; metadata and column permissions remain checked.',
        'execute_cmd': 'Native class/key lookup, bound kwargs, can_run and direct execution restored. Keys belong to current user/ticket; resolved class policy applies. use_transaction=False skips nested hooks, not outer API rollback.',
        'eval': 'Native expressions include COLOR/GRADIENT/PALETTE. Gradient offsets are data literals, not arbitrary Python. Unsupported remote/domain relations and raw SQL forms remain explicit failures.',
        'add_config_element': 'Native XML display/action/attributes and view_as_attr restored, including named attribute views without @. Persisted views reload through WidgetDbConfig.',
        'delete_sobject': 'Native dependency deletion and snapshot/file rollback include level-scoped versionless aliases. Remaining protected domain dependencies still fail explicitly; direct SQL Delete does not replace business deletion.'})
    for name, record in manifest['methods'].items():
        if record['status'] != 'excluded':
            record['status'] = 'partial' if name in SUPPORTED_METHODS else 'not_implemented'
        if name in reasons:
            record['reason'] = reasons[name]
    assert set(manifest['methods']) >= SUPPORTED_METHODS
    assert len(manifest['methods']) == 129
    assert not manifest['full_api_parity_verified']
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if args.contracts_output:
        guards = []
        for source in sorted((ROOT / 'src').rglob('*.py')):
            content = source.read_text(encoding='utf-8-sig')
            if 'UnsupportedContract' not in content:
                continue
            tree = ast.parse(content)
            parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call)
                        and isinstance(node.exc.func, ast.Name) and node.exc.func.id == 'UnsupportedContract'):
                    continue
                owners, parent = [], parents.get(node)
                while parent:
                    if isinstance(parent, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                        owners.append(parent.name)
                    parent = parents.get(parent)
                guards.append(dict(file=source.relative_to(ROOT).as_posix(), line=node.lineno,
                    function='.'.join(reversed(owners)), message=ast.unparse(node.exc.args[0]) if node.exc.args else ''))
        assert guards and all(item['file'].startswith('src/') and item['line'] > 0 for item in guards)
        args.contracts_output.parent.mkdir(parents=True, exist_ok=True)
        args.contracts_output.write_text(json.dumps({
            'limits': 'Static guards, including security boundaries and exclusions. Not a list of missing features or runtime coverage.',
            'guards': guards}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'exposed': len(manifest['methods']), 'available': len(SUPPORTED_METHODS),
        'scopes_and_limits': reasons, 'excluded': [name for name, record in manifest['methods'].items() if record['status'] == 'excluded'],
        'current_handler_rpc_methods': len(manifest['handler_xmlrpc_call_sites'])}, indent=2))


if __name__ == '__main__':
    main()
