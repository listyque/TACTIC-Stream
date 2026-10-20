###########################################################
#
# Copyright (c) 2005-2009, Southpaw Technology
#                     All Rights Reserved
#
# PROPRIETARY INFORMATION.  This software is proprietary to
# Southpaw Technology, and is not to be reproduced, transmitted,
# or disclosed in any way without written permission.
#
#
#

"""Original built-in permission catalog; HTML security widgets are excluded."""
permission_list = [
    {'group': 'Interface View Permissions'},
    {'key':'view_side_bar', 'title': 'View Side Bar', 'default': 'allow'},
    {'key':'view_site_admin', 'title': 'View Site Admin'},
    {'key':'view_script_editor', 'title': 'View Script Editor'},
    {'key':'side_bar_schema', 'title': 'View Side Bar Schema'},
    {'key':'view_save_my_view', 'title': 'View and Save My Views', 'default': 'allow'},
    {'key':'view_private_notes', 'title': 'View Private Notes'},
    {'key':'view_column_manager', 'title': 'View Column Manager'},
    {'key':'view_template_projects', 'title': 'View Template Projects', 'default': 'deny'},
    {'group': 'Data Manipuation Permissions'},
    {'key':'create_projects', 'title': 'Create Projects', 'description': 'The gives the user the permission to create projects'},
    {'key':'export_all_csv', 'title': 'Export All CSV'},
    {'key':'import_csv', 'title': 'Import CSV'},
    {'key':'retire_delete', 'title': 'Retire and Delete'},
    {'key':'edit', 'title': 'Edit'}
]


from tactic.ui.common import BaseTableElementWdg


class SecurityManagerButtonWdg(BaseTableElementWdg):
    """Open the existing group permission editor; admin groups stay explicit."""

    def get_cell_value(self):
        group = self.get_current_sobject()
        if group.is_admin():
            return dict(text='ADMIN', actions=[])
        return dict(text='', groupCode=group.get_code(), actions=[
            dict(name='security', label='Global Permissions', icon='security')])
