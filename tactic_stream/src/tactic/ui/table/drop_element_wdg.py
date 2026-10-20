# Copyright (c) 2005-2008 Southpaw Technology. See LICENSE.TACTIC.
"""Configured instance links share the existing staged link editor, without Sudo."""
import hashlib
import json
import re

from pyasm.command import Command
from pyasm.search import Search, SearchKey, SearchType
from pyasm.widget import WidgetConfigView
from tactic.ui.common import BaseTableElementWdg


def drop_link_data(parent, options):
    instance_type, accepted = options.get('instance_type'), options.get('accepted_drop_type')
    if not instance_type or not accepted:
        return dict(text='', links=[], available=False, diagnostic='Configure an instance type and accepted Search Type')
    SearchType.get(instance_type)
    SearchType.get(accepted)
    schema = parent.get_schema()
    path = options.get('path') or None
    for target in (parent.get_base_search_type(), accepted):
        if not schema.get_relationship_attrs(instance_type, target, path=path):
            raise ValueError('The configured instance relationship is unavailable')
    instances = parent.get_related_sobjects(instance_type, path=path)
    instances.sort(key=lambda record: str(record.get_display_value()))
    links = []
    for instance in instances:
        targets = instance.get_related_sobjects(accepted)
        if len(targets) != 1:
            raise ValueError('An instance must refer to exactly one accepted object')
        target = targets[0]
        label = Search.eval(options['display_expr'], sobjects=instance, single=True) if options.get('display_expr') else instance.get_display_value()
        links.append(dict(instanceKey=instance.get_search_key(), searchKey=target.get_search_key(),
                          label=str(label or ''), record=dict(__search_key__=target.get_search_key(),
                          id=target.get_id(), code=target.get_code(), name=str(target.get_display_value()))))
    revision = hashlib.sha256(json.dumps([options, sorted((row.get_data() for row in instances),
        key=lambda row: str(row.get('id') or row.get('code')))], sort_keys=True, default=str).encode()).hexdigest()
    background = Search.eval(options.get('css_background-color'), sobjects=parent) if options.get('css_background-color') else ''
    if background and not re.fullmatch(r'#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?(?:[0-9a-fA-F]{2})?', str(background)):
        raise ValueError('Drop background must be a hexadecimal color')
    return dict(text='', links=links, available=True, targetSearchKey=parent.get_search_key(),
        acceptedType=accepted, instanceType=instance_type, path=path or '', expectedRevision=revision, backgroundColor=background,
        relation=dict(relationship='instance', instance_type=instance_type, path=path or '', search_type=accepted))


class DropElementWdg(BaseTableElementWdg):
    ARGS_KEYS = dict.fromkeys(('accepted_drop_type', 'instance_type', 'path', 'display_expr', 'css_background-color', 'cbjs_drop_action'), {})

    def is_editable(self):
        return False

    def get_cell_value(self):
        if not self.get_current_sobject() or self.get_current_sobject().is_insert():
            return dict(text='', links=[], available=False)
        if self.get_option('cbjs_drop_action'):
            raise ValueError('Custom DOM drop callbacks require a Frame action before they can run in both clients')
        cell = drop_link_data(self.get_current_sobject(), self.options)
        return dict(cell, columnName=self.get_name())


def edit_drop_links(search_type, view, column, parent_key, target_keys=None, expected_revision=None, action='prepare'):
    """Self-contained procedure also executed against an original TACTIC server."""
    import hashlib
    import json
    import re
    from pyasm.common import Environment
    from pyasm.search import Search, SearchKey, SearchType
    from pyasm.widget import WidgetConfigView
    if not Environment.get_security().is_admin():
        raise PermissionError('Administration requires administrator access')
    if action not in ('prepare', 'save', 'check'):
        raise ValueError('Invalid link operation')
    from pyasm.biz import Project
    if SearchKey.extract_project(parent_key) not in (None, '', Project.get_project_code()):
        raise ValueError('The configured table target belongs to another project')
    if SearchKey.extract_base_search_type(parent_key) != SearchType.get(search_type).get_base_key():
        raise ValueError('The configured table target is unavailable')
    config = WidgetConfigView.get_by_search_type(search_type, view, use_cache=False)
    if column not in config.get_element_names() or config.get_display_handler(column) not in (
        'tactic.ui.table.DropElementWdg', 'tactic.ui.table.drop_element_wdg.DropElementWdg'):
        raise ValueError('The configured drop column changed. Reload before saving.')
    options = dict(config.get_display_options(column) or {})
    if options.get('cbjs_drop_action'):
        raise ValueError('Custom DOM drop callbacks require a Frame action before they can run in both clients')
    instance_type, accepted = options.get('instance_type'), options.get('accepted_drop_type')
    if not instance_type or not accepted:
        raise ValueError('Configure an instance type and accepted Search Type')
    if action == 'save':
        sql = Search(instance_type).get_sql()
        lock = getattr(sql.get_database_impl(), 'lock_collection_table', None)
        if lock:
            lock(sql, SearchType.get(instance_type).get_table())
        elif sql.get_database_type() == 'PostgreSQL':
            sql.do_update('LOCK TABLE "%s" IN EXCLUSIVE MODE' % SearchType.get(instance_type).get_table().replace('"','""'))
        else:
            raise ValueError('Instance revisions require a transactional database lock')
    parent = Search.get_by_search_key(parent_key)
    if parent is None:
        raise ValueError('The configured table target is unavailable')
    path = options.get('path') or None
    for target in (parent.get_base_search_type(), accepted):
        if not parent.get_schema().get_relationship_attrs(instance_type,target,path=path):
            raise ValueError('The configured instance relationship is unavailable')
    instances = parent.get_related_sobjects(instance_type, path=path)
    revision = hashlib.sha256(json.dumps([options, sorted((row.get_data() for row in instances),
        key=lambda row: str(row.get('id') or row.get('code')))], sort_keys=True, default=str).encode()).hexdigest()
    current = {}
    for instance in instances:
        targets = instance.get_related_sobjects(accepted)
        if len(targets) != 1:
            raise ValueError('An instance must refer to exactly one accepted object')
        current.setdefault(targets[0].get_search_key(), []).append(instance)
    if action == 'prepare':
        return dict(expected_revision=revision, target_keys=list(current))
    if not isinstance(target_keys,list) or len(target_keys)>500 or any(not isinstance(key,str) or not key for key in target_keys):
        raise ValueError('Choose at most 500 linked objects')
    wanted = {}
    for key in target_keys:
        if SearchKey.extract_base_search_type(key) != accepted:
            raise ValueError('Dropped objects belong to another Search Type')
        if SearchKey.extract_project(key) not in (None, '', Project.get_project_code()):
            raise ValueError('Dropped objects belong to another project')
        target = Search.get_by_search_key(key)
        if target is None:
            raise ValueError('A linked object is no longer available')
        wanted[target.get_search_key()] = target
    if action == 'check':
        return dict(state='saved' if set(wanted)==set(current) else 'unchanged' if revision==expected_revision else 'conflict')
    if not expected_revision or revision != expected_revision:
        raise ValueError('Instance links or their definition changed. Reload before saving.')
    # All targets and the entire relation revision are checked before deleting an instance.
    for key, rows in current.items():
        if key not in wanted:
            for instance in rows:
                instance.delete()
    for key, target in wanted.items():
        if key not in current:
            instance = SearchType.create(instance_type)
            instance.add_related_connection(parent,target,src_path=path)
            instance.commit()
    return dict(state='saved', search_key=parent.get_search_key())


class DropElementEditCmd(Command):
    def execute(self):
        self.info = edit_drop_links(**self.kwargs)
        return self.info
