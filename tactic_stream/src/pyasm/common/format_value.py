###########################################################
#
# Copyright (c) 2005-2008, Southpaw Technology
#                     All Rights Reserved
#
# PROPRIETARY INFORMATION.  This software is proprietary to
# Southpaw Technology, and is not to be reproduced, transmitted,
# or disclosed in any way without written permission.
#
#
#


__all__ = ['FormatValue']


import datetime
import locale
import os
from dateutil import parser

from .timecode import TimeCode

import six
basestring = six.string_types


# Formatting must not change process-wide locale in threaded workers.


class FormatValue(object):

    def convert_to_float(self, num):
        try:
            num = float(num)
        except:
            num = 0
        return num


    def number_format(self, num, places=0):
        """Format a number according to locality and given places"""
        if not isinstance(num, float):
            num = float(num)
        return locale.format_string("%.*f", (places, num), True)

    def currency_format(self, num, grouping=False, monetary=False):
        """Format a currency according to locality and given places"""
        try:
            num = float(num)
        except ValueError as e:
            num = 0
        return locale.currency(num, True, grouping, monetary)



    def get_format_value(self, value, format, format_option=None):
        '''format is required. format_option is optional where applicable like fps for timecode'''
        real_value = value
        if value == '':
            return value

        if isinstance(value, datetime.datetime):
            real_value = value
            value = str(value)
        elif not isinstance(value, basestring):
            real_value = value
            value = str(value)

        if isinstance(real_value, basestring) and value.startswith("{") and value.endswith("}"):
            from pyasm.search import Search
            value = Search.eval(value)

        # ------------------------------------------------
        # Integer
        if format == '-1234':
            if not value:
                # Case where value is '', 0, 0.0, -0.0 . 
                value = 0
            value = "%0.0f" % self.convert_to_float(value)

        elif format == '-1,234':
            if value == None:
                value = ""
            elif not value:
                value = 0
            # Group the value into three numbers seperated by a comma.
            value = self.number_format(value, places=0)

        # ------------------------------------------------
        # Float
        elif format == '-1234.12':
            if not value:
                value = 0
            value = "%0.2f" % self.convert_to_float(value)

        elif format == '-1,234.12':
            # break the value up by 3s
            if not value:
                value = 0

            elif isinstance(value, basestring):
                value = float(value)

            value = self.number_format(value, places=2)

        # ------------------------------------------------
        # Percentage
        elif format == '-13%':
            if not value:
                value = 0
            value = self.convert_to_float(value) * 100
            value = "%0.0f" % self.convert_to_float(value) + "%"

        elif format == '-12.95%':
            if not value:
                value = 0
            value = self.convert_to_float(value) * 100
            value = "%0.2f" % self.convert_to_float(value) + "%"

        # ------------------------------------------------
        # Currency
        elif format == '-$1,234':
            # break the value up by 3s
            if not value:
                value = 0
            value = self.currency_format(value, grouping=True)
            value = value[0:-3]

        elif format == '-$1,234.00':
            if not value:
                value = 0
            value = self.currency_format(value, grouping=True)

        elif format == '-$1,234.--':
            # break the value up by 3s
            if not value:
                value = 0
            value = self.currency_format(value, grouping=True)
            value = value[0:-3] + ".--"

        elif format == '-$1,234.00 CAD':
            # break the value up by 3s
            if not value:
                value = 0
            value = self.currency_format(value, grouping=True, monetary=True)


        elif format == '($1,234.00)':
            # break the value up by 3s
            if not value:
                value = "-"
            else:
                value = self.currency_format(value, grouping=True)
                if value.startswith("-"):
                    value = "(%s)" % value.replace("-", "")

        # ------------------------------------------------
        # Date
        elif format == '31/12/99':
            if not value:
                value = ''
            else:
                
                value = parser.parse(value)
                value = value.strftime("%d/%m/%y")

        elif format == 'December 31, 1999':
            if not value:
                value = ''
            else:
                value = parser.parse(value)
                value = value.strftime("%B %d, %Y")

        elif format == '31/12/1999':
            if not value:
                value = ''
            else:
               
                value = parser.parse(value)
                value = value.strftime("%d/%m/%Y")

        elif format == 'Dec 31, 99':
            if not value:
                value = ''
            else:
                value = parser.parse(value)
                value = value.strftime("%b %d, %y")

        elif format == 'Dec 31, 1999':
            if not value:
                value = ''
            else:
                value = parser.parse(value)
                value = value.strftime("%b %d, %Y")

        elif format == '31 Dec, 1999':
            if not value:
                value = ''
            else:
                value = parser.parse(value)
                value = value.strftime("%d %b, %Y")

        elif format == '31 December 1999':
            if not value:
                value = ''
            else:
                value = parser.parse(value)
                value = value.strftime("%d %B %Y")

        elif format == 'Fri, Dec 31, 99':
            if not value:
                value = ''
            else:
                value = parser.parse(value)
                value = value.strftime("%a, %b %d, %y")

        elif format == 'Fri 31/Dec 99':
            if not value:
                value = ''
            else:
                value = parser.parse(value)
                value = value.strftime("%a %d/%b %y")

        elif format == 'Fri, December 31, 1999':
            if not value:
                value = ''
            else:
                value = parser.parse(value)
                value = value.strftime("%a, %B %d, %Y")

        elif format == 'Friday, December 31, 1999':
            if not value:
                value = ''
            else:
                value = parser.parse(value)
                value = value.strftime("%A, %B %d, %Y")

        elif format == '12-31':
            if not value:
                value = ''
            else:
                value = parser.parse(value)
                value = value.strftime("%m-%d")

        elif format == '99-12-31':
            if not value:
                value = ''
            else:
                value = parser.parse(value)
                value = value.strftime("%y-%m-%d")

        elif format == '1999-12-31':
            if not value:
                value = ''
            else:
                value = parser.parse(value)
                value = value.strftime("%Y-%m-%d")

        elif format == '12-31-1999':
            if not value:
                value = ''
            else:
                value = parser.parse(value)
                value = value.strftime("%m-%d-%Y")

        elif format == '12/99':
            if not value:
                value = ''
            else:
                value = parser.parse(value)
                value = value.strftime("%m-%y")

        elif format == '31/Dec':
            if not value:
                value = ''
            else:
                value = parser.parse(value)
                value = value.strftime("%d/%b")

        elif format == 'December':
            if not value:
                value = ''
            else:
                value = parser.parse(value)
                value = value.strftime("%B")

        elif format == '52':
            if not value:
                value = ''
            else:
                value = parser.parse(value)
                value = value.strftime("%U")

        # ------------------------------------------------
        # Time
        elif format == '13:37':
            if not value:
                value = ''
            else:
                value = parser.parse(value)
                value = value.strftime("%H:%M")

        elif format == '13:37:46':
            if not value:
                value = ''
            else:
                value = parser.parse(value)
                value = value.strftime("%H:%M:%S")

        elif format == '01:37 PM':
            if not value:
                value = ''
            else:
                value = parser.parse(value)
                value = value.strftime("%I:%M %p")

        elif format == '01:37:46 PM':
            if not value:
                value = ''
            else:
                value = parser.parse(value)
                value = value.strftime("%I:%M:%S %p")

        elif format == '31/12/99 13:37':
            if not value:
                value = ''
            else:
                value = parser.parse(value)
                value = value.strftime("%d/%m/%y %H:%M")


        elif format == '99/12/31 13:37':
            if not value:
                value = ''
            else:
                value = parser.parse(value)
                value = value.strftime("%y/%m/%d %H:%M")

        elif format == '1999/12/31 13:37':
            if not value:
                value = ''
            else:
                value = parser.parse(value)
                value = value.strftime("%Y/%m/%d %H:%M")



        elif format == 'YYYY/MM/DD HH:MM AM':
            if not value:
                value = ''
            else:
                value = parser.parse(value)
                value = value.strftime("%Y/%m/%d %I:%M %p")

        elif format == '31/12/99 13:37:46':
            if not value:
                value = ''
            else:
                value = parser.parse(value)
                value = value.strftime("%d/%m/%y %H:%M:%S")

        elif format == 'DATETIME':
            if not value:
                value = ''
            else:
                value = parser.parse(value)
                from pyasm.biz import ProjectSetting
                setting = ProjectSetting.get_value_by_key('DATETIME')
                if not setting:
                    setting = "%Y-%m-%d %H:%M"
                value = value.strftime(setting)

        elif format == 'DATE':
            if not value:
                value = ''
            else:
                value = parser.parse(value)
                from pyasm.biz import ProjectSetting
                setting = ProjectSetting.get_value_by_key('DATE')
                if not setting:
                    setting = "%Y-%m-%d"
                value = value.strftime(setting)

        elif format == 'TIME_AGO':
            if not value:
                value = ''
            else:
                value = parser.parse(value)
                from pyasm.common import SPTDate
                value = SPTDate.get_time_ago(value)


        elif format == 'DAYS':
            if not real_value:
                value = 0
            else:
                value = real_value.days

        elif format == 'SECONDS':
            if not real_value:
                value = 0
            else:
                value = real_value.days*24*3600 + real_value.seconds



        # ------------------------------------------------
        # Scientific
        elif format == '-1.23E+03':
            if not value:
                value = ''
            else:
                try:
                    value = "%.2e" % self.convert_to_float(value)
                except:
                    value = "0.00"

        elif format == '-1.234E+03':
            if not value:
                value = ''
            else:
                try:
                    value = "%.2e" % self.convert_to_float(value)
                except:
                    value = "0.00"

        # ------------------------------------------------
        # Boolean
        # false = 0, true = 1
        elif format in ['True|False']:
            if real_value and str(real_value).lower() not in ('false', '0'):
                value = 'True'
            else: 
                value = 'False'

        elif format in ['true|false']:
            if real_value and str(real_value).lower() not in ('false', '0'):
                value = 'true'
            else: 
                value = 'false'


        # ------------------------------------------------
        # Timecode
        elif format in ['MM:SS.FF','MM:SS:FF', 'MM:SS', 'HH:MM:SS.FF', 'HH:MM:SS:FF','HH:MM:SS']:
            #fps = self.get_option('fps')
            fps = format_option
            if not fps:
                fps = 24
            else:
                fps = int(fps)
            timecode = TimeCode(frames=value, fps=fps)

            value = timecode.get_timecode(format)

        # ------------------------------------------------
        # Dictionary
        elif format == "DICT":

            dict_as_str = ""
            dict_list = []

            if not value:
                value = ''

            else:
                for key, value in sorted(real_value.items()):
                    dict_list.append("%s : %s" % (key, value))

            dict_as_str = "<br />".join(dict_list)
            value = dict_as_str

        # ------------------------------------------------
        # File Size
        elif format in ['KB']:
            value = float(value)
            ext = " B"
            if not value:
                value = 0
                ext = "B"
            elif value > 1024**5/2:
                value = float(value)/1024**5
                ext = "PB"
            elif value > 1024**4/2:
                value = float(value)/1024**4
                ext = "TB"
            elif value > 1024**3/2:
                value = float(value)/1024**3
                ext = "GB"
            elif value > 1024**2/2:
                value = float(value)/1024**2
                ext = "MB"
            elif value > 1024/2:
                value = float(value)/1024
                ext = "KB"
            else:
                value = int(value)
                return "%s B" % value

            # Preserve the original one-decimal display without requiring a
            # currency locale or slicing its symbol/grouping characters.
            value = self.number_format(value, places=2)[:-1]
            value = "%s %s" % (value, ext)


        elif format in ['ROOT']:
            value, ext = os.path.splitext(value)

        elif format in ['EXT']:
            base, value = os.path.splitext(value)
            value = value.lstrip(".")

        elif format in ['BASENAME']:
            value = os.path.basename(value)

        elif format in ['DIRNAME']:
            value = os.path.dirname(value)

       
        return value


