"""Identical form/action calls in the original and headless kernels."""
from pyasm.command import Command
from pyasm.common import Container, Environment
from pyasm.search import Search, SearchType, WidgetDbConfig
from pyasm.web import WebContainer
from tactic.ui.panel import EditWdg, EditCmd
from pyasm.security import Security


def install_fixture(db, id_definition='integer PRIMARY KEY AUTOINCREMENT'):
    db.execute("UPDATE project SET database='sthpw' WHERE code='one'")
    db.execute('CREATE TABLE edit_entity (id %s, code varchar(256), name text, amount integer, active boolean, metadata text, s_status text)' % id_definition)
    db.execute("INSERT INTO search_object (code,search_type,namespace,database,table_name,class_name) VALUES ('contract/edit_entity','contract/edit_entity','contract','sthpw','edit_entity','pyasm.search.SObject')")
    db.execute("INSERT INTO edit_entity (id,code,name,amount,active) VALUES (1,'A','Original',0,false)")


def run(case):
    if not Environment.get_security():
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    view = 'contract_edit_' + case.get('operation', 'edit')
    config = SearchType.create('config/widget_config')
    config.set_value('search_type', 'contract/edit_entity')
    config.set_value('view', view)
    config.set_value('config', '''<config><%s>
        <element name="name" title="Item title" description="Description">
          <display class="pyasm.widget.TextWdg"><default>untitled</default></display>
          <action class="pyasm.command.DatabaseAction"><empty>false</empty></action>
        </element>
        <element name="amount" type="integer"><action class="pyasm.command.DatabaseAction"/></element>
        <element name="active"><display class="pyasm.widget.CheckboxWdg"/></element>
        <element name="choice"><display class="pyasm.widget.SelectWdg"><values>draft|review</values><labels>Draft|Review</labels><empty>true</empty><default>review</default></display></element>
        <element name="metadata" type="text" edit="false"/>
      </%s></config>''' % (view, view))
    setup = Command()
    setup.get_transaction().set_sync(False)
    setup.execute = lambda: config.commit()
    Command.execute_cmd(setup)
    WidgetDbConfig.clear_cache()
    key = 'contract/edit_entity?project=one&code=A'
    # Source widget init primes input fields; HTML itself is not compared.
    widget = EditWdg(search_type='contract/edit_entity', search_key=key, view=view)
    for item in widget.get_widgets():
        item.set_input_prefix(widget.input_prefix)
    metadata = dict(names=widget.element_names, titles=widget.element_titles,
                    descriptions=widget.element_descriptions, mode=widget.mode,
                    prefix=widget.input_prefix, skipped=widget.skipped_element_names,
                    inputs=[dict(name=item.get_name(), class_name=item.get_class_name(),
                                 values=item.get_values(), options=item.options)
                            for item in widget.get_widgets()])
    metadata['choices'] = {item.name: item.get_select_values() for item in widget.get_widgets()
                           if hasattr(item, 'get_select_values')}
    if case.get('operation') == 'metadata':
        return metadata
    web = WebContainer.get_web()
    web.set_form_value('edit|name', 'Updated')
    web.set_form_value('edit|amount', '1234')
    web.set_form_value('edit|active', False)
    cmd = EditCmd(search_key=key, view=view, element_names=['name', 'amount', 'active'])
    cmd.get_transaction().set_sync(False)
    Command.execute_cmd(cmd)
    after = Search.get_by_search_key(key)
    result = dict(metadata=metadata, action=cmd.get_info('action'),
                  values=[after.get_value(name) for name in ('name', 'amount', 'active')])
    # A later field failure must roll back the already-staged name change.
    web.set_form_value('edit|name', '')
    web.set_form_value('edit|amount', '9')
    failing = EditCmd(search_key=key, view=view, element_names=['amount', 'name'])
    failing.get_transaction().set_sync(False)
    try:
        Command.execute_cmd(failing)
    except Exception as error:
        result['error'] = type(error).__name__
    fresh = Search('contract/edit_entity')
    fresh.add_filter('code', 'A')
    after = fresh.get_sobject()
    result['rollback'] = [after.get_value(name) for name in ('name', 'amount', 'active')]
    return result
