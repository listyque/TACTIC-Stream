"""Configured REST execution through authenticated API/Command boundaries."""
from pyasm.command import Command
from pyasm.common import Common, Container, Environment
from pyasm.common.errors import SecurityException
from tactic_stream.server.custom_urls import read_custom_url, resolve_custom_url


class CustomUrlCmd(Command):
    def execute(self):
        if self.kwargs.get('action') == 'resolve':
            self.info = resolve_custom_url(self.kwargs.get('path'), self.kwargs.get('parameters'))
            return self.info
        definition = read_custom_url(self.kwargs.get('path'), self.kwargs.get('parameters'))
        handler, configured = definition['handler'], definition['options']
        builtins = ('tactic.protocol.PythonRestHandler', 'tactic.protocol.python_rest_handler.PythonRestHandler',
                    'tactic.protocol.APIRestHandler', 'tactic.protocol.rest_handler.APIRestHandler')
        if handler not in builtins and not Environment.get_security().is_admin():
            raise SecurityException('Custom REST class execution requires administrator access')
        from tactic.protocol import BaseRestHandler, PythonRestHandler
        implementation = Common.resolve_class(handler)
        if not isinstance(implementation, type) or not issubclass(implementation, (BaseRestHandler, PythonRestHandler)):
            raise ValueError('This custom URL is a page, not a REST handler')
        arguments = dict(definition['parameters'], **configured)
        if issubclass(implementation, PythonRestHandler):
            if not configured.get('script_path'):
                raise ValueError('Python REST requires a configured script_path')
        method = self.kwargs.get('method')
        if method not in ('GET', 'POST', 'PUT', 'DELETE'):
            raise ValueError('Unsupported REST method')
        arguments.update(Method=method, Accept=self.kwargs.get('accept', 'application/json'))
        from pyasm.web import Web, WebContainer
        WebContainer.set_web(Web(arguments))
        Container.put('REST:body', self.kwargs.get('body'))
        self.info = implementation(**arguments).get_display()
        return self.info
