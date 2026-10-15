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

__all__ = ['FilterData']

from pyasm.common import Container

from pyasm.common import SetupException, Container, jsonloads, jsondumps

import ast

import six
basestring = six.string_types


class FilterData(object):
    '''Utility class to manipulate data used by filters.  The data is a global
    container one or more filters and filters make use of it to extract data.
    The reason for this class is that this data structured is marshalled to
    and from many locations, so it requires a centralized class to manage it.
    Also because the data structure is relatively flat, it can be annoying
    to extract data manually'''

    @staticmethod
    def _decode(data):
        # Legacy configs may contain Python literal dictionaries, but never code.
        # Do not globally replace apostrophes: valid values such as O'Reilly
        # would be corrupted. A new instance must not mutate a cached JSON list.
        import copy
        if isinstance(data, basestring):
            data = data.strip()
            if not data:
                return []
            try:
                data = jsonloads(data)
            except ValueError:
                try:
                    data = ast.literal_eval(data)
                except (ValueError, SyntaxError) as exc:
                    raise SetupException('FilterData is not JSON or a Python literal') from exc
        if data is None:
            return []
        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list) or any(not isinstance(item, dict) for item in data):
            raise SetupException('FilterData must contain a list of dictionaries')
        return copy.deepcopy(data)

    def __init__(self, data=None):
        self.data = self._decode(data)

    def set_data(self, data):
        self.data = self._decode(data)

    def add_data(self, data):
        self.data.extend(self._decode(data))

    def set_to_cgi(self):
        from pyasm.web import WebContainer
        web = WebContainer.get_web()
        data = jsondumps(self.data)
        if web:
            web.set_form_value('json', data)
        Container.put("FilterData", self)


    def is_empty(self):
        '''serialize the data into a string'''
        if not self.data:
            return True
        return False



    def serialize(self):
        '''serialize the data into a string'''
        value = jsondumps(self.data)
        return value

    def get_data(self):
        return self.data
        

    def get_values_by_prefix(self, prefix):
        '''get data values for a specific prefix'''
        data = []
        for values in self.data:
            if values.get('prefix') == prefix:
                data.append(values)

        return data
            
    def get_values_by_index(self, prefix, filter_index=0):
        '''get data values for a specific prefix and index.
           The index refers to the index of the list that shares the
           same prefix'''
        count = 0
        for values in self.data:
            if not values.get('prefix') == prefix:
                continue

            if not count == filter_index:
                count += 1
                continue

            return values 

        return {}


    def get_values(self, prefix, name):
        '''Method to get the value from a certain prefix, regardless of
        index'''
        ret_values = []
        for values in self.data:
            if not values.get('prefix') == prefix:
                continue

            value = values.get(name)
            ret_values.append(value)


        return ret_values




    #
    # Static functions
    #
    def get_from_cgi(cls):
        # explicitly get from cgi.  Do not store
        from pyasm.web import WebContainer
        web = WebContainer.get_web()
        data = web.get_form_value('json')
        filter_data = FilterData(data)
        return filter_data
    get_from_cgi = classmethod(get_from_cgi)

    def get(cls):
        filter_data = Container.get("FilterData")
        if filter_data == None:
            from pyasm.web import WebContainer
            web = WebContainer.get_web()
            if web:
                data = web.get_form_value('json')
            else:
                data = {}
            filter_data = FilterData(data)
            Container.put("FilterData", filter_data)
        return filter_data

    get = classmethod(get)





