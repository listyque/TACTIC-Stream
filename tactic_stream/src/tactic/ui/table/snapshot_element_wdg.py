# Copyright (c) 2005 Southpaw Technology. See LICENSE.TACTIC.
"""Native snapshot version display; legacy HTML is not executed."""
from pyasm.common import Config
from tactic.ui.common import BaseTableElementWdg
from pyasm.biz import File, Snapshot
from pyasm.search import SearchException
from os.path import basename


class SnapshotVersionElementWdg(BaseTableElementWdg):
    def get_cell_value(self):
        version = self.get_value()
        if version in ('', None):
            text = 'No version'
        elif version == -1:
            text = 'Latest'
        elif version == 0:
            text = 'Current'
        else:
            padding = int(Config.get_value('checkin', 'version_padding') or 3)
            text = '%s%0*d' % (self.get_name()[0], padding, version)
        return {'text': text, 'label': text if version in ('', None, -1, 0) else ''}


class SnapshotLockedElementWdg(BaseTableElementWdg):
    """Original lock lookup, batched by parent and snapshot context."""

    def preprocess(self):
        self.locks = {}
        for snapshot in self.sobjects:
            key = self.get_key(snapshot)
            if key in self.locks:
                continue
            try:
                self.locks[key] = Snapshot.is_locked(snapshot.get_parent(), snapshot.get_value('context'))
            except SearchException:
                self.locks[key] = False

    def get_key(self, snapshot):
        return (snapshot.get_value('search_type'), snapshot.get_value('search_id'), snapshot.get_value('context'))

    def get_cell_value(self):
        locked = bool(self.locks.get(self.get_key(self.get_current_sobject())))
        return {'text': 'Locked' if locked else '', 'checked': locked}


class SnapshotFileElementWdg(BaseTableElementWdg):
    def get_cell_value(self):
        snapshot = self.get_current_sobject()
        if not snapshot or snapshot.is_insert():
            return {'text': '', 'href': ''}
        if isinstance(snapshot, File):
            path = snapshot.get_web_path()
            filename = snapshot.get_file_name()
            if snapshot.get_file_range():
                filename = '%s (%s)' % (filename, snapshot.get_file_range())
            return {'text': filename, 'href': path}
        path = snapshot.get_web_path_by_type()
        filename = basename(path)
        if snapshot.get_value('snapshot_type') == 'sequence':
            filename = '%s (%s)' % (filename, snapshot.get_file_range().get_display())
        return {'text': filename, 'href': path}
