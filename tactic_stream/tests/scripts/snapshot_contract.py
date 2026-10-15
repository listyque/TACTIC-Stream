"""The same metadata reads in original TACTIC and Stream, on owned fixtures."""
from pyasm.biz import Snapshot, File, FileRange, FileGroup
from pyasm.search import Search, SObject


def install_fixture(db):
    db.execute("INSERT INTO spt_naming (code,search_type,snapshot_type,context) VALUES ('READ_SPECIFIC','contract/snapshot_entity','file','construction/named')")
    db.execute("INSERT INTO spt_naming (code,search_type,snapshot_type,context,latest_versionless) VALUES ('READ_LATEST','contract/snapshot_entity','file','construction/named',TRUE)")
    db.execute('CREATE TABLE snapshot_entity (id integer PRIMARY KEY, code text)')
    db.execute('CREATE TABLE snapshot_other (id integer PRIMARY KEY, title text)')
    db.execute("INSERT INTO snapshot_entity VALUES (1,'A')")
    db.execute("INSERT INTO snapshot_other VALUES (1,'Other')")
    for name in ('snapshot_entity', 'snapshot_other'):
        kind = 'contract/' + name
        db.execute("INSERT INTO search_object (code,search_type,namespace,database,table_name,class_name) VALUES ('" + kind + "','" + kind + "','contract','sthpw','" + name + "','pyasm.search.SObject')")
    xml = '<snapshot><file name="scene.ma" type="main" file_code="F1"/><file name="frame.####.exr" type="image" file_code="F2" file_range="1-5/2"/></snapshot>'
    for code, version, revision, current, latest, retired in (
            ('C0', 1, 0, 'TRUE', 'FALSE', 'NULL'), ('C1', 2, 0, 'FALSE', 'TRUE', 'NULL'),
            ('C2', 2, 1, 'FALSE', 'FALSE', 'NULL'), ('C3', 3, 0, 'FALSE', 'FALSE', "'retired'")):
        db.execute("INSERT INTO snapshot (code,search_type,search_id,search_code,column_name,snapshot,login,project_code,process,context,version,revision,is_current,is_latest,s_status,timestamp) VALUES ('" + code + "','contract/snapshot_entity',1,'A','snapshot','" + xml + "','admin','admin','publish','publish'," + str(version) + ',' + str(revision) + ',' + current + ',' + latest + ',' + retired + ",'2026-10-01 12:00:0" + code[-1] + "')")
    db.execute("INSERT INTO snapshot (code,search_type,search_id,column_name,snapshot,login,project_code,process,context,version,revision,is_current,is_latest,timestamp) VALUES ('D1','contract/snapshot_other',1,'snapshot','<snapshot/>','admin','admin','publish','publish',1,0,TRUE,TRUE,'2026-10-01 12:00:04')")
    db.execute("INSERT INTO snapshot (code,search_type,search_code,search_id,column_name,snapshot,login,project_code,process,context,version,revision,is_latest,timestamp) VALUES ('CA','contract/snapshot_entity?project=admin','A',1,'snapshot','<snapshot><file name=\"api.ma\" type=\"main\" file_code=\"FA\"/></snapshot>','admin','admin','publish','publish',1,0,TRUE,'2026-10-01 12:00:05')")
    db.execute("INSERT INTO file (code,file_name,search_type,search_id,search_code,snapshot_code,project_code,type) VALUES ('FA','api.ma','contract/snapshot_entity?project=admin',1,'A','CA','admin','main')")
    db.execute("INSERT INTO snapshot (code,search_type,search_code,search_id,column_name,snapshot,login,project_code,process,context,version,revision,is_latest,timestamp) VALUES ('CE','contract/snapshot_entity?project=admin','A',1,'snapshot','<snapshot/>','admin','admin','empty','empty',1,0,TRUE,'2026-10-01 12:00:06')")
    for code, filename, kind, base in (('F1', 'scene.ma', 'main', 'file'), ('F2', 'frame.####.exr', 'image', 'sequence')):
        db.execute("INSERT INTO file (code,file_name,search_type,search_id,search_code,snapshot_code,project_code,type,base_type,file_range) VALUES ('" + code + "','" + filename + "','contract/snapshot_entity',1,'A','C1','admin','" + kind + "','" + base + "','1-5/2')")


def codes(objects):
    return [obj.get_code() for obj in objects]


def run(case):
    parent = Search.get_by_code('contract/snapshot_entity', 'A')
    other = Search.get_by_id('contract/snapshot_other', 1)
    kind = parent.get_search_type()
    snapshot = Snapshot.get_snapshot(kind, 'A', context='publish', version=-1)
    assert isinstance(snapshot, Snapshot) and isinstance(snapshot, SObject), (kind, [(obj.get_code(), obj.get_value('search_type')) for obj in Search('sthpw/snapshot').get_sobjects()])
    files = snapshot.get_all_file_objects()
    assert all(isinstance(obj, File) for obj in files)
    result = {
        'selected': snapshot.get_code(), 'parent': snapshot.get_sobject().get_search_key(),
        'current': Snapshot.get_current_by_sobject(parent, 'publish').get_code(),
        'previous': snapshot.get_previous().get_code(),
        'by_parent': codes(Snapshot.get_by_sobject(parent)),
        'by_type': codes(Snapshot.get_by_search_type(kind, 'A', 'publish')),
        'by_parents': codes(Snapshot.get_by_sobjects([parent, other])),
        'latest_map': {key: value.get_code() for key, value in Snapshot.get_by_sobjects([parent, other], return_dict=True).items()},
        'files': codes(files), 'types': snapshot.get_all_file_types(),
        'names': snapshot.get_all_file_names(), 'file_codes': snapshot.get_all_file_codes(),
        'image': snapshot.get_file_by_type('image').get_file_name(),
        'expanded': snapshot.get_expanded_file_names('image'),
        'grouped': {key: codes(value) for key, value in Snapshot.get_files_dict_by_snapshots([snapshot]).items()},
        'filename': File.get_by_filename('scene.ma').get_code(),
        'skip_filename': File.get_by_filename('scene.ma', skip_id=files[0].get_id()) is None,
        'template': FileGroup.extract_template_and_range(['frame.0001.exr', 'frame.0002.exr']),
        'missing': Snapshot.get_snapshot(kind, 'A', context='missing') is None,
    }
    first = Snapshot._get_by_version(kind, 'A', context='publish', version=2, revision=0)
    revised = Snapshot._get_by_version(kind, 'A', context='publish', version=2, revision=-1)
    active = Snapshot._get_by_version(kind, 'A', context='publish', version='max')
    retired = Snapshot._get_by_version(kind, 'A', context='publish', version='max', show_retired=True)
    result['construction'] = construction_contract(parent, snapshot)
    result['fixes'] = {'first': first.get_value('revision'), 'revision': revised.get_value('revision'),
                       'active': active.get_code(), 'retired': retired.get_code(),
                       'frames': FileRange.get('1-5/2').get_num_frames()}
    return result


def construction_contract(parent, existing):
    from pyasm.common import Environment
    from pyasm.security import Security
    previous = Environment.get_security()
    if previous is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    try:
        return _construction_contract(parent, existing)
    finally:
        Environment.set_security(previous)


def _construction_contract(parent, existing):
    import tempfile
    from pathlib import Path
    from pyasm.checkin import SnapshotBuilder
    from pyasm.common import Environment, Xml

    def metadata(obj, names):
        return {name: obj.get_value(name) for name in names}

    def tree(node):
        return [Xml.get_node_name(node), Xml.get_attributes(node),
                [tree(child) for child in Xml.get_children(node)]]

    result = {}
    drafts = []
    for kwargs in ({}, {'is_revision': True}, {'version': 9},
                   {'context': 'draft', 'description': ''}):
        options = {'context': 'publish', 'commit': False, **kwargs}
        draft = Snapshot.create(parent, 'file', **options)
        drafts.append(draft)
    result['drafts'] = [metadata(obj, ('search_type', 'search_id', 'search_code',
            'column_name', 'snapshot_type', 'version', 'revision', 'description',
            'context', 'process', 'project_code', 'login', 'is_synced')) for obj in drafts]
    from pyasm.biz import Naming
    named = Snapshot.create(parent, 'file', 'construction/named', commit=False)
    result['naming'] = [Naming.get(parent, named).get_code(), Naming.get(parent, named, 'latest', mode='check').get_code(), Naming.has_versionless(parent, named, 'current')]
    result['data'] = Snapshot.create(parent, 'file', 'data', commit=False,
                                    data={'nested': {'ready': True}}).get_json_value('data')
    result['versions'] = {}
    for version in (2, 7):
        try:
            draft = Snapshot.create(parent, 'file', 'publish', version=version,
                                    is_revision=True, commit=False)
            result['versions'][str(version)] = [draft.get_value('version'), draft.get_value('revision')]
        except UnboundLocalError:
            result['versions'][str(version)] = 'UnboundLocalError'

    snapshot = drafts[-1]
    result['default_flags'] = metadata(Snapshot.set_booleans(parent, snapshot), ('is_latest', 'is_current'))
    parent.has_auto_current = lambda: False
    try:
        try:
            draft = Snapshot.create(parent, 'file', 'publish', commit=False)
            result['manual_flags'] = metadata(Snapshot.set_booleans(parent, draft), ('is_latest', 'is_current'))
            fresh = Snapshot.create(parent, 'file', 'new_context', commit=False)
            result['fresh_flags'] = metadata(Snapshot.set_booleans(parent, fresh), ('is_latest', 'is_current'))
        except NameError:
            result['manual_flags'] = 'NameError'
            result['fresh_flags'] = 'NameError'
    finally:
        del parent.has_auto_current

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'scene.ma'
        path.write_bytes(b'fixture scene')
        file = File.create(str(path), parent.get_search_type(), parent.get_id(),
                           file_type='main', search_code=parent.get_code(), commit=False)
        file.set_value('code', 'DRAFT_FILE')
        result['file'] = metadata(file, ('file_name', 'search_type', 'search_id', 'search_code',
                                        'type', 'base_type', 'project_code', 'st_size'))
        missing = File.create(str(Path(directory) / 'missing.exr'), parent.get_search_type(),
                              parent.get_id(), requires_file=False, st_size=123, commit=False)
        result['missing_file'] = metadata(missing, ('file_name', 'base_type', 'st_size'))
        try:
            File.create(str(Path(directory) / 'missing.exr'), parent.get_search_type(), parent.get_id(), commit=False)
        except Exception as error:
            result['missing_error'] = type(error).__name__
        builder = SnapshotBuilder()
        builder.add_root_attr('process', 'publish')
        builder.add_file(file, {'type': 'main'})
        group = builder.add_node('group', {'name': 'nested'})
        builder.add_ref_by_snapshot(existing, instance_name='scene', parent=group, node_name='asset')
        builder.add_ref(parent, 'publish', 2, type='input_ref', tag='input')
        builder.add_ref(parent, 'publish', 2, type='cache', node_name='cache_node')
        builder.add_unknown_ref('unknown.ma')
        builder.add_fref_by_snapshot(existing, instance_name='instance', node_name='forward_node')
        builder.add_ref_by_file_path('scene.ma', node_name='path_ref')
        before = len(Environment.get_warning())
        builder.add_ref_by_snapshot_code('MISSING_REFERENCE')
        builder.add_ref_by_file_path('MISSING_FILE.ma')
        result['warnings'] = [[warning.get_label(), warning.get_msg(), warning.get_type()]
                              for warning in Environment.get_warning()[before:]]
        source = SnapshotBuilder(Xml('<snapshot><ref name="move"/></snapshot>'))
        moved = source.get_xml().get_node('snapshot/ref')
        builder.copy_node(moved, group)
        builder.copy_node(moved, group)  # Same-parent moves must not duplicate nodes.
        result['moved_source'] = tree(source.get_root_node())
        result['xml'] = tree(builder.get_root_node())
        result['serialized'] = tree(Xml(builder.to_string()).get_root_node())
    return result
