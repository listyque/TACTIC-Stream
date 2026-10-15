"""Identical REST calls in the original TACTIC and Stream runtime."""
from pyasm.common import Environment
from pyasm.command import Command
from pyasm.web.api_xmlrpc import ApiXMLRPC
from pyasm.search import Search
from pyasm.security import Security


def run(case):
    previous = Environment.get_security()
    if previous is None:
        security = Security()
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
        Environment.set_security(security)
    try:
        def execute():
            api = ApiXMLRPC()
            api.set_protocol('local')
            try:
                rest = case['rest']
                return api.send_rest_request(dict(project='one'), rest['method'], rest['url'], rest['params'])
            except ValueError as error:
                return dict(error=type(error).__name__)
        cmd = Command()
        cmd.get_transaction().set_sync(False)
        cmd.execute = execute
        return Command.execute_cmd(cmd)
    finally:
        Environment.set_security(previous)
