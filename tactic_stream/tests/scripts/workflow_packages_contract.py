"""Original snapshot package selection on owned primary/hierarchy/alternate graphs."""
from pyasm.biz import Pipeline, Snapshot, Task, Project
from pyasm.command import Command, Workflow, Trigger
from pyasm.command.workflow import WorkflowManualNodeHandler
from pyasm.common import Environment
from pyasm.search import Search, SearchType
from pyasm.security import Security


class Setup(Command):
    def execute(self):
        self.get_transaction().set_sync(False)
        Pipeline.create('Packages root', '', 'contract/dep_parent',
            '<pipeline><process name="work" type="manual"/><process name="gate" type="hierarchy"/><process name="done" type="action"/><connect from="work" to="gate"/><connect from="gate" to="done"/></pipeline>', code='PK_ROOT')
        Pipeline.create('Packages child', '', 'contract/dep_parent',
            '<pipeline><process name="work" type="manual"/><process name="exit" type="output"/><connect from="work" to="exit"/></pipeline>', code='PK_CHILD')
        for code in ('PK_ALT', 'PK_EMPTY'):
            Pipeline.create(code, '', 'contract/dep_parent', '<pipeline><process name="work" type="manual"/></pipeline>', code=code)
        root = Pipeline.get_by_code('PK_ROOT')
        definition = root.get_process_sobject('gate')
        definition.set_value('subpipeline_code', 'PK_CHILD')
        definition.commit(triggers=False)
        done = root.get_process_sobject('done')
        done.set_json_value('workflow', {'version': 2, 'on_action':
            "from pyasm.biz import Note\nimport json\nNote.create(sobject,json.dumps(input['packages']),process='packages')\nreturn True"})
        done.commit(triggers=False)
        parent = SearchType.create('contract/dep_parent?project=' + Project.get_project_code())
        parent.set_value('code', 'PK_PARENT')
        parent.set_value('pipeline_code', 'PK_ROOT')
        parent.commit(triggers=False)
        for process, context, status, latest in (
                ('work', 'primary_final', 'Final', True), ('work', 'primary_wip', 'WIP', True),
                ('gate/work', 'nested_final', 'Final', True), ('gate/work', 'nested_wip', 'WIP', True),
                ('gate/work', 'nested_old', 'Final', False), ('PK_ALT::work', 'alternate_wip', 'WIP', True)):
            snapshot = Snapshot.create(parent, 'file', context, process=process, is_latest=latest, triggers=False)
            snapshot.set_value('status', status)
            snapshot.commit(triggers='none')
        for process in ('work', 'gate/work'):
            Task.create(parent, process, status='Pending', triggers='none')
        return parent.get_search_key()


def handler(kind):
    obj = Search.get_by_search_key('contract/dep_parent?project=%s&code=PK_PARENT' % Project.get_project_code())
    root = Pipeline.get_by_code('PK_ROOT')
    pipeline = root if kind == 'primary' else Pipeline.get_by_code('PK_CHILD' if kind == 'nested' else 'PK_ALT' if kind == 'alternate' else 'PK_EMPTY')
    return WorkflowManualNodeHandler(input={'pipeline': pipeline, 'sobject': obj, 'process': 'work',
        'parent_pipelines': [root] if kind == 'nested' else [], 'parent_processes': ['gate'] if kind == 'nested' else [],
        'packages': {'custom': {'value': 9}, 'default': {'keep': 3}, 'message': {'body': 'keep message'}}})


def summary(packages):
    result = dict(packages)
    result['default'] = dict(packages['default'])
    result['default']['snapshot_codes'] = sorted(Search.get_by_code('sthpw/snapshot', code).get_value('context')
                                                for code in packages['default']['snapshot_codes'])
    return result


class Inspect(Command):
    def execute(self):
        self.get_transaction().set_sync(False)
        return {kind: summary(handler(kind).get_output_packages()) for kind in ('primary', 'nested', 'alternate', 'empty')}


class Begin(Command):
    def execute(self):
        self.get_transaction().set_sync(False)
        Workflow().init(quiet=True)
        obj = Search.get_by_search_key('contract/dep_parent?project=%s&code=PK_PARENT' % Project.get_project_code())
        Trigger.call(self, 'process|pending', {'sobject': obj, 'pipeline': Pipeline.get_by_code('PK_ROOT'),
            'process': 'work', 'packages': {'custom': {'value': 9}, 'message': {'body': 'keep message'}}})


def run(case):
    previous = Environment.get_security()
    if previous is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    try:
        Command.execute_cmd(Setup())
        return Command.execute_cmd(Inspect())
    finally:
        Environment.set_security(previous)
