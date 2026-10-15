"""Three local entry points, shared controller. No working DB/runtime is initialized by these tests."""
from contextlib import redirect_stdout, redirect_stderr
import hashlib
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/local'))
import control as c


class CommandPlans(unittest.TestCase):
    def plan(self, *argv, profile=None, env=None):
        a = c.parse(list(argv))
        cfg = c.effective(a, profile or {'format': 1}, ROOT, {} if env is None else env)
        return c.plan_command(a, cfg, ROOT)

    def test_default_cluster_three_workers(self):
        v = self.plan('start').argv
        self.assertIn(str(ROOT / 'tools/local/cluster.py'), v)
        self.assertEqual(v[v.index('--workers') + 1], '3')
        self.assertEqual(v[v.index('--port') + 1], '9123')

    def test_single(self):
        v = self.plan('start', '--single').argv
        self.assertIn(str(ROOT / 'tools/local/launch.py'), v)
        self.assertNotIn('--workers', v); self.assertNotIn('--legacy', v)

    def test_legacy(self):
        self.assertIn('--legacy', self.plan('start', '--legacy').argv)

    def test_saved_single_overridden_by_explicit_mode(self):
        v = self.plan('start', '--mode', 'cluster', profile={'format': 1, 'mode': 'single', 'workers': 4}).argv
        self.assertIn(str(ROOT / 'tools/local/cluster.py'), v)
        self.assertEqual(v[v.index('--workers') + 1], '4')

    def test_invalid_worker_range(self):
        with self.assertRaises(ValueError): self.plan('start', '--workers', '9')

    def test_worker_flags_not_ignored_in_single(self):
        with self.assertRaises(ValueError): self.plan('start', '--single', '--workers', '3')

    def test_overlap_ports(self):
        with self.assertRaises(ValueError): self.plan('start', '--port', '9130', '--worker-base-port', '9129')

    def test_port_overflow(self):
        with self.assertRaises(ValueError): self.plan('start', '--port', '65534')

    def test_bad_timeout(self):
        with self.assertRaises(ValueError): self.plan('start', '--timeout', '5')

    def test_custom_worker_ports(self):
        v = self.plan('start', '--port', '9250', '--workers', '2', '--worker-base-port', '9400', '--timeout', '123').argv
        self.assertEqual(v[v.index('--worker-base-port') + 1], '9400')
        self.assertEqual(v[v.index('--timeout') + 1], '123')

    def test_all_diagnostics_map_to_original_flags(self):
        for kind, flag in [('env', '--check'), ('db', '--check-local-db'), ('startup', '--check-startup')]:
            with self.subTest(kind=kind):
                p = self.plan('check', kind)
                self.assertIn(flag, p.argv); self.assertIn(str(ROOT / 'tools/local/launch.py'), p.argv)

    def test_all_database_commands_map_to_original_flags(self):
        for kind, flag in [('init', '--init-sqlite'), ('upgrade', '--upgrade-local'), ('restore', '--restore-local')]:
            with self.subTest(kind=kind): self.assertIn(flag, self.plan('db', kind).argv)

    def test_no_auto_confirm_switch(self):
        for cmd in [('db','init'), ('db','upgrade'), ('db','restore'), ('configure',)]:
            with self.subTest(cmd=cmd), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                c.parse([*cmd, '--yes'])

    def test_configure_flags_preserved(self):
        v = self.plan('configure', '--writes', 'on', '--uploads', 'off', '--scripts', 'on').argv
        self.assertIn(str(ROOT / 'tools/local/configure_native.py'), v)
        self.assertEqual(v[-6:], ['--writes','on','--uploads','off','--scripts','on'])

    def test_show_configure_without_writes(self):
        v = self.plan('configure').argv
        self.assertNotIn('--writes', v); self.assertNotIn('--scripts', v)

    def test_setup_flags_and_original_script(self):
        v = self.plan('setup', '--repair', '--offline').argv
        self.assertIn(str(ROOT / 'tools/local/setup_env.ps1'), v)
        self.assertEqual(v[-2:], ['-Offline', '-Repair'])
        self.assertNotIn('init', v)

    def test_build_original_script(self):
        v = self.plan('build').argv
        self.assertEqual(v[-1], str(ROOT / 'tools/native_ui/build.cjs'))

    def test_paths_metacharacters_preserved_as_one_argument(self):
        path = str(ROOT / 'данные с пробелами & % ! (x)')
        v = self.plan('start', '--data-dir', path).argv
        self.assertEqual(v[v.index('--data-dir')+1], path)

    def test_python_priority(self):
        a=c.parse(['start','--python',sys.executable])
        result=c.effective(a,{'format':1,'python':'other'},ROOT,{'TACTIC_PYTHON':'wrong'})
        self.assertEqual(result['python'],c.clean_path(sys.executable))
        a=c.parse(['start'])
        result=c.effective(a,{'format':1,'python':'other'},ROOT,{'TACTIC_PYTHON':sys.executable})
        self.assertEqual(result['python'],c.clean_path(sys.executable))

    def test_explicit_config_infers_data_not_saved_wrong_data(self):
        a=c.parse(['start','--config',str(ROOT/'NEW/config/tactic-conf.xml')])
        cfg=c.effective(a,{'format':1,'data_dir':str(ROOT/'OLD')},ROOT,{})
        self.assertEqual(cfg['data_dir'], str(ROOT/'NEW'))

    def test_nonstandard_config_needs_data_dir(self):
        with self.assertRaises(ValueError): self.plan('start','--config',str(ROOT/'other.xml'))

    def test_explicit_data_clears_saved_other_config(self):
        p=self.plan('start','--data-dir',str(ROOT/'new'),profile={'format':1,'data_dir':str(ROOT/'old'),'config':str(ROOT/'old/config/tactic-conf.xml')})
        self.assertNotIn('--config',p.argv)

    def test_db_external_config_blocked(self):
        with self.assertRaises(ValueError): self.plan('db','init','--config',str(ROOT/'x/config/tactic-conf.xml'))

    def test_null_control_chars_in_path_rejected(self):
        for value in ('', 'abc\nxyz', 'x\0', 'ab"cd'):
            with self.subTest(value=value), self.assertRaises(ValueError): c.clean_path(value)

    def test_quoted_paths_and_symlink_interpreter(self):
        self.assertEqual(c.clean_path('"'+str(ROOT/'a b')+'"'),str(ROOT/'a b'))
        with tempfile.TemporaryDirectory() as t:
            linked=Path(t)/'python';linked.symlink_to(sys.executable)
            self.assertEqual(c.clean_path(str(linked)),str(linked))

    def test_no_args_selects_menu(self):self.assertEqual(c.parse([]).command,'menu')
    def test_options_without_command_select_menu(self):self.assertEqual(c.parse(['--port','9200']).command,'menu')

    def test_unknown_command_does_not_become_start(self):
        with redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):c.parse(['star'])

    def test_help_does_not_load_profile(self):
        with patch.object(c,'read_profile',side_effect=AssertionError('read')),redirect_stdout(io.StringIO()),self.assertRaises(SystemExit) as cm:c.main(['--help'])
        self.assertEqual(cm.exception.code,0)


class Profiles(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
    def test_absent_profile(self):self.assertEqual(c.read_profile(self.root),({'format':1},None))
    def test_unknown_fields_rejected(self):
        with self.assertRaises(ValueError):c.validate_profile({'format':1,'password':'no'},self.root)
    def test_non_object_rejected(self):
        with self.assertRaises(ValueError):c.validate_profile([],self.root)
    def test_bool_port_rejected(self):
        with self.assertRaises(ValueError):c.validate_profile({'format':1,'port':True},self.root)
    def test_fraction_workers_rejected(self):
        with self.assertRaises(ValueError):c.validate_profile({'format':1,'workers':3.5},self.root)
    def test_mode_rejected(self):
        with self.assertRaises(ValueError):c.validate_profile({'format':1,'mode':'taskkill'},self.root)
    def test_round_trip_unicode_and_backup(self):
        c.save_profile(self.root,{'format':1,'data_dir':'данные & !','python':sys.executable,'port':9123},None)
        value,revision=c.read_profile(self.root);self.assertTrue(value['data_dir'].endswith('данные & !'))
        raw=(self.root/c.PROFILE_NAME).read_bytes()
        c.save_profile(self.root,dict(value,port=9201),revision)
        self.assertEqual((self.root/(c.PROFILE_NAME+'.previous')).read_bytes(),raw)
        self.assertEqual(list(self.root.glob('.launcher-*.tmp')),[])
    def test_conflict_keeps_original(self):
        c.save_profile(self.root,{'format':1},None)
        original=(self.root/c.PROFILE_NAME).read_bytes()
        with self.assertRaises(ValueError):c.save_profile(self.root,{'format':1,'port':9100},'old')
        self.assertEqual((self.root/c.PROFILE_NAME).read_bytes(),original)
    def test_corrupt_profile_not_silently_reset(self):
        p=self.root/c.PROFILE_NAME;p.write_text('{')
        with self.assertRaises(ValueError):c.read_profile(self.root)
        self.assertEqual(p.read_text(),'{')
    def test_profile_size_limit(self):
        (self.root/c.PROFILE_NAME).write_text(' '*17000)
        with self.assertRaises(ValueError):c.read_profile(self.root)
    def test_profile_save_changes_no_database_files(self):
        db=self.root/'data.db';db.write_bytes(b'preserve')
        with redirect_stdout(io.StringIO()):self.assertEqual(c.main(['settings','--save','--data-dir','new data','--python',sys.executable],self.root),0)
        self.assertEqual(db.read_bytes(),b'preserve');self.assertFalse((self.root/'new data').exists())
    def test_settings_preview_does_not_write(self):
        with redirect_stdout(io.StringIO()):c.main(['settings','--save','--dry-run','--data-dir','NEW'],self.root)
        self.assertFalse((self.root/c.PROFILE_NAME).exists())
    def test_settings_path_change_clears_old_external_xml(self):
        c.save_profile(self.root,{'format':1,'config':str(self.root/'old/config/tactic-conf.xml')},None)
        with redirect_stdout(io.StringIO()):c.main(['settings','--save','--data-dir','NEW'],self.root)
        p,_=c.read_profile(self.root);self.assertNotIn('config',p)
    def test_settings_config_alone_saves_matching_data(self):
        f=self.root/'NEW/config/tactic-conf.xml';f.parent.mkdir(parents=True);f.write_text('<config/>')
        with redirect_stdout(io.StringIO()):c.main(['settings','--save','--config',str(f)],self.root)
        p,_=c.read_profile(self.root);self.assertEqual(p['data_dir'],str(f.parent.parent))
    def test_menu_settings_cancel(self):
        cfg=c.effective(c.parse(['start']),{'format':1},self.root,{})
        with redirect_stdout(io.StringIO()):c.settings_menu(cfg,self.root,lambda prompt:'')
        self.assertFalse((self.root/c.PROFILE_NAME).exists())


class Execution(unittest.TestCase):
    def test_dry_run_never_spawns(self):
        for argv in [['start'],['db','init'],['db','upgrade'],['configure','--writes','on'],['setup','--repair'],['build']]:
            with self.subTest(argv=argv),patch.object(c,'execute',side_effect=AssertionError('spawn')),redirect_stdout(io.StringIO()):
                self.assertEqual(c.main(argv+['--dry-run']),0)
    def test_original_exit_codes_propagated(self):
        for code in (0,2,3,7):
            with self.subTest(code=code),redirect_stdout(io.StringIO()):
                result=c.execute(c.Plan([sys.executable,'-c',f'raise SystemExit({code})'],str(ROOT),'test',sys.executable))
                self.assertEqual(result,code)
    def test_no_shell_and_environment_envelope_removed(self):
        with tempfile.TemporaryDirectory(prefix='TACTIC spaces & ! ') as t:
            out=Path(t)/'argv.json';value='слова & echo NO ! % (x) \\'
            script='import sys,json,os;open(sys.argv[1],"w").write(json.dumps([sys.argv[2:],os.getenv("TACTIC_BOOTSTRAP_ARGV_JSON")]))'
            with patch.dict(os.environ,{c.BOOTSTRAP_ARGV:'["secret"]'}),redirect_stdout(io.StringIO()):
                self.assertEqual(c.execute(c.Plan([sys.executable,'-c',script,str(out),value,''],t,'test',sys.executable)),0)
            self.assertEqual(json.loads(out.read_text()),[[value,''],None])
    def test_bootstrap_json_round_trip(self):
        args=['start','--data-dir',str(ROOT/'Тест & ! %'), '--dry-run']
        stream=io.StringIO()
        with patch.dict(os.environ,{c.BOOTSTRAP_ARGV:json.dumps(args)}),redirect_stdout(stream):c.main(['--bootstrap-argv'])
        out=json.loads(stream.getvalue());self.assertIn(args[2],out['argv'])
    def test_bootstrap_bad_envelope(self):
        with patch.dict(os.environ,{c.BOOTSTRAP_ARGV:'{}'}),self.assertRaises(ValueError):c.main(['--bootstrap-argv'])
    def test_missing_interpreter_no_fallback(self):
        with self.assertRaises(ValueError):c.execute(c.Plan(['/no/python','x'],str(ROOT),'', '/no/python'))
    def test_menu_redirected_input_fails_without_actions(self):
        with patch.object(sys,'stdin',io.StringIO('1\n')),patch.object(c,'execute',side_effect=AssertionError('spawn')),self.assertRaises(ValueError):c.main([])
    def run_menu(self, responses, code=0, args=None, root=ROOT):
        inputs=iter(responses);seen=[]
        with patch.object(sys.stdin,'isatty',return_value=True),redirect_stdout(io.StringIO()):
            rc=c.interactive(args or c.parse([]),root,lambda _:next(inputs),lambda p:seen.append(p) or code)
        return rc,seen
    def test_menu_check_then_exit(self):
        rc,seen=self.run_menu(['2','1','','0'])
        self.assertEqual(rc,0);self.assertEqual(len(seen),1);self.assertIn('--check',seen[0].argv)
    def test_menu_exit_does_not_run(self):
        self.assertEqual(self.run_menu(['0']), (0, []))
    def test_menu_does_not_offer_runtime_repair_inside_running_python(self):
        source=__import__('inspect').getsource(c.interactive)
        self.assertNotIn("['setup'",source);self.assertNotIn('return 91',source)
        self.assertIn('SETUP_ENV.bat',source)
    def test_menu_db_only_check_does_not_auto_upgrade_on_3(self):
        rc,seen=self.run_menu(['2','2','','0'],3)
        self.assertEqual(len(seen),1);self.assertIn('--check-local-db',seen[0].argv)
    def test_menu_db_upgrade_uses_old_tool_without_confirmation_bypass(self):
        rc,seen=self.run_menu(['4','2','','0'])
        self.assertIn('--upgrade-local',seen[0].argv);self.assertNotIn('--yes',seen[0].argv)
    def test_menu_db_init_is_separate_not_default(self):
        rc,seen=self.run_menu(['4','1','','0'])
        self.assertEqual(len(seen),1);self.assertIn('--init-sqlite',seen[0].argv)
    def test_menu_db_restore_is_explicit(self):
        rc,seen=self.run_menu(['4','3','','0'])
        self.assertIn('--restore-local',seen[0].argv)
    def test_menu_back_without_action(self):
        rc,seen=self.run_menu(['2','0','3','0','4','0','0'])
        self.assertEqual(seen,[])
    def test_menu_permission_flags(self):
        cases={'1': [],'2':['--writes','off'],'3':['--writes','on'],
               '4':['--writes','on','--uploads','on'],
               '5':['--writes','on','--scripts','on'],
               '6':['--uploads','off'],'7':['--scripts','off']}
        for choice,flags in cases.items():
            with self.subTest(choice=choice):
                _,seen=self.run_menu(['3',choice,'','0'])
                if flags:self.assertEqual(seen[0].argv[-len(flags):],flags)
                else:self.assertNotIn('--writes',seen[0].argv)
    def test_menu_build_original_script(self):
        _,seen=self.run_menu(['5','','0'])
        self.assertTrue(seen[0].argv[-1].endswith('tools/native_ui/build.cjs'))
    def test_changed_menu_profile_used_in_same_session(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            args=c.parse(['menu','--data-dir',str(root/'OLD')])
            _,seen=self.run_menu(['1',sys.executable,str(root/'NEW'),'','','','','yes','2','2','','0'],args=args,root=root)
            self.assertEqual(seen[0].argv[seen[0].argv.index('--data-dir')+1],str(root/'NEW'))
    def test_menu_without_selection_never_runs_server_or_setup(self):
        source=__import__('inspect').getsource(c.interactive)
        self.assertNotIn("command = ['start']",source)
        self.assertNotIn("command = ['setup']",source)
    @unittest.skipIf(os.name=='nt','POSIX console group test; Windows covered by separate manual smoke')
    def test_ctrl_c_waits_for_child_cleanup(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);ready=root/'ready';done=root/'done';child=root/'child.py'
            child.write_text('import signal,time,pathlib\n'
                             f'pathlib.Path({str(ready)!r}).write_text("ready")\n'
                             'try:\n while True: time.sleep(.1)\n'
                             f'except KeyboardInterrupt: pathlib.Path({str(done)!r}).write_text("clean")\n')
            code=f'import sys;sys.path.insert(0,{str(ROOT/"tools/local")!r});import control;raise SystemExit(control.execute(control.Plan([sys.executable,{str(child)!r}],{t!r},"test",sys.executable)))'
            p=subprocess.Popen([sys.executable,'-c',code],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
            try:
                deadline=time.monotonic()+8
                while not ready.exists() and time.monotonic()<deadline:time.sleep(.03)
                self.assertTrue(ready.exists())
                os.killpg(p.pid,signal.SIGINT)
                output=p.communicate(timeout=8)[0]
                self.assertEqual(p.returncode,0,output);self.assertEqual(done.read_text(),'clean')
            finally:
                if p.poll() is None:os.killpg(p.pid,signal.SIGKILL);p.wait()


class SourceContract(unittest.TestCase):
    def test_exactly_three_bat_entire_distribution(self):
        self.assertEqual(sorted(str(p.relative_to(ROOT)) for p in ROOT.rglob('*.bat')),
                         ['MANAGE_TACTIC.bat','SETUP_ENV.bat','START_TACTIC.bat'])
    def test_batch_is_short_quoted_crlf_no_call(self):
        entries={'START_TACTIC.bat':'start','SETUP_ENV.bat':'setup','MANAGE_TACTIC.bat':'manage'}
        for name,entry in entries.items():
            with self.subTest(name=name):
                raw=(ROOT/name).read_bytes();s=raw.decode('ascii')
                self.assertIn(b'\r\n',raw);self.assertNotIn(b'\n',raw.replace(b'\r\n',b''))
                self.assertIn('DisableDelayedExpansion',s)
                self.assertIn('"%~dp0tools\\local\\tactic_bootstrap.ps1"',s)
                self.assertEqual(s.count('%*'),1)
                self.assertNotIn('\ncall ',s.lower());self.assertIn('exit /b %RESULT%',s)
                self.assertIn('set "TACTIC_LAUNCH_ENTRY='+entry+'"',s)
    def test_shared_dispatch_preserves_distinct_default_actions(self):
        s=(ROOT/'tools/local/tactic_bootstrap.ps1').read_text(encoding='utf-8-sig')
        for rule in ("'start' { return ,(@('start') + $items) }", "'setup' { return ,(@('setup') + $items) }", "'manage' { return ,$items }"):
            self.assertIn(rule,s)
        self.assertIn('$arguments = Get-TacticEntryArguments',s)
    def test_setup_is_dispatched_before_resolving_python(self):
        s=(ROOT/'tools/local/tactic_bootstrap.ps1').read_text(encoding='utf-8-sig')
        main=s[s.index('function Invoke-TacticBootstrap'):]
        self.assertLess(main.index('Invoke-TacticSetup'),main.index('Get-TacticPython'))
    def test_batch_environment_marker_not_leaked_to_child(self):
        with patch.dict(os.environ,{'TACTIC_LAUNCH_ENTRY':'start'}),patch.object(c.subprocess,'Popen') as popen:
            popen.return_value.wait.return_value=0
            with redirect_stdout(io.StringIO()):c.execute(c.Plan([sys.executable,'-V'],str(ROOT),'test',sys.executable))
            self.assertNotIn('TACTIC_LAUNCH_ENTRY',popen.call_args.kwargs['env'])
    def test_bootstrap_bom_for_ps51(self):
        raw=(ROOT/'tools/local/tactic_bootstrap.ps1').read_bytes();self.assertTrue(raw.startswith(b'\xef\xbb\xbf'))
        self.assertNotIn(b'\n',raw.replace(b'\r\n',b''))
    def test_no_eval_shell_or_raw_parameter_in_command(self):
        s=(ROOT/'tools/local/tactic_bootstrap.ps1').read_text(encoding='utf-8-sig')
        self.assertNotIn('Invoke-Expression',s);self.assertNotIn('-Command ',s)
        self.assertIn('TACTIC_BOOTSTRAP_ARGV_JSON',s);self.assertIn("'--bootstrap-argv'",s);self.assertIn("$code = Invoke-TacticNative",s)
    def test_bootstrap_inherits_console_for_prompts_and_trace(self):
        s=(ROOT/'tools/local/tactic_bootstrap.ps1').read_text(encoding='utf-8-sig')
        for name in ('Input','Output','Error'):
            self.assertIn('$info.RedirectStandard'+name+' = $false',s)
        self.assertIn('$info.UseShellExecute = $false',s)
        self.assertIn('$process.WaitForExit()',s)
        self.assertNotIn('| Out-Host',s.replace('through Out-Host',''))
    def test_missing_explicit_python_cannot_loop_install_prompt(self):
        s=(ROOT/'tools/local/tactic_bootstrap.ps1').read_text(encoding='utf-8-sig')
        self.assertIn("if ($explicit) { throw",s)
    def test_setup_uses_original_integrity_and_safety_checks(self):
        s=(ROOT/'tools/local/setup_env.ps1').read_text(encoding='utf-8-sig')
        for token in ('Get-AuthenticodeSignature','Get-FileHash','Unknown runtime','validate_pip_zipapp.py','--only-binary=:all:','setup-complete.json'):
            self.assertIn(token,s)
    def test_original_database_prompts_not_removed(self):
        s=(ROOT/'tools/local/launch.py').read_text()
        for token in ('Type CREATE','Type UPGRADE','secure_password()','local_lock(data)'):
            self.assertIn(token,s)
    def test_runtime_manifest_not_changed(self):
        s=json.loads((ROOT/'tools/local/runtime-manifest.json').read_text())
        self.assertTrue(s['pip']['url'].startswith('https://bootstrap.pypa.io/pip/zipapp/'))
    def test_no_obsolete_command_in_live_hints(self):
        old=['START_CLUSTER.bat','CHECK_LOCAL_DB.bat','UPGRADE_LOCAL_SQLITE.bat','RESTORE_LOCAL_SQLITE.bat','CONFIGURE_NATIVE.bat']
        for p in [* (ROOT/'tools/local').glob('*.py'),*(ROOT/'tools/local').glob('*.ps1'),ROOT/'src/tactic/ui_api/system_diagnostics.py']:
            s=p.read_text(encoding='utf-8-sig')
            for token in old:self.assertNotIn(token,s,(p,token))

if __name__=='__main__':unittest.main()
