from pyasm.biz import Project, ProjectSetting
from pyasm.search import Search
from tactic_stream.server.sidebar_editor import SidebarDraft, read_sidebar, save_sidebar
from tactic_stream.server.navigation import read_navigation

if Project.get_project_code() in ('admin', 'sthpw'):
    raise ValueError('Studio Review requires a business project')
setting = ProjectSetting.create('studio_review/installed', '1.0.0')
setting.set_value('code', 'STUDIO_REVIEW_INSTALLED')
setting.commit()
state = read_sidebar()
groups = [row.get_data() for row in Search('sthpw/login_group').get_sobjects()]
source = 'handler' if read_navigation()['view'] == 'tactic_handler' else 'tactic'
draft = SidebarDraft(state['documents'], groups, Project.get_project_code(), source)
if not any(entry['name'] == 'studio_review' for entry in draft.entries):
    draft._selected_row = -1
    draft.add_entry('link')
    for name, value in dict(name='studio_review', title='Studio Review', searchType='studio/review',
                            widgetType='view_panel', searchView='studio_review.table', icon='check').items():
        draft.update_selected(name, value)
    save_sidebar(draft, state['revision'])
