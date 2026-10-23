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

__all__ = ['FilterData']

import ast
import copy
import six

from pyasm.common import SetupException, Container, jsonloads, jsondumps

basestring = six.string_types


class FilterData(object):
    '''Utility class to manipulate data used by filters.'''

    @staticmethod
    def _decode(data):
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

    def is_empty(self):
        return not bool(self.data)

    def serialize(self):
        return jsondumps(self.data)

    def get_data(self):
        return self.data

    def get_values_by_prefix(self, prefix):
        data = []
        for values in self.data:
            if values.get('prefix') == prefix:
                data.append(values)
        return data

    def get_values_by_index(self, prefix, filter_index=0):
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
        ret_values = []
        for values in self.data:
            if not values.get('prefix') == prefix:
                continue
            ret_values.append(values.get(name))
        return ret_values

    @classmethod
    def get(cls):
        filter_data = Container.get("FilterData")
        if filter_data is None:
            filter_data = FilterData({})
            Container.put("FilterData", filter_data)
        return filter_data
