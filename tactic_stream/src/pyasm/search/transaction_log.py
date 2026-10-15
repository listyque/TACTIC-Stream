"""TransactionLog reads and explicit system writes from the original module.

See LICENSE.TACTIC and compatibility/source_manifest.json.
Creation/indexing and SObject replay require an active owned transaction;
Ordinary local schema replay uses native snapshots; remote queues remain guarded.
"""
from pyasm.common.errors import UnsupportedContract
from pyasm.common.common import Common
from pyasm.common.environment import Environment
from pyasm.common.lxml_wrapper import Xml
from pyasm.search.search import Search, SearchType, SObject, _context


class TransactionLog(SObject):
    SEARCH_TYPE = 'sthpw/transaction_log'

    def get_code_key(self):
        return 'TRANSACTION'

    @staticmethod
    def get_last(type=None):
        from pyasm.biz.project import Project
        search = Search(TransactionLog.SEARCH_TYPE)
        search.add_filter('login', _context.get().login)
        search.add_filter('namespace', Project.get_project_code())
        if type:
            search.add_filter('type', type)
        search.add_order_by('timestamp desc')
        search.add_order_by('id desc')
        return search.get_sobject()

    @staticmethod
    def get_next_redo():
        from pyasm.biz.project import Project
        search = Search(TransactionLog.SEARCH_TYPE)
        search.add_filter('login', _context.get().login)
        search.add_filter('namespace', Project.get_project_code())
        search.add_filter('type', 'redo')
        search.add_order_by('timestamp')
        search.add_order_by('id')
        return search.get_sobject()

    @classmethod
    def get(cls, user_name=None, namespace=None, time_interval=None):
        if time_interval and time_interval != 'NONE':
            raise UnsupportedContract('TransactionLog interval expressions are not migrated')
        search = Search(TransactionLog.SEARCH_TYPE)
        if user_name:
            search.add_filter('login', user_name)
        if namespace:
            search.add_filter('namespace', namespace)
        search.add_order_by('timestamp desc')
        search.set_limit(100)
        return search.get_sobjects()

    @classmethod
    def create(cls, command, transaction_data, description, title='', state=None, keywords=None):
        from pyasm.biz.project import Project
        from pyasm.search.transaction import Transaction
        transaction = Transaction.get()
        if transaction is None or not transaction.is_in_transaction() or Environment.get_security() is None:
            raise UnsupportedContract('TransactionLog creation requires active Transaction and Environment Security')
        if keywords and not SearchType.column_exists(cls.SEARCH_TYPE, 'keywords'):
            # Shipped schema has no keywords column, despite the old public
            # argument. Fail before deleting redo, not halfway through creation.
            raise UnsupportedContract('TransactionLog keywords require a schema column not present in the original seed')
        # Refuse unported journal operations before deleting redo or
        # writing a log. This also prevents a caught failure from persisting it.
        xml = Xml(transaction_data)
        for node in xml.get_nodes('transaction/*'):
            if xml.get_node_name(node) not in ('sobject', 'file', 'table', 'alter') or Xml.get_attribute(node, 'site'):
                raise UnsupportedContract('Only local SObject, file and schema transaction journals are migrated')
            if xml.get_node_name(node) == 'file' and (Xml.get_attribute(node, 'type') not in
                    ('mkdir', 'rmdir', 'remove', 'create', 'copy', 'move', 'symlink') or
                    Xml.get_attribute(node, 'state') == 'pending'):
                raise UnsupportedContract('Unsupported or incomplete file journal operation')
        length_before = len(transaction_data)
        cutoff = 10 * 1024
        data = Common.compress_transaction(transaction_data) if length_before > cutoff else transaction_data
        cls.delete_all_redo()
        log = SearchType.create(cls.SEARCH_TYPE)
        for name, value in [('login', Environment.get_user_name()), ('command', command),
                            ('transaction', data), ('title', title), ('description', description),
                            ('type', 'undo'), ('namespace', Project.get_project_code()),
                            ('ticket', Environment.get_ticket())]:
            log.set_value(name, value)
        if state:
            log.set_value('state', state)
        if keywords:
            log.set_value('keywords', keywords)
        # Config.install.server/multisite are outside the owned local scope.
        log.commit(triggers=False)
        if length_before <= cutoff:
            cls.create_sobject_log(log, transaction_data)
        return log

    @classmethod
    def create_sobject_log(cls, log, transaction_data=None):
        from pyasm.search.transaction import Transaction
        transaction = Transaction.get()
        if transaction is None or not transaction.is_in_transaction() or Environment.get_security() is None:
            raise UnsupportedContract('SObjectLog indexing requires active Transaction and Environment Security')
        from pyasm.security.access_manager import Sudo
        from pyasm.search.sobject_log import SObjectLog
        from pyasm.search.search import SearchException
        from pyasm.search.sql import SqlException
        transaction_data = transaction_data or log.get_value('transaction')
        if transaction_data.startswith('zlib:'):
            transaction_data = Common.decompress_transaction(transaction_data)
        xml = Xml(transaction_data)
        nodes = xml.get_nodes('transaction/*')
        if any(Xml.get_attribute(node, 'site') for node in nodes):
            raise UnsupportedContract('Site-specific SObject logs are not migrated')
        sudo = Sudo()
        try:
            already_logged = set()
            excluded_types = set()
            not_logged = {'sthpw/transaction_log', 'sthpw/clipboard', 'sthpw/sobject_log',
                          'sthpw/file', 'sthpw/message', 'sthpw/message_log'}
            find_parent = {'sthpw/snapshot', 'sthpw/note', 'sthpw/task'}
            for node in nodes:
                if xml.get_node_name(node) != 'sobject':
                    continue
                search_type = Xml.get_attribute(node, 'search_type')
                if search_type in excluded_types:
                    continue
                base = SearchType.get(search_type).get_base_key()
                if base in not_logged:
                    excluded_types.add(search_type)
                    continue
                # An indexed object's native hooks may change type definitions.
                excluded_types.clear()
                search_id, search_code = Xml.get_attribute(node, 'search_id'), Xml.get_attribute(node, 'search_code')
                key = '%s?code=%s' % (search_type, search_code) if search_code else '%s|%s' % (search_type, search_id)
                if key in already_logged:
                    continue
                already_logged.add(key)
                action = Xml.get_attribute(node, 'action')
                if action == 'delete':
                    continue
                obj = Search.get_by_code(search_type, search_code) if search_code else Search.get_by_id(search_type, search_id)
                if obj:
                    SObjectLog.create(obj, log, action)
                if base in find_parent:
                    try:
                        if obj:
                            obj = obj.get_parent()
                    except (SearchException, SqlException):
                        pass
                    if obj:
                        SObjectLog.create(obj, log, 'child_%s' % action)
        finally:
            sudo.exit()

    @staticmethod
    def delete_all_redo():
        from pyasm.search.transaction import Transaction
        transaction = Transaction.get()
        if transaction is None or not transaction.is_in_transaction() or Environment.get_security() is None:
            raise UnsupportedContract('Redo deletion requires active Transaction and Environment Security')
        search = Search(TransactionLog.SEARCH_TYPE, sudo=True)
        search.add_order_by('timestamp')
        search.add_filter('type', 'redo')
        search.add_filter('login', Environment.get_user_name())
        for log in search.get_sobjects():
            log.delete()

    def undo(self, ignore_files=False):
        from pyasm.common import Container
        from pyasm.search.search import SObjectUndo
        xml, nodes = self._get_replay_nodes(ignore_files, 'undo')
        from pyasm.search.transaction import Transaction, FileUndoReplay, TableUndo, TableDropUndo, AlterTableUndo
        replay = FileUndoReplay(True, self.get_value('ticket', no_exception=True), nodes=nodes)
        if not ignore_files and any(node.tag == 'file' for node in nodes):
            Transaction.get().register(replay)
        previous = Container.get('is_undo')
        previous_checkin = Container.get('Checkin:writing')
        previous_workflow = Container.get('Workflow:replay')
        previous_complete = Container.get('Checkin:replay_complete')
        Container.put('Checkin:replay_complete', not ignore_files and xml.get_root_node().get('checkin_file_replay') == 'complete')
        Container.put('is_undo', True)
        try:
            nodes.reverse()
            for node in nodes:
                Container.put('Checkin:writing', self._replay_parents.get(node, previous_checkin))
                Container.put('Workflow:replay', self._replay_effects.get(node))
                if xml.get_node_name(node) == 'sobject':
                    cache = SObject.get_cache_dict(search_type=Xml.get_attribute(node, 'search_type').split('?')[0])
                    cache.clear()
                    from pyasm.security import Sudo
                    sudo = Sudo() if node.get('search_type') == 'sthpw/sobject_list' else None
                    try:
                        SObjectUndo.undo(node)
                    finally:
                        if sudo:
                            sudo.exit()
                    cache.clear()
                elif not ignore_files and xml.get_node_name(node) == 'file':
                    replay.apply(node)
                elif node.tag == 'table':
                    (TableUndo if node.get('action') == 'create' else TableDropUndo).undo(node)
                elif node.tag == 'alter':
                    AlterTableUndo.undo(node)
            if replay.nodes or any(node.tag in ('table', 'alter') or node.get('search_type', '').split('?')[0] in ('sthpw/note', 'sthpw/task', 'config/process_state') for node in nodes):
                data = xml.to_string()
                self.set_value('transaction', Common.compress_transaction(data) if len(data) > 10 * 1024 else data)
        finally:
            Container.put('Checkin:writing', previous_checkin)
            Container.put('Workflow:replay', previous_workflow)
            Container.put('is_undo', previous)
            Container.put('Checkin:replay_complete', previous_complete)

    def redo(self, ignore=[], base_dir=''):
        from pyasm.common import Container
        from pyasm.search.search import SObjectUndo
        xml, nodes = self._get_replay_nodes('file' in ignore, 'redo')
        from pyasm.search.transaction import Transaction, FileUndoReplay, TableUndo, TableDropUndo, AlterTableUndo
        replay = FileUndoReplay(False, self.get_value('ticket', no_exception=True), base_dir, nodes)
        if 'file' not in ignore and any(node.tag == 'file' for node in nodes):
            Transaction.get().register(replay)
        previous = Container.get('is_undo')
        previous_checkin = Container.get('Checkin:writing')
        previous_workflow = Container.get('Workflow:replay')
        previous_complete = Container.get('Checkin:replay_complete')
        Container.put('Checkin:replay_complete', 'file' not in ignore and xml.get_root_node().get('checkin_file_replay') == 'complete')
        Container.put('is_undo', True)
        try:
            timestamp = self.get_value('timestamp')
            for node in nodes:
                Container.put('Checkin:writing', self._replay_parents.get(node, previous_checkin))
                Container.put('Workflow:replay', self._replay_effects.get(node))
                if xml.get_node_name(node) == 'sobject':
                    xml.set_attribute(node, 'timestamp', timestamp)
                    cache = SObject.get_cache_dict(search_type=Xml.get_attribute(node, 'search_type').split('?')[0])
                    cache.clear()
                    from pyasm.security import Sudo
                    sudo = Sudo() if node.get('search_type') == 'sthpw/sobject_list' else None
                    try:
                        SObjectUndo.redo(node)
                    finally:
                        if sudo:
                            sudo.exit()
                    cache.clear()
                elif 'file' not in ignore and xml.get_node_name(node) == 'file':
                    replay.apply(node)
                elif node.tag == 'table':
                    (TableUndo if node.get('action') == 'create' else TableDropUndo).redo(node)
                elif node.tag == 'alter':
                    AlterTableUndo.redo(node)
            if replay.nodes or any(node.tag in ('table', 'alter') for node in nodes):
                data = xml.to_string()
                self.set_value('transaction', Common.compress_transaction(data) if len(data) > 10 * 1024 else data)
        finally:
            Container.put('Checkin:writing', previous_checkin)
            Container.put('Workflow:replay', previous_workflow)
            Container.put('is_undo', previous)
            Container.put('Checkin:replay_complete', previous_complete)

    def _get_replay_nodes(self, ignore_files=False, direction=None):
        from pyasm.search.transaction import Transaction, TableUndo
        transaction = Transaction.get()
        if transaction is None or not transaction.is_in_transaction() or Environment.get_security() is None:
            raise UnsupportedContract('Journal replay requires active Command/Transaction and Security')
        from pyasm.search import DbContainer, SearchKey
        from pyasm.biz import Project
        from pyasm.common.errors import SecurityException
        security = Environment.get_security()
        sql = DbContainer.get(_context.get().store.get_db_resource())
        transaction.register_database(sql)
        if sql.conn is None:
            sql.connect()
        ordinary = not sql._admin_sql
        if ordinary:
            if not security.is_logged_in() or security.get_user_name() != _context.get().login:
                raise SecurityException('Journal replay requires the authenticated request identity')
            sql.lock_transaction_log(self.get_id())
            saved = Search(self.SEARCH_TYPE)
            saved.add_id_filter(self.get_id())
            saved = saved.get_sobject()
            project = Project.get_project_code()
            if (saved is None or saved.get_data() != self.get_data() or
                    saved.get_value('login') != _context.get().login or
                    saved.get_value('namespace') != project or saved.get_value('type') != direction):
                raise SecurityException('Replay requires an unchanged own journal in the current project and direction')
            if not security.check_access('project', [{'code': '*'}, {'code': project}], 'allow', default='deny'):
                raise SecurityException('Journal project access denied')
        data = self.get_value('transaction') or '<transaction/>'
        if data.startswith('zlib:'):
            data = Common.decompress_transaction(data)
        # Unlike get_xml_value's display fallback, a malformed write journal
        # must fail. Validate all node kinds before making any changes.
        xml = Xml(data)
        if xml.get_root_node().tag != 'transaction':
            raise ValueError('Expected a transaction XML root')
        nodes = xml.get_nodes('transaction/*')
        self._replay_parents = {}
        self._replay_effects = self._check_workflow_replay(nodes, direction, xml) if ordinary else {}
        workflow_parents = {(scope['parent'].get_search_type(), scope['parent'].get_code())
                            for scope in self._replay_effects.values()}
        if ordinary and any(node.tag == 'file' or node.get('search_type') in ('sthpw/file', 'sthpw/snapshot') for node in nodes):
            self._replay_parents = self._check_checkin_replay(nodes, project, ignore_files, direction)
        parents = {(node.get('search_type'), code) for node in nodes for code in
                   (node.get('search_code'), node.get('prev_search_code'), node.get('search_id')) if code}
        parents.update((node.get('search_type'), column.get(field)) for node in nodes
                       for column in Xml.xpath(node, 'column') if column.get('name') == 'id'
                       for field in ('from', 'to') if column.get(field))
        for node in nodes:
            kind = xml.get_node_name(node)
            if ordinary:
                # ponytail: schema and other system journals need their own replay ACL before opening them.
                stype = Xml.get_attribute(node, 'search_type')
                base = SearchKey.extract_base_search_type(stype) if stype else ''
                node_project = project
                if kind == 'sobject' and stype in ('sthpw/task', 'sthpw/note'):
                    node_project = self._check_parent_replay(node, nodes, project, direction, workflow_parents)
                elif node in self._replay_effects:
                    node_project = self._replay_effects[node]['parent'].get_project_code()
                elif (stype, node.get('search_code')) in workflow_parents:
                    node_project = SearchKey.extract_project(stype)
                if node in self._replay_parents:
                    if kind == 'file':
                        continue
                    base = stype
                if kind == 'sobject' and stype == 'sthpw/sobject_list' and not node.get('site'):
                    indexed = Search.get_by_code(stype, node.get('search_code'))
                    data = indexed.get_data() if indexed else {}
                    field = 'from' if node.get('action') == 'delete' else 'to'
                    data.update({column.get('name'): column.get(field) for column in Xml.xpath(node, 'column')})
                    parent_type = data.get('search_type', '')
                    index_project = data.get('project_code')
                    if (SearchKey.extract_project(parent_type) != index_project or
                            (index_project != project and (parent_type, data.get('search_code')) not in workflow_parents) or
                            not any((parent_type, identity) in parents for identity in
                                    (data.get('search_code'), str(data.get('search_id'))))):
                        raise SecurityException('Replay index must belong to a project object in its own journal')
                    if node.get('action') not in ('insert', 'update', 'delete'):
                        raise ValueError('Unknown SObject journal action')
                    continue
                if (kind != 'sobject' or not base or (node not in self._replay_parents and
                        (node not in self._replay_effects and stype not in ('sthpw/task', 'sthpw/note') and
                         (base.startswith(('sthpw/', 'config/')) or SearchKey.extract_project(stype) != node_project)))):
                    raise UnsupportedContract('Ordinary-user replay supports project objects, tasks, own notes and complete check-in journals')
                action = Xml.get_attribute(node, 'action')
                if action not in ('insert', 'update', 'delete'):
                    raise ValueError('Unknown SObject journal action')
                operation = {'insert': 'delete', 'update': 'edit', 'delete': 'insert'}.get(action) if direction == 'undo' else ('edit' if action == 'update' else action)
                if not security.check_access('project', [{'code': '*'}, {'code': node_project}], 'allow', default='deny'):
                    raise SecurityException('Replay object project access denied')
                keys = [{'code': base}, {'code': base, 'project': node_project}, {'code': '*'}, {'code': '*', 'project': node_project}]
                if not security.check_access('search_type', keys, operation, default='allow' if node in self._replay_effects else 'deny'):
                    raise SecurityException('Journal search type access denied')
                for code in (node.get('search_code'), node.get('prev_search_code')):
                    if code and not security.check_access('sobject', {'project': node_project, 'search_type': base, 'code': code}, operation, default='allow'):
                        raise SecurityException('Journal object access denied')
                for column in Xml.xpath(node, 'column') if operation != 'delete' else ():
                    if not security.check_access('sobject_column', {'project': node_project, 'search_type': base, 'column': column.get('name')}, 'edit'):
                        raise SecurityException('Journal column access denied')
            if kind in ('table', 'alter') and not Xml.get_attribute(node, 'site'):
                actions = ('create', 'drop') if kind == 'table' else ('add', 'drop')
                if node.get('action') not in actions or not node.get('database') or not node.get('table'):
                    raise UnsupportedContract('Unknown or incomplete schema journal operation')
                if kind == 'alter' and not node.get('column'):
                    raise ValueError('Column journal name is required')
                backup = TableUndo._load(node)
                sql = TableUndo._sql(node)
                if backup['table'] != node.get('table') or backup['vendor'] != sql.get_db_resource().get_vendor():
                    raise ValueError('Schema backup does not match its journal')
                continue
            if kind == 'file' and ignore_files:
                continue
            if kind == 'file' and not Xml.get_attribute(node, 'site'):
                operation = Xml.get_attribute(node, 'type')
                if operation not in ('move', 'copy', 'remove', 'mkdir', 'rmdir', 'create', 'symlink'):
                    raise UnsupportedContract('Unknown file replay operation')
                if Xml.get_attribute(node, 'state') == 'pending':
                    raise ValueError('Cannot replay an unfinished file operation')
                if not Xml.get_attribute(node, 'src') or (operation in ('move', 'copy', 'remove', 'symlink')
                        and not Xml.get_attribute(node, 'dst')):
                    raise ValueError('File replay paths are required')
                if operation == 'symlink' and not Xml.get_attribute(node, 'state'):
                    raise UnsupportedContract('Historical versionless journals require backup migration')
                continue
            if kind != 'sobject' or Xml.get_attribute(node, 'site'):
                raise UnsupportedContract('Multi-site replay is not migrated')
            if Xml.get_attribute(node, 'action') not in ('insert', 'update', 'delete'):
                raise ValueError('Unknown SObject journal action')
        return xml, nodes

    def _check_parent_replay(self, node, nodes, project, direction, workflow_parents):
        from pyasm.common.errors import SecurityException
        from pyasm.search import SearchKey
        stype, code = node.get('search_type'), node.get('search_code')
        owners = ('project_code', 'search_type', 'search_code', 'search_id') + (('login', 'parent_id') if stype == 'sthpw/note' else ())
        data, saved = self._get_replay_data(node, nodes, direction, owners)
        parent_type = data.get('search_type', '')
        parent_project = SearchKey.extract_project(parent_type)
        if parent_project != project and (parent_type, data.get('search_code')) not in workflow_parents:
            raise SecurityException('Replay task/note requires its cross-project Workflow parent')
        project = parent_project
        if (data.get('project_code') != project or SearchKey.extract_project(parent_type) != project or
                SearchKey.extract_base_search_type(parent_type).startswith(('sthpw/', 'config/'))):
            raise SecurityException('Replay task/note metadata differs from its project parent')
        parent = Search.get_by_code(parent_type, data.get('search_code')) if data.get('search_code') else Search.get_by_id(parent_type, data.get('search_id'))
        if parent is None or str(parent.get_id()) != str(data.get('search_id')):
            raise SecurityException('Replay task/note requires its visible original parent')
        parent._check_business_write('edit')
        security = Environment.get_security()
        if (not security.check_access('search_type', [{'code': stype}, {'code': stype, 'project': project},
                {'code': '*'}, {'code': '*', 'project': project}], 'view', default='deny') or
                not security.check_access('sobject', {'project': project, 'search_type': stype, 'code': code}, 'view', default='allow')):
            raise SecurityException('Replay task/note is not visible')
        if stype == 'sthpw/note' and data.get('login') != security.get_user_name():
            raise SecurityException('Replay note requires its authenticated author')
        return project

    @staticmethod
    def _get_replay_data(node, nodes, direction, owners):
        from pyasm.common.errors import SecurityException
        stype, code = node.get('search_type'), node.get('search_code')
        saved = Search.get_by_code(stype, node.get('prev_search_code') if direction == 'redo' and node.get('prev_search_code') else code)
        related = [value for value in nodes if value.get('search_type') == stype and value.get('search_code') == code]
        actions = [value.get('action') for value in related]
        expected, restored = ('insert', 'delete') if direction == 'undo' else ('delete', 'insert')
        if saved is None and (expected in actions or restored not in actions):
            raise SecurityException('Replay task/note is missing or outside its read policy')
        data = saved.get_data() if saved else {}
        for value in related:
            for column in Xml.xpath(value, 'column'):
                for field in ('from', 'to'):
                    if column.get(field) not in (None, ''):
                        name, contents = column.get('name'), column.get(field)
                        if name in owners and str(data.get(name, contents)) != contents:
                            raise SecurityException('Replay ownership cannot change')
                        data[name] = contents
        data.setdefault('id', node.get('search_id'))
        data.setdefault('code', code)
        return data, saved

    def _check_workflow_replay(self, nodes, direction, xml):
        from pyasm.common.errors import SecurityException
        from pyasm.search import SearchKey
        from pyasm.command.workflow import _check_parent
        effects = {}
        records = {}
        adoptions = {}
        adoption_values = {}
        for node in nodes:
            base = node.get('search_type', '').split('?')[0]
            if node.tag != 'sobject' or base not in ('sthpw/task', 'config/process_state', 'sthpw/status_log', 'sthpw/message', 'sthpw/message_log'):
                continue
            if base in ('config/process_state', 'sthpw/message', 'sthpw/message_log') and xml.get_root_node().get('workflow_replay') != 'complete':
                raise UnsupportedContract('Historical Workflow journals lack complete message backups')
            owners = ('project_code', 'search_type', 'search_code', 'search_id', 'process', 'pipeline_code', 'message_code')
            if base in ('sthpw/status_log', 'sthpw/message_log'):
                owners += ('login',)
            key = (node.get('search_type'), node.get('search_code'))
            if key not in records:
                related = [value for value in nodes if value.get('search_type') == key[0] and value.get('search_code') == key[1]]
                adoption = base == 'config/process_state' and any(value.get('action') == 'update' and
                    column.get('name') == 'pipeline_code' and not column.get('from') and column.get('to')
                    for value in related for column in Xml.xpath(value, 'column'))
                records[key] = self._get_replay_data(node, nodes, direction,
                    tuple(name for name in owners if name != 'pipeline_code') if adoption else owners)
                if adoption:
                    adoptions[key] = related
            if base != 'sthpw/task':
                effects[node] = dict(node=node, data=records[key][0], owners=owners)
        for node, scope in effects.items():
            stype, data = node.get('search_type'), scope['data']
            base = stype.split('?')[0]
            source_data = data
            if base == 'sthpw/status_log':
                source_type, source_code = data.get('search_type', ''), data.get('search_code')
                source_nodes = [value for value in nodes if value.get('search_type') == source_type and value.get('search_code') == source_code]
                if not source_nodes:
                    raise SecurityException('Status history requires its source in the same journal')
                source = Search.get_by_code(source_type, source_code)
                source_data = records.get((source_type, source_code), (source.get_data() if source else {}, None))[0]
                if str(source_data.get('id')) != str(data.get('search_id')):
                    raise SecurityException('Status history requires its original source ID')
                if source_type.split('?')[0] not in ('sthpw/task', 'config/process_state'):
                    source_data = dict(search_type=source_type, search_code=source_code, search_id=data.get('search_id'))
            if base in ('sthpw/message', 'sthpw/message_log'):
                key = data.get('code' if base == 'sthpw/message' else 'message_code', '')
                parts = key.rsplit('|', 2)
                if len(parts) != 3 or not parts[1] or parts[2] not in ('status', 'state'):
                    raise SecurityException('Workflow replay requires a native parent message key')
                parent = Search.get_by_search_key(parts[0])
                if parent is None or parts[0] != parent.get_search_key():
                    raise SecurityException('Workflow message requires its visible original parent')
            else:
                parent_type = source_data.get('search_type', '')
                parent = Search.get_by_code(parent_type, source_data.get('search_code')) if source_data.get('search_code') else Search.get_by_id(parent_type, source_data.get('search_id'))
                if parent is None or (source_data.get('search_id') not in (None, '') and str(parent.get_id()) != str(source_data['search_id'])):
                    raise SecurityException('Workflow replay requires its visible original parent')
            project = parent.get_project_code()
            if base == 'config/process_state' and SearchKey.extract_project(stype) != project:
                raise SecurityException('Workflow replay state database differs from its parent')
            _check_parent(parent)
            key = (stype, node.get('search_code'))
            if key in adoptions:
                if key not in adoption_values:
                    adoption_values[key] = self._check_pipeline_adoption(adoptions[key], records[key][1], parent, direction)
                scope['data'] = dict(data, pipeline_code=adoption_values[key][node])
            if base != 'config/process_state' and data.get('project_code') != project:
                raise SecurityException('Workflow replay metadata project differs from its parent')
            security = Environment.get_security()
            if base in ('sthpw/status_log', 'sthpw/message_log') and data.get('login') != security.get_user_name():
                raise SecurityException('Workflow replay history requires its authenticated author')
            if not security.check_access('search_type', [{'code': base}, {'code': base, 'project': project}, {'code': '*'}, {'code': '*', 'project': project}], 'view', default='allow') or not security.check_access('sobject', {'project': project, 'search_type': base, 'code': node.get('search_code')}, 'view', default='allow'):
                raise SecurityException('Workflow replay effect is not visible')
            scope['parent'] = parent
            action = node.get('action')
            scope['operation'] = {'insert': 'delete', 'update': 'edit', 'delete': 'insert'}.get(action) if direction == 'undo' else ('edit' if action == 'update' else action)
        return effects

    @staticmethod
    def _check_pipeline_adoption(nodes, saved, parent, direction):
        from pyasm.biz import Pipeline
        from pyasm.common.errors import SecurityException
        if saved is None or any(node.get('search_id') and node.get('search_id') != str(saved.get_id()) for node in nodes):
            raise SecurityException('Pipeline adoption requires its original existing state ID')
        owner = parent.get_value('pipeline_code', no_exception=True)
        pipeline = Pipeline.get_by_code(owner) if owner else None
        process = saved.get_value('process')
        if pipeline is None or (process != '__PIPELINE__' and pipeline.get_process_sobject(process) is None):
            raise SecurityException('Pipeline adoption requires the visible original parent pipeline and process')
        current = ''
        expected = {}
        for node in nodes:
            if node.get('action') != 'update':
                raise SecurityException('Legacy pipeline adoption only restores an existing state')
            before = current
            for column in Xml.xpath(node, 'column'):
                if column.get('name') != 'pipeline_code':
                    continue
                old, new = column.get('from') or '', column.get('to') or ''
                if old != current or new != owner or (old and old != new):
                    raise SecurityException('Pipeline adoption cannot switch its recorded owner')
                current = new
            expected[node] = before if direction == 'undo' else current
        if (saved.get_value('pipeline_code') or '') != (current if direction == 'undo' else ''):
            raise SecurityException('Pipeline adoption state no longer matches its journal direction')
        return expected

    def _check_checkin_replay(self, nodes, project, ignore_files, direction):
        from pathlib import Path
        import json
        from pyasm.common.errors import SecurityException
        from pyasm.search import SearchKey, FileUndo
        from pyasm.biz import FileGroup, FileRange
        if ignore_files or not any(node.tag == 'file' for node in nodes) or not any(
                node.get('search_type') == 'sthpw/snapshot' for node in nodes):
            raise UnsupportedContract('User file replay requires a complete check-in journal, including its files')
        records = {}
        scopes = {}
        for node in nodes:
            if node.tag != 'sobject' or node.get('search_type') not in ('sthpw/file', 'sthpw/snapshot'):
                continue
            key = (node.get('search_type'), node.get('search_code'))
            if key not in records:
                saved = Search.get_by_code(*key)
                actions = [value.get('action') for value in nodes if (value.get('search_type'), value.get('search_code')) == key]
                expected = 'insert' if direction == 'undo' else 'delete'
                restored = 'delete' if direction == 'undo' else 'insert'
                if saved is None and (expected in actions or restored not in actions):
                    raise SecurityException('Replay repository record is missing or outside its read policy')
                records[key] = saved.get_data() if saved else {}
            for column in Xml.xpath(node, 'column'):
                for field in ('from', 'to'):
                    if column.get(field) not in (None, ''):
                        name, value = column.get('name'), column.get(field)
                        if name in ('search_type', 'search_code', 'search_id', 'project_code') and str(records[key].get(name, value)) != value:
                            raise SecurityException('Replay repository ownership cannot change')
                        records[key][name] = value
        paths = set()
        checked_parents = {}
        def add_paths(data):
            if data.get('relative_dir') and data.get('file_name'):
                path = Path(Environment.get_asset_dir()) / data['relative_dir'] / data['file_name']
                expanded = FileGroup.expand_paths(str(path), FileRange.get(data['file_range'])) if data.get('base_type') == 'sequence' else [path]
                for value in expanded:
                    value = Path(value)
                    paths.update((value, value.with_name('.' + value.name + '.link')))
        for key, data in records.items():
            stype = data.get('search_type', '')
            if data.get('project_code') != project or SearchKey.extract_project(stype) != project:
                raise SecurityException('Replay repository parent must belong to the current project')
            parent_key = (stype, data.get('search_code'))
            parent = checked_parents.get(parent_key)
            if parent is None:
                parent = Search.get_by_code(*parent_key)
            if parent is None or str(parent.get_id()) != str(data.get('search_id')):
                raise SecurityException('Replay requires its visible original repository parent')
            if parent_key not in checked_parents:
                parent._check_business_write('edit')
                query = Search('sthpw/file')
                query.add_filter('search_type', stype); query.add_filter('search_code', parent.get_code())
                query.add_filter('project_code', project)
                for file in query.get_sobjects():
                    add_paths(file.get_data())
                checked_parents[parent_key] = parent
            security = Environment.get_security()
            if (not security.check_access('search_type', [{'code': key[0]}, {'code': key[0], 'project': project},
                    {'code': '*'}, {'code': '*', 'project': project}], 'view', default='deny') or
                    not security.check_access('sobject', {'project': project, 'search_type': key[0], 'code': key[1]}, 'view', default='allow')):
                raise SecurityException('Replay repository record is not visible')
            for node in nodes:
                if (node.get('search_type'), node.get('search_code')) == key:
                    scopes[node] = {'parent': parent, 'replay_node': node}
            if key[0] == 'sthpw/file':
                add_paths(data)
        asset = Path(Environment.get_asset_dir()).resolve()
        temp = Path(Environment.get_tmp_dir()).resolve()
        upload = Path(Environment._ticket_directory(temp / 'upload', self.get_value('ticket'), create=False)).resolve()
        ancestors = {parent for path in paths for parent in path.parents if parent.is_relative_to(asset)}
        def allowed(value, directory=False):
            path = Path(FileUndo._resolve_path(value))
            # Check both the recorded path and the filesystem; directory links must not escape.
            safe = (path.parent.resolve().is_relative_to(asset) or (directory and path == asset)) and path in (ancestors if directory else paths)
            return safe or path.resolve().is_relative_to(upload) or path.resolve().is_relative_to(temp / 'undo')
        parent = next(iter(scopes.values()))['parent']
        for node in nodes:
            if node.tag != 'file':
                continue
            if node.get('site') or node.get('type') not in ('move', 'copy', 'remove', 'mkdir', 'rmdir', 'create', 'symlink') or node.get('state') == 'pending':
                raise UnsupportedContract('Unfinished or unsupported file replay operation')
            if not node.get('src') or (node.get('type') in ('move', 'copy', 'remove', 'symlink') and not node.get('dst')):
                raise ValueError('File replay paths are required')
            if node.get('type') == 'symlink' and not node.get('state'):
                raise UnsupportedContract('Historical versionless journals require backup migration')
            values = [node.get(field) for field in ('src', 'dst', 'orig', 'cache', 'link', 'prev', 'undo_cache', 'undo_link_cache') if node.get(field)]
            if any(not allowed(value, node.get('type') in ('mkdir', 'rmdir')) for value in values):
                raise SecurityException('Replay path must belong to its check-in files, upload or undo cache: ' + ', '.join(value for value in values if not allowed(value, node.get('type') in ('mkdir', 'rmdir'))))
            if any(not allowed(value, True) for value in json.loads(node.get('parents') or '[]')):
                raise SecurityException('Replay directories must belong to its check-in: ' + node.get('parents'))
            scopes[node] = {'parent': parent, 'replay_node': node}
        return scopes

    def trigger_remote_sync(self):
        from pyasm.biz.project import Project
        if self.get_value('state') == 'start':
            return
        # Original TransactionQueueAppendCmd returns before querying sync
        # servers for the admin project. Preserve that supported local branch.
        if Project.get().get_code() == 'admin':
            return
        raise UnsupportedContract('TransactionLog remote synchronization is not migrated')

    def trigger_remote_undo(self):
        if self.get_value('state') == 'start':
            return
        raise UnsupportedContract('TransactionLog remote undo is not migrated')
