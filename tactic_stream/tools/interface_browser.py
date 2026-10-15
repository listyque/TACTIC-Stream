"""Start a disposable HTTP server, exercise the built Vue UI, and shut it down."""
import json
from ast import literal_eval
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tests'))
from test_transport import Transport
from tactic_stream.server.api import Api

Transport.setUpClass()
try:
    with Transport.store.connection(write=True) as db:
        db.execute("INSERT INTO project (code,title,database) VALUES ('view_browser','Browser project','sthpw')")
        db.execute("INSERT INTO login (code,login,password) SELECT 'browser_reader','browser_reader',password FROM login WHERE login='admin'")
        db.execute("INSERT INTO login_group (code,login_group,access_rules) VALUES ('browser_readers','browser_readers',?)",
                   ('<rules><rule group="search_type" code="view_browser/ui_item" project="view_browser" access="view"/></rules>',))
        db.execute("INSERT INTO login_in_group (login,login_group) VALUES ('browser_reader','browser_readers')")
    api = Api(Transport.store)
    token = api.get_ticket('admin', 'private-test-password')
    reader = api.get_ticket('browser_reader', 'private-test-password')
    ticket = dict(ticket=token, project='view_browser')
    api.dispatch('insert', (ticket, 'sthpw/pref_setting', dict(key='timezone', login='admin', value='Asia/Tokyo')))
    kind = 'view_browser/ui_item'
    api.dispatch('execute_cmd', (ticket, 'tactic.core.schema_commands.SearchTypeCreatorCmd',
                 dict(search_type_name=kind, asset_title='Browser items',
                      column_name=['amount', 'active', 'status', 'deadline', 'due_day'],
                      data_type=['integer', 'boolean', 'varchar', 'timestamp', 'date'])))
    form = '''<element name="code"><display class="pyasm.widget.TextWdg"><read_only>true</read_only></display></element>
      <element name="name" title="Item name"><display class="pyasm.widget.TextWdg"><default>Untitled</default></display>
        <action class="pyasm.command.DatabaseAction"><empty>false</empty></action></element>
      <element name="description"><display class="pyasm.widget.TextAreaWdg"/></element>
      <element name="amount" type="integer"><display class="pyasm.widget.TextWdg"><default>0</default></display></element>
      <element name="active"><display class="pyasm.widget.CheckboxWdg"><default>false</default></display></element>
      <element name="status"><display class="pyasm.widget.SelectWdg"><values>draft|review</values><labels>Draft|Review</labels><default>review</default></display></element>
      <element name="deadline"><display class="tactic.ui.widget.CalendarInputWdg"><show_time>true</show_time><default>2026-10-09T12:30</default></display></element>
      <element name="due_day" type="date" title="Due day"/>'''
    for view in ('edit', 'insert'):
        configs = api.dispatch('query', (ticket, 'config/widget_config'),
                               dict(filters=[['search_type', kind], ['view', view]]))
        if isinstance(configs, str):
            configs = literal_eval(configs)
        xml = '<config><%s>%s</%s></config>' % (view, form, view)
        if configs:
            for config in configs:
                api.dispatch('update', (ticket, config['__search_key__'], dict(config=xml)))
        else:
            api.dispatch('insert', (ticket, 'config/widget_config', dict(search_type=kind, view=view, config=xml)))
    api.dispatch('insert', (ticket, kind, dict(code='BROWSER', name='Browser object',
        description='<img src=x onerror="window.badMarkupExecuted=true">', amount=0, active=False, status='draft',
        deadline='2026-10-07T01:02:03.123456Z', due_day='2026-10-08')))
    child_type = 'view_browser/ui_child'
    api.dispatch('execute_cmd', (ticket, 'tactic.core.schema_commands.SearchTypeCreatorCmd',
                 dict(search_type_name=child_type, asset_title='Browser children', sobject_parent=kind,
                      column_name=['ui_item_code'], data_type=['varchar'])))
    for view in ('insert', 'edit'):
        configs = literal_eval(api.dispatch('query', (ticket, 'config/widget_config'),
                               dict(filters=[['search_type', child_type], ['view', view]])))
        xml = '<config><%s><element name="name" title="Child name"/><element name="description"/>' % view
        xml += '<element name="ui_item_code"><display class="pyasm.widget.TextWdg"><read_only>true</read_only></display></element></%s></config>' % view
        for config in configs:
            api.dispatch('update', (ticket, config['__search_key__'], dict(config=xml)))
    from pyasm.search.search import RequestContext, request_context
    from tactic_stream.server.interface import read_form
    with request_context(RequestContext(Transport.store, 'admin', 'view_browser')):
        api.auth.bind_security('admin', token)
        descriptor = read_form(kind, 'edit', kind + '?project=view_browser&code=BROWSER')
        assert [field['name'] for field in descriptor['fields']] == ['code', 'name', 'description', 'amount', 'active', 'status', 'deadline', 'due_day']
    with request_context(RequestContext(Transport.store, 'admin', 'view_browser')):
        api.auth.bind_security('admin', token)
        assert read_form(kind, 'insert')['mode'] == 'insert'
    import workflow_form_contract
    import upload_form_contract
    import compound_form_contract
    with Transport.store.connection(write=True) as db:
        db.execute("DELETE FROM schema WHERE code='one' OR project_code='one'")
        workflow_form_contract.install_fixture(db)
        upload_form_contract.install_fixture(db)
        compound_form_contract.install_fixture(db)
    with request_context(RequestContext(Transport.store, 'admin', 'one')):
        api.auth.bind_security('admin', token)
        workflow_form_contract.run({'operation': 'metadata'})
    workflow_ticket = dict(ticket=token, project='one')
    for workflow_type in ('contract/work_item', 'contract/work_task'):
        configs = literal_eval(api.dispatch('query', (workflow_ticket, 'config/widget_config'),
                              dict(filters=[['search_type', workflow_type], ['view', 'workflow_form_test']])))
        xml = configs[0]['config'].replace('workflow_form_test', 'edit')
        if workflow_type == 'contract/work_item':
            xml = xml.replace('</edit>', '<element name="attachment"><display class="tactic.ui.widget.UploadWdg"><context>browser_form|browser_review</context></display><action class="pyasm.command.UploadAction"/></element></edit>')
            xml = xml.replace('<element name="with_pipeline_type"><display class="tactic.ui.input.SearchTypeWithPipelineInputWdg"/></element>', '<element name="with_pipeline_type"><display class="pyasm.widget.MultiSelectWdg"><values>model|review|finish</values></display><action class="pyasm.command.MultiDatabaseAction"/></element>')
            xml = xml.replace('</edit>', '<element name="attachments"><display class="pyasm.widget.UploadWdg"><upload_type>arbitrary</upload_type><context>publish|review</context></display><action class="pyasm.command.MultiUploadAction"><upload_type>arbitrary</upload_type></action></element></edit>')
            xml = xml.replace('</edit>', '<element name="clock"><display class="tactic.ui.widget.TimeInputWdg"/><action class="tactic.ui.widget.TimeDatabaseAction"/></element><element name="start_date"><display class="tactic.ui.widget.TimeInputWdg"/><action class="pyasm.command.TimeAction"><column>start_date</column></action></element><element name="archives"><display class="pyasm.widget.UploadWdg"><upload_type>arbitrary</upload_type><context>archive</context></display><action class="pyasm.command.MultiZipUploadAction"><upload_type>arbitrary</upload_type><naming>compound_form_contract.ZipNaming</naming></action></element></edit>')
        else:
            xml = xml.replace('</edit>', '<element name="parent_key"><display class="tactic.ui.input.TaskSObjectInputWdg"/><action class="pyasm.command.NullAction"/></element></edit>')
        api.dispatch('insert', (workflow_ticket, 'config/widget_config', dict(search_type=workflow_type, view='edit', config=xml)))
    run = subprocess.run(['node', str(ROOT / 'tools/interface_browser.mjs')], cwd=ROOT,
        input=json.dumps(dict(url=Transport.url, archivePayload=__import__('base64').b64encode(compound_form_contract.archive_payload()).decode('ascii'), ticket=token, readerTicket=reader, project='view_browser', type=kind)),
        text=True, encoding='utf-8', env=dict(os.environ, PLAYWRIGHT_BROWSERS_PATH=str(ROOT / '.browser-cache')), timeout=60)
    raise SystemExit(run.returncode)
finally:
    Transport.tearDownClass()
