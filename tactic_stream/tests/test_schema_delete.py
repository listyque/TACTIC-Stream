"""One native deletion lifecycle, also run against isolated PostgreSQL."""
import ast
from pathlib import Path
import tempfile
import unittest

from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from tactic_stream.server.api import Api


def exercise_deletion(call, project):
    def command(name, **values):
        return call('execute_cmd', name, values)['info']
    def review(action='load', **values):
        return command('tactic.ui.panel.schema_delete_cmd.SchemaDeleteCmd',
                       action=action, project_code=project, identity=identity, **values)
    def rejected(message, function):
        try:
            function()
        except Exception as error:
            assert message in str(error), str(error)
        else:
            raise AssertionError('Unsafe deletion accepted: ' + message)
    def script(code):
        return call('execute_python_script', '', {'code': code})['info']

    created = command('tactic.ui.panel.search_types_cmd.SearchTypesCmd', action='save',
        project_code=project, document={'title': 'Delete candidate', 'hasPipeline': True})
    identity = created['identity']
    start = review()
    assert start['canWrite'] and start['metadata']['objects'] == 0
    rejected('confirm', lambda: review('save', expected_revision=start['revision'], document={'confirmation': 'wrong'}))
    retired = call('insert', identity, {'code': 'RETIRED', 's_status': 'retired'})
    assert review()['metadata']['objects'] == 1 and not review()['canWrite']
    rejected('in use', lambda: review('save', expected_revision=start['revision'], document={'confirmation': identity}))
    call('delete_sobject', retired['__search_key__'])
    pipeline = call('insert', 'sthpw/pipeline', {'code': project + '_used', 'search_type': identity,
        'project_code': project, 'pipeline': '<pipeline><process name="work"/></pipeline>'})
    assert pipeline['code'] in review()['metadata']['usedPipelines']
    call('delete_sobject', pipeline['__search_key__'])
    note = call('insert', 'sthpw/note', {'search_type': identity, 'project_code': project, 'note': 'dependency'})
    assert {'type': 'sthpw/note', 'count': 1} in review()['metadata']['references']
    call('delete_sobject', note['__search_key__'])
    registration = ast.literal_eval(call('query', 'sthpw/search_object', [('search_type', identity)]))[0]
    alias = call('insert', 'sthpw/search_object', {'search_type': project + '/alias', 'namespace': project,
        'database': registration['database'], 'table_name': registration['table_name'], 'class_name': 'pyasm.search.SObject'})
    assert project + '/alias' in review()['metadata']['aliases']
    call('delete_sobject', alias['__search_key__'])
    call('update', registration['__search_key__'], {'database': project})
    # A different schema keeps a fixed registration alive.
    other = call('insert', 'sthpw/schema', {'code': project + '_other', 'schema': '<schema><search_type name="%s"/></schema>' % identity})
    assert project + '_other' in review()['metadata']['otherSchemas']
    call('delete_sobject', other['__search_key__'])
    fresh = review()
    script("""from pyasm.biz import Schema
s = Schema.get_by_code(%r)
s.set_xml(s.get_value('schema').replace('<schema', '<schema reviewed="changed"', 1))
s.commit()
return True""" % project)
    rejected('changed', lambda: review('save', expected_revision=fresh['revision'], document={'confirmation': identity}))
    fresh = review()
    # Failure after native DROP must restore both databases and registry/XML.
    rejected('late deletion failure', lambda: script("""from tactic.ui.panel.schema_delete_cmd import schema_delete_request
schema_delete_request('save', %r, %r, {'confirmation': %r}, %r)
raise ValueError('late deletion failure')""" % (project, identity, identity, fresh['revision'])))
    assert review()['revision'] == fresh['revision']
    assert ast.literal_eval(call('query', identity)) == []
    deleted = review('save', expected_revision=fresh['revision'], document={'confirmation': identity})
    assert identity not in deleted['metadata']['schema']['xml']
    assert not ast.literal_eval(call('query', 'sthpw/search_object', [('search_type', identity)]))
    log_id = script("""from pyasm.search import DbContainer
return DbContainer.get('sthpw').get_value('SELECT id FROM transaction_log ORDER BY id DESC LIMIT 1')""")
    call('undo', None, log_id)
    assert review()['canWrite']
    assert ast.literal_eval(call('query', identity)) == []
    call('redo', None, log_id)
    assert script("""from pyasm.biz import Project
return Project.get().get_sql().table_exists('delete_candidate')""") is False
    # {project} registrations survive dropping this project's own table.
    created = command('tactic.ui.panel.search_types_cmd.SearchTypesCmd', action='save',
        project_code=project, document={'title': 'Shared candidate'})
    identity = created['identity']
    shared = review()
    assert shared['metadata']['sharedRegistration']
    review('save', expected_revision=shared['revision'], document={'confirmation': identity})
    assert ast.literal_eval(call('query', 'sthpw/search_object', [('search_type', identity)]))
    return {'retired': True, 'dependencies': True, 'stale': True, 'rollback': True, 'undoRedo': True}


class SchemaDeletion(unittest.TestCase):
    def test_native_lifecycle(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory))
            store.initialize(hash_password('delete-test-password'))
            api = Api(store)
            auth = dict(ticket=api.get_ticket('admin', 'delete-test-password'), project='admin', language='python')
            api.dispatch('execute_cmd', (auth, 'tactic.command.CreateProjectCmd', {'project_code': 'delete_contract', 'project_title': 'Deletion contract'}))
            auth['project'] = 'delete_contract'
            exercise_deletion(lambda method, *args: api.dispatch(method, (auth, *args)), auth['project'])
            api.dispatch('insert', (auth, 'sthpw/login', {'login': 'delete_reader', 'password': hash_password('reader-password')}))
            auth['ticket'] = api.get_ticket('delete_reader', 'reader-password')
            for name, values in (
                    ('tactic.ui.panel.schema_delete_cmd.SchemaDeleteCmd', {'action': 'load', 'project_code': auth['project'], 'identity': 'delete_contract/shared_candidate'}),
                    ('tactic.ui.tools.DeleteSearchTypeCmd', {'search_type': 'delete_contract/shared_candidate'})):
                with self.assertRaises(Exception):
                    api.dispatch('execute_cmd', (auth, name, values))


if __name__ == '__main__':
    unittest.main()
