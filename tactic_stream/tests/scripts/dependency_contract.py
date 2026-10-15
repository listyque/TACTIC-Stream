"""The same persisted Workflow dependency script runs on both TACTIC cores."""
import json
from pyasm.biz import Pipeline, Task
from pyasm.command import Command, Trigger, Workflow
from pyasm.common import Environment
from pyasm.search import Search
from pyasm.security import Security


CASES = ['WAIT', 'NOWAIT', 'V1', 'ATTRIBUTES', 'EMPTY', 'READY', 'SHARED', 'REVISE']
PARENT = '<pipeline><process name="start" type="dependency"/><process name="done" type="action"/><connect from="start" to="done"/></pipeline>'
CHILD = '<pipeline><process name="work" type="manual"/></pipeline>'


def install_fixture(db, project='one', id_definition='integer PRIMARY KEY'):
    db.execute("UPDATE project SET database='sthpw' WHERE code='%s'" % project)
    db.execute('CREATE TABLE dep_parent (id ' + id_definition + ', code varchar(256), pipeline_code varchar(256))')
    db.execute('CREATE TABLE dep_child (id ' + id_definition + ', code varchar(256), pipeline_code varchar(256), parent_code varchar(256), group_code varchar(256), status varchar(256))')
    db.execute('CREATE TABLE IF NOT EXISTS spt_pipeline (id integer PRIMARY KEY, code text, pipeline text, search_type text, project_code text, s_status text)')
    for name in ('parent', 'child'):
        db.execute("INSERT INTO search_object (code,search_type,namespace,database,table_name,class_name) VALUES ('contract/dep_%s','contract/dep_%s','contract','sthpw','dep_%s','pyasm.search.SObject')" % (name, name, name))
    connection = '<connect from="contract/dep_child" to="contract/dep_parent" relationship="code" from_col="parent_code" to_col="code"/>'
    db.execute("UPDATE schema SET schema=replace(schema,'</schema>','%s</schema>') WHERE code='%s'" % (connection, project))
    # A stand-alone fixture has no existing project schema.
    db.execute("INSERT INTO schema (code,project_code,schema) SELECT '%s','%s','<schema parent=\"__NONE__\">%s</schema>' WHERE NOT EXISTS (SELECT 1 FROM schema WHERE code='%s')" % (project, project, connection, project))
    db.execute("INSERT INTO pipeline (code,pipeline,project_code) VALUES ('DEP_CHILD','%s','%s')" % (CHILD, project))
    callbacks = {"on_" + event: "from pyasm.biz import Note\nimport json\nNote.create(sobject, json.dumps([process, '%s', data]), process='dependency')" % event for event in ('action', 'complete', 'revise', 'reject')}
    callbacks['on_action'] += '\nreturn True'
    child_workflow = json.dumps(callbacks).replace("'", "''")
    db.execute("INSERT INTO spt_process (code,process,pipeline_code,workflow) VALUES ('DEP_CHILD_work','work','DEP_CHILD','%s')" % child_workflow)
    child_id = 0
    for index, code in enumerate(CASES, 1):
        parent_code = 'DEP_' + code
        graph = PARENT
        settings = {'related_search_type': 'contract/dep_child', 'related_process': 'work', 'related_wait': True}
        if code == 'NOWAIT':
            settings['related_wait'] = False
        if code == 'SHARED':
            settings.update(related_search_type="@SOBJECT(contract/dep_child['group_code','SHARED'])", related_scope='global')
        if code == 'ATTRIBUTES':
            graph = graph.replace('type="dependency"', 'type="dependency" search_type="contract/dep_child" process="work" wait="true"')
        db.execute("INSERT INTO pipeline (code,pipeline,project_code) VALUES ('%s','%s','%s')" % (parent_code, graph, project))
        db.execute("INSERT INTO dep_parent VALUES (%s,'%s','%s')" % (index, code, parent_code))
        for process in ('start', 'done'):
            workflow = dict(callbacks)
            if process == 'start':
                workflow.update(settings if code == 'V1' else {'version': 2, 'default': settings})
            text = json.dumps(workflow).replace("'", "''")
            db.execute("INSERT INTO spt_process (code,process,pipeline_code,workflow) VALUES ('%s_%s','%s','%s','%s')" % (parent_code, process, process, parent_code, text))
        if code != 'EMPTY':
            for number in range(1, 3 if code == 'WAIT' else 2):
                child_id += 1
                child_code = code + '_' + str(number)
                parent_value = '' if code == 'SHARED' else code
                status = 'Complete' if code == 'READY' else ''
                db.execute("INSERT INTO dep_child VALUES (%s,'%s','DEP_CHILD','%s','%s','%s')" % (child_id, child_code, parent_value, code, status))
    db.execute("INSERT INTO dep_parent VALUES (99,'SHARED_OTHER','DEP_SHARED')")
    if id_definition.startswith('serial'):
        for table in ('dep_parent', 'dep_child'):
            db.execute("SELECT setval(pg_get_serial_sequence('%s','id'), (SELECT MAX(id) FROM %s), true)" % (table, table))


def snapshot(objects):
    result = {}
    for obj in objects:
        search = Search('config/process_state')
        search.add_parent_filter(obj)
        states = {row.get_value('process'): row.get_value('status') or '' for row in search.get_sobjects()}
        notes = Search('sthpw/note')
        notes.add_parent_filter(obj)
        notes.add_order_by('id')
        result[obj.get_code()] = {'states': states, 'notes': [json.loads(row.get_value('note')) for row in notes.get_sobjects()],
                                 'tasks': [[task.get_value('process'), task.get_value('status')] for task in Task.get_by_sobject(obj)]}
    return result


class Begin(Command):
    def __init__(self, code):
        super().__init__()
        self.code = code

    def execute(self):
        self.get_transaction().set_sync(False)
        parent = Search.get_by_code('contract/dep_parent', self.code)
        children = Search('contract/dep_child')
        children.add_filter('group_code', self.code)
        for child in children.get_sobjects():
            Task.create(child, 'work', status='Pending', triggers='none')
        Workflow().init(quiet=True)
        Trigger.call(self, 'process|pending', {'sobject': parent, 'pipeline': Pipeline.get_by_code('DEP_' + self.code),
                                              'process': 'start', 'data': {'value': 7}})
        if self.code == 'SHARED':
            other = Search.get_by_code('contract/dep_parent', 'SHARED_OTHER')
            Trigger.call(self, 'process|pending', {'sobject': other, 'pipeline': Pipeline.get_by_code('DEP_SHARED'),
                                                  'process': 'start', 'data': {'value': 8}})


class Finish(Command):
    def __init__(self, code, number, revise=False, fail=False):
        super().__init__()
        self.code, self.number, self.revise, self.fail = code, number, revise, fail

    def execute(self):
        self.get_transaction().set_sync(False)
        Workflow().init(quiet=True)
        parent = Search.get_by_code('contract/dep_parent', self.code)
        pipeline = Pipeline.get_by_code('DEP_' + self.code)
        if self.fail:
            definition = pipeline.get_process_sobject('done')
            definition.set_value('workflow', {'on_action': "raise ValueError('late dependency failure')"})
            definition.commit()
        if self.revise:
            Trigger.call(self, 'process|revise', {'sobject': parent, 'pipeline': pipeline, 'process': 'start'})
        else:
            child = Search.get_by_code('contract/dep_child', self.code + '_' + str(self.number))
            task = Task.get_by_sobject(child, process='work')[0]
            task.set_value('status', 'Complete')
            task.commit()


def run(case):
    previous = Environment.get_security()
    if previous is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    try:
        code = case['graph']
        Command.execute_cmd(Begin(code))
        children = Search('contract/dep_child')
        children.add_filter('group_code', code)
        objects = [Search.get_by_code('contract/dep_parent', code)] + children.get_sobjects()
        if code == 'SHARED':
            objects.append(Search.get_by_code('contract/dep_parent', 'SHARED_OTHER'))
        result = {'before': snapshot(objects)}
        if code not in ('EMPTY', 'READY'):
            Command.execute_cmd(Finish(code, 1, fail=case.get('fail', False)))
            result['middle'] = snapshot(objects)
            if code == 'WAIT':
                Command.execute_cmd(Finish(code, 2))
            if code == 'REVISE':
                Command.execute_cmd(Finish(code, 1, revise=True))
        result['after'] = snapshot(objects)
        return result
    finally:
        Environment.set_security(previous)
