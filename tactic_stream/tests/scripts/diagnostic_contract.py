"""Unchanged diagnostics calls in original and native kernels."""
from pyasm.biz import DebugLog, Project, ProjectSetting
from pyasm.common import Environment
from pyasm.command import Command
from pyasm.search import Search, ExceptionLog
from pyasm.security import Batch, Security


def run(case):
    batch = Batch(login_code=case.get('user', 'admin'), project_code=Project.get_project_code()) if Environment.get_security() is None else None
    previous = Environment.get_security()
    if case.get('user'):
        security = Security()
        security._is_logged_in = 1
        Environment.set_security(security)
        security._login = Search.get_by_code('sthpw/login', case['user'])
        security.setup_access_manager()
        security.get_access_manager().add_xml_rules(case['rules'])
    name = 'diag_' + case['name']
    result = {}
    try:
        if case.get('api'):
            from pyasm.web.api_xmlrpc import ApiXMLRPC
            api = ApiXMLRPC()
            api.set_protocol('local')
            result['api'] = api.log(dict(project=Project.get_project_code(), language='python'), 'warning', 'Текст & данные', name)
            result['saved'] = True
        elif case.get('standalone'):
            obj = DebugLog.debug('Текст & данные', category=name)
            result['saved'] = obj.get_id() > 0
            try:
                raise ValueError('Trace ' + name)
            except ValueError as error:
                trace = ExceptionLog.get_stack_trace(error)
                log = ExceptionLog.log(error, message=name)
            result['exception'] = dict(login=log.get_value('login'), klass=log.get_value('class'), message=log.get_value('message'),
                                       trace=bool(log.get_value('stack_trace')), normalized='\\' not in trace)
        else:
            command = Command()
            def execute():
                command.get_transaction().set_sync(False)
                ProjectSetting.create(name, 'pending data')
                original = command.get_transaction()
                obj = DebugLog.log('info', 'Текст & данные', category=name)
                result['saved'] = obj.get_id() > 0
                result['same_transaction'] = original is command.get_transaction()
                result['recorded'] = original.record_flag
                if case.get('fail'):
                    raise ValueError(name)
            command.execute = execute
            error = None
            try:
                Command.execute_cmd(command)
            except Exception as exc:
                error = type(exc).__name__
            result['error'] = error
            result['value'] = ProjectSetting.get_value_by_key(name)
            search = Search('sthpw/exception_log')
            search.add_filter('message', name)
            result['exceptions'] = search.get_count()
        search = Search('sthpw/debug_log')
        search.add_filter('category', name)
        result['logs'] = [dict(level=obj.get_value('level'), category=obj.get_value('category'),
                               message=obj.get_value('message'), login=obj.get_value('login')) for obj in search.get_sobjects()]
        return result
    finally:
        Environment.set_security(previous)
        if batch is not None and getattr(batch, '_scope', None) is not None:
            batch._scope.__exit__(None, None, None)
            batch._scope = None
