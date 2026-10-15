"""Same parent, form UploadAction and initial-task commands in both kernels."""
from pathlib import Path
from pyasm.common import Environment
from pyasm.command import Command
from pyasm.search import Search, SearchType, WidgetDbConfig
from pyasm.security import Security, Ticket
from pyasm.web import WebContainer
from tactic.ui.panel import EditWdg, EditCmd

PARENT = 'contract/work_item?project=one&code=PARENT'
TASK = 'contract/work_task?project=one&code=TASK'
VIEW = 'upload_form_test'


def install_fixture(db):
    db.execute('ALTER TABLE work_item ADD COLUMN start_date timestamp')
    db.execute("UPDATE work_item SET start_date='2026-11-02 12:30:00' WHERE code='PARENT'")


def setup():
    configs = {
        'contract/work_item': '''<element name="name"><display class="pyasm.widget.TextWdg"/></element>
          <element name="attachment"><display class="tactic.ui.widget.SimpleUploadWdg"><context>form_upload</context></display><action class="pyasm.command.UploadAction"/></element>
          <element name="start_date"><display class="pyasm.widget.TextWdg"/><action class="pyasm.command.TimeAction"><column>start_date</column></action></element>
          <element name="initial_tasks"><display class="pyasm.widget.CheckboxWdg"/><action class="pyasm.command.InitialTaskCreateAction"/></element>''',
        'contract/work_task': '''<element name="name"><display class="pyasm.widget.TextWdg"/></element>
          <element name="parent_key"><display class="tactic.ui.input.TaskSObjectInputWdg"><parent_key>%s</parent_key></display><action class="pyasm.command.DatabaseAction"><parent_key>true</parent_key></action></element>''' % PARENT.replace('&', '&amp;'),
    }
    def save():
        parent = Search.get_by_search_key(PARENT)
        parent.set_value('start_date', '2026-11-02 12:30:00')
        parent.commit()
        for kind, elements in configs.items():
            config = SearchType.create('config/widget_config')
            config.set_value('search_type', kind)
            config.set_value('view', VIEW)
            config.set_value('config', '<config><%s>%s</%s></config>' % (VIEW, elements, VIEW))
            config.commit()
    cmd = Command()
    cmd.execute = save
    cmd.get_transaction().set_sync(False)
    Command.execute_cmd(cmd)
    WidgetDbConfig.clear_cache()


def run(case):
    if not Environment.get_security():
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    if not Environment.get_ticket():
        Environment.get_security()._ticket = Ticket.create('upload_form_fixture', 'admin')
    if case.get('operation', '').startswith('multi_'):
        return run_multi(case)
    if case.get('operation', '').startswith('rich_'):
        return run_rich(case)
    setup()
    # Execute original display preparation, intercepting only the upload button's HTML.
    item_form = EditWdg(search_type='contract/work_item', search_key=PARENT, view=VIEW)
    upload = next(item for item in item_form.get_widgets() if item.name == 'attachment')
    if hasattr(upload, 'get_input'):
        upload.get_input()
    else:
        from pyasm.web import Widget
        upload.browse = Widget()
        upload.get_display()
    new_task = EditWdg(search_type='contract/work_task', view=VIEW)
    parent_input = next(item for item in new_task.get_widgets() if item.name == 'parent_key')
    if hasattr(parent_input, 'get_input'):
        parent_value = parent_input.get_input().get_value()
    else:
        from pyasm.widget import HiddenWdg
        rendered = parent_input.get_display()
        parent_value = next(item for item in rendered.get_widgets() if isinstance(item, HiddenWdg)).get_value()
    result = dict(context=upload.context, parent_value=parent_value)
    if case.get('operation') == 'metadata':
        return result
    web = WebContainer.get_web()
    def edit(key, names, values):
        for name, value in values.items():
            web.set_form_value('edit|' + name, value)
        cmd = EditCmd(search_key=key, view=VIEW, element_names=names)
        cmd.get_transaction().set_sync(False)
        Command.execute_cmd(cmd)
        return cmd
    # New task links to the configured parent using the original DatabaseAction option.
    web.set_form_value('search_type', 'contract/work_task')
    web.set_form_value('search_id', '-1')
    created = edit(None, ['name', 'parent_key'], dict(name='Inserted task', parent_key=parent_value))
    parent = created.get_sobject().get_parent()
    result['created_parent'] = [parent.get_code(), parent.get_base_search_type()]
    # Date actions preserve the existing day while replacing its hour/minute.
    edit(PARENT, ['start_date'], {'start_date|hour': '9', 'start_date|minute': '15'})
    result['time'] = str(Search.get_by_search_key(PARENT).get_value('start_date'))
    from pyasm.command import DateAction, TaskDateAction
    result['dates'] = []
    for cls in (DateAction, TaskDateAction):
        obj = Search.get_by_search_key(PARENT)
        action = cls()
        action.set_name('start_date')
        action.set_sobject(obj)
        action.set_data('2026-11-03 07:00:00+00:00')
        def save_date():
            action.execute()
            obj.commit()
            action.postprocess()
        cmd = Command()
        cmd.execute = save_date
        cmd.get_transaction().set_sync(False)
        Command.execute_cmd(cmd)
        result['dates'].append(str(Search.get_by_search_key(PARENT).get_value('start_date')))
    edit(PARENT, ['initial_tasks'], dict(initial_tasks='on'))
    tasks = Search('sthpw/task')
    tasks.add_sobject_filter(Search.get_by_search_key(PARENT))
    result['processes'] = sorted(obj.get_value('process') for obj in tasks.get_sobjects())
    # Single file handoff: same submitted names as the original SimpleUploadWdg.
    directory = Path(Environment.get_upload_dir())
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / 'payload.txt'
    payload = b'form upload\n\x00\xff'
    rows = []
    context = 'form_upload_' + case.get('operation', 'edit')
    for number in (1, 2):
        path.write_bytes(payload)
        revision = case.get('operation') == 'revision' and number == 2
        edit(PARENT, ['name', 'attachment'], dict(name='Uploaded parent', **{
            'attachment|path': '/client/payload.txt', 'attachment|ticket': Environment.get_ticket(),
            'attachment|context': context, 'attachment|description': 'Form attachment',
            'attachment|is_revision': 'on' if revision else '',
        }))
        search = Search('sthpw/snapshot')
        search.add_filter('context', context)
        search.add_order_by('version desc')
        search.add_order_by('revision desc')
        snapshot = search.get_sobject()
        files = snapshot.get_all_file_objects()
        main = next(file for file in files if file.get_type() == 'main')
        saved = Path(main.get_lib_path())
        rows.append([snapshot.get_version(), snapshot.get_value('revision'), snapshot.get_value('description'), main.get_value('st_size'), list(saved.read_bytes())])
        assert not path.exists()
    result['files'] = rows
    return result


def run_rich(case):
    from tactic.ui.widget import UploadWdg
    from pyasm.widget import SelectWdg
    from unittest.mock import patch
    import tactic.ui.widget.upload_wdg as upload_module
    view = 'rich_upload_form_test'
    def setup_rich():
        setting = SearchType.create('config/prod_setting')
        setting.set_value('key', 'rich_upload_context')
        setting.set_value('value', 'publish|review')
        setting.commit()
        config = SearchType.create('config/widget_config')
        config.set_value('search_type', 'contract/work_item')
        config.set_value('view', view)
        config.set_value('config', '''<config><%s>
          <element name="name"><display class="pyasm.widget.TextWdg"/></element>
          <element name="attachment"><display class="tactic.ui.widget.UploadWdg"><context>publish|review</context></display><action class="pyasm.command.UploadAction"/></element>
        </%s></config>''' % (view, view))
        config.commit()
    command = Command()
    command.execute = setup_rich
    command.get_transaction().set_sync(False)
    Command.execute_cmd(command)
    WidgetDbConfig.clear_cache()
    form = EditWdg(search_type='contract/work_item', search_key=PARENT, view=view)
    metadata = []
    for options in ({}, {'context': 'publish|review'}, {'context_expr': '@GET(sthpw/pipeline.code)', 'context': 'ignored'},
                    {'setting': 'rich_upload_context'}, {'pipeline': 'true'}, {'pipeline': 'false'}):
        item = UploadWdg(key='attachment', **options)
        item.set_name('attachment')
        item.set_input_prefix('edit')
        item.set_sobject(Search.get_by_search_key(PARENT))
        if hasattr(item, 'get_input'):
            item.get_input()
            control = item.context_input
        else:
            # Execute original get_info_wdg; capture its real SelectWdg before HTML serialization.
            controls = []
            def select(*args, **kwargs):
                control = SelectWdg(*args, **kwargs)
                controls.append(control)
                return control
            with patch.object(upload_module, 'SelectWdg', side_effect=select):
                item.get_info_wdg()
            control = controls[0] if controls else None
        labels, values = control.get_select_values() if isinstance(control, SelectWdg) else ([], [])
        metadata.append(dict(type='select' if isinstance(control, SelectWdg) else 'text', labels=labels, choices=values,
                             show_upload=item.show_upload))
    if case['operation'] == 'rich_metadata':
        return dict(controls=metadata)
    web = WebContainer.get_web()
    directory = Path(Environment.get_upload_dir())
    directory.mkdir(parents=True, exist_ok=True)
    rows = []
    subcontext = 'draft' if case['operation'] == 'rich_subcontext' else ''
    context = 'upload_' + case['operation']
    for index in (1, 2):
        path = directory / 'rich.txt'
        path.write_bytes(b'Rich upload\n')
        web.params.clear() if hasattr(web, 'params') else web.request.params.clear()
        for name, value in {
            'name': 'Rich parent', 'attachment|path': '/client/rich.txt',
            'attachment|ticket': Environment.get_ticket(), 'attachment|column': 'attachment',
            'attachment|context': context, 'attachment|subcontext': subcontext,
            'attachment|description': 'Rich attachment',
            'attachment|is_revision': 'on' if index == 2 and case['operation'] == 'rich_revision' else '',
        }.items():
            web.set_form_value('edit|' + name, value)
        command = EditCmd(search_key=PARENT, view=view, element_names=['name', 'attachment'])
        command.get_transaction().set_sync(False)
        Command.execute_cmd(command)
        search = Search('sthpw/snapshot')
        search.add_filter('search_code', 'PARENT')
        search.add_filter('version', 0, op='>')
        search.add_order_by('id desc')
        snapshot = search.get_sobject()
        file = next(file for file in snapshot.get_all_file_objects() if file.get_type() == 'main')
        rows.append([snapshot.get_value('context'), snapshot.get_version(), snapshot.get_value('revision'),
                     snapshot.get_value('description'), list(Path(file.get_lib_path()).read_bytes())])
        assert not path.exists()
    return dict(controls=metadata, snapshots=rows, name=Search.get_by_search_key(PARENT).get_value('name'))


MULTI_VIEW = 'multi_upload_form_test'


def setup_multi(arbitrary=False, custom_icon=False):
    mode = '<upload_type>arbitrary</upload_type>' if arbitrary else '<names>primary|secondary</names><types>main|alt</types>'
    display = '<upload_type>arbitrary</upload_type>' if arbitrary else '<names>primary|secondary</names><required>true|false</required>'
    if custom_icon:
        mode = '<names>primary|thumbnail</names><types>main|icon_main</types>'
        display = '<names>primary|thumbnail</names>'
    xml = '''<config><%s>
      <element name="name"><display class="pyasm.widget.TextWdg"/></element>
      <element name="with_pipeline_type"><display class="pyasm.widget.MultiSelectWdg"><values>model|review|finish</values></display><action class="pyasm.command.MultiDatabaseAction"/></element>
      <element name="attachments"><display class="pyasm.widget.UploadWdg">%s<context>publish|review</context></display><action class="pyasm.command.MultiUploadAction">%s</action></element>
    </%s></config>''' % (MULTI_VIEW, display, mode, MULTI_VIEW)
    def save():
        obj = Search.get_by_search_key(PARENT)
        obj.set_value('with_pipeline_type', '||model||review||')
        obj.commit()
        config = SearchType.create('config/widget_config')
        config.set_value('search_type', 'contract/work_item')
        config.set_value('view', MULTI_VIEW)
        config.set_value('config', xml)
        config.commit()
    cmd = Command()
    cmd.execute = save
    cmd.get_transaction().set_sync(False)
    Command.execute_cmd(cmd)
    WidgetDbConfig.clear_cache()


def run_multi(case):
    from io import BytesIO
    from pyasm.widget import MultiSelectWdg
    operation = case['operation']
    arbitrary = operation == 'multi_arbitrary'
    custom_icon = operation == 'multi_custom_icon'
    setup_multi(arbitrary, custom_icon)
    form = EditWdg(search_type='contract/work_item', search_key=PARENT, view=MULTI_VIEW)
    selector = next(item for item in form.get_widgets() if isinstance(item, MultiSelectWdg))
    result = dict(selected=[value for value in ['model', 'review', 'finish'] if selector._is_selected(value, selector.get_values(for_display=True))])
    web = WebContainer.get_web()
    names = ['attachments0', 'attachments1'] if arbitrary else ['primary', 'secondary']
    if custom_icon:
        names = ['primary', 'thumbnail']
    directory = Path(Environment.get_upload_dir())
    directory.mkdir(parents=True, exist_ok=True)
    for number in (1, 2) if operation == 'multi_revision' else (1,):
        for index, name in enumerate(names):
            filename = ['primary.txt', 'secondary.bin'][index]
            payload = [b'main\x00\xff', b'alternate\n'][index]
            if custom_icon:
                from PIL import Image
                image = BytesIO()
                Image.new('RGB', (32, 32) if index == 0 else (16, 16), 'blue').save(image, format='PNG')
                filename = ['main.png', 'preview.png'][index]
                payload = image.getvalue()
            if operation == 'multi_handoff' or operation == 'multi_revision':
                (directory / filename).write_bytes(payload)
                web.set_form_value('edit|' + name + '|path', filename)
                web.set_form_value('edit|' + name + '|ticket', Environment.get_ticket())
            else:
                storage = type('FieldStorage', (), {})()
                storage.filename = filename
                storage.file = BytesIO(payload)
                web.set_form_value('edit|' + name, storage)
        web.set_form_value('edit|with_pipeline_type', ['review', 'finish'])
        web.set_form_value('edit|attachments|context', 'multi_' + operation)
        web.set_form_value('edit|attachments|subcontext', 'draft')
        web.set_form_value('edit|attachments|description', 'Two files')
        web.set_form_value('edit|attachments|is_revision', 'on' if number == 2 else '')
        cmd = EditCmd(search_key=PARENT, view=MULTI_VIEW, element_names=['with_pipeline_type', 'attachments'])
        cmd.get_transaction().set_sync(False)
        try:
            Command.execute_cmd(cmd)
        except Exception as error:
            if not custom_icon:
                raise
            return dict(source_error=str(error))
    search = Search('sthpw/snapshot')
    search.add_filter('context', 'multi_' + operation + '/draft')
    search.add_order_by('version desc')
    search.add_order_by('revision desc')
    snapshot = search.get_sobject()
    if custom_icon:
        return dict(file_types=sorted(file.get_type() for file in snapshot.get_all_file_objects()))
    result['snapshot'] = [snapshot.get_version(), snapshot.get_value('revision'), snapshot.get_value('description')]
    result['files'] = sorted([[file.get_type(), list(Path(file.get_lib_path()).read_bytes())] for file in snapshot.get_all_file_objects()])
    result['stored'] = Search.get_by_search_key(PARENT).get_value('with_pipeline_type')
    result['context'] = snapshot.get_value('context')
    return result
