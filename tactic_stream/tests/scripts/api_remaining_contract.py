"""The same original API bodies, command keys and palette calls in both kernels."""
from pyasm.command import Command
from pyasm.common import Container, Environment
from pyasm.search import Search, SearchType
from pyasm.web import WebContainer, HtmlElement


class KeyCmd(Command):
    def requires_key(self):
        return True

    def preprocess(self):
        Container.append_seq('api9.hooks', 'preprocess')

    def execute(self):
        if self.kwargs.get('write'):
            row = SearchType.create('sthpw/note')
            row.set_value('note', self.kwargs['write'])
            row.commit()
        if self.kwargs.get('fail'):
            raise ValueError('api9 late command failure')
        self.info = dict(value=self.kwargs.get('value'),
                         form=WebContainer.get_web().get_form_value('value'),
                         hooks=list(Container.get_seq('api9.hooks')))


def call(api, name, *args, **kwargs):
    function = getattr(api, name)
    if function.__closure__:
        closure = dict(zip(function.__code__.co_freevars,
                           (cell.cell_contents for cell in function.__closure__)))
        function = closure['meth']
        return function(api, None, *args, **kwargs)
    return function(None, *args, **kwargs)


def run(case, api):
    try:
        from pyasm.web import Web
        web = Web()
    except ImportError:
        from pyasm.web.cherrypy30_adapter import CherryPyAdapter
        from types import SimpleNamespace
        web = CherryPyAdapter.__new__(CherryPyAdapter)
        web.request = SimpleNamespace(params={}, wsgi_environ={})
    # Supply only a request adapter; keep the original Batch/Command environment.
    Container.put('WebContainer::web', web)
    if case.get('palette'):
        from pyasm.biz import ExpressionParser
        parser = ExpressionParser()
        return [parser.eval(expression) for expression in (
            '@COLOR(color)', '@COLOR(#123456,10)', '@PALETTE(DARK)',
            '@GRADIENT(background,5,-10)', '@COLOR(missing)')]
    command = Command()

    def execute():
        command.get_transaction().set_sync(False)
        if case.get('info'):
            row = call(api, 'insert', 'contract/entity', {'code': 'API9_INFO', 'name': 'Created'},
                       info={'label': 'Создание', 'nested': {'flag': False}})
            first = dict(api.get_info())
            first_objects = [obj.get_code() for obj in api.get_sobjects()]
            result = call(api, 'update', [row['__search_key__'], 'contract/entity?project=one&code=A'],
                          [{'name': 'Updated'}, {'name': 'Other'}], info={'phase': 2})
            return dict(first=first, first_objects=first_objects, info=api.get_info(),
                        objects=[obj.get_code() for obj in api.get_sobjects()],
                        names=[record['name'] for record in result])
        key = HtmlElement('div').generate_command_key('api_remaining_contract.KeyCmd', {'value': 'Bound'})
        result = call(api, 'execute_cmd', key, {'value': 'Unbound'}, {'value': 'Form'},
                      use_transaction=case.get('use_transaction', True))
        return dict(status=result['status'], info=result['info'], valid_key=key.startswith('$'))

    command.execute = execute
    return Command.execute_cmd(command)
