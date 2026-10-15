"""The same template export calls in original TACTIC and native vendors."""
import ast
from pathlib import Path
import tempfile
from unittest.mock import patch
import zipfile
from xml.etree import ElementTree as ET

from pyasm.biz import Project
from pyasm.command import Command
from pyasm.common import Environment
from pyasm.search import Search, SearchType
from pyasm.security import Security
from tactic.command import ProjectTemplateCreatorCmd


def setup(search_type, different_type=False):
    code = Project.get_project_code()
    kind = 'template_base' if different_type else code
    if not Search.get_by_code('sthpw/project_type', kind):
        obj = SearchType.create('sthpw/project_type')
        obj.set_value('code', kind)
        obj.set_value('type', 'simple')
        obj.commit(triggers=False)
    project = Project.get()
    project.set_value('type', kind)
    project.commit(triggers=False)
    search = Search('sthpw/search_object')
    search.add_filter('search_type', code + '/template_entity')
    obj = search.get_sobject() or SearchType.create('sthpw/search_object')
    for name, value in dict(search_type=code + '/template_entity', namespace=code,
                            database='{project}', table_name=SearchType.get(search_type).get_table(),
                            class_name='pyasm.search.SObject').items():
        obj.set_value(name, value)
    obj.commit(triggers=False)
    obj = Search.get_by_code('config/custom_script', 'TEMPLATE_SCRIPT') or SearchType.create('config/custom_script')
    new = obj.get_id() == -1
    for name, value in dict(id=800, code='TEMPLATE_SCRIPT', folder='template', title='hello',
                            script='return 42\n# Точный текст').items():
        obj.set_value(name, value)
    obj.set_force_insert(new)
    obj.commit(triggers=False)
    obj = Search.get_by_code('sthpw/notification', 'EXPORT_CONTRACT_NOTICE') or SearchType.create('sthpw/notification')
    for name, value in dict(code='EXPORT_CONTRACT_NOTICE', project_code=code,
                            event='export_contract_notice', subject='Точное уведомление').items():
        obj.set_value(name, value)
    obj.commit(triggers=False)


def run(case):
    previous = Environment.get_security()
    if previous is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    try:
        root = Path(Environment.get_tmp_dir())
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as directory:
            base = Path(directory)
            package = base / Project.get_project_code()
            package.mkdir()
            (package / 'config_custom_script.spt').write_bytes(b'previous template')
            cmd = Command()
            def execute():
                cmd.get_transaction().set_sync(False)
                setup(case.get('search_type', 'contract/entity'), case.get('namespace', False))
                creator = ProjectTemplateCreatorCmd(base_dir=str(base))
                creator.execute()
                cmd.zip_path = creator.get_zip_path()
                if case.get('fail'):
                    raise ValueError('late template export')
            cmd.execute = execute
            with patch.object(Environment, 'get_dist_dir', return_value=str(base / 'dist')):
                try:
                    Command.execute_cmd(cmd)
                except ValueError:
                    if not case.get('fail'):
                        raise
                    return dict(previous=(package / 'config_custom_script.spt').read_bytes() == b'previous template',
                                zip_exists=Path(cmd.zip_path).exists())
            with zipfile.ZipFile(cmd.zip_path) as archive:
                zip_manifest = any(name.endswith('/manifest.xml') for name in archive.namelist())
            manifest = ET.parse(package / 'manifest.xml').getroot()
            scripts = (package / 'config_custom_script.spt').read_text(encoding='utf-8')
            values = []
            for line in ast.walk(ast.parse(scripts)):
                if isinstance(line, ast.Call) and isinstance(line.func, ast.Attribute) and line.func.attr == 'set_value':
                    if line.args and ast.literal_eval(line.args[0]) == 'script':
                        values.append(ast.literal_eval(line.args[1]))
            seq_max = int(manifest.find("sobject[@search_type='config/custom_script']").get('seq_max'))
            notice = (package / 'sthpw_notification.spt').read_text(encoding='utf-8')
            return dict(definition=manifest.find("search_type[@code='%s/template_entity']" % Project.get_project_code()) is not None,
                        script='return 42\n# Точный текст' if 'return 42\n# Точный текст' in values else None,
                        sequence_floor=seq_max >= 800, zip_manifest=zip_manifest,
                        notification=manifest.find("sobject[@search_type='sthpw/notification']") is not None,
                        notice_subject='Точное уведомление' in notice)
    finally:
        Environment.set_security(previous)
