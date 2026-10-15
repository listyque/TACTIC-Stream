"""Unchanged node/event script for the original engine and Stream."""
import json
from xml.etree.ElementTree import fromstring

from pyasm.biz import Pipeline, Task
from pyasm.command import Command, Trigger, Workflow
from pyasm.common import Environment
from pyasm.search import Search
from pyasm.security import Security


CONDITION = '<pipeline><process name="choose" type="condition"/><process name="left" type="action"/><process name="right" type="action"/><process name="join" type="action"/><connect from="choose" to="left" from_attr="go"/><connect from="choose" to="right" from_attr="other"/><connect from="left" to="join"/><connect from="right" to="join"/></pipeline>'
GRAPHS = {
    'STREAMS': CONDITION, 'NAMES': CONDITION, 'EMPTY': CONDITION,
    'TRUE': CONDITION.replace('from_attr="go"', 'from_attr="success"'),
    'FALSE': CONDITION.replace('from_attr="other"', 'from_attr="fail"'),
    'HOOK': CONDITION,
    'PROGRESS': '<pipeline><process name="start" type="action"/><process name="hold" type="progress"/><connect from="start" to="hold"/></pipeline>',
    'CHILD': '<pipeline><process name="start" type="input"/><process name="work" type="action"/><process name="exit" type="output"/><connect from="start" to="work"/><connect from="work" to="exit"/></pipeline>',
    'ROOT': '<pipeline><process name="start" type="hierarchy"/><process name="done" type="action"/><connect from="start" to="done"/></pipeline>',
    'MIDDLE': '<pipeline><process name="start" type="hierarchy"/><process name="exit" type="output"/><connect from="start" to="exit"/></pipeline>',
    'NESTED': '<pipeline><process name="start" type="hierarchy"/><process name="done" type="action"/><connect from="start" to="done"/></pipeline>',
    'REUSED': '<pipeline><process name="start" type="action"/><process name="first" type="hierarchy"/><process name="second" type="hierarchy"/><process name="done" type="action"/><connect from="start" to="first"/><connect from="start" to="second"/><connect from="first" to="done"/><connect from="second" to="done"/></pipeline>',
    'HOLD_CHILD': '<pipeline><process name="start" type="input"/><process name="left" type="action"/><process name="hold" type="manual"/><process name="exit" type="output"/><connect from="start" to="left"/><connect from="start" to="hold"/><connect from="left" to="exit"/><connect from="hold" to="exit"/></pipeline>',
    'HOLD_ROOT': '<pipeline><process name="start" type="hierarchy"/><process name="done" type="action"/><connect from="start" to="done"/></pipeline>',
}
CASES = ['STREAMS', 'NAMES', 'EMPTY', 'TRUE', 'FALSE', 'HOOK', 'PROGRESS', 'ROOT', 'NESTED', 'REUSED', 'HOLD_ROOT']


def install_fixture(db):
    db.execute('CREATE TABLE nodes_entity (id integer PRIMARY KEY, code varchar(256), pipeline_code varchar(256))')
    db.execute('CREATE TABLE IF NOT EXISTS spt_pipeline (id integer PRIMARY KEY, code text, pipeline text, search_type text, project_code text, s_status text)')
    db.execute("INSERT INTO search_object (code,search_type,namespace,database,table_name,class_name) VALUES ('contract/nodes','contract/nodes','contract','sthpw','nodes_entity','pyasm.search.SObject')")
    for index, (code, graph) in enumerate(GRAPHS.items(), 1):
        db.execute("INSERT INTO pipeline (code,pipeline,project_code) VALUES ('%s','%s','admin')" % (code, graph))
        db.execute("INSERT INTO nodes_entity VALUES (%s,'%s','%s')" % (index, code, code))
        for node in fromstring(graph).findall('process'):
            name = node.attrib['name']
            result = {'STREAMS': "['go', 'go']", 'NAMES': "'left'", 'EMPTY': '[]', 'FALSE': 'False'}.get(code, 'True')
            if node.attrib['type'] != 'condition':
                result = 'True'
            workflow = {}
            for event in ('action', 'complete', 'revise'):
                workflow['on_' + event] = "from pyasm.biz import Note\nimport json\nNote.create(sobject, json.dumps([pipeline.get_code(), process, '%s', data, input.get('packages', {}).get('custom')]), process='nodes')" % event
            workflow['on_action'] += '\nreturn ' + result
            if code == 'HOOK':
                workflow['on_success'] = "from pyasm.biz import Note\nNote.create(sobject, 'success hook', process='nodes')"
            child = {'ROOT': 'CHILD', 'MIDDLE': 'CHILD', 'NESTED': 'MIDDLE', 'REUSED': 'CHILD', 'HOLD_ROOT': 'HOLD_CHILD'}.get(code, '') if node.attrib['type'] == 'hierarchy' else ''
            if child:
                workflow.update(version=2, default={'subpipeline': child, 'task_creation': 'all'})
            text = json.dumps(workflow).replace("'", "''")
            db.execute("INSERT INTO spt_process (code,process,pipeline_code,subpipeline_code,workflow) VALUES ('%s_%s','%s','%s','%s','%s')" % (code, name, name, code, child, text))


def snapshot(parent):
    search = Search('config/process_state')
    search.add_parent_filter(parent)
    states = {row.get_value('process'): row.get_value('status') or '' for row in search.get_sobjects()}
    search = Search('sthpw/note')
    search.add_parent_filter(parent)
    search.add_order_by('id')
    notes = [row.get_value('note') for row in search.get_sobjects()]
    return {'states': states, 'notes': notes,
            'tasks': sorted([row.get_value('process'), row.get_value('status')] for row in Task.get_by_sobject(parent))}


class Run(Command):
    def __init__(self, case):
        super().__init__()
        self.case = case

    def execute(self):
        self.get_transaction().set_sync(False)
        code = self.case['graph']
        parent = Search.get_by_code('contract/nodes', code)
        pipeline = Pipeline.get_by_code(code)
        if code == 'PROGRESS':
            task = Task.create(parent, 'hold', status='Pending', triggers='none')
        elif code == 'HOLD_ROOT':
            Task.add_initial_tasks(parent, pipeline_code=code, start_date='2026-10-05')
            task = Task.get_by_sobject(parent, process='start/hold')[0]
        Workflow().init(quiet=True)
        event = {'sobject': parent, 'pipeline': pipeline, 'process': 'choose' if code in CASES[:6] else 'start',
                 'data': {'value': 7}, 'packages': {'custom': {'value': 9}}}
        Trigger.call(self, 'process|pending', event)
        before = snapshot(parent)
        if code == 'PROGRESS':
            Trigger.call(self, 'process|revise', dict(event, process='hold'))
        elif code == 'HOLD_ROOT':
            if self.case.get('fail'):
                definition = pipeline.get_process_sobject('done')
                definition.set_value('workflow', {'on_action': "raise ValueError('late hierarchy failure')"})
                definition.commit()
            task.set_value('status', 'Complete')
            task.commit()
        return {'before': before, 'after': snapshot(parent)}


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
