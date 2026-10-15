###########################################################
#
# Copyright (c) 2005, Southpaw Technology
#                     All Rights Reserved
#
# PROPRIETARY INFORMATION.  This software is proprietary to
# Southpaw Technology, and is not to be reproduced, transmitted,
# or disclosed in any way without written permission.
#
#
#
__all__ = ['PythonCmd', 'PythonTrigger']

from pyasm.common import TacticException, Environment, Config, Container, jsondumps, jsonloads
from pyasm.command import Command, CommandExitException, Trigger
from pyasm.common.errors import SecurityException, UnsupportedContract
from pyasm.biz import Project
from pyasm.search import Search
from tactic_client_lib import TacticServerStub

from mako.template import Template, ModuleTemplate
from mako import exceptions

import os
import traceback
from collections import OrderedDict
from threading import Lock
from types import ModuleType

_compiled_scripts = OrderedDict()
_compiled_scripts_lock = Lock()


def format_script_traceback(error):
    """Mako's source map, formatted by Python with the original exception chain."""
    formatted = traceback.TracebackException.from_exception(error)
    pending = [(error, formatted)]
    while pending:
        current, output = pending.pop()
        sources = getattr(current, 'tactic_script_sources', {})
        if sources:
            rich = exceptions.RichTraceback(error=current, traceback=current.__traceback__)
            frames = []
            for record in rich.records:
                source = sources.get(record[0])
                if source and record[5] is not None:
                    label, lines, offset = source
                    number = record[5] - offset
                    if 1 <= number <= len(lines):
                        frames.append((label, number, record[2], lines[number - 1]))
                else:
                    frames.append(record[:4])
            if isinstance(current, (exceptions.CompileException, exceptions.SyntaxException)):
                label, lines, offset = sources.get(None, next(iter(sources.values())))
                number = max(1, (current.lineno or offset + 1) - offset)
                line = lines[number - 1] if number <= len(lines) else ''
                frames.append((label, number, '<script>', line))
            output.stack = traceback.StackSummary.from_list(frames)
        if current.__cause__ is not None and output.__cause__ is not None:
            pending.append((current.__cause__, output.__cause__))
        if current.__context__ is not None and output.__context__ is not None:
            pending.append((current.__context__, output.__context__))
    return ''.join(formatted.format())

def check_script_execution(require_transaction=True, python=False):
    # PythonCmd's source api_cmd grant authorizes trusted Python, not a sandbox.
    # Other administrative callers keep the persisted-admin requirement.
    from pyasm.search.search import _context
    from pyasm.search import Transaction
    from pyasm.security.authenticator import Authenticator
    context = _context.get(None)
    security = Environment.get_security()
    if (context is None or security is None or not security.is_logged_in() or
            security.get_user_name() != context.login):
        raise SecurityException("Script execution requires authenticated security")
    resource = context.store.get_db_resource()
    with context.store.connection() as db:
        marker = resource.get_database_impl().get_parameter()
        active = db.execute("SELECT 1 FROM login WHERE login=" + marker + " AND (s_status IS NULL OR s_status!='retired')", (context.login,)).fetchone()
        administrator = active and Authenticator._admin(db, context.login, marker)
    if not (security.is_admin() and administrator):
        from pyasm.security import Sudo
        if (not python or not active or security.is_admin() or Sudo.is_sudo() or
                not security.check_access('project', Project.get_project_code(), 'allow', default='deny') or
                not security.check_access('api_cmd', 'tactic.command.PythonCmd', 'allow', default='deny')):
            raise SecurityException("Script execution requires administrator access or an explicit PythonCmd grant with project access")
    transaction = Transaction.get()
    if require_transaction and (transaction is None or not transaction.is_in_transaction()):
        raise UnsupportedContract("Script execution requires an active Command transaction")


class PythonCmd(Command):

    def can_run(self, source="api"):
        if source == "api":
            return False


    def get_results(self):
        check_script_execution(python=True)
        code = self.kwargs.get("code")
        script_path = self.kwargs.get("script_path")
        file_path = self.kwargs.get("file_path")

        # if a script path is specified, then get it from the custom_script
        # table
        if script_path:

            folder = os.path.dirname(script_path)
            title = os.path.basename(script_path)

            from pyasm.search import SObject
            key = (folder, title)
            custom_script = SObject._get_cached_for_read(key, search_type='config/custom_script')
            if custom_script is not None and custom_script != '__NONE__' and custom_script.update_data:
                custom_script = None
            if custom_script is None:
                search = Search("config/custom_script")
                search.add_filter("folder", folder)
                search.add_filter("title", title)
                custom_script = search.get_sobject()
                SObject.cache_sobject(key, custom_script, search_type='config/custom_script')
            elif custom_script == '__NONE__':
                custom_script = None
            if not custom_script:
                raise TacticException("Custom script with path [%s/%s] does not exist" % (folder, title) )
            code = custom_script.get_value("script")

        elif file_path:
            with open(file_path, encoding="utf-8") as f:
                code = f.read()


        server = TacticServerStub.get(protocol='local')
        server.login = Environment.get_user_name()
        spt_mako_results = {}
        source = code
        label = file_path if file_path and not script_path else 'tactic://%s/%s' % (Project.get_project_code(), script_path or getattr(self, 'source_path', None) or 'inline.py')
        template = None
        try:
            cache = Container.get_full_dict('PythonCmd:compiled')
            key = (Project.get_project_code(), label, source)
            compiled = cache.get(key)
            reusable = isinstance(source, str) and len(source) <= 65536
            # Only immutable code survives requests; inputs, globals and access checks stay fresh.
            if compiled is None and reusable:
                with _compiled_scripts_lock:
                    compiled = _compiled_scripts.get(key)
                    if compiled is not None:
                        _compiled_scripts.move_to_end(key)
                        cache[key] = compiled
            if compiled is None:
                code = '''
<%%def name='spt_run_code()'>
<%%
%s
%%>
</%%def>

<%%
spt_mako_results['spt_ret_val'] = spt_run_code()
%%>
''' % source
                template = Template(code)
                module_source = template.code
                bytecode = compile(module_source, template.callable_.__code__.co_filename, 'exec')
                # Retain the template's unique id for nested traceback maps in this request.
                cache[key] = (bytecode, module_source, template, code)
                if reusable:
                    with _compiled_scripts_lock:
                        _compiled_scripts[key] = (bytecode, module_source, None, code)
                        _compiled_scripts.move_to_end(key)
                        if len(_compiled_scripts) > 32:
                            _compiled_scripts.popitem(last=False)
            else:
                bytecode, module_source, _, code = compiled
                # Only code is reused; module globals and execution stay fresh for every file.
                module = ModuleType(bytecode.co_filename)
                exec(bytecode, module.__dict__)
                template = ModuleTemplate(module, module_source=module_source, template_source=code)
            template.render(server=server,spt_mako_results=spt_mako_results, kwargs=self.kwargs,**self.kwargs)
        except Exception as e:
            sources = getattr(e, 'tactic_script_sources', {})
            filename = template.callable_.__code__.co_filename if template is not None else None
            # The unchanged original wrapper adds three lines before the script.
            sources[filename] = (label, source.splitlines(), 3)
            e.tactic_script_sources = sources
            raise

        return spt_mako_results['spt_ret_val']



    def execute(self):

        code = self.kwargs.get("code")
        script_path = self.kwargs.get("script_path")
        file_path = self.kwargs.get("file_path")
        assert code or script_path or file_path

        results = self.get_results()

        # set info and description
        self.info = results 
        class_name = self.__class__.__name__
        if script_path:
            desc = 'Run %s with script path [%s]' % (class_name, script_path)
        else:
            desc = "Run %s with explicit code" % class_name
        self.add_description(desc)

        return results




class PythonTrigger(Trigger):

    def __init__(self, **kwargs):
        super(PythonTrigger,self).__init__()
        self.kwargs = kwargs
        self.ret_val = None
        self.script_path = self.kwargs.get("script_path")


    def can_run(self, source="api"):
        if source == "api":
            return False



    def set_script_path(self, script_path):
        self.script_path = script_path

    def get_title(self):
        return self.script_path

    def get_ret_val(self):
        return self.ret_val


    def execute(self):
        check_script_execution(python=True)
        dirname = os.path.dirname(self.script_path)
        basename = os.path.basename(self.script_path)

        project = Project.get()

        # treat the code as a python
        search = Search("config/custom_script")
        search.add_filter("folder", dirname)
        search.add_filter("title", basename)
        script_sobj = search.get_sobject()

        if not script_sobj:
            try:
                # get from the sthpw database
                search = Search("sthpw/custom_script")
                search.add_filter("folder", dirname)
                search.add_filter("title", basename)
                script_sobj = search.get_sobject()
                if not script_sobj:
                    print("WARNING: Script with path [%s] does not exist in this project [%s] or Admin Site" % (self.script_path, project.get_code()))
                    return {}
            except LookupError:
                print("WARNING: Script with path [%s] does not exist in this project [%s] or Admin Site" % (self.script_path, project.get_code()))
                return

        script = script_sobj.get_value("script")
        if not script:
            print("WARNING: Empty python script [%s]" %script_sobj.get_code())
            return {}



        if self.trigger_sobj:
            trigger_sobj = self.trigger_sobj.get_sobject_dict()
            self.input['trigger_sobject'] = trigger_sobj

        language = script_sobj.get_value("language")
        if language == "server_js":
            from .js_cmd import JsCmd
            cmd = JsCmd(code=script, input=self.input)
        else:
            cmd = PythonCmd(code=script, input=self.input)
        cmd.source_path = self.script_path

        ret_val = cmd.execute()

        self.ret_val = ret_val
        self.info['result'] = ret_val

        #print "input: ", self.input
        #print "output: ", self.output
        #print "options: ", self.options

        return ret_val






