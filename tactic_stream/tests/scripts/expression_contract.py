"""One unchanged expression/Naming script for the original and native kernels."""
import datetime
from pyasm.biz import ExpressionParser, Naming, NamingUtil
from pyasm.common import Container, Environment
from pyasm.search import Search
from pyasm.security import Security


def install_fixture(db):
    for code, condition in (('EX_DEFAULT', ''), ('EX_FALSE', '@GET(snapshot.version)=999'),
                            ('EX_MATCH', '@GET(snapshot.version)=2')):
        db.execute("INSERT INTO spt_naming (code,search_type,snapshot_type,context,condition) VALUES ('"
                   + code + "','contract/snapshot_entity','file','expression/named','" + condition + "')")


def run(case):
    previous = Environment.get_security()
    if previous is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    try:
        if case.get('select_serialization'):
            return select_serialization_contract(case)
        if case.get('search_select'):
            return search_select_contract(case)
        if case.get('timestamp_filters'):
            return timestamp_filter_contract(case)
        if case.get('op_filters'):
            return filter_expression_contract(case)
        if case.get('site_context'):
            return site_contract(case)
        if case.get('connections'):
            return connection_contract(case)
        if case.get('virtual'):
            return virtual_contract(case)
        if case.get('variable'):
            return variable_contract(case)
        if case.get('format_value'):
            return format_contract(case)
        if case.get('file_paths'):
            return file_paths_contract(case)
        return expression_contract()
    finally:
        Environment.set_security(previous)


def select_serialization_contract(case):
    import json
    from pyasm.search import Select
    try:
        search = Search('contract/entity')
        search.add_order_by('id')
        for step in case.get('steps', []):
            target = search if step.get('target') == 'search' else search.get_select()
            getattr(target, step['method'])(*step.get('args', []), **step.get('kwargs', {}))
        exported = json.loads(search.get_select().dumps())
        if case.get('omit_join_tables'):
            exported.pop('join_tables', None)
        exported.update(case.get('changes', {}))
        target = Select() if case.get('standalone') else Search('contract/entity').get_select()
        target.loads(json.dumps(exported))
        rows = target.execute(search.get_sql())
        columns = search.get_sql().get_columns_from_description()
        values = [row[0] if len(columns) == 1 else row[columns.index('code')] for row in rows]
        return {'values':values, 'projection':columns if case.get('projection') else len(columns),
                'secrets':any(name in exported for name in ('sql','db_resource','impl','cursor','_search_owned'))}
    except Exception as error:
        return {'error':type(error).__name__}


def search_select_contract(case):
    search = Search('contract/entity')
    search.add_order_by('id')
    select = search.get_select()
    try:
        for step in case.get('steps', []):
            owner = search if step.get('target') == 'search' else select
            getattr(owner, step['method'])(*step.get('args', []), **step.get('kwargs', {}))
        if case.get('copy'):
            select = select.copy() if case['copy'] == 'select' else search.copy().get_select()
            if case.get('copy_filter'):
                select.add_filter('code', case['copy_filter'])
            copied = select.execute()
            return {'copy': [row[1] for row in copied], 'original': [obj.get_value('code') for obj in search.get_sobjects()]}
        if case.get('execute'):
            rows = select.execute(search.get_sql())
            return [row[0] for row in rows]
        if case.get('select_count'):
            return select.execute_count(search.get_sql())
        if case.get('counts'):
            return {'search': search.get_count(), 'select': select.execute_count(search.get_sql()),
                    'rows': [obj.get_value('code') for obj in search.get_sobjects()]}
        return [obj.get_value('code') for obj in search.get_sobjects()]
    except Exception as error:
        return {'error': type(error).__name__}


def timestamp_filter_contract(case):
    from contextlib import closing
    import sqlite3
    from pyasm.search.database_impl import SqliteImpl, PostgresImpl
    try:
        if case.get('processor'):
            impl = PostgresImpl() if case['processor'] == 'postgres' else SqliteImpl()
            return impl.process_value('timestamp', case['value'], case.get('data_type','timestamp'))
        search = Search('contract/clock')
        conn = search.get_sql().get_connection()
        clock = '2026-10-09 12:00:00'
        conn.create_function('current_timestamp', 0, lambda: clock)
        with closing(sqlite3.connect(':memory:')) as clock_db:
            def fixed_datetime(*values):
                values = tuple(clock if value == 'now' else value for value in values) or (clock,)
                return clock_db.execute('SELECT DATETIME('+','.join('?' for value in values)+')', values).fetchone()[0]
            conn.create_function('datetime', -1, fixed_datetime)
            value = case['value']
            if case.get('generated'):
                value = search.get_database_impl().get_timestamp_now(**case['generated'])
            column = case.get('column','timestamp')
            if case.get('date_range'):
                search.add_op_filters([[column, 'between', value, value]])
            elif case.get('filter_document'):
                search.add_op_filters([[column, case.get('op','<'), value]])
            else:
                search.add_filter(column,value,op=case.get('op','<'),quoted=case.get('quoted'))
            return sorted(search.get_sobject_codes())
    except Exception as error:
        return {'error':type(error).__name__}


def filter_expression_contract(case):
    try:
        search = Search(case.get('search_type', 'contract/entity'))
        search.add_op_filters(case['filters'])
        search.add_order_by('id')
        return search.get_sobject_codes()
    except Exception as error:
        return {'error': type(error).__name__}


def site_contract(case):
    from unittest.mock import patch
    from pyasm.common import Config
    from pyasm.security import Site
    previous_sites = Container.get('sites')
    was_present = Container.has('sites')
    original_get = Config.get_value
    def configured(section, name, *args, **kwargs):
        if (section, name) == ('install', 'default_project'):
            return case.get('default_project', 'one')
        if (section, name) == ('security', 'site_class'):
            return case.get('site_class', '')
        return original_get(section, name, *args, **kwargs)
    try:
        if 'sites' in case:
            Container.put('sites', case['sites'])
        with patch.object(Config, 'get_value', side_effect=configured):
            if case.get('call'):
                owner = Site if case.get('class_call') else Site.get()
                result = getattr(owner, case['call'])(*case.get('args', []), **case.get('kwargs', {}))
            else:
                parent = Site.get() if case.get('site_root') else Search.get_by_code('contract/entity', 'A') if case.get('root') else None
                if case.get('naming'):
                    result = NamingUtil().eval_template(case['expression'], parent)
                else:
                    result = ExpressionParser().eval(case['expression'], parent,
                                                     single=case.get('single', False),
                                                     env_sobjects={'site_object': Site.get()} if case.get('site_env') else {})
            def describe(value):
                if isinstance(value, Site):
                    return dict(type=value.get_search_type(), project=value.get_project_code(), code=value.get_value('code'))
                if isinstance(value, list):
                    return [describe(item) for item in value]
                return value
            return describe(result)
    except Exception as error:
        return {'error': type(error).__name__}
    finally:
        if was_present:
            Container.put('sites', previous_sites)
        else:
            Container.remove('sites')


def install_connection_fixture(db):
    db.execute('ALTER TABLE connection ADD COLUMN s_status varchar(256)')
    admin_id = db.execute("SELECT id FROM project WHERE code='admin'").fetchone()[0]
    rows = [
        ('CON_PUBLISH', 'contract/entity?project=one', 1, 'contract/entity?project=one', 2, 'publish', None),
        ('CON_REVERSE', 'contract/entity?project=one', 2, 'contract/entity?project=one', 1, 'publish', None),
        ('CON_MIXED_PROJECT', 'contract/entity?project=one', 1, 'sthpw/project', admin_id, 'mixed', None),
        ('CON_MIXED_ENTITY', 'contract/entity?project=one', 1, 'contract/entity?project=one', 2, 'mixed', None),
        ('CON_CROSS', 'contract/entity?project=one', 1, 'contract/entity?project=two', 2, 'cross', None),
        ('CON_DANGLING', 'contract/entity?project=one', 1, 'contract/entity?project=one', 999, 'dangling', None),
        ('CON_RETIRED_OBJECT', 'contract/entity?project=one', 1, 'contract/entity?project=one', 3, 'retired_object', None),
        ('CON_RETIRED_LINK', 'contract/entity?project=one', 1, 'contract/entity?project=one', 2, 'retired_link', 'retired'),
        ('CON_QUOTED', 'contract/entity?project=one', 1, 'contract/entity?project=one', 2, "pub/O'Reilly", None),
        ('CON_OTHER_ROOT', 'contract/entity?project=two', 2, 'contract/entity?project=two', 1, 'publish', None),
    ]
    db.executemany("INSERT INTO connection (code,src_search_type,src_search_id,dst_search_type,dst_search_id,context,s_status,project_code) VALUES (?,?,?,?,?,?,?,'one')", rows)


def connection_contract(case):
    from pyasm.biz import SObjectConnection
    roots = [Search.get_by_search_key(key) for key in case.get('roots', [])]
    def records(objects):
        return [dict(type=obj.get_search_type(), code=obj.get_code()) for obj in objects]
    try:
        if case.get('core'):
            links = SObjectConnection.get_connections(roots, direction=case.get('direction', 'dst'),
                                                      context=case.get('context', ''))
            if case.get('return_search'):
                result = SObjectConnection.get_search(links, direction=case.get('direction', 'dst'), filters=case.get('filters'))
            else:
                return records(SObjectConnection.get_sobjects(links, direction=case.get('direction', 'dst'), filters=case.get('filters')))
        elif case.get('naming'):
            return NamingUtil().eval_template(case['expression'], roots[0])
        else:
            result = ExpressionParser().eval(case['expression'], roots,
                                             single=case.get('single', False), show_retired=case.get('show_retired', False))
        if isinstance(result, Search):
            return dict(search_type=result.get_search_type(), records=records(result.get_sobjects()))
        if isinstance(result, list) and result and hasattr(result[0], 'get_search_type'):
            return records(result)
        return result
    except Exception as error:
        return {'error': type(error).__name__}


def virtual_contract(case):
    import json
    from unittest.mock import patch
    from pyasm.search import SearchType, SObjectFactory

    instant = datetime.datetime(2026, 10, 9, 15, 24, 37, 123456)

    class FixedDateTime(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return instant if tz is None else instant.replace(tzinfo=datetime.timezone.utc).astimezone(tz)

        @classmethod
        def today(cls):
            return instant

    with patch('pyasm.biz.expression.datetime.datetime', FixedDateTime):
        if case.get('object'):
            factory = SObjectFactory.create if case.get('factory') else SearchType.create
            obj = factory('sthpw/virtual', case.get('columns'), case.get('row'))
            for name, value in case.get('values', {}).items():
                obj.set_value(name, value, **case.get('write_options', {}))
            result = dict(data=obj.get_data(), normal=obj.get_sobject_dict(**case.get('serialize', {})),
                          fast=obj.get_sobject_dict(mode='fast'),
                          column_info=SearchType.get_column_info('sthpw/virtual'),
                          column_types=SearchType.get_column_types('sthpw/virtual'),
                          search_type=obj.get_search_type(), database=obj.get_database(),
                          table=obj.get_table(), title=obj.get_search_type_obj().get_title())
        else:
            root = Search.get_by_code('contract/entity', 'A') if case.get('root') else None
            if case.get('naming'):
                result = NamingUtil().eval_template(case['expression'], root)
            else:
                result = ExpressionParser().eval(case['expression'], root, state=case.get('state', {}),
                                                 single=case.get('single', False),
                                                 dictionary=case.get('dictionary', False))
            if isinstance(result, list):
                result = [item.get_sobject_dict() if hasattr(item, 'get_sobject_dict') else item for item in result]
    return json.loads(json.dumps(result, default=str))


def variable_contract(case):
    parent = Search.get_by_code('contract/entity', 'A')
    variables = case.get('vars', {}).copy()
    try:
        if case.get('naming'):
            result = NamingUtil().eval_template(case['expression'], parent)
        else:
            result = ExpressionParser().eval(case['expression'], parent, vars=variables,
                                              single=case.get('single', False))
    except Exception as error:
        result = {'error': type(error).__name__}
    return {'result': result, 'vars': variables,
            'amount': Search.get_by_code('contract/entity', 'A').get_value('amount')}


def format_contract(case):
    import locale
    from unittest.mock import patch
    from pyasm.common import FormatValue
    value = case.get('value')
    if case.get('value_type') == 'datetime':
        value = datetime.datetime(*value)
    elif case.get('value_type') == 'timedelta':
        value = datetime.timedelta(**value)
    monetary = dict(decimal_point='.', thousands_sep=',', grouping=[3, 0],
                    mon_decimal_point='.', mon_thousands_sep=',', mon_grouping=[3, 0],
                    int_curr_symbol='USD ', currency_symbol='$', frac_digits=2, int_frac_digits=2,
                    p_cs_precedes=1, n_cs_precedes=1, p_sep_by_space=0, n_sep_by_space=0,
                    p_sign_posn=1, n_sign_posn=1, positive_sign='', negative_sign='-')
    date_locale = locale.setlocale(locale.LC_TIME) if case.get('date_locale') else None
    if date_locale is not None:
        locale.setlocale(locale.LC_TIME, 'C')
    try:
        # A shared monetary fixture, not a worker-wide locale mutation.
        with patch('locale.localeconv', return_value=monetary):
            if case.get('call') == 'core':
                return FormatValue().get_format_value(value, case['format'], case.get('format_option'))
            roots = [Search.get_by_search_key(key) for key in case.get('roots', [])]
            if case.get('call') == 'naming':
                return NamingUtil().eval_template(case['expression'], roots[0])
            return ExpressionParser().eval(case['expression'], roots or None,
                                           single=case.get('single', False), vars=case.get('vars', {}))
    except Exception as error:
        return {'error': type(error).__name__}
    finally:
        if date_locale is not None:
            locale.setlocale(locale.LC_TIME, date_locale)


def install_file_paths_fixture(db):
    db.execute("INSERT INTO snapshot_entity VALUES (2,'B')")
    db.execute("UPDATE snapshot SET search_type='contract/snapshot_entity?project=admin' WHERE code IN ('C0','C1','C2','C3')")
    db.execute("UPDATE file SET search_type='contract/snapshot_entity?project=admin' WHERE snapshot_code='C1'")
    db.execute("UPDATE file SET relative_dir='scenes/A' WHERE snapshot_code IN ('C1','CA')")
    db.execute("INSERT INTO file (code,file_name,relative_dir,snapshot_code,project_code,type,search_type,search_id,search_code) VALUES ('F0','current.ma','scenes/A','C0','admin','main','contract/snapshot_entity?project=admin',1,'A')")
    db.execute("INSERT INTO snapshot (code,search_type,search_id,search_code,project_code,context,version,is_current,is_latest,snapshot,login) VALUES ('PATH_OTHER','contract/snapshot_entity?project=admin',2,'B','admin','texture',1,TRUE,TRUE,'<snapshot/>','admin')")
    db.execute("INSERT INTO file (code,file_name,relative_dir,snapshot_code,project_code,type,search_type,search_id,search_code) VALUES ('PATH_TEXTURE','texture.png','other','PATH_OTHER','admin','image','contract/snapshot_entity?project=admin',2,'B')")
    for code, status, parent_code, project in [('PATH_RETIRED','retired','A','admin'), ('PATH_FOREIGN',None,'A','two')]:
        db.execute("INSERT INTO snapshot (code,search_type,search_id,search_code,project_code,context,version,is_current,is_latest,s_status,snapshot,login) VALUES (?,?,?,?,?,'publish',9,TRUE,TRUE,?,'<snapshot/>','admin')",
                   (code, 'contract/snapshot_entity?project=' + project, 1, parent_code, project, status))
        db.execute("INSERT INTO file (code,file_name,relative_dir,snapshot_code,project_code,type,search_type,search_id,search_code) VALUES (?,?,?,?,?,'main',?,1,?)",
                   (code + '_FILE', code + '.ma', 'excluded', code, project, 'contract/snapshot_entity?project=' + project, parent_code))
    db.execute("INSERT INTO snapshot (code,search_type,search_id,search_code,project_code,context,version,is_current,is_latest,snapshot,login) VALUES ('PATH_QUOTED','contract/snapshot_entity?project=admin',1,'A','admin',?,1,TRUE,TRUE,'<snapshot/>','admin')", ("publish/O'Reilly",))
    db.execute("INSERT INTO file (code,file_name,relative_dir,snapshot_code,project_code,type,search_type,search_id,search_code) VALUES ('PATH_QUOTED_FILE','quoted.ma','scenes/A','PATH_QUOTED','admin','main','contract/snapshot_entity?project=admin',1,'A')")


def file_paths_contract(case):
    roots = [Search.get_by_search_key(key) for key in case.get('roots', [])]
    if case.get('naming'):
        value = NamingUtil().eval_template(case['expression'], roots[0])
    else:
        try:
            value = ExpressionParser().eval(case['expression'], roots or None,
                                           single=case.get('single', False), vars=case.get('vars', {}))
        except Exception as error:
            if not case.get('quoted_context'):
                raise
            return {'error': type(error).__name__}
    # Runtime-owned repository roots differ between the isolated installations.
    def portable(path):
        for name, base in [('assets', Environment.get_asset_dir()), ('web', Environment.get_web_dir())]:
            if path.startswith(base + '/'):
                return '<' + name + '>' + path[len(base):]
        raise AssertionError('Expression returned a path outside its selected repository root: ' + path)
    return [portable(path) for path in value] if isinstance(value, list) else (portable(value) if value else value)


def expression_contract():
    xp = ExpressionParser()
    parent = Search.get_by_code('contract/snapshot_entity', 'A')
    first = Search.get_by_code('sthpw/snapshot', 'C0')
    second = Search.get_by_code('sthpw/snapshot', 'C1')
    third = Search.get_by_code('sthpw/snapshot', 'C2')
    objects = [first, second, third]
    expressions = (
        '', '1+2*3', '(1+2)*3', '5/0', '-2+3', "'hello'+' world'",
        "'abc'=~'^a'", "'abc'!~'^z'", '@GET(.version)', '@GETALL(.revision)',
        '@SUM(.version)', '@AVG(.version)', '@MIN(.version)', '@MAX(.version)',
        '@COUNT()', '@COUNT(@SOBJECT())', '@FLOOR(2.8)', '@UNIQUE(@GET(.version))',
        "@IF(@GET(.version)>1,'new','old')", "@CASE(1=0,'no',1=1,'yes')",
        "@JOIN(@GET(.code),'|')", "@FOREACH(@GET(.version),'v%02d','|')",
        "@SUBSTITUTE('%s_%s',@GET(.code),@GET(.version))",
        "@STARTSWITH(@GET(.code),'C')", "@ENDSWITH(@GET(.code),'0')",
        "@REPLACE(@GET(.code),'C','S')", '@GET(project.code)', '@GET(login.login)',
        '@GET(.version)+1', 'v{@GET(.version),%03d}',
        "{@GET(.timestamp),%Y-%m-%d}", "{@GET(.timestamp)+@RELTIME(days=1),%Y-%m-%d}", '@EVAL(2*3)',
        "@GET(sthpw/snapshot['code','C1'].version)",
        "@COUNT(sthpw/snapshot['version','2']['context','publish'])",
    )
    results = []
    for expression in expressions:
        results.append(xp.eval(expression, objects if 'sthpw/snapshot[' not in expression else None))
    selected = xp.eval("@SOBJECT(sthpw/snapshot['version','2']['context','publish'])")
    query = xp.eval("@SEARCH(sthpw/snapshot['version','2']['context','publish'])")
    cached_query = Search('sthpw/snapshot')
    cached_query.add_filter('context', 'publish')
    cached_query.add_filter('version', 2)
    cached_query.add_order_by('revision')
    cached_query.get_sobjects()
    from_search = xp.eval('@GET(sthpw/snapshot.code)', search=cached_query)
    parent_values = xp.eval('@GET(parent.code)', objects)
    dictionary = xp.eval('@GET(parent.code)', objects, dictionary=True)
    single = xp.eval('@GET(.code)', objects, single=True)
    forced_list = xp.eval('1+2', list=True)
    retired = xp.eval("@GET(sthpw/snapshot['code','C3'].version)", show_retired=True)
    empty = xp.eval("@GET(sthpw/snapshot['code','missing'].code)", single=True)
    variable = xp.eval("'prefix_'+$NAME", vars={'NAME': 'Тест'})
    env = xp.eval('@GET(snapshot.version)', parent, env_sobjects={'snapshot': second})
    second.set_value('context', 'expression/named', temp=True)
    second.set_value('snapshot_type', 'file', temp=True)
    naming = Naming.get(parent, second)
    util = NamingUtil()
    filename = util.naming_to_file('{@GET(.code)}_{$BASEFILE}.{$EXT}', parent, second,
                                   file=Search.get_by_code('sthpw/file', 'F1'))
    directory = util.naming_to_dir('{$PROJECT}/{@GET(snapshot.version)}', parent, second)
    template = util.eval_template('{$LOGIN}_{@GET(.code)}', parent)
    dates = xp.get_date_vars()

    def outcome(call):
        try:
            return call()
        except Exception as error:
            return type(error).__name__

    # Intentional bug fixes are compared with independent expectations.
    xp.clear_cache()
    env_first = xp.eval('@GET(snapshot.version)', parent, env_sobjects={'snapshot': first})
    env_second = xp.eval('@GET(snapshot.version)', parent, env_sobjects={'snapshot': second})
    fixes = {
        'env_cache': [env_first, env_second],
        'numeric_filter': outcome(lambda: xp.eval("@COUNT(sthpw/snapshot['version',2]['context','publish'])")),
        'years': sorted(key for key in dates if 'YEAR' in key and ('AGO' in key or 'AHEAD' in key)),
        'empty_case': outcome(lambda: xp.eval("@CASE(@GET(sthpw/snapshot['code','missing'].code),'yes',1=1,'fallback')")),
    }
    first.set_value('description', '""" + str(6 * 7) + """', temp=True)
    fixes['field_as_code'] = outcome(lambda: xp.eval("@GET(.description)+'suffix'", first))
    fixes['quoted_var'] = outcome(lambda: xp.eval("$NAME", vars={'NAME': "O'Reilly"}))
    fixes['quoted_filter'] = outcome(lambda: xp.eval("@GET(sthpw/snapshot['description',$NAME].code)", vars={'NAME': "O'Reilly"}))
    Container.put('Expression::extra_filters', {'sentinel': []})
    Container.put('Expression::return_mode', 'sentinel')
    outcome(lambda: xp.eval('@BOGUS()', extra_filters={'sthpw/snapshot': [['code', 'missing']]}))
    fixes['state_after_error'] = [Container.get('Expression::extra_filters'), Container.get('Expression::return_mode')]
    return {'results': results, 'selected': [obj.get_code() for obj in selected],
            'query': [obj.get_code() for obj in query.get_sobjects()], 'search': from_search,
            'dictionary': dictionary, 'parents': parent_values, 'single': single, 'list': forced_list, 'empty': empty,
            'retired': retired, 'vars': variable, 'env': env, 'naming': naming.get_code(),
            'filename': filename, 'directory': directory, 'template': template,
            'dates': dates['NEXT_DAY']-dates['TODAY'] == datetime.timedelta(days=1),
            'fixes': fixes}
