"""Original TACTIC inputs, with headless preparation instead of HTML."""
from .pipeline_input_wdg import PipelineInputWdg
from .process_context_wdg import ProcessInputWdg, ReviewProcessInputWdg, SubContextInputWdg, SubContextAction
from .search_type_input_wdg import SearchTypeInputWdg, SearchTypeWithPipelineInputWdg
from .process_group_select_wdg import ProcessGroupSelectWdg, LoginTableElementWdg
from .task_input_wdg import TaskSObjectInputWdg
from .project_user_select_wdg import ProjectSelectWdg, UserSelectWdg
from .color_input_wdg import ColorInputWdg
from .text_input_wdg import TextInputWdg

__all__ = ['PipelineInputWdg', 'ProcessInputWdg', 'ReviewProcessInputWdg',
           'SubContextInputWdg', 'SubContextAction', 'SearchTypeInputWdg', 'SearchTypeWithPipelineInputWdg', 'ProcessGroupSelectWdg', 'TaskSObjectInputWdg', 'ProjectSelectWdg', 'UserSelectWdg', 'ColorInputWdg']
__all__.append('LoginTableElementWdg')
__all__.append('TextInputWdg')
