"""Refresh the two native Handler algorithms used by browser preparation (EPL-1.0)."""
import ast
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HANDLER = Path(os.environ.get('TACTIC_HANDLER_ROOT') or (ROOT.parents[1] / 'TH')) / 'thlib' 

# Native range metadata, calculated from present frames rather than enumerating gaps.
FRAME_RANGES = '''    def get_sequence_frameranges(self, padding=False):
        if not self._sequence_frames:
            return None
        tiled = self.get_type() in ('layer_uv_sequence', 'layer_udim_sequence', 'uv_sequence', 'udim_sequence')
        groups = self._sequence_frames if tiled else [('', self._sequence_frames)]
        output = collections.defaultdict(list)
        self._sequence_start = collections.defaultdict(list) if tiled else None
        self._sequence_end = collections.defaultdict(list) if tiled else None
        self._sequence_length = collections.defaultdict(list) if tiled else None
        for tile, frames in groups:
            present = sorted(set(frames))
            start = end = present[0]
            intervals = []
            for frame in present[1:]:
                if frame == end + 1:
                    end = frame
                else:
                    intervals.append((start, end)); start = end = frame
            intervals.append((start, end))
            render = self.get_frame_with_padding if padding else str
            output[tile] = [render(start) if start == end else render(start) + '-' + render(end) for start, end in intervals]
            if tiled:
                self._sequence_start[tile].append(present[0])
                self._sequence_end[tile].append(present[-1])
                self._sequence_length[tile].append(len(frames))
            else:
                self._sequence_start, self._sequence_end, self._sequence_length = present[0], present[-1], len(frames)
        return list(output.items()) if tiled else output['']
'''


def extract(filename, names):
    source = (HANDLER / filename).read_text(encoding='utf8')
    return '\n\n'.join(ast.get_source_segment(source, node) for node in ast.parse(source).body
                         if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names)


if __name__ == '__main__':
    tree = ast.parse((HANDLER / 'ui/matching_templates.py').read_text(encoding='utf8'))
    defaults = ast.literal_eval(next(node.value for node in tree.body if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'DEFAULT_TEMPLATES' for target in node.targets)))
    import json
    (ROOT / 'frontend/src/features/checkin/matchingDefaults.js').write_text(
        '// Handler MatchingTemplatesController.DEFAULT_TEMPLATES (EPL-1.0).\nexport const matchingDefaults = ' +
        json.dumps([dict(enabled=enabled, pattern=pattern, process='', context='', locked=pattern in ('$FILENAME', '$FILENAME.$EXT')) for enabled, pattern in defaults], indent=2) + '\n', encoding='utf8')
    functions = extract('global_functions.py', {'natural_sort_key', 'FileObject', 'MatchTemplate'})
    # Desktop launch actions have no server counterpart.
    tree = ast.parse(functions)
    lines = functions.splitlines(keepends=True)
    excluded = [node for cls in tree.body if isinstance(cls, ast.ClassDef)
                for node in cls.body if isinstance(node, ast.FunctionDef) and node.name in ('open_file', 'open_folder', 'get_sequence_missing_frames', 'get_sequence_frameranges')]
    for node in sorted(excluded, key=lambda item: item.lineno, reverse=True):
        lines[node.lineno - 1:node.end_lineno] = [FRAME_RANGES] if node.name == 'get_sequence_frameranges' else []
    header = '''"""Handler global_functions.py: native FileObject/MatchTemplate (EPL-1.0).

Desktop launch actions and missing-frame enumeration are excluded. Frame ranges
retain native metadata without allocating gaps. Path/size helpers are platform functions.
"""
import collections
import os
import re

def form_path(path, tp=None):
    return path.replace('\\\\', '/')

def extract_filename(path, no_ext=False):
    name = path.replace('\\\\', '/').rsplit('/', 1)[-1]
    return os.path.splitext(name)[0] if no_ext else name

def extract_dirname(path):
    return path.replace('\\\\', '/').rsplit('/', 1)[0] if '/' in path.replace('\\\\', '/') else ''

def extract_extension(path):
    extension = os.path.splitext(path)[1].lstrip('.')
    return extension, extension.upper(), 'file', 'main'

def get_st_size(path):
    return os.path.getsize(path)

'''
    (ROOT / 'src/tactic_stream/server/file_matching.py').write_text(header + ''.join(lines) + '\n', encoding='utf8')
    functions = extract('tactic_query.py', {'get_virtual_snapshot_extended', 'create_snapshot_extended'})
    functions = functions.replace('def get_virtual_snapshot_extended(search_key,', 'def get_virtual_snapshot_extended(server, search_key,')
    functions = functions.replace('def create_snapshot_extended(search_key,', 'def create_snapshot_extended(server, search_key,')
    functions = re.sub(r'^(def (?:get_virtual_snapshot_extended|create_snapshot_extended)\([^\n]+)\):', r'\1, process=None):', functions, flags=re.M)
    functions = functions.replace('snapshot_type=snapshot_type,', 'snapshot_type=snapshot_type, process=process,')
    (ROOT / 'src/tactic_stream/server/checkin_query.py').write_text(
        '"""Handler tactic_query.py extended naming/check-in procedures (EPL-1.0).\n\nThe request-bound local SDK is passed explicitly instead of the Mako global.\n"""\n\n' + functions + '\n', encoding='utf8')
