# Extracted from Southpaw TACTIC; see LICENSE.TACTIC and source_manifest.json.

from datetime import datetime, time, timedelta
import re
from dateutil import parser

from dateutil.tz import gettz, tzlocal, tzutc

basestring = str
TZLOCAL = tzlocal()
TZUTC = tzutc()
TZGMT = gettz("GMT")

class SPTDate:

    @classmethod
    def add_local_timezone(cls, date):
        if isinstance(date, basestring):
            try:
                date = parser.parse(date)
            except Exception:
                return date
        return date.replace(tzinfo=TZLOCAL)

    @classmethod
    def add_timezone(cls, date, timezone):
        '''Add an arbitrary timezone without affecting the value.'''
        if isinstance(date, basestring):
            try:
                date = parser.parse(date)
            except Exception:
                return date
        new_tz = TZLOCAL if timezone == 'local' else gettz(timezone)
        if new_tz is None:
            raise ValueError('Unknown time zone: ' + str(timezone))
        return date.replace(tzinfo=new_tz)

    @classmethod
    def has_timezone(cls, date):
        if isinstance(date, basestring):
            try:
                date = parser.parse(date)
            except Exception:
                return False
        return date.tzinfo is not None

    @classmethod
    def now(cls):
        date = datetime.utcnow()
        date = date.replace(tzinfo=TZGMT)
        return cls.convert(date)

    @classmethod
    def add_gmt_timezone(cls, date):
        if isinstance(date, basestring):
            try:
                date = parser.parse(date)
            except Exception:
                return date
        return date.replace(tzinfo=TZGMT)

    @classmethod
    def convert(cls, date, is_gmt=False):
        # Parse strings BEFORE treating values as datetime.date. Strings are
        # not accepted by datetime.combine (Python 3); preserve date-only noon.
        if isinstance(date, basestring):
            if date == "CURRENT_TIMESTAMP":
                date = datetime.utcnow()
            elif re.fullmatch(r'\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?', date):
                date = datetime.fromisoformat(date)
            else:
                date = parser.parse(date)
        elif not isinstance(date, datetime):
            from datetime import date as Date
            if not isinstance(date, Date):
                raise TypeError("Expected datetime, date, or an ISO date string")
            return datetime.combine(date, time(12, 0))

        # A naive GMT value is already the original method's final result.
        if is_gmt and type(date) is datetime and date.tzinfo is None and not date.fold:
            return date

        # set the timezone to UTC
        if not is_gmt and date.tzinfo == None:
            # assume local timezone if none is given
            date = date.replace(tzinfo=TZLOCAL)
        else:
            offset = date.utcoffset()
            if offset:
                date = date - date.utcoffset()
            date = date.replace(tzinfo=TZGMT)

        #FIXME: it errors out on time before epoch
        try:
            utc = date.astimezone(TZUTC)
        except Exception as e:
            naive = date.replace(tzinfo=None)
        else:
            naive = utc.replace(tzinfo=None)
        return naive

    @classmethod
    def convert_to_local(cls, date):
        '''convert a time to local time with timezone'''
        if not date:
            return None

        if isinstance(date, basestring):
            try:
                date = parser.parse(date)
            except:
                # This could be "now()", for example
                return date

        if date.tzinfo == None:
            # assume GMT
            date = date.replace(tzinfo=TZGMT)

        #NOTE: it errors out on time before epoch
        try:    
            local = date.astimezone(TZLOCAL)
        except Exception as e:
            local = date.replace(tzinfo=None)

        return local

    @classmethod
    def convert_to_timezone(cls, date, timezone):
        '''convert a time to local time with timezone'''
        if not date:
            return None

        if isinstance(date, basestring):
            try:
                date = parser.parse(date)
            except:
                # This could be "now()", for example
                return date

        if date.tzinfo == None:
            # assume GMT
            date = date.replace(tzinfo=TZGMT)

        TZ = gettz(timezone)
        if TZ is None:
            raise ValueError('Unknown time zone: ' + str(timezone))

        date = date.astimezone(TZ)
        return date


    @classmethod
    def today(cls):
        date = datetime.today()
        return cls.convert(date)

    @classmethod
    def strip_timezone(cls, date):
        if isinstance(date, basestring):
            date = parser.parse(date)

        date = date.replace(tzinfo=None)
        return date

    @classmethod
    def set_noon(cls, date):
        date = datetime(date.year, date.month, date.day, hour=12, minute=0, second=0)
        return date

    @classmethod
    def add_business_days(cls, from_date, add_days, holidays=[]):
        if add_days < 0:
            return cls.subtract_business_days(from_date, -add_days, holidays)
        business_days_to_add = add_days
        current_date = from_date
        
        while business_days_to_add >= 0:
            if business_days_to_add > 1:
                current_date += timedelta(days=1)
                weekday = current_date.weekday()
                if weekday >= 5: # sunday = 6
                    continue
                if current_date in holidays:
                    continue
                business_days_to_add -= 1
                if business_days_to_add == 0:
                    break
            else:
                current_date +=timedelta(days=business_days_to_add)
                weekday = current_date.weekday()
                if weekday >= 5 or current_date in holidays:
                    current_date += timedelta(days=1)
                else:
                    break
                business_days_to_add = 0

        return current_date

    @classmethod
    def subtract_business_days(cls, from_date, sub_days, holidays=[]): 
        business_days_to_sub = sub_days
        current_date = from_date

        while business_days_to_sub >= 0:
            if business_days_to_sub > 1:
                current_date -= timedelta(days=1)
                weekday = current_date.weekday()
                if weekday >= 5: # sunday = 6
                    continue
                if current_date in holidays:
                    continue
                business_days_to_sub -= 1
                if business_days_to_sub == 0:
                    break
            else:
                current_date -=timedelta(days=business_days_to_sub)
                weekday = current_date.weekday()
                if weekday >= 5 or current_date in holidays:
                    current_date -= timedelta(days=1)
                else:
                    break
                business_days_to_sub = 0

        return current_date

    @classmethod
    def get_time_ago(cls, date, convert=False, start=None, show_date=True):

        if isinstance(date, basestring):
            date = parser.parse(date)

        if convert:
            date = cls.convert(date)
        else:
            date = cls.strip_timezone(date)

        if start:
            now = start
        else:
            now = cls.now()

        diff = now - date
        if diff.days < 0:
            diff = date - now
            txt = "from now"
        else:
            txt = "ago"



        if diff.days >= 7:
            if show_date in ['false', False]:
                value = "%s days %s" % (diff.days, txt)
            else:
                value = date.strftime("%b %d at %I:%M %p")

        elif diff.days == 1:
            value = "1 day %s" % txt

        elif diff.days > 1:
            value = "%s days %s" % (diff.days, txt)

        # less than a minute
        elif diff.seconds < 60:
            value = "%s seconds %s" % (diff.seconds, txt)

        # less than an hour
        elif diff.seconds < 60 * 60:
            minutes = int(diff.seconds / 60)
            if minutes == 1:
                value = "1 minute %s" % txt
            else:
                value = "%s minutes %s" % (minutes, txt)

        # less than a day
        elif diff.seconds < 60 * 60 * 24:
            hours = float(diff.seconds) / 60.0 / 60.0
            if hours < 12:
                value = "%0.1f hours %s" % (hours, txt)
            else:
                value = "%s hours %s" % (int(hours), txt)


        else:
            value = date.strftime("%b %d at %I:%m %p")

        return value

