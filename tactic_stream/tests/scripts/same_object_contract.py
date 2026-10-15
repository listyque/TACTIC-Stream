"""Original calls on owned same-object dependency graphs, no client changes."""
import json
from pyasm.biz import Pipeline, Task
from pyasm.command import Command, Trigger, Workflow
from pyasm.common import Environment
from pyasm.search import Search
from pyasm.security import Security

MAIN = '<pipeline><process name="start" type="dependency"/><process name="start2" type="dependency"/><process name="work" type="manual"/><process name="done" type="action"/><connect from="start" to="work"/><connect from="start2" to="work"/><connect from="work" to="done"/></pipeline>'
ALT = '<pipeline><process name="work" type="manual"/><process name="done" type="action"/><connect from="work" to="done"/></pipeline>'

def install_fixture(db, project='one'):
    db.execute("INSERT INTO dep_parent (code,pipeline_code) VALUES ('SAME','SAME_MAIN')")
    for code, graph in [('SAME_MAIN', MAIN), ('SAME_ALT1', ALT), ('SAME_ALT2', ALT)]:
        db.execute("INSERT INTO pipeline (code,pipeline,project_code) VALUES ('%s','%s','%s')" % (code, graph, project))
        for process in ('start', 'start2', 'work', 'done') if code == 'SAME_MAIN' else ('work', 'done'):
            workflow = {'version': 2}
            if process in ('start', 'start2'):
                workflow['default'] = {'related_search_type': "@SOBJECT(contract/dep_parent['code','SAME'])",
                    'related_scope': 'global', 'related_process': 'work', 'related_pipeline_code': 'SAME_ALT' + ('1' if process == 'start' else '2'), 'related_wait': True}
            for event in ('action', 'complete', 'revise', 'reject'):
                workflow['on_' + event] = "from pyasm.biz import Note\nimport json\nNote.create(sobject,json.dumps(['%s',process,'%s',data]),process='same')" % (code, event)
            if process == 'done':
                workflow['on_action'] += '\nreturn True'
            text = json.dumps(workflow).replace("'", "''")
            db.execute("INSERT INTO spt_process (code,process,pipeline_code,workflow) VALUES ('%s_%s','%s','%s','%s')" % (code, process, process, code, text))

def snapshot():
    obj = Search.get_by_code('contract/dep_parent', 'SAME')
    states = Search('config/process_state')
    states.add_parent_filter(obj)
    states = {row.get_value('process'): row.get_value('status') for row in states.get_sobjects()}
    tasks = [[task.get_value('process'), task.get_value('status')] for task in Task.get_by_sobject(obj)]
    tasks.sort()
    notes = Search('sthpw/note')
    notes.add_parent_filter(obj)
    notes.add_order_by('id')
    return {'states': states, 'tasks': tasks, 'notes': [json.loads(row.get_value('note')) for row in notes.get_sobjects()]}

class Begin(Command):
    def execute(self):
        self.get_transaction().set_sync(False)
        obj = Search.get_by_code('contract/dep_parent', 'SAME')
        Task.create(obj, 'work', status='Pending', triggers='none')
        for code in ('SAME_ALT1', 'SAME_ALT2'):
            Task.add_initial_tasks(obj, pipeline_code=code, status='Pending')
        Workflow().init(quiet=True)
        for process, value in (('start', 7), ('start2', 8)):
            Trigger.call(self, 'process|pending', {'sobject': obj, 'pipeline': Pipeline.get_by_code('SAME_MAIN'),
                'process': process, 'data': {'value': value}, 'packages': {'test': {'value': value}}})

def run(case):
    if Environment.get_security() is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    error = ''
    try:
        Command.execute_cmd(Begin())
    except Exception as exc:
        error = type(exc).__name__
    result = snapshot()
    result['error'] = error
    return result

def finish(process, fail=False):
    class Finish(Command):
        def execute(self):
            self.get_transaction().set_sync(False)
            if fail:
                definition = Pipeline.get_by_code('SAME_MAIN').get_process_sobject('done')
                definition.set_value('workflow', {'on_action': "raise ValueError('late same-object failure')"})
                definition.commit()
            Workflow().init(quiet=True)
            obj = Search.get_by_code('contract/dep_parent', 'SAME')
            task = Task.get_by_sobject(obj, process=process)[0]
            task.set_value('status', 'Complete')
            task.commit()
    Command.execute_cmd(Finish())
    return snapshot()
