"""Configured work-hour cells executed by the original WorkHoursElementAction.

Editing is deliberately limited to straight_time mode and the current login.
Time-of-day records and duplicate cells stay visible but cannot be overwritten
by an aggregated value. Zero/empty explicitly deletes the one matching entry,
as in the original action. A native UI switch never changes that rule.
"""
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
import json
from .contracts import ApiError, json_safe, revision, text
from tactic.core.field_policy import field_access

HOUR_ACTIONS={'tactic.ui.table.WorkHoursElementAction',
              'tactic.core.work_hours.WorkHoursElementAction','WorkHoursElementAction'}
HOUR_HANDLERS={'tactic.ui.table.WorkHoursElementWdg','WorkHoursElementWdg'}

class WorkHourService:
    def _hours_config(self, opened=None, element='work_hours'):
        from pyasm.common import Environment
        from .contracts import safe_field
        if not isinstance(element, str) or not safe_field(element):
            raise ApiError(400,'hours_field','Некорректное имя поля рабочего времени')
        opened=opened or {}
        is_task=opened.get('search_type')=='sthpw/task'
        display_view=opened.get('view','table') if is_task else 'table'
        edit_view=((opened.get('options') or {}).get('edit_view') or 'edit') if is_task else 'edit'
        model=self._model('sthpw/task',edit_view)
        display_model=self._model('sthpw/task',display_view)
        el=model.describe(element);display=display_model.describe(element)
        opts={**display['options'],**el['action_options']}
        security=Environment.get_security()
        visible,editable=field_access(security,self._project(),'sthpw/task',element,el['attributes'])
        display_visible,display_editable=field_access(security,self._project(),'sthpw/task',element,display['attributes'])
        if not visible or not display_visible:
            raise ApiError(403,'hours_denied','Нет доступа к полю рабочего времени')
        # WorkHoursElementWdg.get_default_action() supplies this exact handler
        # when a view omits an explicit action. Never choose it for custom Wdg.
        action=el['action_handler'] or display['action_handler'] or ('WorkHoursElementAction' if display['handler'] in HOUR_HANDLERS else '')
        supported=action in HOUR_ACTIONS and display['handler'] in HOUR_HANDLERS
        straight=opts.get('use_straight_time') not in (False,'false')
        own=opts.get('show_all_users') not in (True,'true')
        unit=opts.get('unit') or 'hour'
        try:days=int(opts.get('days_per_page') or 7)
        except (TypeError,ValueError):raise ApiError(400,'hours_config','days_per_page должен быть числом')
        if not 1<=days<=31:raise ApiError(400,'hours_config','Нативный редактор поддерживает days_per_page от 1 до 31')
        editable = editable and display_editable and opts.get('read_only') not in (True,'true') and opts.get('save') not in (False,'false')
        return {'revision':revision({'edit':model.fingerprint(),'display':display_model.fingerprint(),'element':element,'options':opts}),
                'unit':unit,'straight':straight,'own':own,'field':element,'days_per_page':days,
                'show_overtime':opts.get('show_overtime') in (True,'true'),
                'editable':bool(editable and supported and straight and own and unit in ('hour','minute')),
                'options':opts,
                'notice':('Время начала/окончания, custom actions и режим всех пользователей доступны только для чтения'
                          if not (supported and straight and own) else
                          'Изменяются только ваши записи. Ноль/пустая ячейка удаляет соответствующую запись work_hour штатным action.')}

    @staticmethod
    def _hours_window(data, config):
        try:
            start_value=data.get('start') or config.get('options',{}).get('start_date')
            days=config.get('days_per_page',7)
            if start_value:
                start=date.fromisoformat(start_value if data.get('start') else str(start_value)[:10])
            else:
                start=date.today()
                if days>=7:start-=timedelta(days=(start.weekday()+1)%7)
            end=date.fromisoformat(data['end']) if data.get('end') else start+timedelta(days=days-1)
        except (KeyError,ValueError,TypeError) as exc:
            raise ApiError(400,'hours_dates','Нужны start/end в формате YYYY-MM-DD') from exc
        if end<start or (end-start).days>30:
            raise ApiError(400,'hours_dates','Диапазон должен содержать от 1 до 31 дня')
        return start,end

    def _hours_state(self,parent,task,start,end,config):
        from pyasm.search import Search
        from pyasm.common import Environment
        login=Environment.get_user_name()
        search=Search('sthpw/work_hour');search.add_relationship_filter(parent)
        search.add_filter('task_code',task.get_code())
        if config['own']:search.add_filter('login',login)
        search.add_filter('day',start.isoformat()+' 00:00:00',op='>=')
        search.add_filter('day',(end+timedelta(days=1)).isoformat()+' 00:00:00',op='<')
        search.add_order_by('day');search.add_order_by('id');search.set_limit(3001)
        entries=search.get_sobjects()
        if len(entries)>3000:raise ApiError(413,'hours_limit','Слишком много записей в диапазоне')
        raw=[e.get_sobject_dict() for e in entries]
        return entries,revision({'task':task.get_sobject_dict(),'parent':parent.get_sobject_dict(),
                                 'config':config['revision'],'entries':raw,'start':str(start),'end':str(end),'login':login})

    def work_hour_operation(self,method,data):
        from pyasm.common import Environment
        from pyasm.search import Search
        from tactic.core.work_hours import WorkHoursElementAction
        opened,parent=self._task_parent(data)
        task=self._task_for_parent(parent,data.get('task'))
        element=data.get('field') or 'work_hours'
        config=self._hours_config(opened,element);start,end=self._hours_window(data,config)
        entries,current=self._hours_state(parent,task,start,end,config)
        writable=bool(self.allow_writes and config['editable'] and not task.is_retired() and
                      not parent.is_retired() and parent.get_project_code()==self._project() and
                      not parent.get_base_search_type().startswith(('sthpw/','config/')))
        if method=='GET':
            fields=('day','category','straight_time','login','start_time','end_time','description')
            return {'items':[{'key':e.get_search_key(),**{f:json_safe(e.get_value(f,no_exception=True)) for f in fields}} for e in entries],
                    'revision':current,'can_write':writable,'unit':config['unit'],'show_overtime':config['show_overtime'],
                    'login':Environment.get_user_name(),'start':str(start),'end':str(end),'notice':config['notice'],
                    'field':element,'days_per_page':config.get('days_per_page',7),
                    'action':'tactic.core.work_hours.WorkHoursElementAction'}
        if method!='PATCH':raise ApiError(405,'method','Недопустимая операция времени')
        if not writable:raise ApiError(403,'hours_read_only','Изменение рабочего времени этой формы недоступно')
        if not data.get('start') or not data.get('end'):raise ApiError(400,'hours_dates','Сохранение требует точного отображаемого диапазона start/end')
        changes=data.get('cells')
        if not isinstance(changes,list) or not 1<=len(changes)<=62:
            raise ApiError(400,'hours_cells','Передайте от 1 до 62 изменённых ячеек')
        validated={};identities=set()
        for cell in changes:
            if not isinstance(cell,dict) or set(cell)!={'day','category','value'}:
                raise ApiError(400,'hours_cell','Ячейка содержит только day, category, value')
            try:day=date.fromisoformat(cell['day'])
            except (ValueError,TypeError) as exc:raise ApiError(400,'hours_day','Некорректная дата') from exc
            category=cell['category']
            if day<start or day>end or category not in ('regular','overtime') or (category=='overtime' and not config['show_overtime']):
                raise ApiError(400,'hours_cell','Ячейка вне разрешённого диапазона или категории')
            identity=(str(day),category)
            if identity in identities:raise ApiError(400,'hours_duplicate','Одна ячейка передана дважды')
            identities.add(identity)
            value=cell['value']
            try:
                if isinstance(value,bool) or not isinstance(value,(str,int,float)):
                    raise ValueError('type')
                amount=Decimal(str(value).strip() or '0')
                if not amount.is_finite() or amount<0 or amount>(1440 if config['unit']=='minute' else 24) or amount.as_tuple().exponent < -6:
                    raise ValueError('range')
            except (InvalidOperation,ValueError) as exc:
                raise ApiError(400,'hours_value','Нужны неотрицательные часы/минуты в пределах суток, до 6 знаков после точки') from exc
            # Original action distinguishes string '0' to delete an existing row.
            amount_text=format(amount,'f') if amount else '0'
            key=('day_' if category=='regular' else 'otday_')+day.strftime('%Y_%m_%d')
            validated[key]=amount_text
        if data.get('confirm')!='SAVE_HOURS':
            raise ApiError(400,'confirmation','Подтвердите сохранение рабочего времени')
        def apply():
            fresh_task=self._task_for_parent(parent,task.get_search_key())
            fresh_config=self._hours_config(opened,element)
            rows,fresh=self._hours_state(parent,fresh_task,start,end,fresh_config)
            if fresh!=data.get('revision'):
                raise ApiError(409,'conflict','Задача, конфигурация или work_hour изменились')
            for day,category in identities:
                if category=='regular' and any(str(e.get_value('day'))[:10]==day and (e.get_value('category') or 'regular') not in ('regular','overtime') for e in rows):
                    raise ApiError(409,'hours_custom_category','В этот день есть нестандартная категория; редактируйте её в исходном представлении work_hour')
                matches=[e for e in rows if str(e.get_value('day'))[:10]==day and
                         (e.get_value('category') or 'regular')==category and
                         e.get_value('login')==Environment.get_user_name()]
                if len(matches)>1:
                    raise ApiError(409,'hours_duplicate','За этот день несколько записей. Сначала разберите их в отдельном исходном представлении; суммой они не перезаписываются.')
                if any(e.get_value('start_time',no_exception=True) or e.get_value('end_time',no_exception=True) for e in matches):
                    raise ApiError(409,'hours_time_mode','Запись с start/end временем нельзя заменить агрегированным straight_time')
            # The original action loads all parent's work_hour entries. Bound its
            # workload without replacing its task/login matching or write logic.
            all_entries=Search('sthpw/work_hour');all_entries.add_relationship_filter(parent)
            if all_entries.get_count()>5000:
                raise ApiError(413,'hours_parent_limit','У родителя более 5000 work_hour; нужен отдельный пакетный редактор')
            action=WorkHoursElementAction();action.set_sobject(fresh_task);action.set_name(element)
            action.set_data(json.dumps(validated,ensure_ascii=False))
            for key,value in fresh_config['options'].items():action.set_option(key,value)
            if not action.check():raise ApiError(400,'hours_validation','Штатная проверка work_hours отклонила данные')
            action.execute();action.post_execute();action.postprocess()
            return {'saved':True,'cells':len(validated),'command':'WorkHoursElementAction','login':Environment.get_user_name()}
        return self._write(apply)
