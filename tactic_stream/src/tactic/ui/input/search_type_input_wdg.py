# Copyright (c) 2005 Southpaw Technology. See LICENSE.TACTIC.
"""Original schema-scoped search type selects; no HTML."""
from pyasm.search import Search, SearchType
from pyasm.biz import Schema
from pyasm.widget import SelectWdg


class SearchTypeInputWdg(SelectWdg):
    def get_input(self):
        search_type_names = Schema.get().get_search_types(hierarchy=False)
        search = Search('sthpw/search_object')
        search.add_filters('search_type', search_type_names)
        search_types = search.get_sobjects()
        search_types.append(SearchType.get('sthpw/task'))
        values = [x.get_value('search_type') for x in search_types]
        labels = ['%s (%s)' % (x.get_value('title'), x.get_value('search_type')) for x in search_types]
        sobject = self.get_current_sobject()
        value = sobject.get_value(self.get_name()) if sobject else ''
        self.set_option('values', values)
        self.set_option('labels', labels)
        self.add_empty_option('-- Select --')
        if value:
            self.set_value(value)
        return self


class SearchTypeWithPipelineInputWdg(SelectWdg):
    def get_input(self):
        search_type_names = Schema.get().get_search_types(hierarchy=False)
        search = Search('sthpw/search_object')
        search.add_filters('search_type', search_type_names)
        search_types = search.get_sobjects()
        search_types.append(SearchType.get('sthpw/task'))
        values, labels = [], []
        for x in search_types:
            base_type = x.get_base_key()
            if not SearchType.column_exists(base_type, 'pipeline_code'):
                continue
            values.append(base_type)
            labels.append('%s (%s)' % (x.get_value('title'), x.get_value('search_type')))
        sobject = self.get_current_sobject()
        value = sobject.get_value(self.get_name()) if sobject else ''
        self.set_option('values', values)
        self.set_option('labels', labels)
        self.add_empty_option('-- Select --')
        if value:
            self.set_value(value)
        return self
