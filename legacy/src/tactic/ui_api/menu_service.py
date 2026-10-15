"""Read-only context menu descriptor resolved from authorized widget target."""
from .contracts import ApiError
from tactic.core.context_menus import menu_items

SOURCES = {
 'row':'tactic/ui/panel/base_table_layout_wdg.py:get_data_row_smart_context_menu_details',
 'column':'tactic/ui/panel/base_table_layout_wdg.py:get_smart_header_context_menu_data',
 'sidebar':'tactic/ui/panel/panel_wdg.py:add_link_context_menu',
 'tab':'tactic/ui/container/tab_wdg.py:add_context_menu',
 'form-field':'tactic/ui/panel/edit_wdg.py:get_header_context_menu',
 'widget':'native widget container',
}

class MenuService:
    def _menu_admin(self):
        from pyasm.common import Environment
        return bool(Environment.get_security().check_access('builtin','view_site_admin','allow'))

    def context_menu(self, data):
        scope = data.get('scope')
        if scope not in SOURCES:
            raise ApiError(400,'menu_scope','Неизвестная область меню')
        opened = self.open_target(data.get('target')); opts = opened.get('options', {})
        flags = opened.get('spec',{}).get('table_options',{})
        if scope in ('row','column') and (opened['kind'] != 'table' or flags.get('show_context_menu') is False):
            return {'items':[], 'source':SOURCES[scope], 'disabled':True}
        context = {'admin':self._menu_admin()}
        if scope == 'row':
            stype=opened['search_type']; obj=self._object(stype,data.get('key'))
            context.update(can_edit=opened['spec']['capabilities'].get('update') and not opts.get('edit_class'),
                can_upload=self.allow_uploads and self.allow_writes,
                can_retire=self._can_retire(stype), can_delete=self._can_retire(stype), retired=obj.is_retired(),
                subscribable=not stype.startswith(('sthpw/','config/')) or stype in ('sthpw/task','sthpw/note','sthpw/snapshot'),
                pending_cell=data.get('pending_cell') in (True,'true'))
        elif scope in ('column','form-field'):
            spec = opened.get('spec')
            if scope=='form-field':
                if opened['kind'] not in ('table','form'): raise ApiError(400,'menu_scope','Нет формы')
                if opened['kind']=='form':self.check_form_binding(opened,data,'GET','/form')
                spec=self.form(opened['search_type'],data.get('key'))['spec']
            field=next((f for f in (spec or {}).get('fields',[]) if f['name']==data.get('field')),None)
            if not field:raise ApiError(403,'menu_field','Поле отсутствует в разрешённом представлении')
            context.update(sortable=field.get('storage') and field.get('sortable',True),storage=field.get('storage'),
                           column_manager=flags.get('show_column_manager',True) and not opts.get('config_xml') and not opts.get('config_code'),
                           editable=not field.get('read_only'),nullable=field.get('nullable'))
        elif scope=='sidebar':
            # A derived leaf is not an original sidebar link.
            _,targets=self._tree()
            if data.get('target') not in targets:raise ApiError(403,'menu_sidebar','Нет такой sidebar-ссылки')
        elif scope=='tab':
            if opts.get('show_context_menu') in (False,'false'):return {'items':[],'disabled':True}
            context['removable']=opened.get('removable',True)
        return {'items':menu_items(scope,context),'source':SOURCES[scope], 'scope':scope,
                'target':opened['id'],'search_type':opened.get('search_type'),'view':opened.get('view')}
