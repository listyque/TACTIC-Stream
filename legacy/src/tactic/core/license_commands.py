# Copyright (c) 2005 Southpaw Technology. Original TACTIC RenewLicenseCbk.
from pyasm.command import Command
from pyasm.common import Environment, TacticException
from pyasm.web import WebContainer
from pyasm.search import FileUndo
import os

class RenewLicenseCbk(Command):
    ''' Renew License Callback'''

    INPUT_NAME="Renew_License"
    BUTTON_NAME = "Renew License"

    def get_title(self):
        return "Renew License"


    def check(self):
        return True

    def get_web(self):
        from pyasm.web import WebContainer
        web = WebContainer.get_web()
        return web

    def execute(self):
        web = self.get_web()
        keys = web.get_form_keys()
        file_name = self.kwargs.get("file_name")

        # process and get the uploaded files
        dir = Environment.get_upload_dir()
        license_file = "%s/%s" % (dir, file_name)
        if not os.path.exists(license_file):
            raise TacticException("Error retrieving the license file in [%s]"%license_file)

        std_name = 'tactic-license.xml'

        head, file_name = os.path.split(license_file)
        # no restrictions for license file
        #if file_name != std_name:
        #    raise TacticException("License file name should be named tactic-license.xml. The file given is [%s]" %file_name)

        license_dir = Environment.get_license_dir()
        current_license = "%s/%s" %(license_dir, std_name)
        if os.path.exists(current_license):
            FileUndo.remove(current_license)
        FileUndo.move(license_file, current_license)

        self.add_description('Renewed license file')
        security = Environment.get_security()
        security.reread_license()

