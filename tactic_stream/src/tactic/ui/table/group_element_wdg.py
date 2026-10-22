"""Parent groups use object identities, native relationships and existing forms."""
# Adapted from tactic/ui/table/group_element_wdg.py; see LICENSE.TACTIC.
from pyasm.command import DatabaseAction
from tactic.ui.common import BaseTableElementWdg


def read_parent_cells(search_keys):
    """Self-contained read for Stream and Handler's original-server fallback."""
    import hashlib
    import json
    from pyasm.biz import Project
    from pyasm.common import Environment
    from pyasm.search import Search, SearchKey, SearchType
    from pyasm.widget import ThumbWdg

    if not __import__('pyasm.common', fromlist=['Environment']).Environment.get_security().is_admin() and (not __import__('pyasm.common', fromlist=['Environment']).Environment.get_security().is_logged_in() or __import__('pyasm.common', fromlist=['Environment']).Environment.get_security().get_user_name() == 'admin' or not (__import__('pyasm.biz', fromlist=['Project']).Project.get_project_code() in ('admin', 'sthpw') or __import__('pyasm.common', fromlist=['Environment']).Environment.get_security().check_access('project', [{'code': '*'}, {'code': __import__('pyasm.biz', fromlist=['Project']).Project.get_project_code()}], 'allow', default='deny'))):
        raise PermissionError('Administration requires administrator access')
    if not isinstance(search_keys, list) or len(search_keys) > 500:
        raise ValueError('Invalid parent table scope')
    project = Project.get_project_code()

    def check_type(search_type):
        base = SearchKey.extract_base_search_type(search_type)
        if base in ('sthpw/message', 'sthpw/message_log', 'sthpw/ticket') or base.startswith(('prod/', 'flash/')):
            raise ValueError('This object is not available in parent groups')
        metadata = SearchType.get(base, no_exception=True)
        if metadata is None:
            return False
        if str(metadata.get_value('class_name') or '').startswith('pyasm.prod.'):
            raise ValueError('This object is not available in parent groups')
        if hasattr(metadata, 'get_record_read_options') and metadata.get_record_read_options().get('command'):
            raise ValueError('This object is not available in parent groups')
        return True

    for key in search_keys:
        if not isinstance(key, str) or SearchKey.extract_project(key) not in (None, '', 'sthpw', 'admin', project):
            raise ValueError('The configured table target belongs to another project')
        check_type(key)
    objects = Search.get_by_search_keys(search_keys, keep_order=True)
    if len(objects) != len(search_keys) or any(obj is None for obj in objects):
        raise LookupError('Object is no longer available')
    parents, cells = {}, {}
    for obj in objects:
        key = obj.get_search_key()
        own_project = obj.get_value('project_code', no_exception=True) or SearchKey.extract_project(key) or project
        parent_type = obj.get_value('search_type', no_exception=True)
        requested_key = ''
        if parent_type:
            registered = check_type(parent_type)
            # Old global records can store a bare type; their project belongs to the row.
            if not SearchKey.extract_project(parent_type):
                parent_type = SearchType.build_search_type(parent_type, own_project)
            code = obj.get_value('search_code', no_exception=True)
            identity = code or obj.get_value('search_id', no_exception=True)
            parent = None
            if identity not in (None, '', -1, '-1'):
                requested_key = SearchKey.build_search_key(parent_type, identity, column='code' if code else 'id')
                if registered:
                    parent = Search.get_by_search_key(requested_key)
        else:
            parent = obj.get_parent()
        cell = dict(text='', projectCode=own_project, targetSearchKey=key, sourceId=str(obj.get_id()),
            sourceRevision=hashlib.sha256(json.dumps(obj.get_data(), sort_keys=True, default=str).encode()).hexdigest(),
            groupKey='missing:' + requested_key if requested_key else 'no-parent', parent=None)
        if parent is not None:
            check_type(parent.get_search_type())
            parent_key = parent.get_search_key()
            record = {name: parent.get_value(name, no_exception=True) for name in
                ('id', 'code', 'name', 'title', 'description', 'project_code', 'pipeline_code', 'process', 'context')}
            record['__search_key__'] = parent_key
            cell.update(text=parent.get_code() or str(parent.get_id()), groupKey=parent_key,
                parent=dict(searchKey=parent_key, code=parent.get_code() or '',
                    name=parent.get_value('name', no_exception=True) or '',
                    description=parent.get_value('description', no_exception=True) or '',
                    retired=parent.is_retired(), record=record))
            parents[parent_key] = parent
        elif requested_key:
            cell['missingParentKey'] = requested_key
        cells[key] = cell
    records = list(parents.values())
    thumb = ThumbWdg(name='preview', latest_icon='true')
    thumb.set_sobjects(records)
    thumb.preprocess()
    previews = {}
    for index, parent in enumerate(records):
        thumb.set_current_index(index)
        if hasattr(thumb, 'get_cell_value'):
            preview = thumb.get_cell_value()
        else:
            from urllib.parse import urlsplit
            link = thumb.get_data(parent) or ''
            image = thumb.info.get('icon') or thumb.info.get('web') or link
            if urlsplit(image).path.lower().rsplit('.', 1)[-1] not in ('png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'avif'):
                image = ''
            preview = dict(image=image, text=link)
        previews[parent.get_search_key()] = preview
    for cell in cells.values():
        if cell['parent']:
            cell['parent']['preview'] = previews[cell['groupKey']]
    return cells


class ParentGroupTableElementWdg(BaseTableElementWdg):
    ARGS_KEYS = dict.fromkeys(('disable', 'label'), {})

    def is_editable(self):
        return False

    def is_groupable(self):
        return True

    def preprocess(self):
        self.values = read_parent_cells([obj.get_search_key() for obj in self.sobjects if not obj.is_insert()])

    def get_cell_value(self):
        obj = self.get_current_sobject()
        if obj is None or obj.is_insert():
            return dict(text='')
        if not hasattr(self, 'values'):
            self.preprocess()
        return dict(self.values[obj.get_search_key()], parentGrouping=self.get_option('disable') not in (True, 'true'))

    def get_text_value(self):
        return self.get_cell_value()['text']


class ParentGroupAction(DatabaseAction):
    def execute(self):
        value = self.get_value(self.get_input_name())
        if value:
            self.sobject.add_relationship(value)
