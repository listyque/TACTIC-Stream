"""Native values for explicit original display handlers (never column-name guesses).

TaskStatusElementWdg.handle_td -> default / task / parent's process pipeline color.
LoginTableElementWdg.get_value -> display_name, falling back to the stored login.
pyasm.widget.ColorWdg -> a color swatch; original value stays unchanged.
"""
import re
from .contracts import ApiError

LOGIN_DISPLAY = {'tactic.ui.input.LoginTableElementWdg',
                 'tactic.ui.input.process_group_select_wdg.LoginTableElementWdg',
                 'LoginTableElementWdg'}
STATUS_DISPLAY = {'tactic.ui.widget.TaskStatusElementWdg',
                  'tactic.ui.widget.misc_input_wdg.TaskStatusElementWdg',
                  'tactic.ui.table.TaskStatusElementWdg', 'TaskStatusElementWdg'}
COLOR_DISPLAY = {'pyasm.widget.ColorWdg', 'pyasm.widget.input_wdg.ColorWdg', 'ColorWdg'}


def safe_color(value):
    if not isinstance(value, str):
        return None
    text = value.strip()
    if re.fullmatch(r'#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{1}|[0-9a-fA-F]{3}|[0-9a-fA-F]{5})?', text):
        return text
    if re.fullmatch(r'(?:rgb|rgba|hsl|hsla)\([0-9.,% +\-]+\)', text, re.I):
        return text
    if text.lower() in {'transparent','red','green','blue','orange','yellow','purple','pink','gray','grey','black','white','teal'}:
        return text
    return None


class CellValueService:
    def _native_value_spec(self, spec, form=False):
        for f in spec['fields']:
            if f['handler'] in COLOR_DISPLAY and f['storage']:
                f.update(kind='text', supported=True, reason='')
                if not form:
                    f['renderer']='color'
                else:
                    from pyasm.common import Environment
                    from tactic.core.field_policy import field_access
                    from .config_backend import DATABASE_ACTIONS, DENY_EDIT_TYPES
                    attrs=f.get('config_attributes') or {}
                    _,editable=field_access(Environment.get_security(),self._project(),spec['type'],f['name'],attrs)
                    f['read_only']=(not self.allow_writes or not editable or spec['type'] in DENY_EDIT_TYPES or f['action'] not in DATABASE_ACTIONS or attrs.get('edit') in ('false',False) or f['display_options'].get('read_only') in ('true',True))
                    f['color_input']=True
        spec['diagnostics']=[{'field':f['name'],'handler':f['handler'],'reason':f['reason']} for f in spec['fields'] if f.get('reason')]
        return spec

    def _login_labels(self, values):
        from pyasm.search import Search
        codes=sorted({str(v) for v in values if v is not None and v!=''})
        if not codes:return {}
        labels={}
        for start in range(0,len(codes),200):
            batch=codes[start:start+200]
            search=Search('sthpw/login');search.add_filters('code',batch);search.set_limit(201)
            for user in search.get_sobjects():
                labels[user.get_code()]=user.get_value('display_name',no_exception=True) or user.get_code()
        return labels

    def _status_color(self,obj,name,value):
        from pyasm.biz import Task,Pipeline
        # Exact ordering in original TaskStatusElementWdg.handle_td.
        color=Task.get_default_color(str(value)) if value else None
        code=obj.get_value('pipeline_code',no_exception=True)
        if obj.get_base_search_type()=='sthpw/snapshot':code='snapshot'
        if not code:
            process=obj.get_value('process',no_exception=True)
            if process:
                parent=obj.get_parent()
                if parent:
                    parent_code=parent.get_value('pipeline_code',no_exception=True)
                    pipeline=Pipeline.get_by_code(parent_code) if parent_code else None
                    if pipeline:code=pipeline.get_process_attrs(process).get('task_pipeline')
        pipeline=Pipeline.get_by_code(code) if code else None
        if pipeline:
            process=pipeline.get_process(value)
            if process:
                color=process.get_color()
                if not color:
                    settings=pipeline.get_process_sobject(value)
                    if settings:color=settings.get_value('color',no_exception=True)
        return safe_color(color)

    def _native_value_cells(self,obj,row,spec):
        cells=row.setdefault('cells',{})
        for f in spec['fields']:
            if not f.get('storage'):continue
            name=f['name'];handler=f.get('display_handler') or f['handler']
            value=row['values'].get(name)
            if handler in LOGIN_DISPLAY:
                labels=getattr(self,'_cell_login_labels',None)
                if labels is None:labels=self._login_labels([value])
                text=labels.get(str(value),str(value)) if value else '--Select--'
                cells[name]={'kind':'login','text':text,'login':value or '', 'empty':not bool(value)}
            elif handler in STATUS_DISPLAY:
                try:
                    cells[name]={'kind':'status','text':str(value) if value else '--Select--',
                                 'color':self._status_color(obj,name,value),'empty':not bool(value)}
                except Exception as exc:
                    # Do not fabricate a color if the project's pipeline fails.
                    cells[name]={'kind':'text','text':str(value or ''),'warning':'status_color_unavailable','error_type':type(exc).__name__}
            elif handler in COLOR_DISPLAY:
                cells[name]={'kind':'color','text':str(value or ''),'color':safe_color(value)}
        return row
