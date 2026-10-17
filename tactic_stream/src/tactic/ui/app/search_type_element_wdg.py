"""Check a registered table through native project/SQL metadata without creation."""
from pyasm.biz import Project
from pyasm.search import DbContainer
from tactic.ui.common import BaseTableElementWdg


class SearchTypeHasTableElementWdg(BaseTableElementWdg):
    def get_cell_value(self):
        search_type = self.get_current_sobject()
        database = search_type.get_value('database')
        project = Project.get() if database == '{project}' else Project.get_by_code(database)
        if not project:
            return {'text': 'Project does not exist', 'label': 'Project does not exist', 'good': False}
        table = search_type.get_table()
        if not table:
            return {'text': '', 'good': None}
        exists = project.database_exists()
        found = exists and DbContainer.get(project.get_project_db_resource()).table_exists(table)
        return {'text': 'Exists' if found else 'Does not exist', 'label': 'Exists' if found else 'Does not exist', 'good': bool(found)}
