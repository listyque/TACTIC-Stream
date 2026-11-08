# Copyright (c) 2005, Southpaw Technology. MIT; see LICENSE.TACTIC.
"""Native API command identity; transports live in tactic_stream.server.api."""
from pyasm.command import Command
import json


# From get_simple_cmd in the original module. Native workers write each block
# atomically through logging; only the print destination/context are adapted.
def print_primary_info(request_id, now, user, meth, args, output):
    print("request_id: %s" % request_id, file=output)
    print("timestamp: %s" % now.strftime("%Y-%m-%d %H:%M:%S"), file=output)
    print("user: %s" % user, file=output)
    print("simple method: %s" % meth, file=output)
    # This is the original Common.pretty_print body, with the same destination.
    print(json.dumps(args, indent=2), file=output)
    print(file=output)


def print_secondary_info(duration, request_id, rss, increment, output):
    print("Duration: %0.3f seconds (request_id: %s)" % (duration, request_id), file=output)
    print("Memory: %s KB" % rss, file=output)
    print("Increment: %s KB" % increment, file=output)


class ApiException(Exception):
    """Original API error identity; failed native Commands persist ExceptionLog."""


class ApiClientCmd(Command):
    def get_title(self):
        return 'Client API'

    def postprocess(self):
        if not hasattr(self, 'api'):
            return
        # Native get_full_cmd transfers API state separately from its wire result.
        self.sobjects = self.api.get_sobjects()
        self.info = dict(self.api.get_info())
        self.info.update(function_name=self.function_name, args=self.arguments)



class ApiXMLRPC:
    """Selected local SDK calls share the caller's request and transaction."""

    def __init__(self):
        from pyasm.search.search import _context
        from tactic_stream.server.api import Api
        self.context = _context.get()
        self.api = Api(self.context.store)
        self.api.protocol = 'local'

    def set_protocol(self, protocol):
        from pyasm.common.errors import UnsupportedContract
        if protocol != 'local':
            raise UnsupportedContract('ApiXMLRPC supports the local protocol only')

    def get_sobject_dict(self, sobject, columns=None, use_id=False):
        if not sobject:
            return {}
        return self._get_sobjects_dict([sobject], columns, use_id)[0]

    _get_sobject_dict = get_sobject_dict

    def _get_sobjects(self, search_keys, no_exception=False):
        from tactic_stream.server.api import check_record_access
        from pyasm.search import SearchKey
        from pyasm.search.search import _context
        from pyasm.common import Environment
        from pyasm.common.errors import SecurityException, UnsupportedContract
        context = _context.get()
        if (context.container is not self.context.container or context.store is not self.context.store or
                context.login != self.context.login):
            raise UnsupportedContract('A local SDK connection cannot outlive its request context')
        if Environment.get_security() is None:
            raise SecurityException('Local API requires authenticated security')
        self.api.check_method_access('query')
        # Original ApiXMLRPC._get_sobjects: order and duplicates are significant;
        # no_exception discards the entire result if any object is missing.
        if not search_keys:
            raise ApiException("Search key [%s] is None" % search_keys)
        if not isinstance(search_keys, list):
            search_keys = [search_keys]
        sobjects = []
        for search_key in search_keys:
            if isinstance(search_key, dict):
                search_key = search_key.get('__search_key__')
                if not search_key:
                    raise ApiException("Not a valid search key [%s]" % search_key)
            while '&amp;' in search_key:
                search_key = search_key.replace('&amp;', '&')
            check_record_access(search_key.split('?', 1)[0].split('|', 1)[0])
            sobject = SearchKey.get_by_search_key(search_key)
            if not sobject:
                if no_exception:
                    return []
                raise ApiException("SObject [%s] does not exist" % search_key)
            sobjects.append(sobject)
        return sobjects

    def _get_sobjects_dict(self, sobjects, columns=None, use_id=False):
        from pyasm.search.search import _context
        from pyasm.common import Environment
        from pyasm.common.errors import SecurityException, UnsupportedContract
        context = _context.get()
        if (context.container is not self.context.container or context.store is not self.context.store or
                context.login != self.context.login):
            raise UnsupportedContract('A local SDK connection cannot outlive its request context')
        if Environment.get_security() is None:
            raise SecurityException('Local API requires authenticated security')
        self.api.check_method_access('query')
        return self.api._get_sobjects_dict(sobjects, columns, use_id)

    def __getattr__(self, name):
        from tactic_stream.server.api import SUPPORTED_METHODS
        from pyasm.common.errors import SecurityException, UnsupportedContract
        if name not in SUPPORTED_METHODS or name in ('get_ticket', 'get_ticket_data'):
            raise UnsupportedContract("Local TACTIC method '%s' has not been migrated yet" % name)
        function = getattr(self.api, name)
        def call(*args, **kwargs):
            from pyasm.search.search import _context
            from pyasm.common import Container, Environment
            import inspect
            context = _context.get()
            if (context.container is not self.context.container or context.store is not self.context.store or
                    context.login != self.context.login):
                raise UnsupportedContract('A local SDK connection cannot outlive its request context')
            if Environment.get_security() is None:
                raise SecurityException('Local API requires authenticated security')
            signature = self.api._signatures.get(name)
            if signature is None:
                signature = inspect.signature(function)
                self.api._signatures[name] = signature
            arguments = signature.bind(*args, **kwargs)
            if 'ticket' in signature.parameters:
                ticket = arguments.arguments['ticket']
                if not isinstance(ticket, dict) or ticket.get('project') != context.project or ticket.get('site') or ticket.get('language', 'python') != 'python':
                    raise UnsupportedContract('Local API must use the current project and Python context')
            self.api.check_method_access(name, command=arguments.arguments.get('class_name'))
            checkin = self.api.checkin_write_scope(name, arguments.arguments)
            previous = Container.get('Checkin:writing')
            if checkin is not None:
                Container.put('Checkin:writing', checkin)
            try:
                return function(*args, **kwargs)
            finally:
                if checkin is not None:
                    Container.put('Checkin:writing', previous)
        return call
