"""ProjectSetting and SObject cache/code calls shared by both real runtimes."""
import copy
from unittest.mock import patch


def run_settings_case(case):
    from pyasm.biz import ProjectSetting, ProdSetting
    from pyasm.search import SObject, Search
    owner = ProdSetting if case.get('alias') else ProjectSetting
    # Measure this script's cache effects, excluding Batch's temporary login ticket.
    owner.get_cache_dict().clear()
    obj = SObject(case.get('search_type', 'contract/entity'))
    outputs, previous = [], None
    def encode(value):
        if isinstance(value, SObject):
            return {'class': type(value).__name__, 'data': value.get_data()}
        if isinstance(value, dict):
            return {key: encode(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [encode(item) for item in value]
        return value
    for step in case['steps']:
        target = obj if step.get('object') else owner
        try:
            if step['method'] == 'set_cached_value':
                previous.set_value('value', step['args'][0])
                result = None
            elif step['method'] == 'get_by_search':
                search = Search(owner.SEARCH_TYPE)
                search.add_filter('key', step['args'][0])
                result = owner.get_by_search(search, step.get('cache_key', 'probe'), is_multi=step.get('is_multi', False))
            else:
                with patch('os.urandom', lambda n: bytes(range(n))):
                    result = getattr(target, step['method'])(*step.get('args', []), **step.get('kwargs', {}))
            output = {'value': encode(result)}
            if isinstance(result, SObject):
                output['same_as_previous'] = result is previous
                previous = result
        except Exception as exc:
            output = {'error': type(exc).__name__, 'message': str(exc)}
        output['cache'] = encode(owner.get_cache_dict())
        outputs.append(copy.deepcopy(output))
    return outputs
