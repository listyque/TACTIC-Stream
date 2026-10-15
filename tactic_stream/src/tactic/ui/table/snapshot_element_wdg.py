# Copyright (c) 2005 Southpaw Technology. See LICENSE.TACTIC.
"""Native snapshot version display; legacy HTML is not executed."""
from pyasm.common import Config
from tactic.ui.common import BaseTableElementWdg


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
