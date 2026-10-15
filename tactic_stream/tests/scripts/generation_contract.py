"""The same task-generation calls run unchanged in both kernels."""
from datetime import datetime
from pyasm.biz import Task, TaskGenerator, Pipeline
from pyasm.common import Environment, SPTDate
from pyasm.command import Command
from pyasm.search import Search, DbContainer
from pyasm.security import Security


GRAPH = '''<pipeline>
  <process name="design" assigned_group="crew"/>
  <process name="build" duration="1" bid_duration="2"/>
  <process name="review" type="approval" duration="1"/>
  <process name="auto" type="auto"/>
  <process name="publish" duration="1"/>
  <connect from="design" to="review" context="design/output"/>
  <connect from="build" to="review"/>
  <connect from="review" to="auto"/>
  <connect from="auto" to="publish"/>
</pipeline>'''


def install_fixture(db):
    """Disposable system fixture for the same SQLite/PostgreSQL script."""
    db.execute('CREATE TABLE contract_entity (id integer PRIMARY KEY, code varchar(256), pipeline_code text)')
    db.execute("INSERT INTO search_object (code,search_type,namespace,database,table_name,class_name) VALUES ('contract/entity','contract/entity','contract','sthpw','contract_entity','pyasm.search.SObject')")
    db.execute("INSERT INTO pipeline (code,pipeline,project_code) VALUES ('GEN','" + GRAPH.replace("'", "''") + "','admin')")
    db.execute("INSERT INTO contract_entity VALUES (1,'A','GEN')")
    db.execute('''INSERT INTO spt_process (code,process,pipeline_code,workflow,description) VALUES ('GEN_DESIGN','design','GEN','{"version":2,"properties":{"duration":"2","bid_duration":"4"}}','Дизайн')''')


def rows(tasks):
    result = []
    for task in tasks:
        row = {key: task.get_value(key) for key in ('process', 'context', 'status', 'pipeline_code', 'bid_duration', 'assigned_group', 'description')}
        for key in ('bid_start_date', 'bid_end_date'):
            value = task.get_datetime_value(key)
            row[key] = value.strftime('%Y-%m-%d %H:%M:%S') if value else None
        row['parent'] = task.get_parent().get_code()
        result.append(row)
    return result


class Generate(Command):
    def __init__(self, parent, case):
        super().__init__()
        self.parent, self.case = parent, case

    def execute(self):
        self.get_transaction().set_sync(False)
        if self.case.get('prefix'):
            Task.create(self.parent, 'design', context='design/output_extra', triggers='none')
        options = dict(start_date='2026-01-16')
        if self.case.get('explicit'):
            options['processes'] = ['build', 'review']
        if self.case.get('context'):
            options.update(mode='context', contexts=['design:custom'], assigned='admin')
        tasks = Task.add_initial_tasks(self.parent, **options)
        result = {'tasks': rows(tasks)}
        if self.case.get('preview'):
            generator = TaskGenerator(generate_mode=self.case['preview'])
            preview = generator.execute(self.parent, Pipeline.get_by_code('GEN'),
                                        start_date=datetime(2026, 1, 16, 12), today=datetime(2026, 2, 2, 12))
            result['preview'] = rows(preview)
            result['unsaved'] = all(task.get_id() == -1 for task in preview)
        repeated = Task.add_initial_tasks(self.parent, skip_duplicate=not self.case.get('copies'), **options)
        result['repeated'] = rows(repeated)
        result['effects'] = {'tasks': Search('sthpw/task').get_count(),
                             'status_logs': Search('sthpw/status_log').get_count()}
        return result


def run(case):
    if case.get('calendar'):
        monday = datetime(2026, 1, 19, 12)
        friday = datetime(2026, 1, 16, 12)
        holiday = datetime(2026, 1, 20, 12)
        return {'forward': SPTDate.add_business_days(friday, 2, [holiday]).isoformat(),
                'backward': SPTDate.subtract_business_days(monday, 1).isoformat(),
                'negative': SPTDate.add_business_days(monday, -1).isoformat()}
    previous = Environment.get_security()
    security = Security()
    Environment.set_security(security)
    try:
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
        sql = DbContainer.get('sthpw')
        # Each invocation uses its own disposable fixture. Legacy cases share
        # the fixture, so remove the prior case's business rows before probing.
        for table in ('task', 'status_log', 'sobject_log', 'transaction_log', 'change_timestamp'):
            sql.do_update('DELETE FROM "' + table + '"')
        parent = Search.get_by_code('contract/entity', 'A')
        definition = Pipeline.get_by_code('GEN').get_process_sobject('design')
        if case.get('integer'):
            # Fixture edit only; no production configuration persistence claimed.
            project_sql = DbContainer.get(definition.get_db_resource())
            project_sql.do_update("UPDATE spt_process SET workflow='{\"version\":2,\"properties\":{\"duration\":2,\"bid_duration\":4}}' WHERE process='design'")
            Pipeline.get_by_code('GEN').process_sobjects = None
        elif definition:
            project_sql = DbContainer.get(definition.get_db_resource())
            project_sql.do_update("UPDATE spt_process SET workflow='{\"version\":2,\"properties\":{\"duration\":\"2\",\"bid_duration\":\"4\"}}' WHERE process='design'")
            Pipeline.get_by_code('GEN').process_sobjects = None
        try:
            return Command.execute_cmd(Generate(parent, case))
        except Exception as exc:
            return {'error': type(exc).__name__}
    finally:
        Environment.set_security(previous)
