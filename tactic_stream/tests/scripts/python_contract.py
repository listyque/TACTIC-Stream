"""Unchanged PythonCmd/Trigger/Workflow calls in both TACTIC kernels."""
from pyasm.biz import Project, CustomScript
from pyasm.command import Command, Trigger
from pyasm.command.workflow import BaseWorkflowNodeHandler
from pyasm.common import Environment
from pyasm.search import Search, SearchType
from pyasm.security import Security
from tactic.command import PythonCmd, PythonTrigger


SCRIPT = '''
from pyasm.common import Environment
from pyasm.biz import Project
note = server.insert('sthpw/note', {'note': input['text'], 'process': 'python'}, parent_key=Project.get().get_search_key())
return {'value': kwargs['value'], 'text': note['note'], 'login': Environment.get_user_name(), 'project': server.get_project(), 'count': len(server.query('sthpw/note', [['process', 'python']]))}
'''
CALLBACK = '''
return {'object': sobject.get_code(), 'pipeline': pipeline.get_code(), 'process': process, 'status': status, 'data': data, 'input_object': input['sobject']['code'], 'inputs': input['inputs'], 'outputs': input['outputs'], 'packages': input['packages']}
'''


class Run(Command):
    def __init__(self, case):
        super().__init__()
        self.case = case

    def execute(self):
        self.get_transaction().set_sync(False)
        if self.case.get('null_class'):
            script = SearchType.create('sthpw/custom_script')
            script.set_value('code', 'NULL_CLASS_SCRIPT')
            script.set_value('folder', 'contract')
            script.set_value('title', 'null')
            script.set_value('script', 'return 42')
            script.commit()
            record = SearchType.create('sthpw/trigger')
            record.set_value('class_name', '')
            record.set_value('script_path', 'contract/null')
            record.set_value('mode', 'same process,same transaction')
            record.set_value('description', 'NULL class')
            try:
                handlers = Trigger._handle_trigger_sobjs([record], self, 'contract|null', {})
                return {'result': handlers[0].get_ret_val()}
            except TypeError as error:
                return {'error': type(error).__name__}
        saved = SearchType.create('config/custom_script')
        saved.set_value('code', 'PYTHON_SCRIPT')
        saved.set_value('folder', 'contract')
        saved.set_value('title', 'run')
        saved.set_value('script', SCRIPT)
        saved.set_value('language', 'python')
        saved.commit()
        inline = PythonCmd(code=SCRIPT, input={'text': 'Данные O\'Reilly'}, value=7).execute()
        cmd = PythonCmd(script_path='contract/run', input={'text': 'Saved'}, value=9)
        stored = cmd.execute()
        lookup = CustomScript.get_by_path('contract/run').get_value('code')
        central = SearchType.create('sthpw/custom_script')
        central.set_value('code', 'CENTRAL_SCRIPT')
        central.set_value('folder', 'contract')
        central.set_value('title', 'trigger')
        central.set_value('script', "return {'event': input['event'], 'trigger': input['trigger_sobject']['code']}")
        central.set_value('language', 'python')
        central.commit()
        record = SearchType.create('sthpw/trigger')
        record.set_value('code', 'PYTHON_TRIGGER')
        record.set_value('class_name', '')
        record.set_value('script_path', 'contract/trigger')
        record.set_value('mode', 'same process,same transaction')
        record.set_value('event', 'contract|python')
        record.set_value('description', 'Custom Python')
        # An empty persisted class_name is how original script triggers select
        # PythonTrigger. Original set_value('') stages NULL instead.
        record.data['class_name'] = ''
        record.update_data.pop('class_name', None)
        handlers = Trigger._handle_trigger_sobjs([record], self, 'contract|python', {'event': 'contract|python'})
        trigger = handlers[0]
        pipeline = SearchType.create('sthpw/pipeline')
        pipeline.set_value('code', 'PYTHON')
        pipeline.set_pipeline('<pipeline><process name="before"/><process name="run"/><process name="after"/><connect from="before" to="run"/><connect from="run" to="after"/></pipeline>')
        handler = BaseWorkflowNodeHandler(input={'pipeline': pipeline, 'sobject': Project.get(), 'process': 'run', 'status': 'action', 'data': {'count': 3}, 'packages': {'default': {'ready': True}}})
        # get_process_sobj still uses the original database lookup/cache; its
        # configuration is provided by this disposable fixture.
        process = SearchType.create('config/process')
        process.set_value('code', 'PYTHON_RUN')
        process.set_value('workflow', {'on_action': CALLBACK})
        handler.get_process_sobj = lambda pipeline, name: process
        callback = handler.run_callback(pipeline, 'run', 'action')
        process.set_value('workflow', {'on_action_path': 'contract/callback'})
        saved = SearchType.create('config/custom_script')
        saved.set_value('folder', 'contract')
        saved.set_value('code', 'PYTHON_CALLBACK')
        saved.set_value('title', 'callback')
        saved.set_value('script', CALLBACK)
        saved.commit()
        path_callback = handler.run_callback(pipeline, 'run', 'action')
        try:
            PythonCmd(script_path='contract/missing').execute()
        except Exception as error:
            missing = [type(error).__name__, str(error)]
        return {'inline': inline, 'saved': stored, 'description': cmd.get_description(), 'lookup': lookup, 'trigger': trigger.get_ret_val(), 'trigger_info': trigger.get_info()['result'], 'callback': callback, 'path_callback': path_callback, 'missing': missing}


def run(case):
    previous = Environment.get_security()
    if previous is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    try:
        return Command.execute_cmd(Run(case))
    finally:
        Environment.set_security(previous)
