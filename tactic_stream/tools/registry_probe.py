"""Run original registration and unchanged project code in both private kernels."""
from pathlib import Path
import sys

from pyasm.common import Common, Container
from pyasm.command import Trigger
from pyasm.biz import Snapshot
from pyasm.search import Search, SearchType, SObject


def definition(row):
    return {'event': row.get_value('event'), 'class': row.get_value('class_name'),
            'mode': row.get_value('mode'), 'data': row.get_data(),
            'quoted': row.quoted_flag, 'updates': row.has_updates}


def run_registry_case(case):
    old_static, old_integral = Trigger.STATIC_TRIGGERS, Trigger.INTEGRAL_TRIGGERS
    old_snapshot = Snapshot.integral_trigger_added
    Trigger.STATIC_TRIGGERS, Trigger.INTEGRAL_TRIGGERS = [], []
    Snapshot.integral_trigger_added = False
    for key in (Trigger.STATIC_TRIGGER_KEY, Trigger.INTEGRAL_TRIGGER_KEY,
                Trigger.STATIC_TRIGGER_COUNT, 'SearchType::triggers'):
        Container.remove(key)
    try:
        operation = case.get('operation')
        if operation == 'script':
            scripts = str(Path(__file__).resolve().parents[1] / 'tests/scripts')
            sys.path.insert(0, scripts)
            try:
                import registry_contract
                options = dict(case)
                options['operation'] = case.get('script_operation', 'search')
                return registry_contract.run(options)
            finally:
                sys.path.remove(scripts)
        if operation == 'keywords':
            from tactic.command import GlobalSearchTrigger
            value = case['value']
            return {'extract': Common.extract_keywords(value, lower=case.get('lower', True)),
                    'cleanup': GlobalSearchTrigger().cleanup(value),
                    'path': Common.extract_keywords_from_path(case.get('path', ''))}
        if operation == 'exceptions':
            import pyasm.common.common_exception as errors
            names = list(errors.__all__) + ['CodeException']
            result = {}
            for name in names:
                cls = getattr(errors, name)
                error = cls('label', 'message', 'type') if name == 'TacticWarning' else cls('message')
                result[name] = {'bases': [base.__name__ for base in cls.__bases__],
                                'args': error.args, 'str': str(error),
                                'title': error.get_title() if hasattr(error, 'get_title') else getattr(error, 'TITLE', None)}
                if name == 'TacticWarning':
                    result[name]['warning'] = [error.get_label(), error.get_msg(), error.get_type()]
            return result
        if operation == 'noop':
            from tactic.command import FolderTrigger, LoginGroupTrigger, TaskCreatorTrigger
            trigger = {'folder': FolderTrigger, 'login_group': LoginGroupTrigger, 'task_creator': TaskCreatorTrigger}[case['handler']]()
            trigger.set_input(case.get('input', {}))
            if case.get('caller'):
                trigger.set_caller(SearchType.create('contract/entity'))
            return {'result': trigger.execute(), 'ret': trigger.get_ret_val()}
        if operation == 'automatic_insert':
            caller = Search.get_by_code('contract/entity', 'A')
            output = {'search_key': caller.get_search_key(), 'mode': 'insert', 'update_data': {}}
            called = Trigger.call(caller, 'insert|contract/entity', output)
            return {'result': [{'class': Common.get_full_class_name(trigger), 'event': trigger.get_event(),
                                'input': trigger.get_input(), 'ret': trigger.get_ret_val()} for trigger in called],
                    'errors': caller.errors,
                    'definitions': [definition(row) for row in Trigger.get_static_triggers()]}
        states = []
        measured_types = {key.split('?')[0] for key in case.get('types', [])} | {'sthpw/trigger'}
        for key in case.get('types', []):
            if operation == 'search':
                Search(key)
            elif operation == 'create':
                SearchType.create(key)
            elif operation == 'direct':
                SObject(key)
            else:
                SearchType.get(key, no_exception=case.get('no_exception', False))
            states.append({'static': [definition(row) for row in Trigger.get_static_triggers()],
                           'integral': [definition(row) for row in Trigger.get_integral_triggers()],
                           # Measure requested types; legacy ACL lookups also touch
                           # unrelated Project metadata with no registered handlers.
                           'flags': {key: value for key, value in (Container.get('SearchType::triggers') or {}).items()
                                     if key in measured_types},
                           'count': Container.get(Trigger.STATIC_TRIGGER_COUNT)})
        return states
    finally:
        Trigger.STATIC_TRIGGERS, Trigger.INTEGRAL_TRIGGERS = old_static, old_integral
        Snapshot.integral_trigger_added = old_snapshot
