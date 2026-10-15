"""Same ZIP naming and date/time actions in the original and native kernels."""
from io import BytesIO
from pathlib import Path
import sys
import zipfile

from pyasm.common import Environment
from pyasm.command import Command
from pyasm.search import Search, SearchType, WidgetDbConfig
from pyasm.security import Security, Ticket
from pyasm.web import WebContainer
from tactic.ui.panel import EditCmd

KEY = 'contract/work_item?project=one&code=PARENT'
VIEW = 'compound_form_test'


def install_fixture(db):
    db.execute('ALTER TABLE work_item ADD COLUMN clock time')
    db.execute('ALTER TABLE work_item ADD COLUMN alternate timestamp')
    db.execute("UPDATE work_item SET clock='08:30:15.250000', alternate='2026-11-03 15:20:25.125000'")
    db.execute("INSERT INTO work_item (code,name) VALUES ('SECOND','Second object')")


class ZipNaming:
    def __init__(self):
        self.objects = {}

    def get_sobject_by_filename(self, filename):
        code = filename.split('__', 1)[0]
        if code not in self.objects:
            self.objects[code] = Search.get_by_code('contract/work_item', code)
        return self.objects[code]


class FreshZipNaming(ZipNaming):
    def get_sobject_by_filename(self, filename):
        search = Search('contract/work_item')
        search.add_filter('code', filename.split('__', 1)[0])
        return search.get_sobject()


def archive_payload(folder='nested'):
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr(folder + '/', b'')
        archive.writestr(folder + '/PARENT__first.txt', b'First object file')
        archive.writestr(folder + '/PARENT__second.txt', b'Second object file')
        archive.writestr('SECOND__first.txt', b'Other object file')
    return buffer.getvalue()


def setup():
    xml = '''<config><compound_form_test>
      <element name="name"><display class="pyasm.widget.TextWdg"/></element>
      <element name="start_date"><display class="tactic.ui.widget.TimeInputWdg"/><action class="tactic.ui.widget.TimeDatabaseAction"/></element>
      <element name="alternate"><display class="tactic.ui.widget.CalendarInputWdg"/><action class="tactic.ui.widget.DateDatabaseAction"><column>start_date|alternate</column></action></element>
      <element name="clock"><display class="tactic.ui.widget.TimeInputWdg"/><action class="tactic.ui.widget.TimeDatabaseAction"/></element>
      <element name="legacy_time"><display class="tactic.ui.widget.TimeInputWdg"><column>start_date</column></display><action class="pyasm.command.TimeAction"><column>start_date</column></action></element>
      <element name="attachments"><display class="pyasm.widget.UploadWdg"><upload_type>arbitrary</upload_type><context>archive</context></display><action class="pyasm.command.MultiZipUploadAction"><upload_type>arbitrary</upload_type><naming>compound_form_contract.ZipNaming</naming></action></element>
    </compound_form_test></config>'''
    def save():
        config = SearchType.create('config/widget_config')
        config.set_value('search_type', 'contract/work_item')
        config.set_value('view', VIEW)
        config.set_value('config', xml)
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
        Environment.get_security()._ticket = Ticket.create('compound_form_fixture', 'admin')
    setup()
    EditCmd(search_key=KEY, view=VIEW, element_names=['name'])
    web = WebContainer.get_web()
    operation = case['operation']
    if operation.startswith('zip_'):
        return run_zip(operation)
    import tactic.ui.widget.calendar_wdg as calendar
    alias_needed = 'basestring' in calendar.TimeDatabaseAction.execute.__code__.co_names and not hasattr(calendar, 'basestring')
    if alias_needed:
        calendar.basestring = str  # Test-only Python 2 compatibility, not a source edit.
    def edit(names, values):
        for name, value in values.items():
            web.set_form_value('edit|' + name, value)
        cmd = EditCmd(search_key=KEY, view=VIEW, element_names=names)
        cmd.get_transaction().set_sync(False)
        Command.execute_cmd(cmd)
    if operation == 'time_only':
        edit(['clock'], dict(clock='06:45'))
        return str(Search.get_by_search_key(KEY).get_value('clock'))
    edit(['start_date'], dict(start_date='6:45 PM'))
    obj = Search.get_by_search_key(KEY)
    result = dict(time=str(obj.get_value('start_date')), python3_alias_needed=alias_needed)
    edit(['alternate'], dict(alternate='2027-02-04'))
    obj = Search.get_by_search_key(KEY)
    result['dates'] = [str(obj.get_value('start_date')), str(obj.get_value('alternate'))]
    edit(['legacy_time'], {'legacy_time|hour': '7', 'legacy_time|minute': '35'})
    result['legacy_time'] = str(Search.get_by_search_key(KEY).get_value('start_date'))
    return result


def run_zip(operation):
    from pyasm.command import MultiZipUploadAction
    import pyasm.command.edit_wdg_action as actions
    # The original eval requires its resolver module in the action's global namespace.
    # Test runtime wiring only; native resolution uses the trusted class path directly.
    actions.compound_form_contract = sys.modules[__name__]
    web = WebContainer.get_web()
    payload = archive_payload(operation)
    if operation == 'zip_handoff':
        path = Path(Environment.get_upload_dir()) / 'objects.zip'
        path.write_bytes(payload)
        web.set_form_value('edit|attachments0|path', path.name)
        web.set_form_value('edit|attachments0|ticket', Environment.get_ticket())
    else:
        storage = type('FieldStorage', (), {})()
        storage.filename = 'objects.zip'
        storage.file = BytesIO(payload)
        web.set_form_value('edit|attachments0', storage)
    web.set_form_value('edit|attachments|context', 'archive')
    web.set_form_value('edit|attachments|description', 'Two objects from ZIP')
    if operation in ('zip_prepare', 'zip_fresh'):
        action = MultiZipUploadAction()
        action.set_name('attachments')
        action.set_input_prefix('edit')
        action.set_option('naming', 'compound_form_contract.FreshZipNaming' if operation == 'zip_fresh' else 'compound_form_contract.ZipNaming')
        action.set_sobject(Search.get_by_search_key(KEY))
        cmd = Command()
        def prepare():
            action.check()
            action._upload_zipped_files()
        cmd.execute = prepare
    else:
        cmd = EditCmd(search_key=KEY, view=VIEW, element_names=['attachments'])
    cmd.get_transaction().set_sync(False)
    try:
        Command.execute_cmd(cmd)
    except Exception as error:
        return dict(error=type(error).__name__, message=str(error))
    if operation in ('zip_prepare', 'zip_fresh'):
        return sorted([[obj.get_code(), sorted([[kind, list(Path(path).read_bytes())] for path, kind in zip(files, types)])]
                       for obj, (files, types) in action.sobject_dict.items()])
    search = Search('sthpw/snapshot')
    search.add_filter('context', 'archive')
    search.add_filter('version', 0, '>')
    return sorted([[snapshot.get_value('search_code'), snapshot.get_version(), snapshot.get_value('description'),
                    sorted([[file.get_type(), list(Path(file.get_lib_path()).read_bytes())] for file in snapshot.get_all_file_objects()])]
                   for snapshot in search.get_sobjects()])
