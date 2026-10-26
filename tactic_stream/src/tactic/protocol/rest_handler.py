# Copyright (c) 2005-2012, Southpaw Technology. See LICENSE.TACTIC.
"""Original REST dispatch adapted to the authenticated native API, without eval."""
import json
import re

from pyasm.common import Container, Environment
from tactic.ui.common import BaseRefreshWdg


class BaseRestHandler(BaseRefreshWdg):
    def authenticate(self):
        raise NotImplementedError('Must override authenticate')

    def get_display(self):
        method = self.kwargs.get('Method')
        if method not in ('GET', 'POST', 'PUT', 'DELETE'):
            raise ValueError('Unsupported REST method')
        return getattr(self, method)()

    def GET(self):
        pass

    def POST(self):
        return self.GET()

    def PUT(self):
        pass

    def DELETE(self):
        pass


class APIRestHandler(BaseRestHandler):
    def get_content_type(self):
        return 'application/json'

    def get_body(self):
        return Container.get('REST:body')

    def GET(self):
        return 'TACTIC REST Interface'

    def POST(self):
        from tactic_client_lib import TacticServerStub
        from tactic_stream.server.api import SUPPORTED_METHODS
        body = self.get_body() or {}
        if not isinstance(body, dict):
            raise ValueError('REST API body must be an object')
        values = dict(self.kwargs, **body)
        method = values.get('method', '')
        if not isinstance(method, str) or not re.fullmatch(r'[A-Za-z]\w*', method) or method not in SUPPORTED_METHODS:
            raise ValueError('Choose a public TACTIC API method')
        security = Environment.get_security()
        if method == 'get_ticket':
            return security.get_ticket_key()
        if method == 'get_ticket_data':
            ticket = security.get_ticket()
            return ticket.get_value('data') if ticket else None
        args, kwargs = values.get('args', []), values.get('kwargs', {})
        if isinstance(args, str):
            args = json.loads(args)
        if isinstance(kwargs, str):
            kwargs = json.loads(kwargs)
        if not isinstance(args, list) or not isinstance(kwargs, dict):
            raise ValueError('Invalid REST API arguments')
        if 'args' not in values and 'kwargs' not in values:
            kwargs = {key: value for key, value in values.items()
                      if key not in ('method', 'Method', 'Accept', 'login_ticket', 'ticket', 'password', 'domain')}
        return getattr(TacticServerStub.get(protocol='local'), method)(*args, **kwargs)
