"""Server script executed unchanged by both TACTIC kernels on private data."""
from pyasm.command import Command, Trigger
from pyasm.common import Container
from pyasm.search import Search, SearchType, Transaction


class CustomTrigger(Trigger):
    def execute(self):
        tx = Transaction.get()
        Container.get_seq('custom_script:events').append({
            'event': self.get_event(), 'input': self.get_input().copy(),
            'caller': self.get_caller().__class__.__name__,
            'active': tx.is_in_transaction(), 'counter': tx.counter})
        tx.set_record(False)
        Search('contract/entity').get_sql().do_update("UPDATE entity SET name='script trigger' WHERE code='A'")
        return {'handled': True}


class CustomCommand(Command):
    def __init__(self, fail):
        super().__init__()
        self.fail = fail

    def execute(self):
        self.get_transaction().set_record(False)
        obj = Search.get_by_code('contract/entity', 'A')
        obj.set_value('amount', 42)
        Search('contract/entity').get_sql().do_update("UPDATE entity SET name='script caller' WHERE code='A'")
        handlers = Trigger.call(self, 'custom/read', {'key': obj.get_search_key(), 'amount': obj.get_value('amount')})
        if self.fail:
            raise ValueError('custom script failed')
        return {'key': obj.get_search_key(), 'pending': obj.update_data.copy(),
                'handler_results': [handler.get_ret_val() for handler in handlers]}


def run(mode, fail=False):
    definition = SearchType.create('sthpw/trigger')
    definition.set_value('event', 'custom/read')
    definition.set_value('class_name', 'trigger_contract.CustomTrigger')
    definition.set_value('mode', mode)
    Trigger.append_static_trigger(definition)
    try:
        result = {'result': Command.execute_cmd(CustomCommand(fail))}
    except ValueError as exc:
        result = {'error': str(exc)}
    result['events'] = Container.get_seq('custom_script:events')
    result['value'] = Search.get_by_code('contract/entity', 'A').get_value('name')
    search = Search('contract/entity')
    search.add_code_filter('A')
    result['database_value'] = search.get_sobject().get_value('name')
    result['queue'] = len(Container.get_seq('Trigger:called_triggers'))
    return result
