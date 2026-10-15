"""Same workflow input business logic and form commands in both kernels."""
from unittest.mock import patch
from pyasm.command import Command
from pyasm.common import Environment
from pyasm.search import Search, SearchType, WidgetDbConfig
from pyasm.security import Security
from pyasm.web import WebContainer
from pyasm.widget import SelectWdg, TextWdg
from tactic.ui.panel import EditWdg, EditCmd


def install_fixture(db, id_definition='integer PRIMARY KEY AUTOINCREMENT', placeholder='?'):
    db.execute("UPDATE project SET database='sthpw' WHERE code='one'")
    for table, columns in {
        'work_item': 'name text, pipeline_code text, search_type text, with_pipeline_type text',
        'plain_item': 'name text',
        'work_task': 'name text, search_type text, search_code text, pipeline_code text, process text, context text, assigned text, status text',
    }.items():
        db.execute('CREATE TABLE %s (id %s, code varchar(256), %s, s_status text)' % (table, id_definition, columns))
        kind = 'contract/' + table
        db.execute("INSERT INTO search_object (code,search_type,title,namespace,database,table_name,class_name) VALUES (?,?,?,'contract','sthpw',?,'pyasm.search.SObject')".replace('?', placeholder), (kind, kind, table, table))
    db.execute("INSERT INTO work_item (id,code,name,pipeline_code,search_type,with_pipeline_type) VALUES (1,'PARENT','Parent','form_main','contract/work_item','contract/work_item')")
    db.execute("INSERT INTO work_task (id,code,name,search_type,search_code,pipeline_code,process,context,assigned,status) VALUES (1,'TASK','Task','contract/work_item?project=one','PARENT','task','model','model/old','alice','Pending')")
    if 'serial' in id_definition:
        for table in ('work_item', 'work_task'):
            db.execute("SELECT setval('%s_id_seq', (SELECT max(id) FROM %s))" % (table, table))
    schema = '<schema parent="__NONE__"><search_type name="contract/work_item"/><search_type name="contract/plain_item"/><connect from="contract/work_task" to="contract/work_item" relationship="search_code"/></schema>'
    db.execute("INSERT INTO schema (code,schema) VALUES ('one',?)".replace('?', placeholder), (schema,))
    for code, project, search_type, name in (
        ('form_main', 'one', 'contract/work_item', 'Main'),
        ('form_global', None, 'other/work_item', 'Global'),
        ('form_other', 'two', 'contract/work_item', 'Other project'),
        ('form_wrong', 'one', 'contract/plain_item', 'Wrong type'),
    ):
        graph = '<pipeline><process name="model" type="manual" assigned_login_group="artists"/><process name="review" type="approval"/><process name="finish" type="action"/><connect from="model" to="review" context="model"/></pipeline>'
        db.execute('INSERT INTO pipeline (code,project_code,search_type,name,pipeline) VALUES (?,?,?,?,?)'.replace('?', placeholder), (code, project, search_type, name, graph))
    for login, display in (('alice', 'Alice'), ('bob', 'Bob')):
        db.execute('INSERT INTO login (code,login,display_name) VALUES (?,?,?)'.replace('?', placeholder), (login, login, display))
    db.execute("INSERT INTO login_group (code,login_group) VALUES ('artists','artists')")
    db.execute("INSERT INTO login_in_group (login,login_group) VALUES ('alice','artists')")


def run(case):
    if not Environment.get_security():
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    view = 'workflow_form_test'
    item_xml = '''<element name="pipeline_code"><display class="tactic.ui.input.PipelineInputWdg"/></element>
      <element name="search_type"><display class="tactic.ui.input.SearchTypeInputWdg"/></element>
      <element name="with_pipeline_type"><display class="tactic.ui.input.SearchTypeWithPipelineInputWdg"/></element>
      <element name="review"><display class="tactic.ui.input.ReviewProcessInputWdg"><pipeline_code>form_main</pipeline_code></display><action class="DatabaseAction"><save>false</save></action></element>'''
    task_xml = '''<element name="name"><display class="pyasm.widget.TextWdg"/><action class="DatabaseAction"><empty>false</empty></action></element>
      <element name="process"><display class="tactic.ui.input.ProcessInputWdg"/></element>
      <element name="context"><display class="tactic.ui.input.ProcessInputWdg"><context>true</context></display></element>
      <element name="subcontext"><display class="tactic.ui.input.SubContextInputWdg"/><action class="tactic.ui.input.SubContextAction"/></element>
      <element name="assigned"><display class="tactic.ui.input.ProcessGroupSelectWdg"/></element>
      <element name="status"><display class="tactic.ui.widget.TaskStatusSelectWdg"/></element>'''
    def setup():
        for kind, elements in (('contract/work_item', item_xml), ('contract/work_task', task_xml)):
            obj = SearchType.create('config/widget_config')
            obj.set_value('search_type', kind)
            obj.set_value('view', view)
            obj.set_value('config', '<config><%s>%s</%s></config>' % (view, elements, view))
            obj.commit()
        if case.get('operation') == 'process_name':
            task = Search.get_by_code('contract/work_task', 'TASK')
            for name, value in dict(name='Task', context='model/old', assigned='alice', status='Pending').items():
                task.set_value(name, value)
            task.commit()
            pipeline = Search.get_by_code('sthpw/pipeline', 'form_main')
            pipeline.set_value('pipeline', '<pipeline><process name="edit|process" type="manual"/><process name="review" type="approval"/></pipeline>')
            pipeline.set_pipeline(pipeline.get_value('pipeline'), cache=False)
            pipeline.commit()
    cmd = Command()
    cmd.execute = setup
    cmd.get_transaction().set_sync(False)
    Command.execute_cmd(cmd)
    WidgetDbConfig.clear_cache()

    def prepare(kind, code):
        widget = EditWdg(search_type=kind, search_key=kind + '?project=one&code=' + code, view=view)
        result = []
        for item in widget.get_widgets():
            item.set_input_prefix(widget.input_prefix)
            if hasattr(item, 'get_input'):
                inputs = [item.get_input()]
            elif type(item) in (TextWdg, SelectWdg):
                inputs = [item]
            else:
                # Intercept only HTML serialization. Execute the original get_display body.
                with patch.object(SelectWdg, 'get_display', lambda self: self), patch.object(SelectWdg, 'get_buffer_display', lambda self: self), patch.object(TextWdg, 'get_display', lambda self: self):
                    rendered = item.get_display()
                inputs = []
                def collect(wdg):
                    if isinstance(wdg, (SelectWdg, TextWdg)):
                        inputs.append(wdg)
                    elif hasattr(wdg, 'get_widgets'):
                        for child in wdg.get_widgets():
                            collect(child)
                collect(rendered)
            assert len(inputs) == 1, (item.name, len(inputs))
            control = inputs[0]
            field = dict(name=item.name, class_name=item.get_class_name(), values=item.get_values(for_display=True), type='select' if isinstance(control, SelectWdg) else 'text')
            if isinstance(control, SelectWdg):
                field['labels'], field['choices'] = control.get_select_values()
            result.append(field)
        return result

    result = dict(item=prepare('contract/work_item', 'PARENT'), task=prepare('contract/work_task', 'TASK'))
    if case.get('operation') in ('metadata', 'process_name'):
        return result
    web = WebContainer.get_web()
    key = 'contract/work_task?project=one&code=TASK'
    def edit(names, values):
        for name, value in values.items():
            web.set_form_value('edit|' + name, value)
        cmd = EditCmd(search_key=key, view=view, element_names=names)
        cmd.get_transaction().set_sync(False)
        Command.execute_cmd(cmd)
    def saved():
        obj = Search('contract/work_task').get_sobjects()[0]
        return {name: obj.get_value(name) for name in ('name', 'context', 'assigned', 'status')}
    edit(['context', 'subcontext', 'assigned', 'status'], dict(context='model/old', subcontext='new', assigned='alice', status='In Progress'))
    result['saved'] = saved()
    edit(['subcontext'], dict(subcontext=''))
    result['cleared'] = saved()
    try:
        edit(['context', 'subcontext'], dict(context='', subcontext='invalid'))
    except Exception as error:
        result['error'] = type(error).__name__
    result['after_error'] = saved()
    return result
