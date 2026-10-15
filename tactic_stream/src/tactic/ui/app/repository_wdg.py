# Copyright (c) 2010, Southpaw Technology. See LICENSE.TACTIC.
"""RepositoryEditorController.check_paths through native Config/Environment/FileUndo."""
import os
import re
from pathlib import Path
import tempfile

from pyasm.command import Command
from pyasm.common import Config, Environment, TacticException
from pyasm.search import FileUndo
from pyasm.security.security import _require_admin


class RepositoryPathsCmd(Command):
    def execute(self):
        _require_admin()
        action = self.kwargs.get('action', 'load')
        if action not in ('load', 'check'):
            raise TacticException('Choose load or check for repository paths')
        roots = Environment.get_asset_dirs()
        roots.setdefault('default', Environment.get_asset_dir())
        if 'paths' in self.kwargs:
            paths = self.kwargs['paths']
            if action != 'check' or not isinstance(paths, dict) or not 1 <= len(paths) <= 100 or any(not isinstance(alias, str) or not re.fullmatch(r'[A-Za-z0-9_.-]+', alias) or not isinstance(path, str) or len(path) > 4096 or any(ord(char) < 32 for char in path) for alias, path in paths.items()):
                raise TacticException('Choose valid repository paths')
            roots = {alias:Environment._directory(path) if path.strip() else '' for alias, path in paths.items()}
        display = Config.get_dict_value('checkin', 'repository_display')
        rows = []
        for alias, path in roots.items():
            presentation = display.get(alias, {})
            presentation = presentation if isinstance(presentation, dict) else {}
            row = dict(alias=alias, path=path, title=presentation.get('title') or alias,
                       color=presentation.get('color') or '', is_default=alias == 'default', status='unchecked')
            if action == 'check':
                try:
                    if not path:
                        raise OSError('Repository path is empty')
                    if Path(path).exists() and not Path(path).is_dir():
                        raise OSError('Repository path is not a directory')
                    FileUndo.mkdir(path)
                    if not Path(path).is_dir():
                        raise OSError('Repository path is not a directory')
                    if not os.access(path, os.R_OK):
                        raise PermissionError('Repository folder is not readable')
                    # Windows os.access alone does not verify the service account's write ACL.
                    with tempfile.TemporaryFile(dir=path) as probe:
                        probe.write(b''); probe.flush()
                    row['status'] = 'available'
                except OSError:
                    row['status'] = 'inaccessible'
            rows.append(row)
        return dict(repositories=rows, platform='Windows' if os.name == 'nt' else 'Linux')
