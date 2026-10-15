"""Unchanged connection/instance/DDL script for original TACTIC and both vendors."""
from pyasm.biz import Project, SObjectConnection
from pyasm.command import Command
from pyasm.common import Environment
from pyasm.web.api_xmlrpc import ApiXMLRPC
from pyasm.search import Search, SearchType, CreateTable, DbContainer
from pyasm.security import Security


def install_fixture(db, id_definition='integer PRIMARY KEY AUTOINCREMENT', project='one'):
    db.execute("UPDATE project SET database='sthpw' WHERE code='%s'" % project)
    for table in ('schema_asset', 'schema_tag', 'schema_instance'):
        db.execute('CREATE TABLE %s (id %s, code varchar(256), name text, asset_code varchar(256), tag_code varchar(256), s_status varchar(256))' % (table, id_definition))
        db.execute("INSERT INTO search_object (code,search_type,namespace,database,table_name,class_name) "
                   "VALUES ('contract/%s','contract/%s','contract','sthpw','%s','pyasm.search.SObject')" % (table, table, table))
    db.execute("INSERT INTO schema_asset (id,code,name) VALUES (1,'ASSET','Asset')")
    db.execute("INSERT INTO schema_tag (id,code,name) VALUES (1,'TAG','Tag')")
    xml = ('<schema parent="__NONE__"><connect from="contract/schema_asset" to="contract/schema_tag" '
           'relationship="instance" instance_type="contract/schema_instance"/>'
           '<connect from="contract/schema_instance" to="contract/schema_asset" relationship="code" '
           'from_col="asset_code" to_col="code"/>'
           '<connect from="contract/schema_instance" to="contract/schema_tag" relationship="code" '
           'from_col="tag_code" to_col="code"/></schema>')
    db.execute("INSERT INTO schema (code,project_code,schema) VALUES ('%s','%s','%s')" % (project, project, xml))


class Run(Command):
    def execute(self):
        self.get_transaction().set_sync(False)
        api = ApiXMLRPC()
        api.set_protocol('local')
        ticket = {'project': 'one', 'language': 'python'}
        first = Search.get_by_code('contract/schema_asset', 'ASSET')
        second = Search.get_by_code('contract/schema_tag', 'TAG')
        created = api.connect_sobjects(ticket, first.get_search_key(), {'__search_key__': second.get_search_key()}, 'reference')
        connected = api.get_connected_sobjects(ticket, first.get_search_key(), 'reference')
        single = api.get_connected_sobject(ticket, second.get_search_key(), 'reference')
        assert connected[0]['code'] == 'TAG' and single['code'] == 'ASSET'
        assert created['src_search_id'] == second.get_id() and created['dst_search_id'] == first.get_id()
        connection_lookup_count = len(SObjectConnection.get_connections([first]))
        instance = api.add_instance(ticket, first.get_search_key(), second.get_search_key())
        assert instance['asset_code'] == 'ASSET' and instance['tag_code'] == 'TAG'
        instances = api.get_instances(ticket, first.get_search_key(), 'contract/schema_tag')
        assert len(instances) == 1
        api.remove_instance(ticket, first.get_search_key(), second.get_search_key())
        assert api.get_instances(ticket, first.get_search_key(), 'contract/schema_tag') == []
        # Use the original low-level builder, independently of its old UI creator.
        table = CreateTable()
        table.set_table('schema_ddl')
        table.add('id', 'serial', primary_key=True)
        table.add_column('code', 'varchar', not_null=True)
        table.add('data', 'json')
        table.add_constraint(['code'])
        table.commit()
        sql = DbContainer.get(Project.get().get_project_db_resource())
        columns = sql.get_column_info('schema_ddl')
        assert not columns['code']['nullable']
        classes = []
        for name in ('pyasm.search.SObject', 'pyasm.search.NoSuchClass'):
            try:
                classes.append(api.class_exists(ticket, name))
            except NameError:
                classes.append('NameError')
        assert api.check_access(ticket, 'search_type', 'contract/schema_asset', 'edit')
        assert api.get_server_api_version(ticket)
        assert api.get_server_version(ticket) == api.get_release_version(ticket)
        if self.fail:
            raise ValueError('schema API rollback')
        return {'connected': [row['code'] for row in connected], 'single': single['code'],
                'connection_context': created['context'], 'instance': [instance['asset_code'], instance['tag_code']],
                'instance_count': len(instances), 'columns': sorted(columns),
                'connection_lookup_count': connection_lookup_count,
                'lookup_types': [first.get_search_type(), created['dst_search_type']],
                'classes': classes,
                'api_version': api.get_server_api_version(ticket)}


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
        return Command.execute_cmd(command)
    finally:
        Environment.set_security(previous)
