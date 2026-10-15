"""Same persisted Snapshot/File lifecycle in original TACTIC and Stream."""
from pyasm.biz import Snapshot, File, Naming
from pyasm.checkin import SnapshotBuilder
from pyasm.command import Command, Trigger
from pyasm.common import Environment, Container
from pyasm.search import Search, SearchType
from pyasm.security import Security


def state(context):
    search = Search('sthpw/snapshot')
    search.add_filter('context', context)
    search.add_order_by('version')
    search.add_order_by('revision')
    return [[row.get_value('version'), row.get_value('revision'),
             bool(row.get_value('is_latest')), bool(row.get_value('is_current')),
             row.get_all_file_names()] for row in search.get_sobjects()]


class SnapshotRecord(Trigger):
    def execute(self):
        row = self.get_input()['sobject']
        Container.append_seq('snapshot_write.events', [row['version'], row['revision']])


class Write(Command):
    def __init__(self, case):
        super().__init__()
        self.case = case

    def execute(self):
        self.get_transaction().set_sync(False)
        parent = Search.get_by_code('contract/snapshot_entity', 'A')
        trigger = SearchType.create('sthpw/trigger')
        for field, value in {'event': 'insert|sthpw/snapshot',
                             'search_type': parent.get_base_search_type(),
                             'class_name': 'snapshot_write_contract.SnapshotRecord',
                             'mode': 'same process,same transaction'}.items():
            trigger.set_value(field, value, temp=True)
        Trigger.append_static_trigger(trigger)
        context = self.case.get('context', 'write_contract')
        # Prime an empty version cache before the first insert.
        assert Snapshot.get_snapshot(parent.get_search_type(), parent.get_code(), context) is None
        first = Snapshot.create(parent, 'file', context, is_current=True)
        assert Snapshot.get_snapshot(parent.get_search_type(), parent.get_code(), context).get_code() == first.get_code()
        first.set_value('timestamp', '2026-10-06 12:00:01')
        first.commit()
        second = Snapshot.create(parent, 'file', context, is_current=False, triggers=False)
        second.set_value('timestamp', '2026-10-06 12:00:02')
        second.commit()
        revision = Snapshot.create(parent, 'file', context, is_revision=True, is_current=False)
        revision.set_value('timestamp', '2026-10-06 12:00:03')
        revision.commit()
        created = state(context)
        first.set_latest()
        latest = state(context)
        revision.set_current()
        current = state(context)
        first.set_current()
        current_back = state(context)
        # No repository copy: original File.create stores metadata and SnapshotBuilder XML.
        file = File.create('contract_missing.ma', parent.get_search_type(), parent.get_id(),
                           file_type='main', requires_file=False, st_size=123,
                           search_code=parent.get_code())
        file.set_value('snapshot_code', revision.get_code())
        file.commit()
        builder = SnapshotBuilder()
        builder.add_file(file, {'type': 'main'})
        revision.set_value('snapshot', builder.to_string())
        revision.commit()
        files = Snapshot.get_by_code(revision.get_code()).get_all_file_objects()
        result = {'events': Container.get_seq('snapshot_write.events'), 'created': created, 'latest': latest, 'current': current, 'current_back': current_back,
                  'file': [[obj.get_file_name(), int(obj.get_value('st_size')), obj.get_value('type')] for obj in files],
                  'naming': Naming.has_versionless(parent, revision, 'latest')}
        if self.case.get('fail'):
            raise ValueError('snapshot rollback')
        # Deleting an empty latest snapshot promotes the newest remaining timestamp.
        second.delete()
        result['deleted'] = state(context)
        return result


def run(case):
    previous = Environment.get_security()
    if previous is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    try:
        try:
            result = Command.execute_cmd(Write(case))
        except ValueError as error:
            result = {'error': str(error), 'after': state(case.get('context', 'write_contract'))}
        return result
    finally:
        Environment.set_security(previous)
