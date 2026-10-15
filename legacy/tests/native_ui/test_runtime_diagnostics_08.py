"""Environment URL/cache/isolated-launch and read-only schema service checks."""
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock,patch
import zipfile
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'src/client'),str(ROOT/'tools/local')]
import validate_pip_zipapp as pipzip
from managed_seed_08 import create_seed
from tactic.core.schema_health import CORE_REQUIRED,CONFIG_REQUIRED,inspect_schema
from tactic.ui_api.system_diagnostics import schema_diagnostics
from tactic.ui_api.admin_service import AdminService
from tactic.ui_api.version import VERSION,BUILD_VERSION
from tactic.ui_api.contracts import ApiError

class PipTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.p=Path(self.temp.name)/'pip.pyz'
    def zip(self,main="print('pip 26.2.1 from test (python 3.13)')"):
        with zipfile.ZipFile(self.p,'w') as z:
            z.writestr('__main__.py',main);z.writestr('padding',b'0'*110_000)
    def test_manifest_points_to_versioned_official_file(self):
        manifest=json.loads((ROOT/'tools/local/runtime-manifest.json').read_text())
        self.assertEqual(manifest['pip']['url'],'https://bootstrap.pypa.io/pip/zipapp/pip-'+manifest['pip']['version']+'.pyz')
    def test_cached_html_rejected_before_subprocess(self):
        self.p.write_text('<html>Index of zipapp</html>'*8000)
        with patch.object(pipzip.subprocess,'run') as execute,self.assertRaises(ValueError):pipzip.main([str(self.p),'--version','26.2.1'])
        execute.assert_not_called()
    def test_too_short_archive(self):
        self.p.write_bytes(b'PK03\x04')
        with self.assertRaises(ValueError):pipzip.check_archive(self.p)
    def test_missing_main(self):
        with zipfile.ZipFile(self.p,'w') as z:z.writestr('data',b'0'*110_000)
        with self.assertRaises(ValueError):pipzip.check_archive(self.p)
    def test_crc_failure(self):
        self.zip();data=self.p.read_bytes();where=data.index(b'0'*100)
        self.p.write_bytes(data[:where]+b'1'+data[where+1:])
        with self.assertRaises(ValueError):pipzip.check_archive(self.p)
    def test_matching_version(self):
        self.zip();self.assertEqual(pipzip.main([str(self.p),'--version','26.2.1']),0)
    def test_wrong_version_rejected(self):
        self.zip("print('pip 25.0 from test')")
        with self.assertRaises(ValueError):pipzip.main([str(self.p),'--version','26.2.1'])
    def test_cached_failure_removes_pip_not_python(self):
        ps=(ROOT/'tools/local/setup_env.ps1').read_text(encoding='utf-8-sig')
        start=ps.index('validate_pip_zipapp.py');end=ps.index("$Site =",start)
        snippet=ps[start:end];self.assertIn('Remove-Item -LiteralPath $Pip',snippet);self.assertNotIn('Remove-Item -LiteralPath $PythonDir',snippet)
    def test_bat_new_commands_and_crlf(self):
        raw=(ROOT/'MANAGE_TACTIC.bat').read_bytes();self.assertIn(b'\r\n',raw);self.assertIn(b'%*',raw)
        import control
        for command,flag in [('check db','--check-local-db'),('db restore','--restore-local')]:
            args=control.parse(command.split());cfg=control.effective(args,{'format':1},ROOT)
            self.assertIn(flag,control.plan_command(args,cfg,ROOT).argv)
    def test_version_single_source(self):
        self.assertEqual(VERSION,(ROOT/'NATIVE_UI_VERSION').read_text().strip());self.assertEqual(BUILD_VERSION,VERSION+'.0-source-fork')
    def test_isolated_python_local_check_imports_siblings(self):
        with tempfile.TemporaryDirectory() as t:
            data=Path(t)/'data';create_seed(data)
            result=subprocess.run([sys.executable,'-I',str(ROOT/'tools/local/launch.py'),'--check-local-db','--data-dir',str(data)],capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,3,result.stdout+result.stderr)
            self.assertIn('structure_ready',result.stdout);self.assertNotIn('ModuleNotFoundError',result.stderr)
    def test_isolated_worker_import_not_dependent_on_cwd(self):
        r=subprocess.run([sys.executable,'-I',str(ROOT/'tools/local/sqlite_worker.py')],cwd=Path(tempfile.gettempdir()),capture_output=True,text=True,timeout=15)
        self.assertEqual(r.returncode,1);self.assertIn('Internal usage',r.stderr);self.assertNotIn("No module named 'launch'",r.stderr)

class SchemaTests(unittest.TestCase):
    def registry(self):return {s:'spt_'+s.split('/')[1] for s in CONFIG_REQUIRED}
    def columns(self):
        return dict(CORE_REQUIRED,**{self.registry()[k]:v for k,v in CONFIG_REQUIRED.items()})
    def test_complete_required_schema(self):
        r=inspect_schema(lambda t:self.columns().get(t,()),self.registry())
        self.assertTrue(r['ready']);self.assertTrue(all(x['state']=='ok' for x in r['checks']))
    def test_missing_table_and_columns_different(self):
        columns=self.columns();del columns['message_log'];columns['spt_widget_config']=['code','view']
        r=inspect_schema(lambda t:columns.get(t,()),self.registry())
        self.assertFalse(r['ready']);checks={x['table']:x for x in r['checks'] if 'table' in x}
        self.assertEqual(checks['message_log']['state'],'missing_table');self.assertEqual(checks['spt_widget_config']['state'],'missing_columns')
    def test_missing_registration_not_default_table(self):
        r=inspect_schema(lambda t:self.columns().get(t,()),{})
        self.assertFalse(r['ready']);self.assertEqual(sum(x['state']=='missing_registration' for x in r['checks']),len(CONFIG_REQUIRED))
    def test_real_table_names_from_registry(self):
        reg=self.registry();reg['config/widget_config']='{public}.widget_config';columns=self.columns();columns['widget_config']=columns.pop('spt_widget_config')
        r=inspect_schema(lambda t:columns.get(t,()),reg)
        self.assertTrue(r['ready']);self.assertIn('widget_config',[x.get('table') for x in r['checks']])
    def test_system_diagnostics_metadata_not_rows_or_writes(self):
        reg=self.registry();objects=[Mock(get_value=lambda name,k=k,v=v:k if name=='search_type' else v) for k,v in reg.items()]
        search=Mock(get_sobjects=lambda:objects)
        project=Mock(get_code=lambda:'sthpw',get_project_db_resource=lambda:'RESOURCE')
        db=Mock(get_columns=lambda t,use_cache=False:list(self.columns().get(t,())),get_database_type=lambda:'Sqlite')
        with patch('pyasm.search.Search',return_value=search),patch('pyasm.biz.Project.get_by_code',return_value=project),patch('pyasm.biz.Project.get',return_value=project),patch('pyasm.search.DbContainer.get',return_value=db):
            r=schema_diagnostics()
        self.assertTrue(r['ready']);self.assertTrue(r['read_only']);self.assertEqual(len(r['databases']),1);db.do_update.assert_not_called()
        search.add_filters.assert_called_once_with('search_type',list(CONFIG_REQUIRED))
    def test_metadata_error_sanitizes_credentials(self):
        with patch('pyasm.search.Search',side_effect=RuntimeError('password=super-secret local/path')):
            r=schema_diagnostics()
        self.assertFalse(r['ready']);self.assertNotIn('super-secret',str(r));self.assertNotIn('local/path',str(r))
    def test_system_wrong_configured_handler_denied(self):
        service=AdminService();service.open_target=lambda _: {'kind':'table'}
        with patch('pyasm.common.Environment.get_security',return_value=Mock(is_admin=lambda:True)),self.assertRaises(ApiError) as caught:
            service.admin_operation('GET','/system',{'target':'x'})
        self.assertEqual(caught.exception.status,403)
    def test_system_requires_admin(self):
        with patch('pyasm.common.Environment.get_security',return_value=Mock(is_admin=lambda:False)),self.assertRaises(ApiError) as caught:
            AdminService().admin_operation('GET','/system',{'target':'x'})
        self.assertEqual(caught.exception.status,403)
