# Copyright (c) 2015, Southpaw Technology. MIT; see LICENSE.TACTIC.
"""Native synchronous JS/API bridge, using QuickJS-NG instead of obsolete PyV8."""
from importlib.resources import files
import logging
import inspect
import quickjs
from pyasm.common import Container, jsondumps, jsonloads


class ApiDelegator:
    def execute(self, func_name, args='[]', kwargs='{}'):
        from tactic_stream.server.api import SUPPORTED_METHODS
        from tactic_client_lib import TacticServerStub
        if func_name not in SUPPORTED_METHODS or func_name in ('get_ticket', 'get_ticket_data'):
            raise ValueError('Unsupported local JavaScript API method: ' + str(func_name))
        args = jsonloads(args) if args else []
        kwargs = jsonloads(kwargs) if kwargs else {}
        if not isinstance(args, list) or not isinstance(kwargs, dict):
            raise ValueError('JavaScript API arguments must be an array and an object')
        server = TacticServerStub.get(protocol='local')
        function = getattr(server.server, func_name)
        if 'ticket' in inspect.signature(getattr(server.server.api, func_name)).parameters:
            args.insert(0, server.ticket)
        # JS query/eval methods decode JSON themselves; retain the wire result.
        return jsondumps(function(*args, **kwargs))


class JsWrapper:
    def __init__(self):
        self.ctx = quickjs.Context()
        self.delegator = ApiDelegator()
        self.ctx.add_callable('__tactic_api', self._delegate)
        self.ctx.add_callable('__tactic_console', lambda message: logging.getLogger('tactic.script.js').info('%s', message))
        self.ctx.eval('''
            var spt = {browser: {is_IE: function() {return false;}}};
            spt.error = function(error) {throw error;};
            spt.exception = {handler: function(error) {return error;}};
            // Native client error handlers must fail a server command, not show a browser alert.
            function alert(error) {throw error;}
            var console = {log: function() {
                __tactic_console(Array.from(arguments).map(String).join(' '));
            }};
        ''')
        for name in ('environment', 'client_api'):
            self.ctx.eval((files('pyasm.common') / ('js/' + name + '.js')).read_text(encoding='utf-8'))
        self.ctx.eval('''
            spt._delegate = function(func_name, args, kwargs, ret_type) {
                var positional = Array.from(args || []);
                // JS helpers append kwargs, including an undefined placeholder.
                if (positional.length && (positional[positional.length - 1] === undefined ||
                    kwargs && positional[positional.length - 1] === kwargs)) {
                    positional.pop();
                }
                var reply = JSON.parse(__tactic_api(func_name,
                    JSON.stringify(positional), JSON.stringify(kwargs || {})));
                if (!reply.ok) {throw new Error(reply.error);}
                if (ret_type === 'string' && typeof reply.value !== 'string') {
                    return JSON.stringify(reply.value);
                }
                return reply.value;
            };
            // Server scripts have no document, cookies or HTTP transport.
            var server = new TacticServerStub();
            TacticServerStub.servers.default = server;
        ''')
        from pyasm.biz import Project
        self.ctx.eval('server.set_project(' + jsondumps(Project.get_project_code()) + ')')

    def _delegate(self, method, args, kwargs):
        try:
            result = self.delegator.execute(method, args, kwargs)
            return '{"ok":true,"value":' + result + '}'
        except Exception as error:
            return jsondumps({'ok': False, 'error': type(error).__name__ + ': ' + str(error)})

    @staticmethod
    def get():
        wrapper = Container.get('JsWrapper')
        if wrapper is None:
            wrapper = JsWrapper()
            Container.put('JsWrapper', wrapper)
        return wrapper

    def execute(self, js, kwargs=None):
        if not isinstance(js, str):
            raise ValueError('JavaScript source must be a string')
        for name, value in (kwargs or {}).items():
            self.ctx.eval('globalThis[' + jsondumps(name) + '] = ' + jsondumps(value))
        return self.ctx.eval(js)

    def execute_func(self, js, kwargs=None):
        value = self.execute('''JSON.stringify((function() {
            var result = (function() {
''' + js + '''
            })();
            if (result && typeof result.then === 'function') {
                throw new Error('Server JavaScript execution is synchronous; Promise results are unsupported');
            }
            return result;
        })())''', kwargs)
        return jsonloads(value) if value is not None else None
