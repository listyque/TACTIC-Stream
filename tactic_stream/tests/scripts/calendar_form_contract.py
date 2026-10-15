"""Identical CalendarInputWdg/EditCmd calls in the original and native kernels."""
from pyasm.common import Environment
from pyasm.command import Command
from pyasm.search import Search, SearchType
from pyasm.security import Security
from pyasm.web import WebContainer
from tactic.ui.panel import EditWdg, EditCmd


def install_fixture(db, id_definition='integer PRIMARY KEY AUTOINCREMENT'):
    db.execute("UPDATE project SET database='sthpw' WHERE code='one'")
    db.execute('CREATE TABLE calendar_entity (id %s, code varchar(256), name text, deadline timestamp, due_day date, s_status text)' % id_definition)
    db.execute("INSERT INTO search_object (code,search_type,namespace,database,table_name,class_name) VALUES ('contract/calendar_entity','contract/calendar_entity','contract','sthpw','calendar_entity','pyasm.search.SObject')")
    db.execute("INSERT INTO calendar_entity (id,code,name,deadline,due_day) VALUES (1,'C','Calendar','2026-10-07 01:02:03.123456','2026-10-08')")


def run(case):
    if not Environment.get_security():
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    kind, view = 'contract/calendar_entity', 'calendar_test'
    config = SearchType.create('config/widget_config')
    config.set_value('search_type', kind)
    config.set_value('view', view)
    config.set_value('config', '''<config><calendar_test>
      <element name="name"><display class="pyasm.widget.TextWdg"/><action class="DatabaseAction"><empty>false</empty></action></element>
      <element name="deadline"><display class="tactic.ui.widget.CalendarInputWdg"><show_time>true</show_time></display></element>
      <element name="due_day"><display class="tactic.ui.widget.CalendarInputWdg"/></element>
    </calendar_test></config>''')
    pref = SearchType.create('sthpw/pref_setting')
    pref.set_value('key', 'timezone')
    pref.set_value('login', 'admin')
    pref.set_value('value', 'Asia/Tokyo')
    setup = Command()
    setup.get_transaction().set_sync(False)
    setup.execute = lambda: (config.commit(), pref.commit())
    Command.execute_cmd(setup)
    key = kind + '?project=one&code=C'
    widget = EditWdg(search_type=kind, search_key=key, view=view)
    result = dict(names=widget.element_names, fields=[], display=[])
    for item in widget.get_widgets():
        item.set_input_prefix(widget.input_prefix)
        values = item.get_values(for_display=True)
        if item.name == 'due_day':
            values = [str(value)[:10] for value in values]
        result['fields'].append(dict(name=item.name, class_name=item.get_class_name(), values=values, options=item.options))
        try:
            result['display'].append(item.get_value())
        except Exception as error:
            result['display'].append(dict(error=type(error).__name__))
    if case.get('operation') == 'metadata':
        return result
    web = WebContainer.get_web()
    web.set_form_value('edit|deadline', '2026-11-02T10:30:15.250')
    web.set_form_value('edit|due_day', '2026-11-05')
    cmd = EditCmd(search_key=key, view=view, element_names=['deadline', 'due_day'])
    cmd.get_transaction().set_sync(False)
    Command.execute_cmd(cmd)
    def saved():
        search = Search(kind)
        search.add_filter('code', 'C')
        obj = search.get_sobject()
        return dict(deadline=obj.get_value('deadline'), due_day=str(obj.get_value('due_day'))[:10])
    result['saved'] = saved()
    web.set_form_value('edit|deadline', '2026-12-01T09:00')
    web.set_form_value('edit|name', '')
    failing = EditCmd(search_key=key, view=view, element_names=['deadline', 'name'])
    failing.get_transaction().set_sync(False)
    try:
        Command.execute_cmd(failing)
    except Exception as error:
        result['error'] = type(error).__name__
    result['after_error'] = saved()
    return result
