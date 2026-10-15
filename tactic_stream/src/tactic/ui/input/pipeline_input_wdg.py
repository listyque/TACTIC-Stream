# Copyright (c) 2005 Southpaw Technology. See LICENSE.TACTIC.
"""PipelineInputWdg's original select preparation, without HTML."""
from pyasm.search import Search
from pyasm.widget import BaseInputWdg, SelectWdg
from pyasm.common.errors import UnsupportedContract


class PipelineInputWdg(BaseInputWdg):
    def get_input(self):
        search_type = self.get_state().get('search_type')
        sobj = self.get_current_sobject()
        if not search_type:
            raise UnsupportedContract('Pipeline input requires search_type state')
        st_suffix = search_type.split('/', 1)
        if len(st_suffix) == 2:
            st_suffix = st_suffix[1]
        search = Search('sthpw/pipeline')
        search.add_op_filters([('search_type', 'EQ', '/%s' % st_suffix)])
        search.add_project_filter(show_unset=True)
        sobjects = search.get_sobjects()
        codes = [x.get_code() for x in sobjects]
        if self.get_option('use_code') in [True, 'true']:
            names = codes
        else:
            names = [x.get_value('name') or x.get_code() for x in sobjects]
        select = SelectWdg(self.get_input_name())
        select.add_empty_option('-- Default --' if sobj and sobj.is_insert() else '---')
        select.set_option('values', codes)
        select.set_option('labels', names)
        if sobj:
            value = sobj.get_value(self.get_name(), no_exception=True)
            if value:
                select.set_value(value)
        return select

    get_display = get_input
