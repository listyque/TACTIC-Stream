"""Identical Workflow event/task script for original TACTIC and Stream."""
import json
from pyasm.biz import Pipeline, Task
from pyasm.command import Command, Workflow, Trigger
from pyasm.common import Environment
from pyasm.search import Search
from pyasm.security import Security


GRAPHS = {
    'ENGINE': '<pipeline><process name="start" type="action"/><process name="left" type="action"/><process name="right" type="auto"/><process name="join" type="action"/><connect from="start" to="left"/><connect from="start" to="right"/><connect from="left" to="join"/><connect from="right" to="join"/></pipeline>',
    'WAIT': '<pipeline><process name="start" type="action"/><process name="hold" type="action"/><process name="done" type="action"/><connect from="start" to="hold"/><connect from="start" to="done"/></pipeline>',
    'REJECT': '<pipeline><process name="start" type="action"/></pipeline>',
    'MANUAL': '<pipeline><process name="start" type="manual"/></pipeline>',
    'APPROVAL': '<pipeline><process name="start" type="approval"/></pipeline>',
    'APPROVAL_FORK': '<pipeline><process name="start" type="action"/><process name="left" type="approval"/><process name="right" type="approval"/><process name="join" type="action"/><connect from="start" to="left"/><connect from="start" to="right"/><connect from="left" to="join"/><connect from="right" to="join"/></pipeline>',
    'CUSTOM': '<pipeline><process name="start" type="manual"/></pipeline>',
    'MANUAL_COMPLETE': '<pipeline><process name="start" type="manual"/><process name="done" type="action"/><connect from="start" to="done"/></pipeline>',
    'MANUAL_NOT_REQUIRED': '<pipeline><process name="start" type="manual"/><process name="done" type="action"/><connect from="start" to="done"/></pipeline>',
}


def install_fixture(db):
    db.execute('CREATE TABLE engine_entity (id integer PRIMARY KEY, code varchar(256), pipeline_code varchar(256))')
    # Original template resolution expects this project table, even when empty.
    db.execute('CREATE TABLE IF NOT EXISTS spt_pipeline (id integer PRIMARY KEY, code text, pipeline text, search_type text, project_code text, s_status text)')
    db.execute("INSERT INTO search_object (code,search_type,namespace,database,table_name,class_name) VALUES ('contract/engine','contract/engine','contract','sthpw','engine_entity','pyasm.search.SObject')")
    for index, (code, graph) in enumerate(GRAPHS.items(), 1):
        db.execute("INSERT INTO pipeline (code,pipeline,project_code) VALUES ('" + code + "','" + graph + "','admin')")
        db.execute("INSERT INTO engine_entity VALUES (" + str(index) + ",'" + code + "','" + code + "')")
        names = {'ENGINE': ['start', 'left', 'right', 'join'], 'APPROVAL_FORK': ['start', 'left', 'right', 'join'], 'WAIT': ['start', 'hold', 'done'], 'MANUAL_COMPLETE': ['start', 'done'], 'MANUAL_NOT_REQUIRED': ['start', 'done']}.get(code, ['start'])
        for name in names:
            result = "'wait'" if name == 'hold' else 'False' if code == 'REJECT' else 'True'
            script = "from pyasm.biz import Note\nNote.create(sobject, process + '|action', process='engine')\nreturn " + result
            workflow = json.dumps({'on_action': script,
                                   'on_pending': "from pyasm.biz import Note\nNote.create(sobject, process + '|pending', process='engine')",
                                   'on_revise': "from pyasm.biz import Note\nNote.create(sobject, process + '|revise', process='engine')"})
            db.execute("INSERT INTO spt_process (code,process,pipeline_code,workflow) VALUES ('" + code + '_' + name + "','" + name + "','" + code + "','" + workflow.replace("'", "''") + "')")
        if code.startswith('MANUAL_'):
            db.execute("INSERT INTO snapshot (code,search_type,search_code,search_id,project_code,process,context,version,revision,is_latest,status,snapshot,column_name,login) VALUES ('" + code + "_SNAP','contract/engine','" + code + "'," + str(index) + ",'admin','start','start',1,0,TRUE,'Final','<snapshot/>','snapshot','admin')")


def snapshot(parent, pipeline):
    states = Search('config/process_state')
    states.add_parent_filter(parent)
    statuses = {row.get_value('process'): row.get_value('status') or '' for row in states.get_sobjects()}
    notes = Search('sthpw/note')
    notes.add_parent_filter(parent)
    notes.add_order_by('id')
    tasks = Task.get_by_sobject(parent)
    return {'states': {name: statuses.get(name, '') for name in pipeline.get_process_names() + ['__PIPELINE__']},
            'notes': [row.get_value('note') for row in notes.get_sobjects()],
            'tasks': [[row.get_value('process'), row.get_value('status')] for row in tasks]}


class Run(Command):
    def __init__(self, case):
        super().__init__()
        self.case = case

    def execute(self):
        self.get_transaction().set_sync(False)
        code = self.case.get('graph', 'ENGINE')
        parent = Search.get_by_code('contract/engine', code)
        pipeline = Pipeline.get_by_code(code)
        if code == 'CUSTOM':
            from pyasm.search import SearchType
            definition = SearchType.create('config/process')
            definition.set_value('pipeline_code', 'task')
            definition.set_value('process', 'Assignment')
            definition.set_value('workflow', {'direction': 'current', 'status': 'revise'})
            definition.commit()
            Workflow().init(quiet=True)
            error = ''
            try:
                Trigger.call(self, 'process|custom', {'sobject': parent, 'pipeline': pipeline,
                                                    'process': 'start', 'status': 'Assignment'})
            except NameError as exc:
                error = str(exc)
            return {'error': error, 'after': snapshot(parent, pipeline)}
        if code == 'MANUAL' or code.startswith('MANUAL_'):
            task = Task.create(parent, 'start', status='Pending', triggers='none')
            if code == 'MANUAL_COMPLETE':
                second = Task.create(parent, 'start', status='Pending', triggers='none')
        Workflow().init(quiet=True)
        Workflow().init(quiet=True)
        Trigger.call(self, 'process|pending', {'sobject': parent, 'pipeline': pipeline, 'process': 'start', 'data': {'value': 7}})
        before = snapshot(parent, pipeline)
        if code == 'WAIT':
            Trigger.call(self, 'process|complete', {'sobject': parent, 'pipeline': pipeline, 'process': 'hold'})
        elif code == 'MANUAL':
            task.set_value('status', 'In Progress')
            task.commit()
            task.set_value('status', 'Revise')
            task.commit()
        elif code == 'APPROVAL':
            task = Task.get_by_sobject(parent, process='start')[0]
            task.set_value('status', 'Approved')
            task.commit()
        elif code == 'APPROVAL_FORK':
            for process in ('left', 'right'):
                Trigger.call(self, 'process|approved', {'sobject': parent, 'pipeline': pipeline, 'process': process})
        elif code.startswith('MANUAL_'):
            task.set_value('status', 'Not Required' if code == 'MANUAL_NOT_REQUIRED' else 'Complete')
            task.commit()
            if code == 'MANUAL_COMPLETE':
                self.intermediate = snapshot(parent, pipeline)
                second.set_value('status', 'Complete')
                second.commit()
            from pyasm.command.workflow import BaseWorkflowNodeHandler
            handler = BaseWorkflowNodeHandler(input={'sobject': parent, 'pipeline': pipeline, 'process': 'start'})
            packages = handler.retrieve_state().get('packages')
            return {'before': before, 'after': snapshot(parent, pipeline), 'packages': packages,
                    'intermediate': getattr(self, 'intermediate', None)}
        return {'before': before, 'after': snapshot(parent, pipeline)}


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
