"""Non-HTML formatting algorithm extracted from original FormatElementWdg.

Checkbox and negative-currency HTML construction are hooks. The legacy widget
retains its DOM hooks; native UI returns typed data and never trusts HTML.
Numeric rounding, date patterns, locale and TimeCode calculations remain the
original algorithm. DAYS/SECONDS fix an undefined original local variable.
"""
import datetime
from dateutil import parser
from pyasm.common.format_value import FormatValue


class FormatValueMixin(FormatValue):
    def format_checkbox(self, value):
        return {'kind': 'boolean', 'checked': bool(value), 'text': 'True' if value else 'False'}

    def format_negative_currency(self, value):
        return {'kind': 'text', 'text': '(' + value + ')', 'negative': True}

    def convert_to_float(self, num):
        try:
            num = float(num)
        except:
            num = 0
        return num

    def number_format(self, num, places=0):
        """Format a number according to locality and given places"""
        num = float(num)
        import locale
        return locale.format_string("%.*f", (places, num), True)

    def get_format_value(self, value, format):
        # Original DAYS/SECONDS branches referenced an undefined real_value.
        real_value = value if hasattr(value, "days") and hasattr(value, "seconds") else None
        if isinstance(value, (datetime.datetime, datetime.date)):
            value = str(value)
        if format not in ['Checkbox'] and value == '':
            return ''
        # ------------------------------------------------
        # Integer
        if format == '-1234':
            if not value:
                # Case where value is '', 0, 0.0, -0.0 . 
                value = 0
            value = "%0.0f" % self.convert_to_float(value)

        elif format == '-1,234':
            if not value:
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
            if not value or value == "0":
                value = " "
            else:
                value = self.currency_format(value, grouping=True)
                if value.startswith("-"):
                    value = self.format_negative_currency(value.replace("-", ""))


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
                try:
                    value = parser.parse(value)
                except:
                    # try utc
                    value = int(value)
                    value = datetime.datetime.fromtimestamp(value)

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
                """
                # TO BE REMOVED: outdated as it is processed in get_display()
                from pyasm.common import SPTDate

                # this is a special column based timezone override
                timezone = self.get_option('timezone')
                if not timezone:
                    pass
                elif timezone == "local":
                    pass # already the default
                    #value = SPTDate.convert_to_local(value)
                else:
                    value = SPTDate.convert_to_timezone(value, timezone)
                """
                value = value.strftime("%I:%M:%S %p")

        elif format == '31/12/99 13:37':
            if not value:
                value = ''
            else:
                value = parser.parse(value)
                value = value.strftime("%d/%m/%y %H:%M")

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
                from pyasm.biz import ProdSetting
                setting = ProdSetting.get_value_by_key('DATETIME')
                if not setting:
                    #setting = "%Y-%m-%d (%I:%M %p)"
                    if value.hour == 0 and value.minute == 0 and value.second == 0:
                        setting = "%b %d, %Y"
                    else:
                        setting = "%b %d, %Y (%I:%M %p)"
                
                value = value.strftime(setting)
                
                

        elif format == 'DATE':
            if not value:
                value = ''
            else:
                value = parser.parse(value)
                from pyasm.biz import ProdSetting
                setting = ProdSetting.get_value_by_key('DATE')
                if not setting:
                    setting = "%Y-%m-%d"
                value = value.strftime(setting)


        elif format == 'TIME_AGO':
            if not value:
                value = ''
            else:
                value = parser.parse(value)
                from pyasm.common import SPTDate
                value = SPTDate.convert(value)
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
            if value:
                value = 'True'
            else: 
                value = 'False'

        elif format in ['true|false']:
            if value:
                value = 'true'
            else: 
                value = 'false'

        elif format == 'Checkbox':
            value = self.format_checkbox(value)

        # ------------------------------------------------
        # Timecode
        elif format in ['MM:SS.FF','MM:SS:FF', 'MM:SS', 'HH:MM:SS.FF', 'HH:MM:SS:FF', 'HH:MM:SS']:
            fps = self.get_option('fps')
            if not fps:
                fps = 24
            else:
                fps = int(fps)
            from pyasm.common import TimeCode
            timecode = TimeCode(frames=value, fps=fps)

            value = timecode.get_timecode(format)


        # ------------------------------------------------
        # Text formats
        elif format in ['wiki']:
            pass



        # ------------------------------------------------
        # File Size
        elif format in ['KB']:
            from pyasm.common import FormatValue
            value = FormatValue().get_format_value(value, 'KB')

        return value

    def get_timezone_value(self, value):
        '''given a datetime value, try to convert to timezone specified in the widget.
           If not specified, use the My Preferences time zone'''
        from pyasm.biz import PrefSetting
        from pyasm.common import SPTDate
        timezone = self.get_option('timezone')
        if not timezone:
            timezone = PrefSetting.get_value_by_key('timezone')
        
        if timezone in ["local", '']:
            value = SPTDate.convert_to_local(value)
        else:
            value = SPTDate.convert_to_timezone(value, timezone)
        
        return value
