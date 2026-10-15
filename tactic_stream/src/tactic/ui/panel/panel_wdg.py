# Copyright (c) 2005, Southpaw Technology. See LICENSE.TACTIC.
"""Original sidebar configuration entry points; HTML panels are excluded."""
from tactic.core.sidebar_config import SidebarConfig


class SideBarBookmarkMenuWdg:
    add_internal_config = staticmethod(SidebarConfig.add_internal_config)

    @classmethod
    def get_config(cls, config_search_type, view, default=False, personal=False):
        return SidebarConfig.get_config(config_search_type, view, default=default, personal=personal)
