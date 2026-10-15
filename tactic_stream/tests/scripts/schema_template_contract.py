"""Original creator copy_from_template call, with observable copied schema effects."""
from pyasm.biz import Schema, Project, Pipeline
from pyasm.command import Command
from pyasm.common import Environment
from pyasm.search import Search, SearchType, DbContainer, WidgetDbConfig
from pyasm.security import Security
from tactic.core.schema_commands import SearchTypeCreatorCmd


def install_fixture(db, id_definition='integer PRIMARY KEY AUTOINCREMENT'):
    db.execute("CREATE TABLE tmpl_original (id %s, code varchar(256) UNIQUE, name text DEFAULT 'tmpl_original', tmpl_original_value integer NOT NULL DEFAULT 7 CHECK (tmpl_original_value>=0), data json, active boolean DEFAULT false, stamp timestamp DEFAULT CURRENT_TIMESTAMP, s_status text)" % id_definition)
    db.execute("CREATE INDEX tmpl_original_name_idx ON tmpl_original(lower(name)) WHERE name<>'tmpl_original'")
    db.execute("INSERT INTO search_object (code,search_type,namespace,database,table_name,class_name) VALUES ('contract/tmpl_original','contract/tmpl_original','contract','{project}','tmpl_original','pyasm.search.SObject')")
    db.execute("INSERT INTO tmpl_original(id,code,name) VALUES (50,'TEMPLATE_ROW','Existing source row')")


class Run(Command):
    def execute(self):
        self.get_transaction().set_sync(False)
        if self.operation.startswith('views'):
            from xml.etree import ElementTree as ET
            names = ['amount', 'label']
            formats = ['0.00', ''] if self.operation == 'views' else []
            kind = 'contract/tmpl_' + self.operation
            creator = SearchTypeCreatorCmd(search_type_name=kind, asset_title='Items & jobs',
                column_name=names, data_type=['integer', 'varchar'], format=formats, sobject_pipeline=True)
            creator.execute()
            def tree(node):
                return [node.tag, dict(node.attrib), (node.text or '').strip(), [tree(child) for child in node]]
            def saved(kind, view):
                search = Search('config/widget_config')
                search.add_filter('search_type', kind)
                search.add_filter('view', view)
                return search.get_sobject().get_value('config')
            configs = {view: tree(ET.fromstring(saved(kind, view)))
                       for view in ('definition', 'table', 'edit')}
            sidebar = {view: tree(ET.fromstring(saved('SideBarWdg', view)))
                       for view in ('definition', 'project_view')}
            return dict(configs=configs, sidebar=sidebar)
        if self.operation.startswith('pipeline'):
            suffix = 'escaped' if self.operation == 'pipeline_escaped' else 'plain'
            names = ['model', 'Review & approve'] if suffix == 'escaped' else ['model', 'review']
            creator = SearchTypeCreatorCmd(search_type_name='contract/tmpl_pipeline_' + suffix, sobject_pipeline=True, process=names)
            creator.execute()
            code = 'one/tmpl_pipeline_' + suffix
            pipeline = Pipeline.get_by_code(code)
            return dict(code=pipeline.get_code(), names=pipeline.get_process_names(),
                        processes=[[obj.get_value('process'), obj.get_value('sort_order'), obj.get_json_value('workflow')] for obj in Search('config/process').get_sobjects() if obj.get_value('pipeline_code') == code])
        creator = SearchTypeCreatorCmd(search_type_name='contract/tmpl_copy', copy_from_template='contract/tmpl_original')
        creator.execute()
        if self.fail:
            raise ValueError('late template failure')
        assert Search('contract/tmpl_copy').get_count() == 0
        assert Search('contract/tmpl_original').get_count() == 1
        rows = []
        for code in ('COPY1', 'COPY2'):
            obj = SearchType.create('contract/tmpl_copy')
            obj.set_value('code', code)
            obj.set_json_value('data', {'from': 'template', 'index': len(rows)})
            obj.commit()
            rows.append([obj.get_id(), obj.get_value('name'), obj.get_value('tmpl_original_value'), obj.get_value('active'), bool(obj.get_value('stamp')), obj.get_json_value('data')])
        schema = Schema.get('one')
        return dict(rows=rows, columns=sorted(Search('contract/tmpl_copy').get_columns()),
                    schema='contract/tmpl_copy' in schema.get_search_types(),
                    source=[obj.get_code() for obj in Search('contract/tmpl_original').get_sobjects()])


def run(case):
    previous = Environment.get_security()
    if previous is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    try:
        command = Run()
        command.fail = case.get('fail', False)
        command.operation = case.get('operation', 'copy')
        return Command.execute_cmd(command)
    finally:
        Environment.set_security(previous)
