"""Original 4.0 parent search_id -> search_code repair, callable in-process.

Existing search_code values are never overwritten. A missing/ambiguous parent
is an actionable migration failure, not a successful update with an empty code.
"""
def fix_search_code(search_types=None, verbose=False, strict=False):
    from pyasm.search import Search, SearchType
    search_types = search_types or ['sthpw/task', 'sthpw/snapshot', 'sthpw/file',
                                   'sthpw/note', 'sthpw/work_hour', 'sthpw/sobject_list']
    report = {'updated': 0, 'preserved': 0, 'without_parent': 0, 'unresolved': []}
    for search_type in search_types:
        search = Search(search_type)
        search.set_show_retired(True)
        for obj in search.get_sobjects():
            current = obj.get_value('search_code', no_exception=True)
            if current:
                report['preserved'] += 1
                continue
            parent_type = obj.get_value('search_type', no_exception=True)
            parent_id = obj.get_value('search_id', no_exception=True)
            if not parent_type or parent_id in (None, '', -1, '-1'):
                report['without_parent'] += 1
                continue
            try:
                parent = Search.get_by_id(parent_type, parent_id)
                code = parent.get_value('code', no_exception=True) if parent else None
                if not code:
                    raise ValueError('Parent is missing or has no code')
                obj.set_value('search_code', code)
                obj.commit(triggers=False)
                report['updated'] += 1
            except Exception as exc:
                report['unresolved'].append({'key': obj.get_search_key(), 'parent_type': parent_type,
                                             'parent_id': str(parent_id), 'error': str(exc)})
    if verbose:
        print('Search-code repair:', report['updated'], 'filled,', report['preserved'], 'preserved,',
              len(report['unresolved']), 'unresolved')
    if strict and report['unresolved']:
        raise RuntimeError('Search-code migration has unresolved parents: ' + str(report['unresolved'][:20]))
    return report
