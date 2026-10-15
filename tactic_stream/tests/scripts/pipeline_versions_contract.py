"""Identical Pipeline calls on original/native cores, using owned records only."""
from pyasm.biz import Pipeline
from pyasm.command import Command, Trigger, Workflow
from pyasm.common import Environment
from pyasm.search import Search, SearchType
from pyasm.security import Security
from tactic.core.pipeline_commands import PipelineSaveCbk
from tactic.core.process_commands import NewProcessInfoCmd

SCRIPT = "from pyasm.biz import Note\nfrom pyasm.search import Search\nparent = input['sobject']\nif isinstance(parent, dict):\n    parent = Search.get_by_search_key(parent['__search_key__'])\nNote.create(parent, 'frozen action', process=input['process'])\nreturn True"

class Setup(Command):
    def execute(self):
        self.get_transaction().set_sync(False)
        from tactic.ui.tools.pipeline_wdg import PipelineSaveCmd, PipelinePropertyCbk
        create = PipelineSaveCmd(name='Empty pipeline', category='Fixture')
        create.execute()
        pipeline = Pipeline.create('Version fixture', '', 'contract/dep_parent',
            '<pipeline><process name="publish" type="action"/><process name="gate" type="progress"/></pipeline>', code='PV_MAIN')
        pipeline.update_dependencies()
        NewProcessInfoCmd(pipeline_code=pipeline.get_code(), process='publish', node_type='action', version=2,
            default={'script': SCRIPT, 'execute_mode': 'same process,same transaction'}).execute()
        PipelinePropertyCbk(pipeline_code=pipeline.get_code(), process='publish', flag=True, version=1).execute()
        NewProcessInfoCmd(pipeline_code=pipeline.get_code(), process='gate', node_type='progress', version=2,
            progress={'related_search_type': 'contract/dep_child', 'related_process': 'work'}).execute()
        pipeline.save_version()
        second = pipeline.save_version()
        parent = SearchType.create('contract/dep_parent')
        parent.set_value('code', 'PV_PARENT')
        parent.set_value('pipeline_code', second.get_code())
        parent.commit()

def version_summary(pipeline):
    definition = pipeline.get_process_sobject('publish')
    search = Search('config/trigger')
    search.add_filter('process', definition.get_code())
    trigger = search.get_sobject()
    path = trigger.get_value('script_path') if trigger else ''
    folder, _, title = path.rpartition('/')
    search = Search('config/custom_script')
    search.add_filter('folder', folder)
    search.add_filter('title', title)
    script = search.get_sobject()
    gate = pipeline.get_process_sobject('gate')
    progress = (gate.get_json_value('workflow') or {}).get('progress') or {}
    listener = Search.get_by_code('config/trigger', progress.get('trigger_code')) if progress.get('trigger_code') else None
    owner = (listener.get_json_value('data') or {}) if listener else {}
    workflow = definition.get_json_value('workflow') or {}
    return {'version': pipeline.get_value('version'), 'parent_code': pipeline.get_value('parent_code'),
        'xml_code_matches': pipeline.get_process('publish').get_attribute('process_code') == definition.get_code(),
        'trigger_uses_own_script': folder == '_triggers/' + pipeline.get_code(),
        'script': script.get_value('script') if script else None,
        'workflow_owner_matches': workflow.get('pipeline_code') == pipeline.get_code(),
        'progress_owner_matches': owner.get('pipeline_code') == pipeline.get_code() and owner.get('process_code') == gate.get_code(),
        'workflow': {key: value for key, value in workflow.items() if key != 'pipeline_code'}}

def run(case):
    if Environment.get_security() is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    Command.execute_cmd(Setup())
    search = Search('sthpw/pipeline')
    search.add_filter('parent_code', 'PV_MAIN')
    search.add_order_by('version')
    versions = search.get_sobjects()
    definitions = Search('config/process')
    definitions.add_filter('pipeline_code', 'PV_MAIN')
    definitions.add_filter('process', 'publish')
    empty = Search('sthpw/pipeline')
    empty.add_filter('name', 'Empty pipeline')
    return {'versions': [version_summary(pipeline) for pipeline in versions],
            'original_workflow': Pipeline.get_by_code('PV_MAIN').get_process_sobject('publish').get_json_value('workflow'),
            'properties': definitions.get_sobject().get_json_value('workflow'),
            'created_category': empty.get_sobject().get_value('category')}

def native_lifecycle():
    """Saved versions execute after edits to the current script; rollback is atomic."""
    pipeline = Pipeline.get_by_code('PV_MAIN')
    class EditAndSwitch(Command):
        def execute(self):
            self.get_transaction().set_sync(False)
            NewProcessInfoCmd(pipeline_code=pipeline.get_code(), process='publish', node_type='action', version=2,
                default={'script': SCRIPT.replace('frozen action', 'current action'), 'execute_mode': 'same process,same transaction'}).execute()
            parent = Search.get_by_code('contract/dep_parent', 'PV_PARENT')
            parent.set_value('pipeline_code', pipeline.get_code())
            parent.commit()
            Pipeline.set_to_latest(parent)
            Workflow().init(quiet=True)
            Trigger.call(self, 'process|pending', {'sobject': parent, 'pipeline': Pipeline.get_by_sobject(parent), 'process': 'publish'})
            Pipeline.set_to_versionless(parent)
            Trigger.call(self, 'process|pending', {'sobject': parent, 'pipeline': pipeline, 'process': 'publish'})
    Command.execute_cmd(EditAndSwitch())
    parent = Search.get_by_code('contract/dep_parent', 'PV_PARENT')
    return {'pipeline_code': parent.get_value('pipeline_code'),
            'notes': [note.get_value('note') for note in parent.get_related_sobjects('sthpw/note')]}

def templates():
    class ApplyTemplate(Command):
        def execute(self):
            self.get_transaction().set_sync(False)
            # A differently named old template must never supply this definition.
            decoy = Pipeline.create('Decoy', '', 'contract/dep_parent',
                '<pipeline><process name="work" type="manual"/></pipeline>', code='DECOY/__TEMPLATE__')
            decoy.update_dependencies()
            obj = decoy.get_process_sobject('work')
            obj.set_value('checkin_mode', 'decoy')
            obj.commit()
            template = Pipeline.create('VFX Processes', '', 'contract/dep_parent',
                '<pipeline><process name="work" type="manual" label="Template label" color="#112233" xpos="999"/></pipeline>', code='PV/__TEMPLATE__')
            template.update_dependencies()
            obj = template.get_process_sobject('work')
            obj.set_value('checkin_mode', 'copy')
            obj.commit()
            xml = template.get_pipeline_xml()
            xml.set_attribute(xml.get_nodes('pipeline/process')[0], 'process_code', obj.get_code())
            template.set_value('pipeline', xml.to_string())
            template.commit()
            target = Pipeline.create('Template target', '', 'contract/dep_parent',
                '<pipeline><process name="work" type="manual" xpos="10"/></pipeline>', code='PV_TEMPLATE_TARGET')
            PipelineSaveCbk(search_key=target.get_search_key(),
                pipeline='<pipeline><process name="work" type="manual" xpos="10"/></pipeline>').execute()
            return target.get_code()
    code = Command.execute_cmd(ApplyTemplate())
    pipeline = Pipeline.get_by_code(code)
    result = pipeline.get_process_attrs('work').copy()
    result['process_code_matches'] = result.pop('process_code', None) == pipeline.get_process_sobject('work').get_code()
    result['checkin_mode'] = pipeline.get_process_sobject('work').get_value('checkin_mode')
    return result
