"""Exercise the same Trigger entry points in both kernels on private fixtures."""
import copy
from pathlib import Path
import sys

from pyasm.command import Command, Trigger
from pyasm.common import Common, Container, jsondumps
from pyasm.search import Search, Transaction

# A stable import path also works in the original Marshaller's class cache.
sys.modules['tactic_stream_trigger_probe'] = sys.modules[__name__]


class Definition:
    def __init__(self, spec):
        self.data = dict(spec)
        self.data.setdefault('code', spec.get('label', 'definition'))
        self.data.setdefault('class_name', 'tactic_stream_trigger_probe.RecordedTrigger')
        if spec.get('class_object'):
            self.data['class_name'] = RecordedTrigger
        self.data['data'] = jsondumps(spec.get('data', {}))

    def get_value(self, name, no_exception=False):
        return self.data.get(name, '')

    def get_code(self):
        return self.data['code']

    def get_base_search_type(self):
        return self.data.get('base_type', 'sthpw/trigger')


class RecordedTrigger(Trigger):
    def get_title(self):
        return 'RecordedTrigger'

    def execute(self):
        data = self.get_trigger_data()
        state = Container.get('TriggerProbe:state')
        tx = Transaction.get()
        state['events'].append({
            'label': self.get_trigger_sobj().get_code(), 'event': self.get_event(),
            'input': copy.deepcopy(self.get_input()), 'output': copy.deepcopy(self.get_output()),
            'shared': self.get_input() is self.get_output(),
            'caller': self.get_caller().__class__.__name__, 'description': self.get_description(),
            'active': bool(tx and tx.is_in_transaction()), 'counter': tx.counter if tx else None})
        if data.get('mutate'):
            self.get_output()['added'] = data['mutate']
        if data.get('write'):
            tx.set_record(False)
            sql = Search('contract/entity').get_sql()
            sql.do_update("UPDATE entity SET name='trigger write' WHERE code='A'")
        if data.get('fail'):
            raise ValueError('trigger failed')
        if data.get('recursive'):
            Trigger.call(self.get_caller(), self.get_event(), self.get_input())
        return data.get('result')


RecordedTrigger.__module__ = 'tactic_stream_trigger_probe'


class RecordedHandler:
    """The client Handler protocol, without depending on either client package."""
    def __init__(self):
        self.input = self.output = None
        self.event = self.description = ''
        self.ret_val = None

    def set_event(self, value): self.event = value
    def get_event(self): return self.event
    def set_input(self, value): self.input = value
    def get_input(self): return self.input
    def set_output(self, value): self.output = value.copy()
    def get_output(self): return self.output
    def set_description(self, value): self.description = value
    def get_description(self): return self.description
    def get_title(self): return 'RecordedHandler'
    def set_ret_val(self, value): self.ret_val = value
    def get_ret_val(self): return self.ret_val

    def execute(self):
        tx = Transaction.get()
        Container.get('TriggerProbe:state')['events'].append({
            'handler': True, 'event': self.event, 'input': copy.deepcopy(self.input),
            'output': copy.deepcopy(self.output), 'shared': self.input is self.output,
            'active': bool(tx and tx.is_in_transaction()), 'counter': tx.counter if tx else None})
        return False


RecordedHandler.__module__ = 'tactic_stream_trigger_probe'


class ProbeValue:
    def __init__(self, value=1, **kwargs):
        self.value, self.kwargs = value, kwargs


def run_trigger_case(case):
    if case.get('caller_write'):
        from pyasm.search import DbContainer, DbResource
        DbContainer.close_thread_sql()
        DbContainer.close_all()
        Container.remove(Transaction.KEY)
        DbContainer.get(DbResource.get_default('one')).do_update("UPDATE entity SET name='Первый' WHERE code='A'")
    # Load the SObject before establishing the controlled registries. The
    # original SearchType registers unrelated Task/GlobalSearch/Folder handlers
    # on first access; their persistence is outside this dispatch comparison.
    sobject = Search.get_by_code('contract/entity', 'A') if case.get('operation') == 'sobject_events' else None
    old_static, old_integral = Trigger.STATIC_TRIGGERS, Trigger.INTEGRAL_TRIGGERS
    Trigger.STATIC_TRIGGERS, Trigger.INTEGRAL_TRIGGERS = [], []
    Container.remove(Trigger.STATIC_TRIGGER_KEY)
    Container.remove(Trigger.INTEGRAL_TRIGGER_KEY)
    state = {'events': []}
    Container.put('TriggerProbe:state', state)
    try:
        if case.get('operation') == 'script':
            # Import the same file; do not rewrite its source/imports for either runtime.
            scripts = str(Path(__file__).resolve().parents[1] / 'tests/scripts')
            sys.path.insert(0, scripts)
            try:
                import trigger_contract
                return trigger_contract.run(case['mode'], case.get('fail', False))
            finally:
                sys.path.remove(scripts)
        if case.get('operation') == 'lookup_cache':
            lookup = getattr(Search, case['lookup'])
            first = lookup('contract/entity', case['identity'], case.get('first_retired', True))
            if first is not None:
                first.set_value('name', 'pending script value')
            second = lookup('contract/entity', case['identity'], case.get('second_retired', True))
            return {'same': first is second, 'first': None if first is None else first.get_value('name'),
                    'second': None if second is None else second.get_value('name')}
        for spec in case.get('definitions', []):
            method = Trigger.append_integral_trigger if spec.get('integral') else Trigger.append_static_trigger
            method(Definition(spec), startup=spec.get('startup', False))
        if case.get('operation') == 'common':
            path = 'tactic_stream_trigger_probe.ProbeValue'
            obj = Common.create_from_class_path(path, case.get('args', []), case.get('kwargs', {}))
            return {'parts': Common.breakup_class_path(path), 'value': obj.value, 'kwargs': obj.kwargs}

        def invoke():
            operation = case.get('operation', 'call')
            if operation == 'sobject_events':
                sobject._call_triggers(case.get('updates', {}), case.get('mode', 'update'),
                                   case.get('output', {}), case.get('process'), case.get('parent_type'),
                                   case.get('triggers', True))
                return
            args, kwargs = case.get('args', []), case.get('kwargs', {})
            if operation == 'call':
                return Trigger.call(caller, case.get('event', 'changed'), case.get('output', {}), **kwargs)
            if operation == 'call_by_key':
                return Trigger.call_by_key(case.get('key', {'event': 'changed'}), caller,
                                           case.get('output', {}), **kwargs)
            if operation == 'handle':
                return Trigger._handle_trigger_sobjs([Definition(spec) for spec in case['handlers']], caller,
                                                     'changed', case.get('output', {}), **kwargs)
            return getattr(Trigger, operation)(*args, **kwargs)

        class Caller(Command):
            def execute(self):
                self.info = {'from_caller': True}
                if case.get('caller_write'):
                    self.get_transaction().set_record(False)
                    Search('contract/entity').get_sql().do_update("UPDATE entity SET name='caller write' WHERE code='A'")
                capture()
                if case.get('caller_fail'):
                    raise ValueError('caller failed')
                return {'caller_result': True}

        caller = Caller()

        def capture():
            result = invoke()
            if case.get('operation') in ('_get_triggers', 'get_by_event', 'get_db_triggers', 'get_notifications_by_event'):
                state['result'] = [obj.get_code() for obj in result]
            elif result is not None:
                state['result'] = [{'event': trigger.get_event(), 'ret_val': trigger.get_ret_val(),
                                    'input': copy.deepcopy(trigger.get_input()), 'output': copy.deepcopy(trigger.get_output())}
                                   for trigger in result]
            else:
                state['result'] = None
            state['queue_before'] = len(Container.get_seq('Trigger:called_triggers'))

        try:
            if case.get('command'):
                state['command_result'] = Command.execute_cmd(caller)
            else:
                capture()
                if case.get('flush'):
                    Trigger.call_all_triggers()
        except Exception as exc:
            state['error'] = {'type': type(exc).__name__, 'message': str(exc)}
        state['caller_errors'] = caller.get_errors()
        state['queue_after'] = len(Container.get_seq('Trigger:called_triggers'))
        if case.get('inspect_value'):
            state['value'] = Search.get_by_code('contract/entity', 'A').get_value('name')
        if case.get('cache_steps'):
            state['cache_steps'] = []
            for step in case['cache_steps']:
                operation, args = step[0], step[1:]
                if operation == 'append_static':
                    Trigger.append_static_trigger(Definition(args[0]))
                    value = None
                else:
                    value = getattr(Trigger, operation)(*args)
                    if isinstance(value, list):
                        value = [obj.get_code() for obj in value]
                state['cache_steps'].append(value)
        return state
    finally:
        Trigger.STATIC_TRIGGERS, Trigger.INTEGRAL_TRIGGERS = old_static, old_integral
