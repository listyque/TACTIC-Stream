"""Per-user view state in ORIGINAL sthpw/wdg_settings / WidgetSettings.

Native JSON is namespaced: it must not overwrite legacy FilterData XML or
TabSaveStateCmd's differently shaped values. Saved named views remain in
config/widget_config. Search/result records and unsaved edits are never stored.
"""
import hashlib
import json
from .contracts import ApiError, revision, clean_query, coerce_value
from tactic.core.query_model import normalize_tree

SCOPES = {'workspace', 'query', 'geometry', 'appearance', 'tabs', 'timeline', 'navigation', 'stype-editor'}
MAX_BYTES = 65536


def storage_key(scope, target=''):
    if not isinstance(scope, str) or scope not in SCOPES or not isinstance(target, str) or len(target) > 4000:
        raise ApiError(400, 'state_scope', 'Неизвестный тип настроек')
    return 'native:ui:v1:'+scope+(':'+hashlib.sha256(target.encode()).hexdigest() if target else '')


def _names(value, allowed, name, limit=256):
    if not isinstance(value, list) or len(value)>limit or any(not isinstance(n,str) or n not in allowed for n in value) or len(set(value))!=len(value):
        raise ApiError(400,'state_columns','Некорректные имена/дубли: '+name)
    return list(value)


def validate_state(scope, value, spec=None):
    if not isinstance(scope, str) or scope not in SCOPES:
        raise ApiError(400,'state_scope','Неизвестный тип настроек')
    if not isinstance(value, dict):
        raise ApiError(400,'state_object','Настройки должны быть объектом')
    try:
        if len(json.dumps(value, ensure_ascii=False, allow_nan=False).encode('utf-8')) > MAX_BYTES:
            raise ValueError('too large')
    except (ValueError, TypeError):
        raise ApiError(400,'state_size','Некорректные или слишком большие настройки')
    if scope == 'stype-editor':
        if set(value)-{'selected','tab'} or value.get('selected','') not in set(spec['types'])|{''} or value.get('tab','columns') not in ('columns','metadata','views','references','import'):
            raise ApiError(400,'state_editor','Некорректное состояние редактора SearchType')
        return {'selected':value.get('selected',''),'tab':value.get('tab','columns')}
    if scope == 'workspace':
        if set(value)-{'ids','active'}:
            raise ApiError(400,'state_fields','Неизвестные параметры рабочего пространства')
        ids=value.get('ids',[]);active=value.get('active','')
        if not isinstance(ids,list) or len(ids)>32 or any(not isinstance(x,str) or not x or len(x)>4000 for x in ids) or len(set(ids))!=len(ids) or not isinstance(active,str) or active and active not in ids:
            raise ApiError(400,'state_tabs','Некорректные вкладки')
        return {'ids':ids,'active':active}
    if scope == 'appearance':
        if set(value)-{'theme'} or value.get('theme') not in ('light','dark'):
            raise ApiError(400,'state_theme','Некорректная тема')
        return {'theme':value['theme']}
    if scope == 'navigation':
        folders=value.get('folders',{})
        if set(value)-{'folders'} or not isinstance(folders,dict) or len(folders)>1024 or any(k not in spec['folders'] or not isinstance(v,bool) for k,v in folders.items()):
            raise ApiError(400,'state_navigation','Некорректные папки sidebar')
        return {'folders':folders}
    if scope == 'tabs':
        if set(value)-{'order','closed','selected','titles'}:
            raise ApiError(400,'state_tabs','Неизвестные параметры вкладок')
        children=spec['children'];names={c['name'] for c in children}
        if len(names)!=len(children):
            raise ApiError(409,'ambiguous_tabs','Повторяющиеся имена вкладок требуют отдельного разрешения')
        order=_names(value.get('order',[]),names,'order',64);closed=_names(value.get('closed',[]),names,'closed',64)
        selected=value.get('selected','');titles=value.get('titles',{})
        if not isinstance(selected,str) or selected and (selected not in names or selected in closed):
            raise ApiError(400,'state_tabs','Выбранная вкладка скрыта или отсутствует')
        if any(c['name'] in closed and not c['removable'] for c in children):
            raise ApiError(403,'protected_tab','Защищённую вкладку нельзя закрыть')
        if spec.get('container',{}).get('allow_drag') is False and order and order!=[c['name'] for c in children]:
            raise ApiError(403,'tab_order','Перестановка запрещена исходной конфигурацией')
        if not isinstance(titles,dict) or any(k not in names or not isinstance(v,str) or not v.strip() or len(v)>200 for k,v in titles.items()):
            raise ApiError(400,'tab_titles','Некорректные названия вкладок')
        return {'order':order,'closed':closed,'selected':selected,'titles':titles}
    fields=spec['fields'];allowed={f['name'] for f in fields if not f.get('write_only')}
    if scope == 'timeline':
        from datetime import date
        keys={'mode','start','end','month','zoom','startField','endField','includeUndated'}
        if set(value)!=keys:
            raise ApiError(400,'state_timeline','Некорректные параметры календаря')
        try:
            if not all(isinstance(value[k],str) for k in ('start','end','month')):raise ValueError()
            start=date.fromisoformat(value['start']);end=date.fromisoformat(value['end'])
            date.fromisoformat(value['month']+'-01')
            if not 0<=(end-start).days<366:raise ValueError()
        except (ValueError,TypeError):raise ApiError(400,'state_dates','Некорректный период')
        dates={f['name'] for f in fields if f.get('storage') and f['kind'] in ('date','datetime') and not f.get('hidden')}
        if value['mode'] not in ('gantt','calendar') or any(not isinstance(value[k],str) or value[k] and value[k] not in dates for k in ('startField','endField')) or not isinstance(value['includeUndated'],bool) or isinstance(value['zoom'],bool) or not isinstance(value['zoom'],(int,float)) or not 10<=value['zoom']<=70:
            raise ApiError(400,'state_timeline','Недопустимые параметры календаря')
        return dict(value)

    if scope == 'geometry':
        if set(value)-{'widths','order','hidden','pinned','density','wrap','groupField','mode'}:
            raise ApiError(400,'state_fields','Неизвестные параметры таблицы')
        widths=value.get('widths',{})
        if not isinstance(widths,dict) or any(n not in allowed or isinstance(w,bool) or not isinstance(w,(int,float)) or not 64<=w<=1200 for n,w in widths.items()):
            raise ApiError(400,'state_width','Некорректная ширина колонки')
        result={'widths':widths}
        for k in ('order','hidden','pinned'):
            result[k]=_names(value.get(k,[]),allowed,k)
        density=value.get('density','comfortable');wrap=value.get('wrap',False);mode=value.get('mode','table');group=value.get('groupField','')
        if density not in ('compact','comfortable','spacious') or not isinstance(wrap,bool) or mode not in ('table','cards') or not isinstance(group,str) or group and group not in allowed:
            raise ApiError(400,'state_geometry','Некорректные параметры отображения')
        result.update(density=density,wrap=wrap,mode=mode,groupField=group)
        return result
    if scope == 'query':
        keys={'filters','where','sort','record_state','offset','limit','presentation','search_open','quickField','quickText','quickOp'}
        if set(value)-keys:
            raise ApiError(400,'state_fields','Неизвестные параметры поиска')
        clean=clean_query(value,fields,spec.get('default_sort'))
        advanced=normalize_tree(value.get('where'),fields,coerce_value,maximum=40)
        presentation=value.get('presentation','data');opened=value.get('search_open',False)
        quick_field=value.get('quickField','');quick_text=value.get('quickText','');quick_op=value.get('quickOp','contains')
        if presentation not in ('data','tree','timeline','collections') or not isinstance(opened,bool) or not isinstance(quick_field,str) or (quick_field and quick_field not in allowed) or not isinstance(quick_text,str) or len(quick_text)>2000 or quick_op not in ('contains','eq','ne','gt','lt','null','not_null'):
            raise ApiError(400,'state_query','Некорректные параметры поиска')
        return {**{k:clean[k] for k in ('filters','record_state','offset','limit')},
                'where':advanced,'sort':value.get('sort'), 'presentation':presentation,'search_open':opened,
                'quickField':quick_field,'quickText':quick_text,'quickOp':quick_op}
    raise ApiError(400,'state_scope','Неизвестный тип настроек')


class UiStateService:
    def ui_state_operation(self, method, data):
        from pyasm.web import WidgetSettings
        from pyasm.common import Environment
        from pyasm.search import Search
        scope=data.get('scope');target=data.get('target','')
        key=storage_key(scope,target)
        if scope in ('workspace','appearance','navigation') and target:
            raise ApiError(400,'state_target','Рабочее пространство не принимает target')
        spec=None
        if scope in ('geometry','query','timeline','tabs'):
            opened=self.open_target(target)
            if opened.get('kind')!=('tabs' if scope=='tabs' else 'table'):
                raise ApiError(400,'state_target','Настройки предназначены для конфигурационной таблицы')
            spec=opened if scope=='tabs' else opened['spec']
        if scope=='stype-editor':
            screen=self.open_target(target)
            if screen['kind']!='search-types':raise ApiError(403,'state_target','Состояние не относится к редактору SearchType')
            spec={'types':[o.get_value('search_type') for o in self._stype_objects()]}
        if scope=='navigation':
            def folders(nodes):
                result=set()
                for n in nodes:
                    if n.get('kind')=='folder':result.add(n['id'])
                    result.update(folders(n.get('children',[])))
                return result
            spec={'folders':folders(self.sidebar()['sections'])}
        search=Search('sthpw/wdg_settings');search.add_filter('project_code',self._project())
        search.add_filter('login',Environment.get_user_name());search.add_filter('key',key)
        if search.get_count()>1:
            raise ApiError(409,'duplicate_state','Найдены дубли настроек; автоматическая перезапись запрещена')
        persistence_disabled=False
        if scope=='query':
            from pyasm.prod.biz import ProdSetting
            persistence_disabled=ProdSetting.get_value_by_key('set_persistent_search')=='false'
            if method!='GET' and persistence_disabled:
                raise ApiError(403,'search_persistence_disabled','Проект отключает сохранение последнего поиска (set_persistent_search=false)')
        raw=WidgetSettings.get_value_by_key(key,default='')
        current_revision=revision(raw or '')
        if method=='GET':
            warning=None;value=None
            if raw and not persistence_disabled:
                try:
                    decoded=json.loads(raw)
                    if decoded.get('format')!=1 or decoded.get('scope')!=scope or decoded.get('target','')!=target:
                        raise ValueError('unsupported state envelope')
                    value=validate_state(scope,decoded['value'],spec)
                except (ValueError,TypeError,KeyError,AttributeError,ApiError):
                    warning='Сохранённые настройки не подходят текущей конфигурации. Исходные данные в БД не удалены; применены настройки представления.'
            return {'value':value,'revision':current_revision,'can_write':self.allow_writes and not persistence_disabled,
                    'storage':'sthpw/wdg_settings','setting_key':key,'warning':warning}
        if method!='PATCH':
            raise ApiError(405,'method','Метод не поддерживается')
        if set(data)-{'project','scope','target','value','revision'}:
            raise ApiError(400,'state_fields','Произвольные login/ключи настроек запрещены')
        if data.get('revision')!=current_revision:
            raise ApiError(409,'state_conflict','Настройки изменены в другом окне. Перечитайте сохранённые настройки перед заменой.')
        value=validate_state(scope,data.get('value'),spec)
        payload={'format':1,'scope':scope,'target':target,'value':value}
        serialized=json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':'))
        def save():
            # Original API manages user/project identity and updates data with
            # triggers=False, just as WidgetSettingSaveCbk in the legacy UI.
            if serialized != raw:
                WidgetSettings.set_value_by_key(key,serialized)
            return {'saved':True,'value':value,'revision':revision(serialized),'storage':'sthpw/wdg_settings','setting_key':key}
        return self._write(save)
