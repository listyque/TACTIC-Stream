"""An unchanged server script with project-defined SObject classes."""
from pyasm.common import Container
from pyasm.search import Search, SearchType, SObject, SObjectFactory


class CustomRow(SObject):
    SEARCH_TYPE = 'contract/custom'

    def __init__(self, search_type, columns=None, result=None, fast_data=None):
        self.arguments = {
            'type': search_type.__class__.__name__,
            'columns': list(columns) if columns else None,
            'result': list(result) if result else None,
            'fast': bool(fast_data),
            'keys': sorted(fast_data) if fast_data else [],
        }
        super(CustomRow, self).__init__(search_type, columns, result, fast_data=fast_data)

    def label(self):
        return '%s: %s' % (self.get_code(), self.get('name', no_exception=True))


class OldStyleRow(SObject):
    SEARCH_TYPE = 'contract/old_style'

    def __init__(self, search_type, columns=None, result=None):
        self.arguments = {'type': search_type.__class__.__name__, 'columns': list(columns) if columns else None,
                          'result': list(result) if result else None, 'fast': False, 'keys': []}
        super(OldStyleRow, self).__init__(search_type, columns, result)

    def label(self):
        return '%s: %s' % (self.get_code(), self.get('name', no_exception=True))


class RetryRow(CustomRow):
    SEARCH_TYPE = 'contract/retry'

    def __init__(self, search_type, columns=None, result=None, fast_data=None):
        Container.put('RegistryContract:attempts', (Container.get('RegistryContract:attempts') or 0) + 1)
        if fast_data:
            raise ValueError('retry without fast_data')
        super(RetryRow, self).__init__(search_type, columns, result)


def run(case):
    search_type = case['search_type']
    cls = {'contract/custom': CustomRow, 'contract/old_style': OldStyleRow, 'contract/retry': RetryRow}[search_type]
    operation = case.get('operation', 'search')
    if operation in ('create', 'factory'):
        creator = SearchType if operation == 'create' else SObjectFactory
        obj = creator.create(search_type, ['id', 'code', 'name'], [12, 'NEW', 'Custom'])
        rows = [obj]
    else:
        metadata = SearchType.get(search_type)
        search = Search(cls if operation == 'class_search' else metadata if operation == 'metadata_search' else search_type)
        search.add_code_filter(case.get('code', 'A'))
        for column in case.get('columns', []):
            search.add_column(column)
        rows = search.get_sobjects()
    return {'rows': [{'class': row.__class__.__name__, 'arguments': row.arguments,
                      'label': row.label(), 'data': row.get_data(),
                      'metadata_cached': row.search_type_obj is SearchType.get(search_type),
                      'metadata_method': row.get_search_type_obj() is row.search_type_obj,
                      'resource_method': row.get_db_resource() is row.db_resource,
                      'database': row.db_resource.get_database()} for row in rows],
            'attempts': Container.get('RegistryContract:attempts') or 0}
