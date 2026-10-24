"""SObjectLog and RetireLog from pyasm/search/sobject_log.py.
See LICENSE.TACTIC and compatibility/source_manifest.json.
SObjectLog.create uses the original body and the selected system persistence path.
RetireLog uses the same native Command and journal path.
"""
from pyasm.common.errors import UnsupportedContract
from pyasm.search.search import Search, SearchType, SObject


class SObjectLog(SObject):
    SEARCH_TYPE = 'sthpw/sobject_log'

    @staticmethod
    def create(sobject, transaction, action):
        assert sobject
        log = SObjectLog.create_new()
        # Audit identity must not resolve through a project's wildcard connection.
        log.set_value('search_type', sobject.get_search_type())
        log.set_value('search_id', sobject.get_id())
        if SearchType.column_exists(sobject.get_search_type(), 'code'):
            log.set_value('search_code', sobject.get_value('code'))
        log.set_user()
        log.set_value('transaction_log_id', transaction.get_id())
        if sobject.get_base_search_type() in ['sthpw/task', 'sthpw/snapshot', 'sthpw/note', 'sthpw/work_hour']:
            log.set_value('parent_type', sobject.get_value('search_type'))
            log.set_value('parent_code', sobject.get_value('search_code'))
        log.set_value('action', action)
        log.commit(triggers='none')


class RetireLog(SObject):
    SEARCH_TYPE = 'sthpw/retire_log'

    @staticmethod
    def get_all_by_sobject(sobject):
        search = Search(RetireLog.SEARCH_TYPE)
        search.add_filter('search_type', sobject.get_search_type())
        search.add_filter('search_id', sobject.get_id())
        return search.get_sobjects()

    @staticmethod
    def get_by_interval(interval):
        raise UnsupportedContract('RetireLog interval expressions are not migrated')

    @staticmethod
    def create(search_type, search_id=None, search_code=None):
        from pyasm.common import Container, Environment
        assert search_id or search_code
        log = RetireLog(RetireLog.SEARCH_TYPE)
        log.set_value('search_type', search_type)
        if search_id:
            log.set_value('search_id', search_id)
        else:
            log.set_value('search_code', search_code)
        log.set_value('login', Environment.get_user_name())
        previous = Container.get('RetireLog:writing')
        Container.put('RetireLog:writing', log)
        try:
            log.commit()
        finally:
            Container.put('RetireLog:writing', previous)
        return log
