"""Run the same native instance operations in both kernels; roll back every case."""
from pyasm.biz import Schema
from pyasm.command import Command
from pyasm.common import Environment
from pyasm.search import Search
from pyasm.security import Security
from pyasm.web.api_xmlrpc import ApiXMLRPC


class ContractRollback(Exception):
    def __init__(self, result):
        self.result = result
        super().__init__('self-instance comparison rollback')


def pairs():
    rows = Search('contract/node_in_node')
    rows.set_show_retired(True)
    rows.add_order_by('id')
    return [[obj.get_data().get(name) for name in
             ('parent_code', 'child_code', 'parent_id', 'child_id', 's_status')]
            for obj in rows.get_sobjects()]


class Run(Command):
    def execute(self):
        self.get_transaction().set_sync(False)
        if self.case.get('id_keys'):
            schema = Schema.get()
            xml = schema.get_value('schema')
            xml = xml.replace('relationship="code" from_col="parent_code" path="child"',
                              'relationship="id" from_col="parent_id" to_col="id" path="child"')
            xml = xml.replace('relationship="code" from_col="child_code" path="parent"',
                              'relationship="id" from_col="child_id" to_col="id" path="parent"')
            schema.set_value('schema', xml)
            schema.commit()
            schema.init()
        api = ApiXMLRPC()
        api.set_protocol('local')
        ticket = {'project': 'one', 'language': 'python'}
        owner = Search.get_by_code('contract/node', self.case.get('owner', 'D'))
        member = Search.get_by_code('contract/node', self.case.get('member', 'E'))
        before = pairs()
        operation = self.case.get('operation', 'create')
        created = None
        if operation in ('create', 'roundtrip', 'reverse', 'self'):
            link = api.add_instance(ticket, owner.get_search_key(), member.get_search_key())
            created = [link.get(name) for name in ('parent_code', 'child_code', 'parent_id', 'child_id')]
            if operation == 'reverse':
                api.add_instance(ticket, member.get_search_key(), owner.get_search_key())
        instances = api.get_instances(ticket, owner.get_search_key(), 'contract/node')
        owned = [[row.get(name) for name in ('parent_code', 'child_code', 'parent_id', 'child_id')]
                 for row in instances]
        after_add = pairs()
        if operation in ('remove', 'roundtrip', 'reverse', 'self'):
            api.remove_instance(ticket, owner.get_search_key(), member.get_search_key())
        raise ContractRollback(dict(created=created, owned=owned, before=before,
                                    after_add=after_add, after_remove=pairs()))


def run(case):
    previous = Environment.get_security()
    if previous is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    try:
        command = Run()
        command.case = case
        try:
            Command.execute_cmd(command)
        except ContractRollback as error:
            return error.result
        raise AssertionError('The comparison command must roll back')
    finally:
        Environment.set_security(previous)
