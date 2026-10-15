# Copyright (c) 2005-2008, Southpaw Technology. See LICENSE.TACTIC.
"""Calendar/time input metadata and original database actions; HTML is excluded."""
from datetime import datetime
from dateutil import parser
from pyasm.command import DatabaseAction
from pyasm.biz import NamingUtil
from pyasm.search import SObject, SearchType
from pyasm.widget import BaseInputWdg

__all__ = ['CalendarInputWdg']

class CalendarInputWdg(BaseInputWdg):
    ARGS_KEYS = {

         "first_day_of_week": {
            'description': "Integer representing first day of the week (6=Sunday, 0=Monday)",
            'type': 'SelectWdg',
            'labels': 'Sunday|Monday',
            'values': '6|0',
            'empty': 'true',
            'order': 0,
            'category': 'Display'
         },
        "show_time": {
            'description': "Determines whether or not a time value is entered.",
            'type': 'SelectWdg',
            'values': 'true|false',
            'order': 1,
            'category': 'Display'
        },
        "show_calendar": {
            'description': "Determines whether or not the calendar is shown.",
            'type': 'SelectWdg',
            'values': 'true|false',
            'category': 'Display'
        },
        "show_activator": {
            'description': "Determines whether or not to show the default activator for this widget",
            'type': 'SelectWdg',
            'values': 'true|false',
            'empty': 'true',
            'order': 1,
            'category': 'internal'
        },
        "read_only": {
            'description': "Sets the widget to be read only. In this case, the calendar will not show up and only a text box with the date value will be visible.",
            'type': 'SelectWdg',
            'values': 'true|false',
            'empty': 'true',
            'order': 1,
            'category': 'Display'
        },

        "date_format": {
            'description': "format of the date on clicking on a day in the Calendar, e.g. %m-%d-%Y or default to the project setting DATETIME or DATE",
            'type': 'TextWdg',
            'category': 'Display',
            'order': 8,
        },

        "display_format" : {
            'description': "display format like YYYY/MM/DD HH:MM AM or default to the project setting DATETIME or DATE",
            'type': 'TextWdg',
            'category': 'Display',
            'order': 9,
        },

        "hint_text" : {
            'description': "hint_text can be used to tell users why the calendar input is read only",
            'type': 'TextWdg',
            'category': 'Display',
        },


        'default': {
        'description': 'The default selection value in an edit form. Can be a TEL variable.',
        'type': 'TextWdg',
        'category': 'Display',
        'order': 2,
        },
        'search_key': {
        'description': 'The search key from which to extract data from',
        'type': 'TextWdg',
        'category': 'internal'
        },
        "time_input_default": {
        'description': 'The default for time applicable when show_time is true or false. e.g. 5:00 PM',
        'type': 'TextWdg',
        'category': 'Display',
        'order': 3
        },

        "offset" : {
            'description': "offset the calendar, e.g. x,y",
            'type': 'TextWdg',
            'category': 'Display',
            'order': 10,
        },
        "display_mode": {
            'description': "Determines whether to use the TACTIC calendar or the browser calendar",
            'type': 'SelectWdg',
            'values': 'browser|inline',
            'category': 'Display',
            'order': 3
        },
    }

    def __init__(self, name=None, **kwargs):
        super().__init__(name, 'calendar', **kwargs)

    def get_value(self):


        # has to use self.value instead of self.get_value()
        # to avoid a display bug with multiple inputs
        default = self.get_option("default")

        value = ""
        if not self.value and default:
            default_value = NamingUtil.eval_template(default)
            value = default_value
            if value:
                value = parser.parse(value)
                # NOTE: it's better not to do auto-convert for passed in value
                # since it could be already in local time

        current = self.get_current_sobject()

        if current and not current.is_insert():
            column = self.get_option("column")
            if not column:
                column = self.get_name()

            db_date = current.get_value(column, no_exception=True)

            if db_date:
                # This date is assumed to be GMT
                import re
                regex = r"^\d+-\d+-\d+$"
                if re.findall(regex, db_date):
                    # since this is assumed to be GMT, and there is no time,
                    # we are adding 12:00:00
                    db_date = f"{db_date} 12:00:00"
                try:
                    value = parser.parse(db_date)
                except:
                    raise ValueError("Invalid calendar value: " + str(db_date))


                #from pyasm.common import SPTDate
                #from pyasm.search import SObject
                date = value
                if not SObject.is_day_column(self.get_name()) and SearchType.get_column_type(current.get_search_type(), column) != 'date':
                    date = self.get_timezone_value(value)

                # Keep the datetime: localized month names cannot be reparsed by dateutil.
                value = date



        show_time = self.get_option("show_time") in [True, 'true']
        if show_time:
            key = 'DATETIME'
        else:
            key = 'DATE'

        if not value:
            value = self.value

        if value:
            format = self.get_option("display_format")

            if not format:
                format = key

            from pyasm.common import FormatValue
            f = FormatValue()
            value = f.get_format_value(value, format)

        return value


class DateDatabaseAction(DatabaseAction):

    def execute(self):
        name = self.get_name()

        column = self.get_option("column")
        if not column:
            column = name

        columns = column.split("|")
        for column in columns:

            value = self.get_value()
            if value:
                value = parser.parse(value)
                day = value.day
                month = value.month
                year = value.year

            else:
                return


            sobject = self.sobject
            cur_value = sobject.get_value(column)

            if cur_value and isinstance(cur_value, str):
                cur_value = parser.parse(cur_value)

            if cur_value:
                column_info = sobject.get_column_info(column)
                if column_info.get("data_type") in ['timestamp', 'datetime', 'datetime2']:
                    cur_value = cur_value.replace(year=year, month=month, day=day)
                else:
                    cur_value = value
            else:
                cur_value = value

            sobject.set_value(column, cur_value)

        return name


class TimeDatabaseAction(DatabaseAction):

    def execute(self):
        name = self.get_name()

        column = self.get_option("column")
        if not column:
            column = name

        value = self.get_value()
        if value:
            value = parser.parse(value)
            hour = value.hour
            minute = value.minute
        else:
            hour = 12
            minute = 0

        sobject = self.sobject
        cur_value = sobject.get_value(column)
        if cur_value:
            if isinstance(cur_value, str):
                cur_value = parser.parse(cur_value)
        else:
            cur_value = datetime.now()

        column_info = sobject.get_column_info(column)
        if column_info.get("data_type") in ['timestamp', 'datetime', 'datetime2']:
            cur_value = cur_value.replace(hour=hour, minute=minute)
        elif column_info.get('data_type') == 'time':
            cur_value = value.time().isoformat() if value else ''
        else:
            cur_value = value

        sobject.set_value(column, cur_value)

        return name


class TimeInputWdg(BaseInputWdg):
    ARGS_KEYS = {
           "interval": {
                'description': "Interval for minutes, default to 10",
                'type': 'SelectWdg',
                'values': '1|5|10|20|30',
                'empty': 'true',
                'order': 1,
                'category': 'Display'
            },
           "default": {
                'description': "Default time",
                'type': 'TextWdg',
                'order': 2,
                'category': 'Display',
            }
    
        }

    def __init__(self, name=None, **kwargs):
        super().__init__(name, 'time', **kwargs)

    def get_input(self):
        from pyasm.widget import TextWdg
        value = self.get_value(for_display=True)
        if not value:
            value = self.get_option('time') or self.get_option('default') or '12:00 PM'
        date = parser.parse(str(value))
        parent = self.get_parent_wdg()
        handler = parent.config.get_action_handler(self.name) if parent else ''
        current = self.get_current_sobject()
        if current and not current.is_insert() and handler in ('TimeAction', 'pyasm.command.TimeAction', 'pyasm.command.edit_wdg_action.TimeAction'):
            date = self.get_timezone_value(date)
        self.input_value = date.strftime('%H:%M')
        control = TextWdg(self.get_input_name())
        control.set_value(value)
        return control


__all__ += ['TimeInputWdg', 'DateDatabaseAction', 'TimeDatabaseAction']
