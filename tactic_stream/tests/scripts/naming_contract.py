"""Unchanged NamingUtil calls in both kernels; read-only owned fixtures."""
from pyasm.biz import NamingUtil, Snapshot
from pyasm.common import Common, Environment
from pyasm.search import Search, SearchType
from pyasm.security import Security


def run(case):
    previous = Environment.get_security()
    if previous is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    try:
        return naming_contract()
    finally:
        Environment.set_security(previous)


def naming_contract():
    parent = Search.get_by_code('contract/snapshot_entity', 'A')
    for name, value in [('name', 'Shot_01'), ('timestamp', '2026-10-01 12:34:56'),
                        ('identifier', 'human_id'), ('amount', 12.5), ('nullable', None)]:
        parent.set_value(name, value, temp=True, allow_none=True)
    snapshot = Snapshot.create(parent, 'file', 'model/main', version=12, commit=False)
    snapshot.set_value('revision', 3, temp=True)
    snapshot.set_value('timestamp', '2026-10-02 12:34:56', temp=True)
    file = SearchType.create('sthpw/file')
    file.set_value('file_name', 'frame.####.exr', temp=True)
    file.set_value('base_type', 'sequence', temp=True)
    util = NamingUtil()
    result = {
        'files': [util.naming_to_file(template, parent, snapshot, file=file) for template in (
            '{code}_{context[0]}_v{version}_r{revision}.{ext}',
            '{sobject.name}_{snapshot.context[1]}_{snapshot.version}.{ext}',
            '{basefile}_{##}_{file_type}.{ext}', '{login}_{user.login}_{project.code}',
            '{parent.code}', '{context[8]}', 'fixed/path.', '{file.file_name}',
            '{date,contract-date}', '{nullable}.{ext}',
        )],
        'dirs': [util.naming_to_dir(template, parent, snapshot, file=file) for template in (
            '//{project.code}//{sobject.code}/{context[0]}/v{version}/r{revision}',
            '{sobject.timestamp}/{snapshot.timestamp}/{timestamp}',
            '{search_type.table_name}/{login}/{user.login}',
            '{id}/{###}/{file_type}', '{file.file_type}', '{parent.code}',
            '{context[8]}', 'fixed//path/',
        )],
        'templates': [util.eval_template(template, parent, parent=parent, snapshot=snapshot)
                      for template in (None, 'literal', '{sobject.name[1]}_{parent.code}_{user.login}',
                                       '{literal}/{sobject.code}/{sobject.amount}')],
        'built': [util.build_naming(name) for name in ('chr001_model_v004.0001.ext', 'a/b-c', '', 'plain')],
        'common': [Common.get_filesystem_dir('a///b//c/'), Common.get_filesystem_name('a b?.ma')],
        'project': parent.get_project().get_code(),
        'timestamp': util._get_timestamp(snapshot),
    }

    def outcome(call):
        try:
            return call()
        except Exception as error:
            return type(error).__name__

    result['errors'] = [outcome(lambda: util.naming_to_file('{unknown.field}', parent, snapshot)),
                        outcome(lambda: util.naming_to_dir('{unknown.field}', parent, snapshot)),
                        outcome(lambda: util.eval_template('{unknown.field}', parent))]
    result['fixes'] = {
        'dir_ext': outcome(lambda: util.naming_to_dir('{ext}', parent, snapshot, file=file)),
        'hash_dir': outcome(lambda: util.naming_to_dir('{basefile}', parent, snapshot, file=file)),
        'ext_override': outcome(lambda: util.naming_to_file('{basefile}.{ext}', parent, snapshot, file=file, ext='.abc')),
        'float_file': outcome(lambda: util.naming_to_file('{amount}', parent, snapshot)),
        'float_dir': outcome(lambda: util.naming_to_dir('{amount}', parent, snapshot)),
        'nullable_dir': outcome(lambda: util.naming_to_dir('{nullable}', parent, snapshot)),
        'identifier': outcome(lambda: util.naming_to_dir('{identifier}', parent, snapshot)),
        'no_file': outcome(lambda: util.naming_to_file('{basefile}.{ext}', parent, snapshot)),
    }
    file.set_value('file_name', '#frame', temp=True)
    file.set_value('base_type', 'directory', temp=True)
    result['directory'] = util.naming_to_file('{basefile}.{ext}', parent, snapshot, file=file)
    result['fixes']['leading_hash'] = outcome(lambda: util.naming_to_dir('{basefile}', parent, snapshot, file=file))
    return result
