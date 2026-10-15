"""Unchanged local SDK reads and scalar conversion in both TACTIC runtimes."""
from datetime import datetime
from decimal import Decimal

from pyasm.common import Environment
from pyasm.web.api_xmlrpc import ApiXMLRPC
from pyasm.search import Search, SearchType, SObject
from pyasm.security import Security
from tactic_client_lib import TacticServerStub


def run(case):
    previous = Environment.get_security()
    if previous is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    try:
        api = ApiXMLRPC()
        api.set_protocol('local')
        ticket = dict(project='admin', language='python')
        if case.get('base_dirs'):
            from pyasm.common import Config
            Config.set_value('checkin', 'asset_base_dir', {'default': 'X:/repo', 'archive': '/mnt/archive'})
            Config.set_value('checkin', 'web_base_dir', '/media')
            Config.set_value('checkin', 'win32_client_repo_dir', 'Z:/client')
            return api.get_base_dirs(ticket)
        client = TacticServerStub(setup=False, protocol='local')
        client.server = api
        client.ticket = ticket
        options = dict(filters=[('code', 'admin')], order_bys=['id asc'])
        objects = client.query('sthpw/project', return_sobjects=True, **options)
        obj = client.query('sthpw/project', single=True, return_sobjects=True, **options)
        data = client.query('sthpw/project', **options)
        draft = SearchType.create('sthpw/file')
        draft.set_value('id', 37)
        draft.set_value('code', 'DICT_FILE')
        draft.set_value('timestamp', datetime(2026, 10, 6, 12, 34, 56, 123456))
        draft.set_value('size', Decimal('12345678901234567890.123456789'))
        draft.set_value('metadata', '{"name":"Тест","flag":false}')
        converted = api._get_sobject_dict(draft)
        if case.get('fixes'):
            projected = api._get_sobjects_dict([None, obj, draft], columns=['code'], use_id=True)
            return dict(projected=projected, unchanged='__search_key__' not in draft.get_data())
        return dict(native=isinstance(obj, SObject) and all(isinstance(item, SObject) for item in objects),
                    raw=isinstance(data, list), code=obj.get_code(),
                    missing=client.query('sthpw/project', filters=[('code', 'NO_SUCH_PROJECT')],
                                      single=True, return_sobjects=True),
                    many=[item['code'] for item in api._get_sobjects_dict(objects)],
                    empty=[api._get_sobject_dict(None), api._get_sobjects_dict([])],
                    public=api.get_sobject_dict(obj)['code'],
                    timestamp=converted['timestamp'], size=converted['size'], metadata=converted['metadata'],
                    key=converted['__search_key__'], type=converted['__search_type__'])
    finally:
        Environment.set_security(previous)
