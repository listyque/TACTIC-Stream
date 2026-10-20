"""Configured record actions retain optimistic revisions inside native commands."""
from pyasm.command import Command


def object_status_request(search_key, action, expected_revision):
    import hashlib
    import json
    from pyasm.search import Search
    if action not in ('retire', 'reactivate'):
        raise ValueError('Invalid object action')
    obj = Search.get_by_search_key(search_key)
    if obj is None:
        raise LookupError('Object is no longer available')
    sql = obj.get_sql()
    lock = getattr(sql.get_database_impl(), 'lock_collection_table', None)
    if lock:
        lock(sql, obj.get_table())
    elif sql.get_database_type() == 'PostgreSQL':
        sql.do_update('LOCK TABLE "%s" IN EXCLUSIVE MODE' % obj.get_table().replace('"', '""'))
    else:
        raise ValueError('Object revisions require a transactional database lock')
    obj = Search.get_by_search_key(search_key)
    revision = hashlib.sha256(json.dumps(obj.get_data(), sort_keys=True, default=str).encode()).hexdigest()
    if revision != expected_revision:
        raise ValueError('Object changed. Reload before saving.')
    if action == 'retire':
        obj.retire()
    else:
        obj.reactivate()
    return {'search_key': search_key}


class TableObjectStatusCmd(Command):
    def execute(self):
        self.info = object_status_request(**self.kwargs)
        return self.info
