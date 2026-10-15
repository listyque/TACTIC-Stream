"""Fresh-process regression using actual original service classes + bundled CherryPy.

No database, authentication or licence is emulated as a successful live boot.
Only Config auto-upgrade and Environment directories are supplied. register_project
itself, importlib, all stock context modules and the CherryPy mount are real.
"""
import ast
import json
from pathlib import Path
import sys
import tempfile
import textwrap
from types import SimpleNamespace
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools/local'))
from launch import configure_paths
configure_paths(ROOT/'tests/native_ui/no-user-data', ROOT/'tests/native_ui/nonexistent-config.xml')
from pyasm.common import Container
Container.create()
from pyasm.web import cherrypy30_startup as module
import cherrypy
results=[]
def check(name, condition):
    if not condition: raise AssertionError(name)
    results.append({'scenario': name, 'passed': True})
def root():
    result=SimpleNamespace(tactic=module.TacticIndex(), projects=module.TacticIndex())
    cherrypy.root=result; cherrypy.tree.apps.clear(); cherrypy.tree.mount(result, '')
    return result
server=module.CherryPyStartup.__new__(module.CherryPyStartup)
with patch('pyasm.common.Environment.get_install_dir', return_value=str(ROOT)), patch('pyasm.common.Config.get_value', return_value=''):
    if sys.version_info >= (3,13):
        code=(ROOT/'tests/native_ui/fixtures/register_project_08.py.txt').read_text()
        namespace=dict(vars(module));exec(compile(textwrap.dedent(code),'<original 0.8 register_project>','exec'),namespace)
        root()
        # Match the alphabetical Windows directory order in the user's log.
        import os
        original_listdir = os.listdir
        try:
            with patch.object(module.os, 'listdir', side_effect=lambda path: sorted(original_listdir(path))):
                namespace['register_project'](server,'default',{})
        except NameError as exc: check('Original 0.8 method reproduces user Api NameError on Python 3.13', "'Api'" in str(exc))
        else: raise AssertionError('Original failure was not reproduced')
    registered=root();config={};server.register_project('default',config)
    stock=sorted(p.stem for p in (ROOT/'src/tactic_sites/default/context').glob('*.py') if not p.name.startswith('__'))
    for name in stock:
        obj=getattr(registered.tactic.default,name,None)
        check('Original default context '+name+' instantiated', obj is not None and type(obj).__name__==name)
    for name in ('Api','XMLRPC'):
        check(name+' XML-RPC tooling reaches mounted app', cherrypy.tree.apps[''].config['/tactic/default/'+name]['tools.xmlrpc.on'] is True)
    server.register_project('admin',config)
    check('Admin project registers',hasattr(registered.tactic,'admin'))
    server.register_project('default',config,site='studio_a')
    check('Site-specific Api object',hasattr(registered.tactic.studio_a.default,'Api'))
    check('Site-specific XML-RPC tooling',cherrypy.tree.apps[''].config['/tactic/studio_a/default/Api']['tools.xmlrpc.allow_none'] is True)
    check('Projects namespace preserved',hasattr(registered.projects.studio_a,'default'))
    server.config=config
    from startup_probe import inspect_registered_services
    report=inspect_registered_services(server)
    check('Startup probe sees three original services without listener',len(report['registered'])==3 and report['listener_started'] is False)
print(json.dumps({'python':sys.version,'scope':'actual register_project, stock context objects, real CherryPy; no full startup/DB/authentication','scenarios':results},indent=2))
