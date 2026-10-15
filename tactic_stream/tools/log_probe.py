"""Journal objects, XML values and change_timestamp staging in both runtimes."""
import copy
import json


def run_log_case(case):
    from pyasm.common import Common, Container, Xml
    from pyasm.search import TransactionLog, SObjectLog, RetireLog, Search, SObject, Transaction
    owners = {'transaction': TransactionLog, 'sobject': SObjectLog, 'retire': RetireLog}
    owner = owners.get(case.get('owner'), TransactionLog)
    previous = xml_previous = None
    transaction = Transaction()
    transaction.start()
    obj = None
    if 'xml_value' in case:
        obj = Search.get_by_code('contract/entity', 'A')
        if case['xml_value'] is None:
            obj.set_data({**obj.get_data(), 'metadata': None})
        else:
            obj.set_value('metadata', case['xml_value'])
    outputs = []
    def encode(value):
        if isinstance(value, SObject):
            return {'class': type(value).__name__, 'data': value.get_data(),
                    'stored': value.get_data(False), 'pending': value.update_data,
                    'quoted': value.quoted_flag, 'has_updates': value.has_updates}
        if isinstance(value, Xml):
            return {'xml': value.to_string(), 'values': value.get_values('transaction/column')}
        if isinstance(value, dict):
            return {key: encode(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [encode(item) for item in value]
        return value
    for step in case['steps']:
        method, args, kwargs = step['method'], step.get('args', []), step.get('kwargs', {})
        try:
            if method == 'get_change_timestamp':
                value = transaction.get_change_timestamp(*args, **kwargs)
            elif method == 'set_cached_json':
                previous.set_json_value(*args)
                value = None
            elif method == 'reset_transaction':
                transaction.rollback()
                transaction.start()
                value = None
            elif method == 'retire_by_entity':
                value = RetireLog.get_all_by_sobject(Search.get_by_code('contract/entity', args[0]))
            elif method == 'get_xml_value':
                value = obj.get_xml_value('metadata', **kwargs)
            elif method == 'change_xml_value':
                obj.set_value('metadata', args[0])
                value = None
            elif method == 'prefill_xml_cache':
                value = Xml(args[0])
                Container.put('SObject:xml_cache', {obj.get_search_key() + '|metadata': value})
                xml_previous = value
            elif method in ('compress_transaction', 'decompress_transaction'):
                value = getattr(Common, method)(*args)
            elif method == 'code_key':
                value = owner(owner.SEARCH_TYPE).get_code_key()
            elif method in ('trigger_remote_sync', 'trigger_remote_undo'):
                value = getattr(owner.get_by_code(args[0]), method)()
            else:
                value = getattr(owner, method)(*args, **kwargs)
            output = {'value': encode(value)}
            if isinstance(value, SObject):
                output['same_as_previous'] = value is previous
                previous = value
            if isinstance(value, Xml):
                output['same_xml'] = value is xml_previous
                xml_previous = value
        except Exception as exc:
            output = {'error': type(exc).__name__, 'message': str(exc)}
        output['changes'] = encode(transaction.get_change_timestamps())
        output['cache'] = encode(owner.get_cache_dict())
        outputs.append(copy.deepcopy(output))
    transaction.rollback()
    if case.get('compare_compressed_payload'):
        # Python 3.14 uses zlib-ng; compare the uncompressed payload for this case.
        def payload(value):
            if isinstance(value, str) and value.startswith('zlib:'):
                return {'compressed_payload': Common.decompress_transaction(value)}
            if isinstance(value, list):
                return [payload(item) for item in value]
            if isinstance(value, dict):
                return {key: payload(item) for key, item in value.items()}
            return value
        outputs = payload(outputs)
    return json.loads(json.dumps(outputs))
