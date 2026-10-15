"""Native note lifecycle through the same commands exposed over XML-RPC/JSON."""
from unittest.mock import patch
from pyasm.biz import Note
from pyasm.search import Search
from tactic.ui.widget.discussion_wdg import DiscussionElementWdg, DiscussionWdg, DiscussionAddNoteCmd


def exercise(api, auth, key, other_key):
    def command(name, **values):
        return api.dispatch('execute_cmd', (auth, 'tactic.ui.widget.discussion_wdg.'+name,
                            dict(search_key=key, **values)))['info']
    def read():
        return command('DiscussionReadCmd')['notes']
    assert read() == []
    from xmlrpc.client import Binary
    from scripts.table_cells_contract import PNG
    api.dispatch('upload_file', (auth, 'attachment-only.png', Binary(PNG)))
    only_file = command('DiscussionAddNoteCmd', note='', process='publish', files=['attachment-only.png'])['note']
    only_record = next(entry for entry in read() if entry['id'] == only_file['id'])
    assert only_record['body'] == '' and len(only_record['attachments']) == 3
    assert len({file['snapshot_key'] for file in only_record['attachments']}) == 1
    command('DiscussionChangeNoteCmd', action='delete', id=only_file['id'], expected_revision=only_record['revision'])
    api.dispatch('upload_file', (auth, 'note.png', Binary(PNG)))
    root = command('DiscussionAddNoteCmd', note='Native discussion', process='publish', files=['note.png'])['note']
    reply = command('DiscussionAddNoteCmd', note='Native reply', parent_id=root['id'], process='wrong')['note']
    assert reply['process'] == 'publish' and reply['parent_id'] == root['id']
    api.dispatch('update', (auth, root['__search_key__'], dict(access='private')))
    private_reply = command('DiscussionAddNoteCmd', note='Private reply', parent_id=root['id'])['note']
    assert private_reply['access'] == 'private', 'A private thread must not produce public replies'
    private_record = next(entry for entry in read() if entry['id'] == private_reply['id'])
    command('DiscussionChangeNoteCmd', action='delete', id=private_reply['id'], expected_revision=private_record['revision'])
    api.dispatch('update', (auth, root['__search_key__'], dict(access='public')))
    entries = read()
    assert len(entries) == 2 and all(entry['can_change'] for entry in entries)
    parent = Search.get_by_search_key(key)
    task = api.dispatch('insert', (auth, 'sthpw/task', dict(search_type=parent.get_search_type(),
        search_code=parent.get_code(), search_id=parent.get_id(), project_code=parent.get_project_code(), process='publish', context='publish')))
    if isinstance(task, str):
        import ast
        task = ast.literal_eval(task)
    task_widget = DiscussionElementWdg(use_parent=True)
    task_widget.set_sobject(Search.get_by_id('sthpw/task', task['id']))
    assert task_widget.get_cell_value()['count'] == 1 and task_widget.get_cell_value()['search_key'] == key
    attachments = next(entry for entry in entries if entry['id'] == root['id'])['attachments']
    assert len(attachments) == 3 and {file['type'] for file in attachments} == {'main', 'web', 'icon'}, attachments
    assert all(file['href'].startswith('/') and '\\' not in file['path'] for file in attachments)
    widget = DiscussionElementWdg(allow_email='false')
    assert DiscussionElementWdg.is_editable() is False
    objects = [Search.get_by_search_key(key), Search.get_by_search_key(other_key)]
    assert len(DiscussionWdg(sobject=objects[0]).get_notes()) == 2
    widget.set_sobjects(objects)
    with patch.object(DiscussionWdg, 'get_all_notes', wraps=widget.discussion.get_all_notes) as fetch:
        widget.preprocess(); assert widget.get_cell_value()['count'] == 1
        assert 'Native discussion' in widget.get_text_value() and 'Reply: Native reply' in widget.get_text_value()
        widget.set_current_index(1); assert widget.get_cell_value()['count'] == 0
        assert fetch.call_count == 1
    # Compare unchanged source selector bodies without importing its HTML/JS runtime.
    from pathlib import Path
    source_path = Path(__file__).resolve().parents[3] / 'legacy/src/tactic/ui/widget/discussion_wdg.py'
    if source_path.is_file():
        import ast
        from pyasm.biz import Project, Schema
        from pyasm.common import Environment
        from pyasm.widget.table_element_wdg import BaseTableElementWdg
        source = ast.parse(source_path.read_text(encoding='utf-8-sig'))
        original = next(node for node in source.body if isinstance(node, ast.ClassDef) and node.name == 'DiscussionWdg')
        original.bases = [ast.Name(id='BaseTableElementWdg', ctx=ast.Load())]
        original.body = [node for node in original.body if getattr(node, 'name', '') in ('init', '_get_parent', 'preprocess_notes', 'get_all_notes', 'get_notes')]
        namespace = dict(BaseTableElementWdg=BaseTableElementWdg, Project=Project, Schema=Schema, Environment=Environment, Search=Search, basestring=str)
        exec(compile(ast.fix_missing_locations(ast.Module(body=[original], type_ignores=[])), str(source_path), 'exec'), namespace)
        source_widget = namespace['DiscussionWdg'](); source_widget.init(); source_widget.ignore_context_ordering = False
        source_widget.set_sobjects(objects)
        current = DiscussionWdg(); current.set_sobjects(objects)
        for index in range(len(objects)):
            source_widget.set_current_index(index); current.set_current_index(index)
            assert [note.get_id() for note in source_widget.get_notes()] == [note.get_id() for note in current.get_notes()]
    root_record = next(entry for entry in entries if entry['id'] == root['id'])
    command('DiscussionChangeNoteCmd', action='edit', id=root['id'], body='Changed discussion', expected_revision=root_record['revision'])
    updated = next(entry for entry in read() if entry['id'] == root['id'])
    assert updated['body'] == 'Changed discussion' and updated['metadata']['editHistory'][0]['body'] == 'Native discussion'
    for values in (
        dict(action='edit', id=root['id'], body='Stale write', expected_revision=root_record['revision']),
        dict(action='delete', id=root['id'], expected_revision=updated['revision']),
        dict(action='edit', id=root['id'], body='', expected_revision=updated['revision']),
    ):
        try:
            command('DiscussionChangeNoteCmd', **values)
        except (ValueError, LookupError):
            pass
        else:
            raise AssertionError('Invalid note mutation accepted')
    before = len(read())
    api.dispatch('upload_file', (auth, 'rollback note.png', Binary(PNG)))
    counts = [Search(kind).get_count() for kind in ('sthpw/snapshot', 'sthpw/file', 'sthpw/connection')]
    with patch.object(DiscussionAddNoteCmd, 'call_triggers', side_effect=ValueError('Forced note rollback')):
        try:
            command('DiscussionAddNoteCmd', note='Must roll back', files=['rollback note.png'])
        except ValueError:
            pass
        else:
            raise AssertionError('Note failure not propagated')
    assert len(read()) == before
    assert counts == [Search(kind).get_count() for kind in ('sthpw/snapshot', 'sthpw/file', 'sthpw/connection')], 'Attachment records must roll back with the note'
    for values in (dict(note='Mail', mail_cc='someone@example.com'), dict(note='Files', files=['missing.txt']), dict(note='Ticket', ticket='foreign-ticket')):
        try:
            command('DiscussionAddNoteCmd', **values)
        except Exception:
            pass
        else:
            raise AssertionError('Unsupported or foreign note effects accepted')
    assert len(read()) == before
    from tactic.ui.widget.discussion_wdg import can_change_note
    obj = Search.get_by_id('sthpw/note', root['id'])
    import datetime
    original_value = obj.get_value
    with patch.object(obj, 'get_value', side_effect=lambda name, **kwargs: datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=2) if name == 'timestamp' else original_value(name, **kwargs)):
        assert not can_change_note(obj), 'Author edit window must expire'
    reply_record = next(entry for entry in read() if entry['id'] == reply['id'])
    command('DiscussionChangeNoteCmd', action='delete', id=reply['id'], expected_revision=reply_record['revision'])
    command('DiscussionChangeNoteCmd', action='delete', id=root['id'], expected_revision=updated['revision'])
    assert read() == []
    # Keep one fixture entry for table/browser scenarios.
    command('DiscussionAddNoteCmd', note='Native discussion', process='publish', files=[])
