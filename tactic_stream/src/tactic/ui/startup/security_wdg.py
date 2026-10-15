###########################################################
#
# Copyright (c) 2010, Southpaw Technology
#                     All Rights Reserved
#
# PROPRIETARY INFORMATION.  This software is proprietary to
# Southpaw Technology, and is not to be reproduced, transmitted,
# or disclosed in any way without written permission.
#
#


"""Original security menu catalog, without HTML/runtime widgets."""


class GearMenuSecurityWdg:
    @classmethod
    def get_all_menu_names(cls):
        all_gear_menu_names = {'ALL MENU ITEMS':{'label': ['*'],'order': 0},
                               'Edit': {'label': ['Retire Selected Items','Delete Selected Items','Show Server Transaction Log','Undo Last Server Transaction','Redo Last Server Transaction'],'order': 1},
                               'File': {'label': ['Export All ...','Export Selected ...','Export Matched ...','Export Displayed ...','Import CSV','Ingest Files','Check-out Files'], 'order': 2},
                               'Clipboard': {'label': ['Copy Selected','Paste','Connect','Append Selected','Show Clipboard Contents'], 'order': 3},
                               'View': {'label': ['Column Manager','Create New Column','Save Current View','Save a New View','Edit Current View','Edit Config XML'], 'order': 4},
                               'Print': {'label': ['Print Selected','Print Displayed','Print Matched'], 'order': 5},
                               'Chart': {'label': ['Chart Items','Chart Selected'], 'order': 6},
                               'Tasks': {'label': ['Show Tasks','Add Tasks to Selected','Add Tasks to Matched'], 'order': 7},
                               'Notes': {'label': ['Show Notes'], 'order': 8},
                               'Check-ins': {'label': ['Show Check-in History'], 'order': 9},
                               'Pipelines': {'label': ['Show Pipeline Code','Edit Pipelines'], 'order': 10}
                               }
        all_gear_menu_names = sorted(
                all_gear_menu_names.items(),
                #key=lambda (x,y):y['order']
                key=lambda pair: pair[1]['order']
        )
        return all_gear_menu_names
