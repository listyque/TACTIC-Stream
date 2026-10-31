"""Search Views and quick-filter defaults share native data with Handler."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from pyasm.common import Config
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from tactic_stream.server.api import Api
from tactic_stream.server.search_configuration import search_configuration_request as request, metadata_options
from tactic_stream.server.widget_configuration import WidgetConfigConflict
from pyasm.common.errors import SecurityException
from pyasm.search import Search


def exercise(store):
    check = unittest.TestCase()
    check.assertEqual(metadata_options({'choices': [{'value': 'ready', 'label': 'Ready', 'color': '#123456'}]}),
                      [dict(key='ready', title='Ready', count=0, accent='#123456')])
    api = Api(store); ticket = api.get_ticket('admin', 'search-test-password')
    auth = dict(ticket=ticket, project='admin', language='python')
    api.dispatch('insert', (auth, 'sthpw/login', dict(login='alice', first_name='Alice', password=hash_password('alice-test-password'))))
    api.dispatch('insert', (auth, 'sthpw/login', dict(login='bob', first_name='Bob')))
    with request_context(RequestContext(store, 'admin', 'admin')):
        api.auth.bind_security('admin', ticket)
        coordinate = dict(search_type='sthpw/login', scope='sthpw/login@people')
        check.assertIn('groups', request('read', dict(search_type='sthpw/search_object')))
        loaded = request('read', coordinate)
        api.dispatch('insert', (auth, 'config/widget_config', dict(
            search_type='sthpw/login', view='table',
            config='<config><table><element name="first_name" value_icon="material-design:clock" /></table></config>')))
        icons = request('read', coordinate)
        check.assertEqual(next(group for group in icons['groups'] if group['key'] == 'column:first_name')['columnIcon'],
                          'material-design:clock')
        loaded = icons
        api.dispatch('insert', (auth, 'sthpw/pipeline', dict(code='visibility_people',
            name='People workflow', project_code='admin', search_type='sthpw/login',
            pipeline='<pipeline><process name="model" color="#12ab34" /><process name="rig" /></pipeline>')))
        from pyasm.biz import Pipeline
        Pipeline.clear_cache()  # The next HTTP request starts with an empty identity cache.
        visibility = request('visibility', coordinate)
        check.assertEqual([row['key'] for row in visibility['records'] if row['kind'] == 'builtin'][:3],
                          ['publish', 'attachment', 'icon'])
        processes = [row for row in visibility['records'] if row['kind'] == 'process' and row['group'] == 'visibility_people']
        check.assertEqual([row['key'] for row in processes], ['model', 'rig'],
                          [(row['group'], row['key']) for row in visibility['records'] if row['kind'] == 'process'])
        check.assertEqual(processes[0]['accent'], '#12ab34')
        check.assertTrue(all(row['checked'] and row['rowVisible'] for row in visibility['records']))
        check.assertTrue(any(row['hasChildren'] for row in visibility['records'] if row['kind'] == 'pipeline'))
        conditions = [dict(column='login', relation='=', value=value, rowEnabled=True, operator='begin' if index == 0 else 'or')
                      for index, value in enumerate(('alice', 'bob'))]
        saved = request('save', dict(**coordinate, title='People', records=conditions, keyword='alice', order_bys=['login desc'], revision=loaded['revision']))
        preset = saved['presets'][0]
        check.assertEqual(preset['view'], 'link_search:people:sthpw/login@people')
        check.assertEqual(preset['records'], conditions)
        check.assertEqual(preset['keyword'], 'alice')
        check.assertEqual(preset['order_bys'], ['login desc'])
        # Handler's unrelated description/XML metadata survives editing in Vue.
        record = Search.get_by_code('config/widget_config', preset['code'])
        api.dispatch('update', (auth, record.get_search_key(), dict(description='Handler metadata',
            config=record.get_value('config').replace('</config>', '<custom enabled="true" /></config>'))))
        saved = request('read', coordinate)
        rows = request('query', dict(**coordinate, records=conditions))
        check.assertEqual({row['login'] for row in rows}, {'alice', 'bob'})
        page = request('query', dict(**coordinate, records=conditions, limit=1, offset=1,
                                    order_bys=['login asc'], columns=['login'], include_total=True))
        check.assertEqual(page['total'], 2)
        check.assertEqual([row['login'] for row in page['records']], ['bob'])
        check.assertNotIn('email', page['records'][0])
        bob = Search('sthpw/login'); bob.add_filter('login', 'bob')
        bob = bob.get_sobject()
        api.dispatch('update', (auth, bob.get_search_key(), {'s_status': 'retired'}))
        check.assertEqual(request('query', dict(**coordinate, records=conditions, include_total=True))['total'], 1)
        check.assertEqual(request('query', dict(**coordinate, records=conditions, include_total=True, show_retired=True))['total'], 2)
        api.dispatch('update', (auth, bob.get_search_key(), {'s_status': ''}))
        with check.assertRaisesRegex(ValueError, 'Invalid search columns'):
            request('query', dict(**coordinate, columns=['not_a_column'], include_total=True))
        expression = [dict(column='_expression', relation='in', value="@SOBJECT(sthpw/login['login','alice'])", rowEnabled=True, operator='begin')]
        check.assertEqual([row['login'] for row in request('query', dict(**coordinate, records=expression))], ['alice'])
        with check.assertRaises(WidgetConfigConflict):
            request('save', dict(**coordinate, title='Stale', records=conditions, revision=loaded['revision']))
        quick = dict(groups=[dict(key='column:first_name', enabled=True, icon='material-design:rocket')], defaultSelections={'column:first_name': ['Alice']})
        saved = request('quick-save', dict(**coordinate, configuration=quick, revision=saved['revision']))
        check.assertEqual(saved['configuration'], quick)
        rows = request('query', dict(**coordinate, records=conditions, selections=quick['defaultSelections']))
        check.assertEqual([row['login'] for row in rows], ['alice'])
        saved = request('save', dict(**coordinate, code=preset['code'], title='Renamed', records=conditions, keyword='alice', order_bys=['login desc'], revision=saved['revision']))
        check.assertEqual(saved['presets'][0]['view'], preset['view'])
        record = Search.get_by_code('config/widget_config', preset['code'])
        check.assertEqual(record.get_value('description'), 'Handler metadata')
        check.assertIn('<custom enabled="true"', record.get_value('config'))
        saved = request('delete', dict(**coordinate, code=preset['code'], revision=saved['revision']))
        check.assertEqual(saved['presets'], [])
        empty = [dict(column='email', relation='is empty', value='', rowEnabled=True, operator='begin')]
        check.assertTrue(request('query', dict(**coordinate, records=empty)))
        api.dispatch('execute_cmd', (auth, 'tactic.core.schema_commands.SearchTypeCreatorCmd', {'search_type_name': 'contract/tag_cloud'}))
        for code, keywords, status in [('A', 'blue,Blue; red Синий', ''), ('B', 'green red', ''), ('C', 'hidden blue', 'retired')]:
            api.dispatch('insert', (auth, 'contract/tag_cloud', dict(code=code, name={'A': 'Blue', 'B': 'Blue Extra', 'C': 'Hidden'}[code], keywords=keywords, s_status=status)))
        tagged = dict(search_type='contract/tag_cloud')
        catalog = request('tags', tagged)
        check.assertEqual(catalog['column'], 'keywords')
        check.assertEqual([(row['tag'], row['count']) for row in catalog['records']], [('blue', 2), ('red', 2), ('green', 1), ('Синий', 1)])
        check.assertEqual(catalog['records'][0]['weight'], 1)
        check.assertEqual(request('tags', coordinate), dict(column='', records=[]))
        both = request('query', dict(**tagged, tags=['blue', 'green'], include_total=True))
        check.assertEqual({row['code'] for row in both['records']}, {'A', 'B'})
        check.assertEqual(both['total'], 2)
        grouped = request('query', dict(**tagged, tags=['blue', 'green'], filters=[['code', '=', 'A']]))
        check.assertEqual([row['code'] for row in grouped], ['A'], 'OR tags remain within the base filter')
        check.assertEqual([row['code'] for row in request('query', dict(**tagged, tags=['hidden'], show_retired=True))], ['C'])
        for code, process, assigned in [('A', 'model', 'admin'), ('A', 'rig', 'bob'), ('B', 'rig', 'bob')]:
            api.dispatch('insert', (auth, 'sthpw/task', dict(search_type='contract/tag_cloud', search_code=code,
                project_code='admin', process=process, context=process, assigned=assigned, status='Ready')))
        related = request('query', dict(**tagged, selections={'process': ['model'], 'assigned': ['__current_login__']}))
        check.assertEqual([row['code'] for row in related], ['A'], 'My Tasks and process use the same related task')
        check.assertEqual(request('query', dict(**tagged, selections={'process': ['model'], 'assigned': ['bob']})), [])
        generated = request('settings', dict(**tagged, selections={'process':['model'], 'assigned':['__current_login__'], 'column:code':['A']}))['generatedRecords']
        check.assertEqual(generated[0]['value'], 'A')
        check.assertEqual(generated[1]['value'], "@SOBJECT(sthpw/task['assigned', '$LOGIN']['process', 'model'])")
        editable = [{key:value for key,value in row.items() if key not in ('generatedFilterKind','generatedFilterState')} for row in generated]
        check.assertEqual([row['code'] for row in request('query',dict(**tagged,records=editable))],['A'])
        with check.assertRaises(ValueError):
            request('settings',dict(**tagged,selections={'column:not_registered':['x']}))
        with check.assertRaises(ValueError):
            request('query', dict(**tagged, tags=['blue'], tag_column='description'))
        suggestions = request('suggestions', dict(**tagged, keyword='BLUE'))
        check.assertEqual(suggestions['column'], 'name')
        check.assertEqual([row['title'] for row in suggestions['records']], ['Blue', 'Blue Extra'])
        check.assertEqual(suggestions['records'][0]['keyword'], 'blue')
        check.assertEqual([row['title'] for row in request('suggestions', dict(**tagged, keyword='green'))['records']], ['Blue Extra'])
        explicit = request('suggestions',dict(**tagged,keyword='AB',column='code'))
        check.assertEqual(explicit['column'],'code')
        with check.assertRaisesRegex(ValueError,'Invalid suggestion column'):
            request('suggestions',dict(**tagged,keyword='A',column='not_registered'))
        check.assertEqual(request('suggestions', dict(**tagged, keyword='hidden'))['records'], [])
        check.assertEqual(request('suggestions', dict(**tagged, keyword='tactic-search://test'))['records'], [])
        check.assertEqual(request('suggestions', dict(**tagged, keyword='  '))['records'], [])
        check.assertEqual(request('suggestions', dict(search_type='sthpw/project', keyword='Admin'))['column'], 'title')
        with check.assertRaises(ValueError):
            request('suggestions', dict(**tagged, keyword=['blue']))
    alice_ticket = api.get_ticket('alice', 'alice-test-password')
    with request_context(RequestContext(store, login='alice', project='admin')):
        api.auth.bind_security('alice', alice_ticket)
        public = dict(search_type='sthpw/project', scope='sthpw/project@projects')
        check.assertIn('groups', request('read', public))
        check.assertIn('groups', request('read', dict(search_type='sthpw/search_object')))
        with check.assertRaises(SecurityException):
            request('read', coordinate)
        with check.assertRaises(SecurityException):
            request('tags', coordinate)
        with check.assertRaises(SecurityException):
            request('visibility', coordinate)
        with check.assertRaises(SecurityException):
            request('suggestions', dict(**coordinate, keyword='admin'))
        with check.assertRaises(SecurityException):
            request('quick-save', dict(**public, configuration=quick, revision=''))

class SearchConfiguration(unittest.TestCase):
    def test_icon_metadata_validation(self):
        from tactic_stream.server.search_configuration import validate_quick
        for icon in ('', 'clock', 'material-design:rocket', 'fontawesome-solid:clock'):
            config = dict(groups=[dict(key='column:duration', icon=icon)], defaultSelections={})
            self.assertEqual(validate_quick(config), config)
        for icon in (None, 12, [], '<svg>', 'javascript:alert(1)', 'a' * 129):
            with self.subTest(icon=icon), self.assertRaises(ValueError):
                validate_quick(dict(groups=[dict(key='status', icon=icon)], defaultSelections={}))

    def test_quick_task_chips_keep_pipeline_colors_and_titles(self):
        from tactic_stream.server import search_configuration as configuration

        task_search = Mock()
        task_search.get_sobjects.return_value = []
        pipeline = Mock()
        pipeline.get_process_names.return_value = ['model']
        pipeline.get_process_attrs.return_value = {'label': 'Modeling', 'color': '#12ab34'}
        pipeline.get_process.return_value.get_task_pipeline.return_value = 'TASK_PIPELINE'
        statuses = Mock()
        statuses.get_process_names.return_value = ['Ready']
        statuses.get_process_attrs.return_value = {'color': '#ab1234'}
        security = Mock()
        security.is_admin.return_value = False
        with (
            patch.object(configuration, 'Search', return_value=task_search),
            patch.object(configuration.Project, 'get_project_code', return_value='demo'),
            patch.object(configuration.Environment, 'get_security', return_value=security),
            patch.object(configuration.Environment, 'get_user_name', return_value='artist'),
            patch.object(configuration.Pipeline, 'get_by_search_type', return_value=[pipeline]),
            patch.object(configuration.Pipeline, 'get_by_code', return_value=statuses),
        ):
            groups = configuration.quick_groups('demo/asset', {})
        self.assertEqual(groups[0]['options'], [dict(key='model', title='Modeling', accent='#12ab34', showAccentMarker=True)])
        self.assertEqual(groups[1]['options'], [dict(key='Ready', title='Ready', accent='#ab1234', showAccentMarker=True)])
        self.assertTrue(all(group['accent'] == '#607d8b' for group in groups))
        self.assertEqual(groups[2]['options'], [dict(key='__current_login__', title='MY TASKS')])

    def test_declared_column_types_preserve_native_mapping(self):
        from pyasm.search import SearchType
        declarations = {'short':'VARCHAR(128)','long':'varchar (1024)','decimal':'NUMERIC(10, 2)',
                        'char':'CHAR(8)','plain':'varchar','date':'datetime'}
        columns = {name:dict(data_type=value,size=128) for name,value in declarations.items()}
        with patch.object(SearchType,'get_column_info',return_value=columns):
            self.assertEqual({name:SearchType.get_tactic_type('sthpw/file',name) for name in columns},
                             dict(short='varchar',long='text',decimal='float',char='character',plain='varchar',date='datetime'))

    def test_native_search_library_defaults_query_and_conflict(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.dict(os.environ, {'TACTIC_CONFIG_PATH': '', 'TACTIC_TMP_CONFIG_PATH': ''}):
                Config.reload_config()
                store = Store(root / 'sqlite'); store.initialize(hash_password('search-test-password'))
                exercise(store)
            if not os.environ.get('STREAM_POSTGRES_HOST'):
                return
            import uuid
            import psycopg
            from psycopg import sql
            from xml.etree.ElementTree import Element, SubElement, tostring
            credentials = dict(host=os.environ['STREAM_POSTGRES_HOST'], port=os.environ.get('STREAM_POSTGRES_PORT', '5432'),
                user=os.environ.get('STREAM_POSTGRES_USER', 'stream'),
                password=Path(os.environ['STREAM_POSTGRES_PASSWORD_FILE']).read_text().strip())
            database = 'stream_search_' + uuid.uuid4().hex[:12]
            config = Element('config', version='2'); section = SubElement(config, 'database')
            for key, value in dict(vendor='PostgreSQL', sobject_database=database,
                password_file=os.environ['STREAM_POSTGRES_PASSWORD_FILE'],
                **{key: value for key, value in credentials.items() if key != 'password'}).items():
                SubElement(section, key).text = value
            path = root / 'tactic-conf.xml'; path.write_bytes(tostring(config))
            with psycopg.connect(dbname='postgres', autocommit=True, **credentials) as maintenance:
                try:
                    with patch.dict(os.environ, {'TACTIC_CONFIG_PATH': str(path), 'TACTIC_TMP_CONFIG_PATH': ''}):
                        Config.reload_config()
                        store = Store(root / 'postgres'); store.initialize(hash_password('search-test-password'))
                        exercise(store)
                finally:
                    maintenance.execute(sql.SQL('DROP DATABASE IF EXISTS {}').format(sql.Identifier(database)))
                    Config.reload_config()


if __name__ == '__main__':
    unittest.main()
