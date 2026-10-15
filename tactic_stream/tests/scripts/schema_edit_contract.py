"""Unchanged backend schema editor script for both TACTIC runtimes/vendors."""
from xml.etree import ElementTree as ET
from pyasm.biz import Schema
from pyasm.command import Command
from pyasm.common import Environment
from pyasm.search import Search, SearchType, WidgetDbConfig
from pyasm.security import Security
from tactic.core.schema_commands import SearchTypeCreatorCmd
from tactic.ui.tools.schema_wdg import SchemaSaveCmd, SchemaConnectorCbk


def install_fixture(db, id_definition='integer PRIMARY KEY AUTOINCREMENT'):
    for prefix in ('sc', 'si'):
        for suffix in ('child', 'parent'):
            table = prefix + '_' + suffix
            kind = 'contract/' + table
            db.execute('CREATE TABLE %s (id %s, code varchar(256), name text, s_status text)' % (table, id_definition))
            db.execute("INSERT INTO search_object (code,search_type,namespace,database,table_name,class_name) VALUES ('%s','%s','contract','{project}','%s','pyasm.search.SObject')" % (kind, kind, table))
            for view in (('definition', 'edit') if suffix == 'child' else ('definition',)):
                xml = '<config><%s><element name="%s"/></%s></config>' % (view, 'name' if view == 'edit' else 'code', view)
                db.execute("INSERT INTO spt_widget_config (search_type,view,config) VALUES ('%s','%s','%s')" % (kind, view, xml))


def config_value(kind, view):
    search = Search('config/widget_config')
    search.add_filter('search_type', kind)
    search.add_filter('view', view)
    return search.get_sobject().get_value('config')


def config_tree(value):
    node = ET.fromstring(value)
    return [node.tag, dict(node.attrib), (node.text or '').strip(), [config_tree(ET.tostring(child, encoding='unicode')) for child in node]]


class Run(Command):
    def execute(self):
        self.get_transaction().set_sync(False)
        if self.operation == 'cache':
            schema = Schema.get('one')
            child, parent = 'contract/schema_instance', 'contract/schema_asset'
            before = bool(schema.get_relationship_attrs(child, parent))
            schema.edit_connection(child, parent)
            after = bool(schema.get_relationship_attrs(child, parent))
            original_value = schema.get_value('schema')
            schema.add_search_type('contract/draft', parent, commit=False)
            draft_serialized = schema.get_value('schema') != original_value
            return dict(before=before, after=after, draft_serialized=draft_serialized)
        if self.operation == 'save':
            try:
                SchemaSaveCmd(from_search_type='contract/ss_child', to_search_type='contract/ss_parent').execute()
            except NameError as error:
                return dict(error=type(error).__name__, message=str(error))
            return dict(types=[SearchType.get(kind).get_value('search_type') for kind in ('contract/ss_child', 'contract/ss_parent')])
        if self.operation == 'creator':
            parent, child = 'contract/sr_parent', 'contract/sr_child'
            SearchTypeCreatorCmd(search_type_name=parent).execute()
            SearchTypeCreatorCmd(search_type_name=child, sobject_parent=parent).execute()
            return dict(relationship=Schema.get('one').get_relationship_attrs(child, parent),
                        types=[SearchType.get(kind).get_value('search_type') for kind in (child, parent)])
        prefix = 'si' if self.operation == 'id' else 'sc'
        child, parent = 'contract/%s_child' % prefix, 'contract/%s_parent' % prefix
        schema = Schema.get('one')
        schema.add_search_type(child, parent)
        schema.commit()
        column = prefix + '_parent_' + ('id' if self.operation == 'id' else 'code')
        connector = SchemaConnectorCbk(left_search_type=child, left=column,
                                      right_search_type=parent, right='id' if self.operation == 'id' else 'code')
        connector.execute()
        if self.fail:
            raise ValueError('late schema editor failure')
        schema = Schema.get('one')
        if self.operation == 'id':
            xml = schema.get_xml()
            node = xml.get_node("schema/connect[@from='%s']" % child)
            for key, value in dict(relationship='id', from_col=column, to_col='id').items():
                xml.set_attribute(node, key, value)
            schema.set_value('schema', xml.to_string())
            schema.commit()
            schema.init()
        # XML edits and column creation remain separate, as in the original editor.
        parent_object = SearchType.create(parent)
        parent_object.set_value('code', prefix.upper() + '_PARENT')
        parent_object.set_value('name', 'Parent')
        parent_object.commit()
        child_object = SearchType.create(child)
        child_object.set_value('code', prefix.upper() + '_CHILD')
        child_object.set_parent(parent_object)
        child_object.commit()
        schema.edit_connection(child, parent, mode='add')
        schema.commit()
        return dict(parent=child_object.get_value(column),
                    relationship=schema.get_relationship_attrs(child, parent),
                    columns=sorted(Search(child).get_columns()),
                    configs={kind + ':' + view: config_tree(config_value(kind, view))
                             for kind, view in ((child, 'definition'), (child, 'edit'), (child, 'edit_definition'), (parent, 'definition'))})


def run(case):
    previous = Environment.get_security()
    if previous is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    try:
        command = Run()
        command.operation = case.get('operation', 'code')
        command.fail = case.get('fail', False)
        return Command.execute_cmd(command)
    finally:
        Environment.set_security(previous)
