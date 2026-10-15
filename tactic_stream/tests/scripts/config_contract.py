"""One unchanged backend config script for original and native TACTIC."""
from pathlib import Path
import tempfile

from pyasm.common import Environment
from pyasm.command import Command, Trigger
from pyasm.search import Search, SearchType, WidgetDbConfig, WidgetDbConfigCache, DbContainer, SqlException
from pyasm.biz import Project, ProjectSetting
from pyasm.security import Security
from tactic.command import PluginInstaller


class MarkTrigger(Trigger):
    def execute(self):
        ProjectSetting.create(self.get_input()['setting_key'], 'called')
        return 'called'


def entry(search_type, data):
    lines = ['insert = SearchType.create(%r)' % search_type]
    lines.extend('insert.set_value(%r, %r)' % (key, value) for key, value in data.items())
    return '#-- Start Entry --#\n' + '\n'.join(lines) + '\n#-- End Entry --#\n'


class Run(Command):
    def execute(self):
        self.get_transaction().set_sync(False)
        stype = self.case.get('search_type', 'contract/entity')
        view = 'contract_' + self.case.get('name', 'config')
        setting_key = 'package_value_' + view
        trigger_key = 'trigger_result_' + view
        event = 'config_contract_' + view
        if self.case.get('warm_cache'):
            Trigger.call(self, event, {'setting_key': trigger_key})
        xml = '<config><!-- preserved --><%s><element name="name" title="Имя"><display class="custom.Cell"><color><![CDATA[blue]]></color></display></element></%s></config>' % (view, view)
        rows = {
            'config/widget_config': dict(code='WIDGET_' + view, search_type=stype, view=view, config=xml, priority=10),
            'config/prod_setting': dict(code='SETTING_' + view, key=setting_key, value='one', type='string'),
            'config/client_trigger': dict(code='CLIENT_' + view, event='client_contract', callback='example.callback'),
            'config/trigger': dict(code='TRIGGER_' + view, event=event,
                class_name='config_contract.MarkTrigger', mode='same process,same transaction'),
        }
        if self.case.get('extra_config'):
            rows.update({
                'config/pipeline': dict(code='CONFIG_PIPE_' + view, pipeline='<pipeline><process name="first" type="manual"/><process name="second" type="manual"/><connect from="first" to="second"/></pipeline>'),
                'config/custom_property': dict(code='PROPERTY_' + view, search_type=stype, name='amount', description='Параметр'),
                'config/ingest_session': dict(code='SESSION_' + view, title='Сессия', base_dir='/input', location='local', data='{}'),
                'config/ingest_rule': dict(code='RULE_' + view, spt_ingest_session_code='SESSION_' + view, title='Правило', rule='*.png', data='{}'),
                'config/translation': dict(code='TRANSLATION_' + view, name='label_' + view, en='Label', fr='Libellé'),
            })
        root = Path(Environment.get_tmp_dir())
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as directory:
            package = Path(directory)
            nodes = ''.join('<sobject search_type="%s" unique="true"/>' % st for st in rows)
            (package / 'manifest.xml').write_text('<manifest code="config_contract">' + nodes + '</manifest>', encoding='utf-8')
            for st, data in rows.items():
                (package / (st.replace('/', '_') + '.spt')).write_text(entry(st, data), encoding='utf-8')
            PluginInstaller(plugin_dir=str(package), register=True, verbose=False).execute()
        widget = WidgetDbConfig.get_by_search_type(stype, view)
        assert isinstance(widget, WidgetDbConfig)
        widget.append_display_element('amount', 'custom.Number', options={'precision': 2}, element_attrs={'title': 'Число'})
        widget.commit_config()
        widget = WidgetDbConfig.get_by_search_type(stype, view)
        result = dict(names=widget.get_element_names(), attrs=widget.get_element_attributes('name'),
            options=widget.get_display_options('amount'), handler=widget.get_display_handler('name'),
            cached_handler=WidgetDbConfigCache(stype, view).get_display_handler('name'))
        if self.case.get('extra_config'):
            from pyasm.biz import Pipeline, ProjectPipeline, CustomProperty
            pipeline = Pipeline.get_by_code('CONFIG_PIPE_' + view)
            assert isinstance(pipeline, ProjectPipeline)
            pipeline.set_pipeline(pipeline.get_value('pipeline'), cache=False)
            pipeline.update_dependencies()
            processes = Search('config/process')
            processes.add_filter('pipeline_code', pipeline.get_code())
            processes.add_order_by('sort_order')
            prop = Search.get_by_code('config/custom_property', 'PROPERTY_' + view)
            assert isinstance(prop, CustomProperty)
            if self.case.get('bug') == 'property_drop':
                sql = DbContainer.get(Project.get_db_resource_by_search_type(stype))
                sql.do_update('CREATE VIEW property_drop_view AS SELECT amount FROM "%s"' % SearchType.get(stype).get_table())
                prop.delete(log=True)
            else:
                prop.delete()
            result['extra_config'] = dict(pipeline_class=type(pipeline).__name__, processes=pipeline.get_process_names(),
                process_rows=[obj.get_value('process') for obj in processes.get_sobjects()],
                property_rows=Search('config/custom_property').get_count(), amount_column=SearchType.column_exists(stype, 'amount'),
                rule=Search.get_by_code('config/ingest_rule', 'RULE_' + view).get_value('spt_ingest_session_code'),
                session=Search.get_by_code('config/ingest_session', 'SESSION_' + view).get_value('title'),
                translation=Search.get_by_code('config/translation', 'TRANSLATION_' + view).get_value('fr'))
        ProjectSetting.add_value_by_key(setting_key, 'two')
        ProjectSetting.add_value_by_key(setting_key, 'two')
        result['setting'] = ProjectSetting.get_seq_by_key(setting_key)
        # Refresh explicitly for the ordinary source comparison; cache defects
        # are checked separately with both source/native expectations.
        Trigger.clear_db_cache()
        if not self.case.get('warm_cache'):
            from pyasm.common import Container
            Container.put(Trigger.TRIGGER_EVENT_KEY, None)
        handlers = Trigger.call(self, event, {'setting_key': trigger_key})
        result['trigger'] = [handler.get_ret_val() for handler in handlers]
        result['trigger_setting'] = ProjectSetting.get_value_by_key(trigger_key)
        if self.case.get('bug') == 'move':
            error = None
            try:
                widget.move_element_left('amount')
            except Exception as exception:
                error = type(exception).__name__
            result['move'] = dict(error=error, names=widget.get_element_names())
        if self.case.get('fail'):
            raise ValueError('late config failure')
        return result


def run(case):
    previous = Environment.get_security()
    if previous is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    try:
        command = Run()
        command.case = case
        try:
            result = Command.execute_cmd(command)
        except ValueError as error:
            if not case.get('fail'):
                raise
            result = dict(error=str(error))
        except (SqlException, AssertionError) as error:
            if case.get('bug') != 'property_drop':
                raise
            result = dict(error=type(error).__name__)
        view = 'contract_' + case.get('name', 'config')
        search = Search('config/widget_config')
        search.add_filter('view', view)
        result['widget_rows'] = search.get_count()
        return result
    finally:
        Environment.set_security(previous)
