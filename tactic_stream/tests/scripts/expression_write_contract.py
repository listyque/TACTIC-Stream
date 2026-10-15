"""Same expression writes, local API and saved Python in both TACTIC kernels."""
from pyasm.biz import ExpressionParser, Project
from pyasm.command import Command, Trigger
from pyasm.common import Container, Environment
from pyasm.search import Search, SearchType
from pyasm.security import Security
from pyasm.web.api_xmlrpc import ApiXMLRPC


class Changed(Trigger):
    def execute(self):
        Container.append_seq('expression.events', self.get_input()['sobject']['note'])


class Write(Command):
    def execute(self):
        self.get_transaction().set_sync(False)
        note = SearchType.create('sthpw/note')
        for name, value in {'code': 'EX_NOTE', 'note': 'before', 'process': 'expression_contract'}.items():
            note.set_value(name, value)
        note.commit()
        trigger = SearchType.create('sthpw/trigger')
        for name, value in {'event': 'update|sthpw/note', 'class_name': 'expression_write_contract.Changed',
                            'mode': 'same process,same transaction'}.items():
            trigger.set_value(name, value, temp=True)
        Trigger.append_static_trigger(trigger)
        xp = ExpressionParser()
        updated = xp.eval("@UPDATE(sobject,note,'changed')", [note])
        saved = SearchType.create('config/custom_script')
        for name, value in {'code': 'EX_SCRIPT', 'folder': 'expression', 'title': 'run', 'language': 'python',
                            'script': "server.insert('sthpw/note', {'note':'from python','process':'expression_contract'})\nreturn {'root':sobject.get_code(),'calc':server.eval('6 * 7'),'project':server.get_project()}"}.items():
            saved.set_value(name, value)
        saved.commit()
        python = xp.eval("@PYTHON(expression/run)", [note])
        api = ApiXMLRPC()
        api.set_protocol('local')
        ticket = {'project': Project.get().get_code(), 'language': 'python', 'site': None}
        local = api.eval(ticket, "'3'", single=True)
        result = {'updated': [obj.get_value('note') for obj in updated], 'python': python,
                  'local': [local, type(local).__name__], 'events': Container.get_seq('expression.events')}
        if self.fail:
            raise ValueError('expression rollback')
        return result


def run(case):
    previous = Environment.get_security()
    if previous is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    try:
        cmd = Write()
        cmd.fail = case.get('fail', False)
        try:
            result = Command.execute_cmd(cmd)
        except ValueError as error:
            result = {'error': str(error)}
        search = Search('sthpw/note')
        search.add_filter('process', 'expression_contract')
        search.add_order_by('note')
        result['after'] = [obj.get_value('note') for obj in search.get_sobjects()]
        search = Search('config/custom_script')
        search.add_filter('code', 'EX_SCRIPT')
        result['script_exists'] = bool(search.get_sobject())
        return result
    finally:
        Environment.set_security(previous)
