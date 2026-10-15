"""Same parent/collection script for original TACTIC, SQLite and PostgreSQL."""
from pyasm.command import Command
from pyasm.common import Environment
from pyasm.search import Search, SearchType
from pyasm.security import Security
from pyasm.web.api_xmlrpc import ApiXMLRPC


def install_fixture(db, id_definition='integer PRIMARY KEY AUTOINCREMENT', project='one'):
    db.execute("UPDATE project SET database='sthpw' WHERE code='%s'" % project)
    definitions = {
        'collect': '_is_collection boolean, name text, keywords text, user_keywords text, keywords_data text, relative_dir text',
        'collect_in_collect': 'parent_code varchar(256), search_code varchar(256)',
        'parent_child': 'collect_code varchar(256), collect_id integer, search_key text',
        'parent_id_child': 'collect_id integer',
    }
    for name, columns in definitions.items():
        db.execute('CREATE TABLE %s (id %s, code varchar(256), %s, s_status varchar(256))' % (name, id_definition, columns))
        db.execute("INSERT INTO search_object (code,search_type,namespace,database,table_name,class_name,type) "
                   "VALUES ('contract/%s','contract/%s','contract','{project}','%s','pyasm.search.SObject','%s')" %
                   (name, name, name, ''))
    xml = ('<schema parent="__NONE__"><search_type name="contract/collect"/>'
           '<connect from="contract/parent_child" to="contract/collect" relationship="code" from_col="collect_code" type="hierarchy"/>'
           '<connect from="contract/parent_id_child" to="contract/collect" relationship="id" from_col="collect_id" type="hierarchy"/>'
           '<connect from="contract/collect_in_collect" to="contract/collect" relationship="code" from_col="search_code"/>'
           '<connect from="contract/collect_in_collect" to="contract/collect" relationship="code" from_col="parent_code" path="parent" type="hierarchy"/>'
           '</schema>')
    existing = db.execute("SELECT id,schema FROM schema WHERE code='%s' ORDER BY id" % project).fetchone()
    if existing:
        xml = existing[1].replace('</schema>', xml.split('>', 1)[1])
        db.execute("UPDATE schema SET schema='%s' WHERE id=%s" % (xml.replace("'", "''"), existing[0]))
    else:
        db.execute("INSERT INTO schema (code,project_code,schema) VALUES ('%s','%s','%s')" % (project, project, xml))


class Run(Command):
    def execute(self):
        self.get_transaction().set_sync(False)
        api = ApiXMLRPC()
        api.set_protocol('local')
        ticket = {'project': self.project, 'language': 'python'}
        kind = 'contract/collect?project=' + self.project
        if self.keywords:
            membership_type = SearchType.get('contract/collect_in_collect')
            membership_type.set_value('type', 'collection')
            membership_type.commit()
        root = api.insert(ticket, kind, {'code': 'ROOT', 'name': 'Root', '_is_collection': True}, triggers=self.keywords)
        other = api.insert(ticket, kind, {'code': "OTHER'", 'name': 'Other', '_is_collection': True}, triggers=self.keywords)
        child = api.insert(ticket, 'contract/parent_child?project=' + self.project, {'code': 'CHILD'}, parent_key=root['__search_key__'])
        by_id = api.insert(ticket, 'contract/parent_id_child?project=' + self.project, {'code': 'BY_ID'}, parent_key=root['__search_key__'])
        updated = api.update(ticket, child['__search_key__'], parent_key=other['__search_key__'])
        if self.keywords:
            sub = api.insert(ticket, kind, {'code': 'SUB', 'name': 'Sub', '_is_collection': True}, collection_key=root['__search_key__'])
            leaf = api.insert(ticket, kind, {'code': 'LEAF', 'name': 'Leaf'}, collection_key=sub['__search_key__'])
            api.update(ticket, root['__search_key__'], {'name': 'Renamed', 'user_keywords': 'tag'})
            leaf = Search.get_by_code(kind, 'LEAF')
            keywords = sorted(leaf.get_value('keywords').split())
            root_object = Search.get_by_code(kind, 'ROOT')
            leaf.add_to_collection(root_object)
            edges = Search('contract/collect_in_collect')
            edges.add_filter('parent_code', 'ROOT')
            edges.add_filter('search_code', 'LEAF')
            edges.get_sobject().delete()
            assert 'renamed' in Search.get_by_code(kind, 'LEAF').get_value('keywords')
            edges = Search('contract/collect_in_collect')
            edges.add_filter('parent_code', 'ROOT')
            edges.add_filter('search_code', 'SUB')
            edges.get_sobject().delete()
            remaining_keywords = sorted(Search.get_by_code(kind, 'LEAF').get_value('keywords').split())
            assert 'renamed' not in remaining_keywords and 'sub' in remaining_keywords
            return {'collections': sorted(obj.get_code() for obj in leaf.get_collections()),
                    'keywords': keywords, 'remaining_keywords': remaining_keywords,
                    'parents': [child['collect_code'], by_id['collect_id'], updated['collect_code']]}
        leaf = api.insert(ticket, kind, {'code': 'LEAF', 'name': 'Leaf'}, triggers=False, collection_key=root['__search_key__'])
        obj = Search.get_by_code(kind, 'LEAF')
        obj.add_to_collection(Search.get_by_code(kind, 'ROOT'))
        obj.add_to_collection(Search.get_by_code(kind, "OTHER'"))
        return {'collections': sorted(item.get_code() for item in obj.get_collections()),
                'type': obj.get_collection_type(), 'type_class': SearchType.get_collection_type('contract/collect'),
                'memberships': Search('contract/collect_in_collect').get_count(),
                'parents': [child['collect_code'], by_id['collect_id'], updated['collect_code']]}


def run(case):
    if case.get('operation') == 'cte':
        from pyasm.biz import Project
        sql = Project.get().get_sql()
        statement = sql.get_database_impl().get_child_codes_cte('contract/collect_in_collect', 'contract/collect', 'LEAF')
        return [row[0] for row in sql.do_query(statement)]
    previous = Environment.get_security()
    if previous is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    try:
        command = Run()
        command.project = case.get('project', 'one')
        command.keywords = case.get('keywords', False)
        return Command.execute_cmd(command)
    finally:
        Environment.set_security(previous)
