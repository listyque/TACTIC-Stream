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
__all__ = ['JsCmd']


from pyasm.common import TacticException, Environment, Config, jsondumps, jsonloads, JsWrapper
from pyasm.command import Command, CommandExitException
from pyasm.biz import Project
from pyasm.search import Search

from .python_cmd import PythonCmd, check_script_execution

from tactic_client_lib import TacticServerStub


import os

class JsCmd(PythonCmd):

    def get_results(self):
        check_script_execution()
        code = self.kwargs.get("code")
        script_path = self.kwargs.get("script_path")
        file_path = self.kwargs.get("file_path")


        # if a script path is specified, then get it from the custom_script
        # table
        if script_path:

            folder = os.path.dirname(script_path)
            title = os.path.basename(script_path)

            search = Search("config/custom_script")
            search.add_filter("folder", folder)
            search.add_filter("title", title)
            custom_script = search.get_sobject()
            if not custom_script:
                raise TacticException("Custom script with path [%s/%s] does not exist" % (folder, title) )
            code = custom_script.get_value("script")

        elif file_path:
            f = open(file_path)
            code = f.read()
            f.close()


        wrapper = JsWrapper.get()
        try:
            results = wrapper.execute_func(code, self.kwargs)
        except Exception as error:
            error.tactic_js_source = 'tactic://%s/%s' % (Project.get_project_code(), script_path or file_path or getattr(self, 'source_path', None) or 'inline.js')
            raise


        return results


