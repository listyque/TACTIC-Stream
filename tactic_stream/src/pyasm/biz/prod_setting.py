"""ProjectSetting adapted from pyasm/biz/prod_setting.py.

Settings remain config/prod_setting SObjects in each project's database.
See LICENSE.TACTIC and compatibility/source_manifest.json.
"""
from pyasm.common.common import TacticException, Container
from pyasm.biz.project import Project
from pyasm.search.search import Search, SObject, SObjectFactory


class ProjectSetting(SObject):
    SEARCH_TYPE = "config/prod_setting"

    @classmethod
    def _get_container_key(cls, key, search_type=None):
        return "ProjectSetting:%s:%s" % (key, search_type) if search_type else "ProjectSetting:%s" % key

    @classmethod
    def get_by_key(cls, key, search_type=None):
        cached = cls._get_cached_for_read('%s:%s' % (key, search_type))
        if cached is not None:
            return None if cached == '__NONE__' else cached
        try:
            search = Search(cls.SEARCH_TYPE, project_code=Project.get_project_code())
        except LookupError as exc:
            if str(exc).startswith("Unregistered SearchType:"):
                return None
            raise
        search.add_filter("key", key)
        if search_type:
            search.add_filter("search_type", search_type)
        return ProjectSetting.get_by_search(search, '%s:%s' % (key, search_type))

    @classmethod
    def get_value_by_key(cls, key, search_type=None):
        setting = cls.get_by_key(key, search_type)
        return setting.get_value("value") if setting else ''

    @classmethod
    def get_json_value_by_key(cls, key, search_type=None):
        if Project.get_project_name() in ('admin', 'sthpw'):
            return ''
        setting = cls.get_by_key(key, search_type)
        return setting.get_json_value("value") if setting else ''

    @classmethod
    def get_seq_by_key(cls, key, search_type=None):
        value = cls.get_value_by_key(key, search_type)
        return value.split('|') if value else []

    @classmethod
    def get_map_by_key(cls, key, search_type=None):
        result = []
        for item in cls.get_seq_by_key(key, search_type):
            try:
                name, value = item.split(':')
                result.append((name, value))
            except Exception:
                raise TacticException('ProjectSetting should be formated like &lt;key1&gt;:&lt;value1&gt;|&lt;key2&gt;:&lt;value2&gt;|...')
        return result

    @classmethod
    def get_dict_by_key(cls, key, search_type=None):
        return dict(cls.get_map_by_key(key, search_type))

    @classmethod
    def add_value_by_key(cls, key, value, search_type=None):
        seq = cls.get_seq_by_key(key, search_type)
        if not seq:
            seq = []
        elif value in seq:
            return
    
        seq.append(value)
    
        setting = cls.get_by_key(key, search_type)
        if not setting:
            return
    
    
        setting.set_value( "value", "|".join(seq) )
        setting.commit()
    
        container_key = cls._get_container_key(key,search_type)
        value = Container.put(container_key, None)

    @staticmethod
    def create(key, value, type="string", description='', search_type=''):
        '''create a ProjectSetting'''
    
        if Project.get_project_name() in ['admin', 'sthpw']:
            return None
    
        ProjectSetting.clear_cache()
        setting = ProjectSetting.get_by_key(key, search_type)
        if not setting:
            setting= SObjectFactory.create( ProjectSetting.SEARCH_TYPE )
            setting.set_value("key", key)
            setting.set_value("value", value)
            
            setting.set_value("type", type)
            if description:
                setting.set_value("description", description)
            if search_type:
                setting.set_value("search_type", search_type)
        else:
            setting.set_value("value", value)
    
        setting.commit()
        return setting

class ProdSetting(ProjectSetting):
    pass
