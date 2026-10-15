"""Identical server script for automatic recording and preference reads."""
import json
import re
from datetime import datetime

from pyasm.biz import PrefList, PrefSetting
from pyasm.command import Command
from pyasm.common import Container, Environment, Xml
from pyasm.search import DbContainer, Search, SearchType, Transaction
from pyasm.security import Security


def normalized(value, name='', clock_fields=False):
    if name == 'timestamp' and value:
        return '<timestamp>'
    if name == 'code' and isinstance(value, str) and (value.startswith('CHANGE_TIMESTAMP_') or re.fullmatch('[0-9a-f]{19}', value)):
        return '<generated code>'
    if name == 'transaction' and value and clock_fields:
        xml = Xml(value)
        for node in xml.get_nodes('transaction/sobject/column'):
            if Xml.get_attribute(node, 'name') == 'timestamp':
                for attribute in ['from', 'to']:
                    stamp = Xml.get_attribute(node, attribute)
                    if stamp and stamp != 'None':
                        datetime.fromisoformat(stamp)
                        Xml.set_attribute(node, attribute, '<timestamp>')
        return xml.to_string()
    if name == 'changed_on' and value and clock_fields:
        fields = json.loads(value)
        for key in fields:
            if fields[key] != '2000-01-01 00:00:00':
                datetime.fromisoformat(fields[key])
                fields[key] = '<timestamp>'
        return json.dumps(fields)
    if isinstance(value, dict):
        return {key: normalized(item, key, clock_fields) for key, item in value.items()}
    if isinstance(value, list):
        return [normalized(item, clock_fields=clock_fields) for item in value]
    return value


class JournalCommand(Command):
    undoable = True

    @staticmethod
    def is_undoable():
        return JournalCommand.undoable

    def __init__(self, case):
        super().__init__()
        self.case = case

    def execute(self):
        tx = self.get_transaction()
        case = self.case
        if 'record' in case:
            tx.set_record(case['record'])
        if 'sync' in case:
            tx.set_sync(case['sync'])
        if case.get('description'):
            self.add_description(case['description'])
        if case.get('title'):
            tx.set_title(case['title'])
        if case.get('nested'):
            Command.execute_cmd(JournalCommand(dict(case, nested=False)))
        if case.get('empty'):
            return 'empty'
        if case.get('update'):
            obj = Search.get_by_code('sthpw/sobject_log', 'SL1')
        else:
            obj = SearchType.create('sthpw/sobject_log')
            obj.set_user()
            obj.set_value('search_type', 'contract/entity?project=one')
            obj.set_value('search_code', 'A')
            obj.set_value('search_id', 1)
        obj.set_value('action', 'changed')
        obj.commit()
        return obj.get_code()


def run(case):
    previous = Environment.get_security()
    security = Security()
    Environment.set_security(security)
    try:
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
        sql = DbContainer.get('sthpw')
        tables = ['sobject_log', 'transaction_log', 'sobject_list', 'change_timestamp', 'pref_setting', 'pref_list']
        for table in tables:
            sql.do_update('DELETE FROM "' + table + '"')
        sql.do_update("DELETE FROM sqlite_sequence WHERE name IN ('transaction_log','sobject_log','sobject_list','change_timestamp','pref_setting','pref_list')")
        sql.do_update("INSERT INTO pref_setting (login,key,value) VALUES ('admin','timezone','UTC')")
        if case.get('update'):
            sql.do_update("INSERT INTO sobject_log (code,login,search_type,search_code,search_id,action) VALUES ('SL1','admin','contract/entity?project=one','A',1,'before')")
        if case.get('existing_timestamp'):
            sql.do_update("INSERT INTO change_timestamp (code,search_type,search_code,changed_on,changed_by) VALUES ('CT1','sthpw/sobject_log','SL1','{\"old\":\"2000-01-01 00:00:00\"}','{\"old\":\"other\",\"action\":\"other\"}')")
        if case.get('existing_direct'):
            sql.do_update("INSERT INTO change_timestamp (code,search_type,search_code,changed_on,changed_by) VALUES ('CT1','contract/entity?project=one','A','{\"old\":\"2000-01-01 00:00:00\"}','{\"old\":\"other\"}')")
        fail = case.get('fail')
        if fail in ['log', 'timestamp']:
            table = 'transaction_log' if fail == 'log' else 'change_timestamp'
            sql.do_update('CREATE TEMP TRIGGER reject_write BEFORE INSERT ON "' + table + '" BEGIN SELECT RAISE(ABORT, \'blocked write\'); END')
        if case.get('method') == 'preference_contract':
            sql.do_update("INSERT INTO pref_setting (login,key,value,project_code) VALUES ('admin','timezone','Asia/Tokyo','one')")
            sql.do_update("INSERT INTO pref_setting (login,key,value) VALUES ('other','timezone','Europe/Moscow')")
            sql.do_update("INSERT INTO pref_list (key,options) VALUES ('timezone','UTC|local')")
            result = {'values': [PrefSetting.get_value_by_key('timezone'),
                                  PrefSetting.get_value_by_key('timezone', project_code='one'),
                                  PrefSetting.get_value_by_key('timezone', user='other'),
                                  PrefSetting.get_value_by_key('missing'),
                                  PrefList.get_value_by_key('timezone')]}
            before = PrefSetting.get_by_key('timezone')
            sql.do_update("UPDATE pref_setting SET value='local' WHERE login='admin' AND project_code IS NULL")
            result['cache'] = [before is PrefSetting.get_by_key('timezone'), PrefSetting.get_value_by_key('timezone'),
                               PrefSetting.get_by_key('timezone', use_cache=False).get_value('value')]
        elif case.get('direct'):
            tx = Transaction.get(create=True)
            tx.set_record(False)
            log = SearchType.create('sthpw/transaction_log')
            log.set_value('code', 'LOG1')
            log.set_value('timestamp', '2026-01-15 12:00:00', temp=True)
            if case.get('timezone') is not None:
                sql.do_update("UPDATE pref_setting SET value=%s" % sql.quote(case['timezone']))
            staged = tx.get_change_timestamp('contract/entity?project=one', 'A', is_insert=not case.get('existing_direct'))
            staged.set_json_value('changed_on', {'name': 'CHANGED', 'ignored': 'leave'})
            staged.set_json_value('changed_by', {'name': 'admin'})
            try:
                tx.update_change_timestamps(log)
                tx.commit()
                result = {'result': 'direct'}
            except ValueError as error:
                tx.rollback()
                result = {'error': type(error).__name__, 'message': str(error)}
        else:
            JournalCommand.undoable = case.get('undoable', True)
            try:
                result = {'result': Command.execute_cmd(JournalCommand(case))}
            except Exception as error:
                result = {'error': type(error).__name__, 'message': str(error)}
        for table in tables[:4]:
            search = Search('sthpw/' + table)
            # A deterministic order avoids different clock ties in two runtimes.
            search.add_order_by('id')
            result[table] = normalized([obj.get_data() for obj in search.get_sobjects()], clock_fields=not case.get('direct'))
        result['admin'] = security.is_admin()
        tx = Transaction.get()
        result['counter'] = tx.counter if tx else None
        result['stack'] = len(Container.get_seq(Command.TOP_CMD_KEY))
        return result
    finally:
        Environment.set_security(previous)
