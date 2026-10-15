"""Real CG template and browser checks, with an owned server stopped in finally."""
import os
import json
import multiprocessing
from pathlib import Path
import subprocess
import sys
from xmlrpc.client import Binary

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src'), str(ROOT / 'tests')]
from test_transport import Transport
from test_cg_template import exercise
from pyasm.security.authenticator import hash_password
from tactic_stream.server.api import Api

def main():
    Transport.setUpClass()
    try:
        with Transport.store.connection(write=True) as db:
            db.execute("UPDATE login SET password=? WHERE login='admin'", (hash_password('plugin-test-password'),))
        exercise(Transport.store, 'browser')
        api = Api(Transport.store)
        context = dict(ticket=api.get_ticket('admin', 'plugin-test-password'), project='browser_ok')
        if 'mobile_commit_queue.mjs' in sys.argv:
            api.protocol = 'json'
            settings = api.dispatch('query',(context,'config/prod_setting'),dict(filters=[('key','versionless_mode')]))
            if settings: api.dispatch('update',(context,settings[0]['__search_key__'],dict(value='hardlink')))
            else: api.dispatch('insert',(context,'config/prod_setting',dict(key='versionless_mode',value='hardlink')))
        if 'mobile_items.mjs' in sys.argv or 'mobile_refinements.mjs' in sys.argv:
            for index in range(12):
                api.dispatch('insert', (context, 'cg/assets', dict(code='MOBILE_SCROLL_%02d' % index, name='Mobile scroll fixture %02d' % index,
                             description='Private touch navigation fixture')))
        for name in ('publish/model', 'publish/look'):
            api.dispatch('insert', (context, 'sthpw/task', dict(process='publish', context=name, description=name)),
                         dict(parent_key='cg/assets?project=browser_ok&code=DEMO_ROBOT'))
        if 'mobile_refinements.mjs' in sys.argv:
            parent = 'cg/assets?project=browser_ok&code=DEMO_ARM'
            api.dispatch('insert', (context, 'sthpw/task', dict(process='model', context='model', description='Mobile process chooser fixture')), dict(parent_key=parent))
            api.dispatch('insert', (context, 'sthpw/note', dict(process='model', context='model', note='Mobile process chooser fixture')), dict(parent_key=parent))
        api.dispatch('upload_file', (context, 'browser-main.txt', Binary(b'Continuous tree file')))
        api.dispatch('simple_checkin', (context, 'cg/assets?project=browser_ok&code=DEMO_ROBOT', 'publish', 'browser-main.txt'),
                     dict(file_type='main', create_icon=False, keep_file_name=True))
        api.dispatch('upload_file', (context, 'Robot Arm.md', Binary(b'# Robot Arm')))
        api.dispatch('simple_checkin', (context, 'cg/assets?project=browser_ok&code=DEMO_ARM', 'publish', 'Robot Arm.md'),
                     dict(file_type='main', create_icon=False, keep_file_name=True))
        snapshot = api.dispatch('get_snapshot', (context, 'cg/assets?project=browser_ok&code=DEMO_ARM'), dict(context='publish', version='-1', versionless=True))
        api.dispatch('update', (context, snapshot['__search_key__'], dict(description='')))
        if 'mobile_preview.mjs' in sys.argv:
            import io
            from PIL import Image, ImageDraw
            image = Image.new('RGB',(240,160),'#2c5473')
            draw = ImageDraw.Draw(image)
            draw.rectangle((30,20,180,140),fill='#ecb656')
            draw.rectangle((60,45,145,100),fill='#588cba')
            image_data = io.BytesIO(); image.save(image_data,format='PNG')
            api.dispatch('upload_file',(context,'mobile-preview.png',Binary(image_data.getvalue())))
            api.dispatch('simple_checkin',(context,'cg/assets?project=browser_ok&code=DEMO_ARM','icon','mobile-preview.png'),dict(create_icon=True))
        if 'continuous_topology.mjs' in sys.argv:
            from pyasm.search import Search
            from pyasm.search.search import RequestContext, request_context
            from tactic_stream.server.result_items import relations, relation_search, select_labels
            with request_context(RequestContext(Transport.store, 'admin', 'browser_ok')):
                api.auth.bind_security('admin', context['ticket'])
                arm = Search.get_by_search_key('cg/assets?project=browser_ok&code=DEMO_ARM')
                metal = Search.get_by_search_key('cg/texture?project=browser_ok&code=DEMO_TEX_METAL')
                data = dict(project=dict(code='browser_ok'), schema=arm.get_schema().get_value('schema'),
                    stypes=[row.get_sobject_dict() for row in Search('sthpw/search_object').get_sobjects()],
                    views=[row.get_sobject_dict() for row in Search('config/widget_config').get_sobjects()],
                    pipelines=[], objects=[], related={})
                for pipeline in Search('sthpw/pipeline').get_sobjects():
                    row = pipeline.get_sobject_dict()
                    search = Search('config/process'); search.add_filter('pipeline_code', pipeline.get_code())
                    row['stypes_processes'] = [process.get_sobject_dict() for process in search.get_sobjects()]
                    data['pipelines'].append(row)
                for obj in (arm, metal):
                    row = obj.get_sobject_dict()
                    labels = select_labels(obj.get_base_search_type())
                    row['__category_labels__'] = {column: values[row[column]] for column, values in labels.items()
                        if column.endswith('_category_code') and row.get(column) in values}
                    snapshots = Search('sthpw/snapshot'); snapshots.add_parent_filter(obj)
                    row['__snapshots__'] = []
                    for snapshot in snapshots.get_sobjects():
                        snapshot_row = snapshot.get_sobject_dict()
                        snapshot_row['__files__'] = [dict(file.get_sobject_dict(), __fixture_path__=file.get_lib_path()) for file in snapshot.get_all_file_objects()]
                        row['__snapshots__'].append(snapshot_row)
                    data['objects'].append(row)
                    for branch in relations(obj):
                        data['related'][obj.get_code() + ':' + branch['search_type']] = [child.get_code() for child in relation_search(obj, branch).get_sobjects()]
                output = ROOT / '.screenshots/continuous-topology/native.json'
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
            subprocess.run([sys.executable, '-B', '-X', 'utf8', str(ROOT / 'tools/capture_result_topology.py')], check=True, timeout=60)
        for script in sys.argv[1:] or ['result_views.mjs']:
            result = subprocess.run(['node', 'tests/' + script, Transport.url], cwd=ROOT / 'frontend',
                env=dict(os.environ, PLAYWRIGHT_BROWSERS_PATH=str(ROOT / '.browser-cache'),
                         STREAM_CHECK_PASSWORD='plugin-test-password', STREAM_CHECK_PROJECT='browser_ok'), timeout=180)
            if result.returncode:
                raise SystemExit(result.returncode)
            if script == 'mobile_commit_queue.mjs':
                with Transport.store.connection() as db:
                    logs = db.execute("SELECT login,message FROM debug_log WHERE level='error'").fetchall()
                assert any(row['login'] == 'admin' and 'Mobile upload temporarily unavailable' in row['message'] for row in logs), 'Browser error missing from SQLite debug_log'
                assert any(row['login'] == 'admin' and 'Mobile runtime diagnostic' in row['message'] for row in logs), 'Runtime error missing from SQLite debug_log'
                assert all(context['ticket'] not in row['message'] for row in logs), 'Diagnostic leaked an authentication ticket'
                print('PASS: browser upload failure persisted in SQLite debug_log under the authenticated author')
                import io
                from PIL import Image
                from pyasm.search import Search
                from pyasm.search.search import RequestContext, request_context
                image = io.BytesIO(); Image.new('RGB',(8,8),(20,80,120)).save(image,format='PNG')
                api.dispatch('upload_file',(context,'mobile-note.png',Binary(image.getvalue())))
                api.dispatch('execute_cmd',(context,'tactic.ui.widget.discussion_wdg.DiscussionAddNoteCmd',
                    dict(search_key='cg/assets?project=browser_ok&code=DEMO_ARM',process='publish',note='Private mobile attachment check',files=['mobile-note.png'])))
                with request_context(RequestContext(Transport.store,'admin','browser_ok')):
                    api.auth.bind_security('admin',context['ticket'])
                    snapshots = Search('sthpw/snapshot'); snapshots.add_filter('context','attachment/publish/mobile-note.png')
                    rows = snapshots.get_sobjects()
                    original = next(row for row in rows if row.get_value('version') == 1)
                    latest = next(row for row in rows if row.get_value('version') == -1)
                    original_files = {file.get_value('type'):file.get_lib_path() for file in original.get_all_file_objects()}
                    latest_files = {file.get_value('type'):file.get_lib_path() for file in latest.get_all_file_objects()}
                    assert original_files.keys() == latest_files.keys()
                    assert all(os.path.samefile(path,latest_files[kind]) for kind,path in original_files.items()), 'Versionless attachment must link to numbered files'
                    assert Path(original_files['main']).read_bytes() == image.getvalue()
                print('PASS: native note PNG attachment with hard-linked main/web/icon versionless files')
    finally:
        Transport.tearDownClass()
        assert not Transport.thread.is_alive(), 'Owned fixture server remained running'
        assert not multiprocessing.active_children(), 'Owned fixture workers remained running'
        print('PASS: owned server thread and multiprocessing workers stopped')


if __name__ == '__main__':
    main()
