"""Exercise the normal upload/template/project API with the supplied cg.zip."""
import argparse
import ast
import json
import os
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import urllib.error
import urllib.request
from xmlrpc.client import ServerProxy


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('action', choices=['install', 'create', 'verify', 'seed', 'refresh'])
    parser.add_argument('--url', default='http://127.0.0.1:8082')
    parser.add_argument('--code', default='cg_test')
    parser.add_argument('--archive', default=str(Path(__file__).resolve().parents[2] / 'cg.zip'))
    parser.add_argument('--password-file', default=str(Path(__file__).resolve().parents[1] / 'deploy/docker/.local/admin-password'))
    args = parser.parse_args()

    def post(path, data, content_type='application/json'):
        request = urllib.request.Request(args.url + path, data=data, headers={'Content-Type': content_type})
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                result = json.load(response)
                return result['result'] if isinstance(result, dict) and 'result' in result else result
        except urllib.error.HTTPError as error:
            raise RuntimeError(error.read().decode()) from None

    def rpc(method, *values):
        return post('/admin/rpc', json.dumps({'method': method, 'args': values}).encode())

    password = Path(args.password_file).read_text().strip() if args.password_file else os.environ['STREAM_CHECK_PASSWORD']
    token = rpc('get_ticket', 'admin', password)
    context = {'ticket': token, 'project': 'admin', 'language': 'python'}
    if args.action == 'install':
        archive = Path(args.archive)
        boundary = 'stream-cg-template-upload'
        body = (f'--{boundary}\r\nContent-Disposition: form-data; name="login_ticket"\r\n\r\n{token}\r\n'
                f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{archive.name}"\r\n'
                'Content-Type: application/zip\r\n\r\n').encode()
        body += archive.read_bytes() + f'\r\n--{boundary}--\r\n'.encode()
        uploaded = post('/tactic/admin/UploadServer/', body, 'multipart/form-data; boundary=' + boundary)
        print(rpc('execute_cmd', context, 'tactic.ui.app.ProjectTemplateInstallCmd',
                  {'paths': [uploaded[0].replace('\\', '/').split('/')[-1]]}))
    elif args.action == 'refresh':
        # Apply the corrected importer to references in this already imported
        # test project without reimporting records or replacing custom scripts.
        context['project'] = args.code
        source = """from tactic.command import ProjectTemplateInstallerCmd
from pyasm.search import Search
server.set_project(project_code)
cmd = ProjectTemplateInstallerCmd()
cmd.project_code = project_code
cmd.template_project_code = template_code
count = 0
for kind in ('config/process', 'config/trigger', 'sthpw/pipeline'):
    search = Search(kind)
    search.set_show_retired(True)
    if kind == 'sthpw/pipeline':
        search.add_filter('project_code', project_code)
    for obj in search.get_sobjects():
        original = obj.get_data()
        cmd.remap_pipeline_references(obj)
        if obj.get_data() != original:
            obj.commit(triggers=False)
            count += 1
return count
"""
        with zipfile.ZipFile(args.archive) as archive:
            template_code = ET.fromstring(archive.read('cg/manifest.xml')).get('code')
        with ServerProxy(args.url + '/tactic/admin/Api/', allow_none=True) as server:
            print(server.execute_python_script(context, '', {'code': source, 'project_code': args.code, 'template_code': template_code}))
    elif args.action == 'create':
        catalog = post('/admin/project-creation', json.dumps({'ticket': token, 'project': 'admin'}).encode())
        template = next(row for row in catalog['templates'] if row['value'].endswith('/cg.zip'))
        code, path = template['value'].split('|', 1)
        with ServerProxy(args.url + '/tactic/admin/Api/', allow_none=True) as server:
            result = server.execute_cmd(context, 'tactic.command.ProjectTemplateInstallerCmd',
                  {'project_code': args.code, 'project_title': 'CG Test', 'template_code': code,
                   'path': path, 'verbose': False})
            print(result)
    elif args.action == 'seed':
        context['project'] = args.code
        source = Path(__file__).with_name('cg_sample_data.py').read_text(encoding='utf-8')
        source += "\nreturn run(server, kwargs['project_code'], disable_telegram=True)\n"
        with ServerProxy(args.url + '/tactic/admin/Api/', allow_none=True) as server:
            print(server.execute_python_script(context, '', {'code': source, 'project_code': args.code}))
    else:
        context['project'] = args.code
        with ServerProxy(args.url + '/tactic/admin/Api/', allow_none=True) as server:
            print(ast.literal_eval(server.query(context, 'sthpw/project', [('code', args.code)])))
            for name in ['assets_category', 'scenes', 'shot', 'assets', 'assets_in_assets',
                         'assets_in_scenes', 'texture', 'texture_in_assets']:
                rows = ast.literal_eval(server.query(context, 'cg/' + name, [], None, ['id asc'], False, 10, 0))
                print('cg/' + name, 'rows=', len(rows))
        navigation = post('/admin/navigation', json.dumps({'ticket': token, 'project': args.code}).encode())
        print('navigation', json.dumps(navigation, ensure_ascii=False)[:1800])


if __name__ == '__main__':
    main()
