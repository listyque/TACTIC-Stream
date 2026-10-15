"""Native Pipeline calls shared by the new and original runtimes."""
import copy


def run_pipeline_case(case):
    from pyasm.biz import Pipeline, Process, ProcessConnect, ProjectSetting
    from pyasm.common import Container, Xml
    from pyasm.search import Search, SearchType, SObject

    def encode(value):
        if isinstance(value, Process):
            return {'class': type(value).__name__, 'attrs': value.get_attributes(),
                    'name': value.get_name(), 'full_name': value.get_full_name(),
                    'type': value.get_type(), 'sub': value.is_from_sub_pipeline()}
        if isinstance(value, ProcessConnect):
            return {'class': type(value).__name__, 'attrs': Xml.get_attributes(value.node)}
        if isinstance(value, SObject):
            return {'class': type(value).__name__, 'data': encode(value.get_data()),
                    'stored': encode(value.get_data(merged=False))}
        if hasattr(value, 'tag'):
            return {'tag': value.tag, 'attrs': Xml.get_attributes(value),
                    'value': Xml.get_node_value(value), 'children': encode(Xml.get_children(value))}
        if isinstance(value, Xml):
            return value.to_string()
        if isinstance(value, dict):
            return {key: encode(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [encode(item) for item in value]
        return value

    pipeline = Pipeline.get_by_code(case.get('code', 'GRAPH'))
    entity = SearchType.create('contract/entity') if case.get('entity_new') else Search.get_by_code('contract/entity', case.get('entity_code', 'A'))
    outputs, previous = [], None
    for step in case['steps']:
        try:
            target = pipeline
            if step.get('class'):
                target = Pipeline
            elif step.get('entity'):
                target = entity
            elif step.get('search_type_class'):
                target = SearchType
            if 'process' in step:
                target = pipeline.get_process(step['process'])
            elif 'connect' in step:
                target = pipeline._get_connects()[step['connect']]
            method = step['method']
            if method == 'set_autofill':
                ProjectSetting.get_by_key('autofill_pipeline_code').set_value('value', step['args'][0])
                result = None
            elif method == 'get_by_sobject':
                result = Pipeline.get_by_sobject(entity, **step.get('kwargs', {}))
            elif method == 'project_filter':
                search = Search('sthpw/pipeline')
                search.add_filter('search_type', 'contract/entity')
                search.add_project_filter(*step.get('args', []), **step.get('kwargs', {}))
                result = search.get_sobject_codes()
            elif method == 'reload':
                result = Search.get_by_code('sthpw/pipeline', pipeline.get_code())
                result = {'same_xml': result.get_pipeline_xml() is pipeline.get_pipeline_xml(),
                          'processes': result.get_process_names()}
            else:
                result = getattr(target, method)(*step.get('args', []), **step.get('kwargs', {}))
            output = {'value': encode(result)}
            if isinstance(result, SObject):
                output['same_as_previous'] = result is previous
                previous = result
        except Exception as exc:
            output = {'error': type(exc).__name__, 'message': str(exc)}
        output['pipeline_state'] = {'processes': encode(pipeline.processes),
                                    'recursive': encode(pipeline.recursive_processes)}
        output['entity'] = encode(entity)
        output['cache'] = encode(Pipeline.get_cache_dict())
        output['xml_keys'] = sorted((Container.get('Pipeline:xml') or {}).keys())
        outputs.append(copy.deepcopy(output))
    return outputs
