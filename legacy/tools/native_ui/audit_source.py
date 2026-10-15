#!/usr/bin/env python3
"""Reproducible inventory/diff against the uploaded TACTIC archive.

No code from the baseline archive is executed. No percentage of semantic
completeness is inferred from file or class counts.
"""
import argparse
import ast
import collections
import difflib
import hashlib
import json
from pathlib import Path
import re
import sys
import warnings
import zipfile

ROOT = Path(__file__).resolve().parents[2]
MOVED = {
    ('src/tactic/ui/filter/filter_data.py', 'FilterData'): 'tactic.core.filter_data.FilterData',
    ('src/tactic/ui/input/process_context_wdg.py', 'SubContextAction'): 'tactic.core.context_actions.SubContextAction',
    ('src/tactic/ui/table/work_hours_element_wdg.py', 'WorkHoursElementAction'): 'tactic.core.work_hours.WorkHoursElementAction',
    ('src/tactic/ui/tools/pipeline_wdg.py', 'ProcessInfoCmd'): 'tactic.core.process_commands.ProcessInfoCmd',
    ('src/tactic/ui/tools/pipeline_wdg.py', 'NewProcessInfoCmd'): 'tactic.core.process_commands.NewProcessInfoCmd',
    ('src/pyasm/widget/widget_config.py', 'WidgetConfig'): 'tactic.core.widget_config.WidgetConfig',
    ('src/pyasm/widget/widget_config.py', 'WidgetConfigView'): 'tactic.core.widget_config.WidgetConfigView',
    ('src/pyasm/widget/widget_config.py', 'WidgetConfigTestCmd'): 'tactic.core.config_commands.WidgetConfigTestCmd',
    ('src/pyasm/web/web_init.py', 'StatusLogTrigger'): 'tactic.core.bootstrap.StatusLogTrigger',
    ('src/pyasm/web/web_init.py', 'DisplayNameTrigger'): 'tactic.core.bootstrap.DisplayNameTrigger',
    ('src/tactic/ui/panel/edit_cmd.py', 'EditCmd'): 'tactic.core.edit_commands.EditCmd',
    ('src/tactic/ui/panel/edit_cmd.py', 'EditMultipleCmd'): 'tactic.core.edit_commands.EditMultipleCmd',
    ('src/tactic/ui/app/search_type_creator_wdg.py', 'SearchTypeCreatorCmd'): 'tactic.core.schema_commands.SearchTypeCreatorCmd',
    ('src/tactic/ui/tools/pipeline_wdg.py', 'PipelineSaveCbk'): 'tactic.core.pipeline_commands.PipelineSaveCbk',
    ('src/tactic/ui/startup/security_wdg.py', 'UserAssignCbk'): 'tactic.core.security_commands.UserAssignCbk',
}

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def excluded(path: str) -> bool:
    parts = Path(path).parts
    return '__pycache__' in parts or '.git' in parts or '.runtime' in parts or 'local_data' in parts or Path(path).suffix.lower() in {'.pyc', '.pyo'}

def dump(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--out', type=Path, default=ROOT / 'docs/native-ui')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    warnings.simplefilter('ignore', SyntaxWarning)
    with zipfile.ZipFile(args.baseline) as archive:
        prefix = archive.namelist()[0].split('/')[0] + '/'
        original = {name[len(prefix):]: archive.read(name) for name in archive.namelist()
                    if name.startswith(prefix) and not name.endswith('/')}
        comment = archive.comment.decode('ascii', errors='replace')
    baseline = {'filename': args.baseline.name, 'sha256': digest(args.baseline.read_bytes()),
                'git_commit_from_zip_comment': comment if re.fullmatch('[a-f0-9]{40}', comment) else None,
                'version': original.get('VERSION', b'').decode().strip(), 'files': len(original)}
    dump(args.out / 'baseline.json', baseline)
    current = {p.relative_to(args.root).as_posix(): p for p in args.root.rglob('*') if p.is_file() and not excluded(p.relative_to(args.root).as_posix())}
    changes, patches, errors, classes = [], [], [], []
    for name, data in original.items():
        if name.startswith(('src/tactic/ui/', 'src/pyasm/widget/', 'src/pyasm/web/')) and name.endswith('.py'):
            try:
                tree = ast.parse(data, filename=name)
            except (SyntaxError, UnicodeError) as exc:
                errors.append({'path': name, 'error': str(exc)})
                continue
            for node in tree.body:
                if not isinstance(node, ast.ClassDef):
                    continue
                target = MOVED.get((name, node.name))
                classes.append({'source': name, 'class': node.name, 'line': node.lineno,
                                'bases': [ast.unparse(b) for b in node.bases],
                                'methods': [n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))],
                                'status': 'extracted_server_class' if target else 'legacy_present_not_individually_validated',
                                'new_location': target,
                                'extracted_methods': ['_add_time_filter','_evaluate_value','alter_sobject_search','add_ops'] if (name,node.name)==('src/tactic/ui/filter/filter_wdg.py','GeneralFilterWdg') else []})
    for name, path in sorted(current.items()):
        if name.startswith('docs/native-ui/'):
            continue  # Generated report must not diff itself or its binary screenshots.
        after = path.read_bytes()
        before = original.get(name)
        if before == after:
            continue
        changes.append({'path': name, 'change': 'added' if before is None else 'modified',
                        'before_sha256': digest(before) if before is not None else None, 'after_sha256': digest(after)})
        # Source patch excludes binary data, screenshot artifacts and bundled Vue;
        # their exact bytes/hashes are in the full archive and build manifest.
        if path.suffix.lower() in {'.py','.vue','.js','.cjs','.json','.css','.html','.md','.bat','.ps1','.txt'} and 'web/vendor/' not in name:
            try:
                old_lines = (before or b'').decode('utf-8-sig').splitlines(keepends=True)
                new_lines = after.decode('utf-8-sig').splitlines(keepends=True)
            except UnicodeError:
                continue
            patches.extend(difflib.unified_diff(old_lines, new_lines,
                           fromfile='a/' + name if before is not None else '/dev/null', tofile='b/' + name))
    dump(args.out / 'changes.json', {'baseline': baseline, 'changes': changes,
                                    'note': 'Report files and compiled Vue vendor are not included in the textual patch.'})
    (args.out / 'changes.patch').write_text(''.join(patches), encoding='utf-8')
    dump(args.out / 'source-audit.json', {'baseline': baseline, 'classes': classes, 'parse_errors': errors,
                                       'note': 'Inventory only. Shared native renderers are not equivalent to complete parity for every legacy class.'})
    sys.path.insert(0, str(args.root / 'src'))
    from tactic.core.config_model import ConfigSource, ConfigModel, SidebarProjection, parse_xml, view_node
    texts = [(path.read_text(), path.name) for path in [args.root/'src/tactic/ui/config/admin-conf.xml', args.root/'src/tactic/ui/config/DEFAULT-conf.xml']]
    def loader(view, personal=False):
        return ConfigModel(view, [ConfigSource(text, v, label) for v in (view,'definition') for text,label in texts if view_node(parse_xml(text),v) is not None])
    projection = SidebarProjection(loader, lambda name: True, 'admin', 'audit')
    sections = projection.build(['admin_views'])
    dump(args.out / 'admin-targets.json', {'scope': 'File-only stock admin_views; no DB overrides, no generated Schema Views',
                'sections': sections, 'targets': list(projection.targets.values()),
                'renderer_counts': dict(collections.Counter(t['kind'] for t in projection.targets.values())),
                'warning': 'A native renderer family can still have unsupported cells, actions and settings. Not a parity percentage.'})
    print(json.dumps({'changed_original_files':sum(x['change']=='modified' for x in changes),
                      'added_code_files':sum(x['change']=='added' for x in changes),
                      'baseline_ui_classes':len(classes),'baseline_parse_errors':len(errors),
                      'stock_admin_targets':len(projection.targets)}, ensure_ascii=False))

if __name__ == '__main__':
    main()
