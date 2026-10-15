"""Server-owned child views of the stock administration widgets."""
from urllib.parse import unquote
from .contracts import ApiError

class AdminWorkspace:
    def admin_derived_target(self,parent,part,key):
        kind=parent['kind'];options=dict(parent.get('options') or {})
        if part in ('security','assignment','memberships'):
            allowed={'security':('users',),'assignment':('users',),'memberships':('security','users','groups')}
            if kind not in allowed[part]:raise ApiError(403,'admin_child','Недоступный дочерний административный виджет')
            handler={'security':'SecurityWdg','assignment':'UserSecurityWdg','memberships':'UserAssignWdg'}[part]
            return {'id':key,'kind':{'security':'security','assignment':'group-assignment','memberships':'group-membership'}[part],
                    'handler':'tactic.ui.startup.'+handler,'title':handler,'view':'table','search_type':None,'options':{},'attributes':{},'config_view':parent.get('config_view')}
        if part in ('users-table','groups-table'):
            if part=='users-table' and kind!='users' or part=='groups-table' and kind not in ('security','users','groups'):
                raise ApiError(403,'admin_child','Таблица не принадлежит этому административному виджету')
            if part=='users-table':
                view=options.get('view') or 'manage_user'
                # target_spec gives table as a default even when UserPanel has no explicit view.
                if view=='table' and not options.get('view'):view='manage_user'
                opts={'native_user_panel':True,'native_project_users':options.get('filter_mode')=='project',
                      'show_insert':'false' if options.get('show_add') in (False,'false') else 'true',
                      'show_column_manager':'false','show_layout_switcher':'false','show_gear':'false','show_select':'false',
                      'show_search_limit':options.get('show_search_limit','true'), 'simple_search_view':'login_filter'}
                stype='sthpw/login'
            else:
                view=options.get('view') or 'startup' if kind=='groups' else 'startup'
                opts={k:v for k,v in options.items() if k.startswith('show_') or k in ('expression',)} if kind=='groups' else {}
                opts.update(insert_view=options.get('custom_insert_view') or 'insert',edit_view=options.get('custom_edit_view') or 'edit')
                stype='sthpw/login_group'
            return {'id':key,'kind':'table','handler':'tactic.ui.panel.ViewPanelWdg','search_type':stype,'view':view,
                    'title':'Users' if part=='users-table' else 'Groups','options':opts,'attributes':{},'config_view':parent.get('config_view')}
        if part.startswith('stype-tool:'):
            if kind!='search-types':raise ApiError(403,'admin_child','Инструмент не принадлежит редактору SearchType')
            tool,sep,encoded=part[len('stype-tool:'):].partition(':')
            stype=unquote(encoded);self._stype_object(stype)
            tools={'views':('views-manager','tactic.ui.manager.ViewManagerWdg'),
                   'workflow':('pipeline','tactic.ui.tools.PipelineToolWdg'),
                   'schema':('schema','tactic.ui.tools.SchemaToolWdg'),
                   'insert':('form','tactic.ui.panel.EditWdg')}
            if not sep or tool not in tools:raise ApiError(403,'admin_child','Неизвестный инструмент SearchType')
            k,handler=tools[tool];options={'search_type':stype}
            if tool=='insert':options.update(view='insert',mode='insert')
            return {'id':key,'kind':k,'handler':handler,'search_type':stype,'view':'insert' if tool=='insert' else 'table',
                    'title':stype+' · '+tool,'options':options,'attributes':{},'config_view':parent.get('config_view')}
        if part.startswith('stype-table:'):
            if kind!='search-types':raise ApiError(403,'admin_child','Таблица не принадлежит редактору SearchType')
            stype=unquote(part[len('stype-table:'):]);self._stype_object(stype)
            return {'id':key,'kind':'table','handler':'tactic.ui.panel.ViewPanelWdg','search_type':stype,'view':'table',
                    'title':stype,'options':{},'attributes':{},'config_view':parent.get('config_view')}
        raise ApiError(403,'admin_child','Неизвестный дочерний виджет')

    def admin_user_filter(self,search,options):
        """UserPanelWdg's original @SEARCH predicate expressed through Search."""
        from pyasm.search import Search
        search.add_filters('login',['admin','guest'],op='not in')
        search.add_op('begin');search.add_filter('license_type','user');search.add_filter('license_type',None);search.add_op('or')
        if options.get('native_project_users'):
            groups=Search('sthpw/login_group');groups.add_filter('project_code',self._project());names=[g.get_value('login_group') for g in groups.get_sobjects()]
            members=Search('sthpw/login_in_group');members.add_filters('login_group',names)
            logins=[m.get_value('login') for m in members.get_sobjects()] if names else []
            if logins:search.add_filters('login',logins)
            else:search.add_filter('id',-1)
