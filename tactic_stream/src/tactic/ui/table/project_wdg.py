"""Original project database/version indicators as typed cell data."""
from pyasm.common import Environment
from tactic.ui.common import BaseTableElementWdg


class ProjectWdg(BaseTableElementWdg):
    def preprocess(self):
        self.version = Environment.get_release_version()

    def get_cell_value(self):
        project = self.get_current_sobject()
        exists = project.database_exists()
        version = project.get_value('last_version_update')
        current = str(version or '') >= str(self.version)
        return {'text': 'Exists: %s\nVersion: %s' % (exists, version or ''),
                'entries': [{'title': 'Exists', 'value': 'Yes' if exists else 'No', 'translate': True,
                             'color': 'green' if exists else 'error'},
                            {'title': 'Version', 'value': str(version or ''), 'translateTitle': True,
                             'color': 'green' if current else 'error'}]}


class ProjectTemplateUpdateWdg(BaseTableElementWdg):
    def get_cell_value(self):
        return dict(text='', projectCode=self.get_current_sobject().get_code(), actions=[
            dict(name='template', label='Update Template', icon=self.get_option('icon') or 'archive')])
