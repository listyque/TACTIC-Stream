"""Native sandbox/repository path selection, without the legacy applet."""
# Copyright (c) 2005 Southpaw Technology. All Rights Reserved.
# PROPRIETARY INFORMATION. This software is proprietary to Southpaw Technology.
from pyasm.biz import Project
from tactic.ui.common import BaseTableElementWdg


class ExplorerElementWdg(BaseTableElementWdg):
    ARGS_KEYS = {'mode': {'values': 'sandbox|repository'}}

    def get_decrement(self):
        return int(self.get_option('decrement') or 0)

    def get_base_dir(self, sobject):
        return Project.get_sandbox_base_dir(sobject, decrement=self.get_decrement())

    def get_lib_dir(self, sobject):
        return Project.get_project_lib_dir(sobject, None)

    def get_client_repo_dir(self, sobject):
        return Project.get_project_client_lib_dir(sobject, None)

    def is_editable(self):
        return False

    def get_cell_value(self):
        target = self.get_current_sobject()
        mode = self.get_option('mode') or 'sandbox'
        if mode not in ('sandbox', 'repository'):
            raise ValueError('Invalid explorer mode')
        path = self.get_base_dir(target) if mode == 'sandbox' else self.get_client_repo_dir(target)
        return dict(text='', available=bool(path), path=str(path or '').replace('\\', '/'))


class ExplorerTableElementWdg(ExplorerElementWdg):
    pass
