"""The same Search calls run in the original kernel, SQLite and PostgreSQL."""
from pyasm.search import Search


def install_fixture(db, id_definition='integer PRIMARY KEY AUTOINCREMENT'):
    tables = {
        'join_parent': 'code varchar(256), name text, tag_code varchar(256), alternate_code varchar(256)',
        'join_tag': 'code varchar(256), name text',
        'join_ref': 'code varchar(256), search_type text, search_code varchar(256), search_id integer, src_search_type text, src_search_code varchar(256)',
        'join_id_parent': 'name text',
    }
    for name, columns in tables.items():
        db.execute('CREATE TABLE %s (id %s, %s, s_status varchar(256))' % (name, id_definition, columns))
        db.execute("INSERT INTO search_object (code,search_type,namespace,database,table_name,class_name) "
                   "VALUES ('contract/%s','contract/%s','contract','sthpw','%s','pyasm.search.SObject')" % (name, name, name))
    db.execute("INSERT INTO search_object (code,search_type,namespace,database,table_name,class_name) "
               "VALUES ('contract/join_alias','contract/join_alias','contract','sthpw','join_tag','pyasm.search.SObject')")
    db.execute("INSERT INTO join_parent (id,code,name,tag_code,alternate_code) VALUES (1,'P1','Parent 1','T1','T2'),(2,'P2','Parent 2','T2','T1')")
    db.execute("INSERT INTO join_tag (id,code,name) VALUES (1,'T1','Zulu'),(2,'T2','Alpha')")
    db.execute("INSERT INTO join_id_parent (id,name) VALUES (7,'ID parent')")
    db.execute("INSERT INTO join_ref (id,code,search_type,search_code,search_id,src_search_type,src_search_code) VALUES "
               "(1,'R1','contract/join_parent?project=one','P1',1,'contract/join_parent?project=one','P2'),"
               "(2,'OTHER_PROJECT','contract/join_parent?project=two','P1',1,NULL,NULL),"
               "(3,'OTHER_TYPE','contract/join_tag?project=one','P1',1,NULL,NULL),"
               "(4,'ID_REF','contract/join_id_parent?project=one',NULL,7,NULL,NULL)")
    connections = (
        '<connect from="contract/join_parent" to="contract/join_tag" relationship="code" from_col="tag_code" to_col="code"/>'
        '<connect from="contract/join_parent" to="contract/join_tag" path="alternate" relationship="code" from_col="alternate_code" to_col="code"/>'
        '<connect from="contract/join_parent" to="contract/join_alias" relationship="code" from_col="tag_code" to_col="code"/>'
        '<connect from="contract/join_ref" to="contract/join_parent" relationship="search_type"/>'
        '<connect from="contract/join_ref" to="contract/join_parent" path="prefixed" relationship="search_type" prefix="src"/>'
        '<connect from="contract/join_ref" to="contract/join_id_parent" relationship="search_type"/>'
    )
    db.execute("UPDATE schema SET schema=replace(schema,'</schema>','%s</schema>') WHERE project_code='one'" % connections)


def run(case):
    operation = case['operation']
    search_type = 'contract/join_parent'
    if operation in ('child_code', 'child_id', 'prefixed', 'chain'):
        search_type = 'contract/join_ref'
    elif operation == 'parent_id':
        search_type = 'contract/join_id_parent'
    search = Search(search_type, project_code='one')
    try:
        if operation == 'child_code':
            search.add_join('contract/join_parent')
        elif operation == 'parent_code':
            search.add_join('contract/join_ref')
        elif operation == 'child_id':
            search.add_join('contract/join_id_parent')
        elif operation == 'parent_id':
            search.add_join('contract/join_ref')
        elif operation == 'prefixed':
            search.add_join('contract/join_parent', path='prefixed')
            search.add_filter('code', 'P2', table='join_parent')
        elif operation == 'chain':
            search.add_join('contract/join_parent')
            search.add_join('contract/join_tag', 'contract/join_parent')
            search.add_filter('code', 'T1', table='join_tag')
        elif operation == 'branch':
            search.add_join('contract/join_tag')
            search.add_join('contract/join_ref')
        elif operation == 'physical_table':
            search.add_join('contract/join_alias')
            search.add_filter('code', 'T1', table='join_tag')
        elif operation in ('default_order', 'named_order', 'short_named_order'):
            order = {'default_order': 'contract/join_tag.name',
                     'named_order': 'alternate:contract/join_tag.name',
                     'short_named_order': 'alternate:join_tag.name'}[operation]
            search.add_order_by(order)
        elif operation == 'duplicate':
            search.add_join('contract/join_tag')
            search.add_join('contract/join_tag')
        else:
            raise ValueError(operation)
        return [obj.get_value('code', no_exception=True) or obj.get_id() for obj in search.get_sobjects()]
    except Exception as error:
        # Preserve original defects as comparison data, never as a successful read.
        return {'error': type(error).__name__, 'message': str(error)}
