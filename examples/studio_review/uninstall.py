from pyasm.biz import Project, ProjectSetting
import json
from pyasm.search import Search
from tactic_stream.server.sidebar_editor import SidebarDraft, read_sidebar, save_sidebar
from tactic_stream.server.navigation import read_navigation

selected=ProjectSetting.get_value_by_key('appearance/plugin_theme')
if selected.startswith('{'):
    try:
        selected=json.loads(selected).get('view')
    except ValueError:
        selected=''
if selected == 'studio_review.theme':
    ProjectSetting.create('appearance/plugin_theme', '')
state = read_sidebar()
groups = [row.get_data() for row in Search('sthpw/login_group').get_sobjects()]
source = 'handler' if read_navigation()['view'] == 'tactic_handler' else 'tactic'
draft = SidebarDraft(state['documents'], groups, Project.get_project_code(), source)
for root in draft._documents.values():
    for parent in root.iter():
        for child in list(parent):
            if child.tag == 'element' and child.get('name') == 'studio_review':
                parent.remove(child)
draft._rebuild_entries()
save_sidebar(draft, state['revision'])
