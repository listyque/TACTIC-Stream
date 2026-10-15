"""Fresh native CG table values for identical QML/Vue captures; private database only."""
import ast
import datetime
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from unittest.mock import patch

from pyasm.common import Config
from pyasm.command import Command
from pyasm.search import Search, SearchType
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from tactic_stream.server.api import Api
from tactic_stream.server.interface import read_interface
from tactic_stream.server.table_cells import read_table_cells
from tactic_stream.server.widget_configuration import read_widget_configuration
from tactic.ui.table.table_edit import TableCellEditCmd
from tactic.ui.table.task_inspector import TaskTableEditCmd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def write(operation):
    cmd = Command(); cmd.execute = operation; cmd.get_transaction().set_sync(False)
    return Command.execute_cmd(cmd)


with tempfile.TemporaryDirectory(prefix='private-table-', dir=HERE) as directory, patch.dict(os.environ, {'TACTIC_CONFIG_PATH':'','TACTIC_TMP_CONFIG_PATH':''}):
    assert Path(directory).resolve().is_relative_to(HERE)
    Config.reload_config()
    store = Store(Path(directory) / 'data'); store.initialize(hash_password('private-table-password'))
    api = Api(store); token = api.get_ticket('admin','private-table-password')
    api.dispatch('execute_cmd', (dict(ticket=token,project='admin',language='python'), 'tactic.command.ProjectTemplateInstallerCmd',
        dict(project_code='table_fixture', path=str(ROOT.parent/'cg.zip'),verbose=False)))
    try:
        with request_context(RequestContext(store,login='admin',project='table_fixture')):
            api.auth.bind_security('admin',token)
            from pyasm.biz import Pipeline
            pipelines = Search('sthpw/pipeline'); pipelines.add_filter('project_code','table_fixture'); pipelines.add_filter('search_type','cg/assets')
            pipeline = pipelines.get_sobject()
            assert pipeline is not None
            categories = {}
            for code,title in [('CHAR','Characters'),('PROP','Props'),('ENV','Environments')]:
                obj = SearchType.create('cg/assets_category'); obj.set_value('code',code); obj.set_value('name',title); write(lambda obj=obj:obj.commit(triggers=False)); categories[code]=obj
            objects = []
            for index,(title,category) in enumerate([('Hero Robot','CHAR'),('Robot Arm','PROP'),('Robot Body','PROP'),('Shared Tool','PROP'),('Workshop','ENV')]):
                obj = SearchType.create('cg/assets')
                for name,value in dict(code='TABLE_ASSET_' + str(index),name=title,description='Sample asset: '+title,keywords='demo cg '+title.split()[-1].lower(),assets_category_code=category,pipeline_code=pipeline.get_code()).items():
                    obj.set_value(name,value)
                write(lambda obj=obj:obj.commit(triggers=False)); objects.append(obj)
                for count in range(4 if index == 0 else 1):
                    note = SearchType.create('sthpw/note')
                    for name,value in dict(search_type=obj.get_search_type(),search_code=obj.get_code(),project_code='table_fixture',login='admin',context='publish',process='publish',note='Table capture sample').items():
                        note.set_value(name,value)
                    write(lambda note=note:note.commit(triggers=False))
                for process in Pipeline.get_by_code(pipeline.get_code()).get_process_names():
                    node = Pipeline.get_by_code(pipeline.get_code()).get_process(process)
                    if node.get_type() in ('action','condition','dependency'):
                        continue
                    task = SearchType.create('sthpw/task')
                    for name,value in dict(search_type=obj.get_search_type(),search_code=obj.get_code(),project_code='table_fixture',process=process,context=process,assigned='admin' if process == 'model' else '',status='',pipeline_code='task').items():
                        task.set_value(name,value)
                    write(lambda task=task:task.commit(triggers=False))
            # Read only the user's saved column layout; all records and writes above are private.
            with sqlite3.connect('file:' + str(ROOT/'data/db/cg_test.db') + '?mode=ro',uri=True) as db:
                xml = db.execute("SELECT config FROM spt_widget_config WHERE search_type='cg/assets' AND view='table' ORDER BY id DESC LIMIT 1").fetchone()[0]
            config = Search('config/widget_config'); config.add_filter('search_type','cg/assets'); config.add_filter('view','table'); config = config.get_sobject()
            config.set_value('config',xml); write(lambda:config.commit(triggers=False))
            definition = read_interface('cg/assets')
            unavailable = [element for element in definition['table']['elements'] if not element['cell']['supported']]
            assert not unavailable, unavailable
            keys = [obj.get_search_key() for obj in objects]
            cells = read_table_cells('cg/assets','table',keys)
            assert not [(key,name,cell['error']) for key,values in cells.items() for name,cell in values.items() if cell.get('error')]
            for obj in objects:
                # Both presenters use the same already formatted date label in this frozen fixture.
                cells[obj.get_search_key()]['timestamp'] = dict(text='5 days ago',tooltip='2026-10-09 00:00:00')
            data = dict(definition=definition,records=[{**obj.get_data(),'__search_key__':obj.get_search_key()} for obj in objects],cells=cells,
                configuration=read_widget_configuration('cg/assets'),accent=SearchType.get('cg/assets').get_value('color',no_exception=True) or '#e05757',
                captured=datetime.datetime.now().isoformat(timespec='seconds'))
            data['editors'] = {column:write(lambda column=column:TableCellEditCmd(search_type='cg/assets',view='table',column=column,search_keys=keys).execute()) for column in ('name','description','assets_category')}
            model = next(task for task in cells[keys[0]]['task_pipeline_panels']['tasks'] if task['process'] == 'model')
            data['task_editor'] = write(lambda:TaskTableEditCmd(source=dict(search_key=keys[0],task_key=model['taskSearchKey'],process=model['process'],context=model['context']), search_keys=keys).execute())
            # Exercise the alias through the real SelectWdg/DatabaseAction, not a fixture-only UI save.
            plan = data['editors']['assets_category']
            result = write(lambda:TableCellEditCmd(search_type='cg/assets',view='table',column='assets_category',search_keys=keys,
                action='save',plans=plan['plans'],value='PROP').execute())
            assert len(result['records']) == 5
            assert all(Search.get_by_search_key(key).get_value('assets_category_code') == 'PROP' for key in keys)
            assert write(lambda:TableCellEditCmd(search_type='cg/assets',view='table',column='assets_category',search_keys=keys,
                action='check',plans=plan['plans'],value='PROP').execute())['state'] == 'saved'
            for values in data['cells'].values():
                for task in values['task_pipeline_panels']['tasks']:
                    task['assignedLabel'] = task.get('assignedIdentity',{}).get('displayName') if task.get('assignedIdentity') else task['assigned'] or 'Not assigned'
            # Never persist the temporary ticket, data directory or credentials in UI fixtures.
            (HERE/'fixture.json').write_text(json.dumps(data,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
            print(json.dumps(dict(records=len(objects),columns=len(definition['table']['elements']),cell_errors=0,temporary_data=True)))
    finally:
        Config.reload_config()
