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


__all__ = ['WorkHour']

from pyasm.search import *
from pyasm.biz import Project
from pyasm.common import Environment
from decimal import Decimal, InvalidOperation


def hours_value(value):
    try:
        result = Decimal(str(value or 0))
    except InvalidOperation:
        raise ValueError('Invalid work hours') from None
    if not result.is_finite() or result < 0:
        raise ValueError('Invalid work hours')
    return result

class WorkHour(SObject):
    '''Work hour for task or various items'''
    SEARCH_TYPE = "sthpw/work_hour"

    def get_regular_hours(self):
        return Decimal(0) if self.get_value('category') == 'overtime' else hours_value(self.get_value('straight_time'))

    def get_overtime_hours(self):
        value = hours_value(self.get_value('over_time'))
        return value or (hours_value(self.get_value('straight_time')) if self.get_value('category') == 'overtime' else Decimal(0))

    def get_total_hours(self):
        return self.get_regular_hours() + self.get_overtime_hours()

    def is_approved(self):
        return str(self.get_value('status')).lower() == 'approved'

    @staticmethod
    def get_summary(task, entries):
        # Handler WorkHoursController._summary; overtime is not counted twice.
        from .prod_setting import ProjectSetting
        planned = hours_value(task.get_value('bid_duration'))
        if ProjectSetting.get_value_by_key('bid_duration_unit') == 'minute':
            planned /= 60
        logged = sum((entry.get_total_hours() for entry in entries), Decimal(0))
        approved = sum((entry.get_total_hours() for entry in entries if entry.is_approved()), Decimal(0))
        values = dict(planned=planned, logged=logged, approved=approved, pending=max(logged-approved, 0),
            remaining=max(planned-approved, 0), overPlan=max(approved-planned, 0),
            overtime=sum((entry.get_overtime_hours() for entry in entries), Decimal(0)),
            progress=min(100, approved*100/planned) if planned else Decimal(0))
        return dict({name: float(Decimal(value).quantize(Decimal('0.01'))) for name, value in values.items()},
                    entryCount=len(entries))

    def get_defaults(self):
        '''specifies the defaults for this sobject'''
        project_code = Project.get_project_code()
        me = Environment.get_user_name()
        defaults = {
            "project_code": project_code,
            "login": me
        }

        return defaults


 
