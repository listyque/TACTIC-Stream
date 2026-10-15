###########################################################
#
# Copyright (c) 2010, Southpaw Technology
#                     All Rights Reserved
#
# PROPRIETARY INFORMATION.  This software is proprietary to
# Southpaw Technology, and is not to be reproduced, transmitted,
# or disclosed in any way without written permission.
#
#
#


"""Native discussion data and commands, extracted without the HTML runtime."""
import datetime
import hashlib
import json
import os
from pathlib import Path

from pyasm.common import Environment, Common, SecurityException
from pyasm.common.errors import UnsupportedContract
from pyasm.biz import Note, Pipeline, Project, Schema, File, Snapshot, IconCreator
from pyasm.search import Search, SearchType, SearchKey
from pyasm.command import Command
from pyasm.widget.table_element_wdg import BaseTableElementWdg

basestring = str


def discussion_target(search_key):
    if not isinstance(search_key, str) or not search_key or len(search_key) > 2048:
        raise ValueError('Invalid discussion target')
    project = SearchType.breakup_search_type(search_key).get('project')
    if project and project != Project.get_project_code():
        raise ValueError('Discussion belongs to another project')
    target = Search.get_by_search_key(search_key)
    if not target:
        raise LookupError('Discussion target no longer exists')
    return target


def same_note_target(note, target):
    return note.get_value('search_type') == target.get_search_type() and (
        note.get_value('search_code') == target.get_code() if note.get_value('search_code')
        else note.get_value('search_id') == target.get_id())


def note_revision(note):
    return hashlib.sha256(json.dumps(note.get_data(), sort_keys=True, default=str).encode()).hexdigest()


def can_change_note(note):
    # Handler change_note: an author's own note has a one-hour edit window.
    login = Environment.get_user_name()
    author = note.get_login()
    if not login or not author:
        return False
    if login != author:
        return Environment.get_security().is_admin()
    try:
        created = datetime.datetime.fromisoformat(str(note.get_value('timestamp')).replace('Z', '+00:00'))
        if created.tzinfo is None:
            created = created.replace(tzinfo=datetime.timezone.utc)
        return 0 <= (datetime.datetime.now(datetime.timezone.utc) - created).total_seconds() < 3600
    except (TypeError, ValueError):
        return False


class DiscussionWdg(BaseTableElementWdg):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.init()
        self.ignore_context_ordering = kwargs.get('ignore_context_ordering') in (True, 'true')

    def set_sobjects(self, sobjects, search=None):
        super().set_sobjects(sobjects, search)
        self.notes_dict = None
        self.parents = []
        self.parent_processes = []

    def set_options(self, options):
        super().set_options(options)
        self.kwargs.update(options)
        self.init()
        self.ignore_context_ordering = self.kwargs.get('ignore_context_ordering') in (True, 'true')

    def set_option(self, key, value):
        self.set_options({key: value})

    def init(self):
        self.process = self.kwargs.get('process') or ''
        self.contexts = []
        self.use_parent = 'true' if self.kwargs.get('use_parent') in (True, 'true') else 'false'
        self._load_js = False
        self.notes_dict = None
        self.parent_dict = {}
        self.parents = []
        self.parent_processes = []
        self.append_processes = self.kwargs.get('append_process')
        self.custom_processes = self.kwargs.get('custom_processes')
        self.show_task_process = self.kwargs.get('show_task_process')
        self.allow_email = self.kwargs.get('allow_email')
        self.use_puw = self.kwargs.get('use_puw') or True

    def _get_parent(self, sobject):
        """caching is automatically done in SObject level"""
        parent = sobject.get_parent()
        return parent

    def preprocess_notes(self):
        """this call get_all_notes once by design to build the dict"""
        if not self.sobjects and not self.kwargs.get('search_key') and not self.kwargs.get('sobject'):
            self.notes_dict = {}
            return self.notes_dict
        insert_mode = False
        if len(self.sobjects) == 1 and self.sobjects[0].is_insert():
            insert_mode = True
            self.notes_dict = {}
        if self.notes_dict != None or insert_mode:
            return self.notes_dict
        self.parent = self.kwargs.get('sobject')
        has_process = self.parent.has_value('process') if self.parent else False
        if not self.parent:
            if self.sobjects:
                has_process = self.sobjects[0].has_value('process')
                if self.use_parent == 'true':
                    for sobject in self.sobjects:
                        process = ''
                        if has_process:
                            process = sobject.get_value('process')
                        context = sobject.get_value('context')
                        if context != process:
                            self.parent_processes.append(context)
                        else:
                            self.parent_processes.append(process)
                        parent = self._get_parent(sobject)
                        self.parents.append(parent)
                else:
                    self.parents = self.sobjects
            else:
                search_key = self.kwargs.get('search_key')
                assert search_key
                self.parent = Search.get_by_search_key(search_key)
                has_process = self.parent.has_value('process')
                self.sobjects = [self.parent]
                if self.use_parent == 'true':
                    process = ''
                    if has_process:
                        process = self.parent.get_value('process')
                    self.parent_processes.append(process)
                    parent = self.parent.get_parent()
                    self.parents.append(parent)
                else:
                    self.parents = [self.parent]
        else:
            self.parents = [self.parent]
            if not self.sobjects:
                self.set_sobjects([self.parent])
                self.parents = [self.parent]
        if has_process and self.use_parent == 'true':
            self.append_processes = ''
            self.custom_processes = ''
        if self.use_parent == 'true':
            pass
        else:
            self.process = self.kwargs.get('process')
            self.contexts = self.kwargs.get('context')
            if self.contexts and isinstance(self.contexts, basestring):
                self.contexts = self.contexts.split(',')
                self.contexts = [x.strip() for x in self.contexts if x.strip()]
        self.get_all_notes()

    def get_all_notes(self):
        """ this is called by get_notes() in the very first get_display() since we dont have preprocess for BaseRefreshWdg"""
        self.notes_dict = {}
        self.filtered_parents = [p for p in self.parents if p]
        if not self.filtered_parents:
            return self.notes_dict
        search = Search('sthpw/note')
        search.add_relationship_filters(self.filtered_parents, type='hierarchy')
        search.add_order_by('process')
        if not self.ignore_context_ordering:
            search.add_order_by('context')
        search.add_order_by('timestamp desc')
        if self.process:
            search.add_op('begin')
            search.add_filter('process', self.process)
            search.add_filter('process', '%s/%%' % self.process, op='like')
            search.add_op('or')
        if self.contexts:
            search.add_filters('context', self.contexts)
        notes = search.get_sobjects()
        has_process = self.sobjects[0].has_value('process')
        schema = Schema.get()
        for note in notes:
            if self.use_parent in ['true', True] and has_process:
                process = note.get_value('process')
            else:
                process = 'publish'
            if process.endswith('/review') or process.endswith('/error'):
                process = process.split('/')[0]
            search_type = note.get_value('search_type')
            attrs = schema.get_relationship_attrs('sthpw/note', search_type)
            attrs = schema.resolve_relationship_attrs(attrs, 'sthpw/note', search_type)
            from_col = attrs.get('from_col')
            to_col = attrs.get('to_col')
            search_code = note.get_value(from_col)
            if search_code:
                key = '%s|%s|%s' % (search_type, search_code, process)
            else:
                continue
            notes_list = self.notes_dict.get(key)
            if notes_list == None:
                notes_list = []
                self.notes_dict[key] = notes_list
            notes_list.append(note)
        self.attachments = {}
        return self.notes_dict

    def get_notes(self):
        self.preprocess_notes()
        self.parent = None
        if not self.sobjects:
            return []
        idx = self.get_current_index()
        self.sobject = self.sobjects[idx]
        self.parent = None
        if self.sobject.is_insert():
            return []
        self.parent = self.parents[idx]
        has_process = self.sobject.has_value('process')
        if not self.parent:
            key = ''
        else:
            search_type = self.parent.get_search_type()
            from pyasm.biz import Schema
            schema = Schema.get()
            attrs = schema.get_relationship_attrs('sthpw/note', search_type)
            attrs = schema.resolve_relationship_attrs(attrs, 'sthpw/note', search_type)
            from_col = attrs.get('from_col')
            to_col = attrs.get('to_col')
            search_code = self.parent.get_value(to_col)
            if self.use_parent == 'true':
                parent_process = self.parent_processes[idx]
                if has_process:
                    key = '%s|%s|%s' % (search_type, search_code, parent_process)
                else:
                    key = '%s|%s|publish' % (search_type, search_code)
            else:
                key = '%s|%s|publish' % (search_type, search_code)
        notes = self.notes_dict.get(key)
        if not notes:
            notes = []
        security = Environment.get_security()
        project_code = Project.get_project_code()
        allowed = []
        for note in notes:
            process = note.get_value('process')
            keys = [{'process': process}, {'process': '*'}, {'process': process, 'project': project_code}, {'process': '*', 'project': project_code}]
            if security.check_access('process', keys, 'allow', default='deny'):
                allowed.append(note)
        return allowed


class DiscussionElementWdg(BaseTableElementWdg):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.discussion = DiscussionWdg(**kwargs)

    def set_options(self, options):
        super().set_options(options)
        self.kwargs.update(options)
        self.discussion = DiscussionWdg(**self.options)
        self.discussion.set_sobjects(self.sobjects)

    def set_option(self, key, value):
        self.set_options({key: value})

    def set_sobjects(self, sobjects, search=None):
        super().set_sobjects(sobjects, search)
        self.discussion.set_sobjects(sobjects, search)

    def preprocess(self):
        self.discussion.preprocess_notes()

    @classmethod
    def get_args_keys(cls):
        return cls.ARGS_KEYS

    def is_sortable(self):
        return False

    def get_cell_value(self):
        self.discussion.set_current_index(self.get_current_index())
        notes = self.discussion.get_notes()
        counts = {}
        for note in notes:
            if not note.get_parent_id():
                process = note.get_process() or 'publish'
                counts[process] = counts.get(process, 0) + 1
        parent = self.discussion.parent
        return dict(text=str(sum(counts.values())), count=sum(counts.values()),
                    search_key=parent.get_search_key() if parent else '',
                    process=self.discussion.parent_processes[self.get_current_index()] if self.discussion.use_parent == 'true' and self.discussion.parent_processes else self.discussion.process,
                    contexts=self.discussion.contexts or [],
                    processes=self.process_counts(parent, counts))

    @staticmethod
    def process_counts(parent, counts):
        from pyasm.biz import Pipeline
        pipeline = Pipeline.get_by_code(parent.get_value('pipeline_code', no_exception=True)) if parent else None
        records = []
        for process, count in counts.items():
            node = pipeline.get_process(process) if pipeline else None
            records.append(dict(process=process, count=count, label=node.get_label() if node else process, accent=node.get_color() if node else ''))
        return records

    ARGS_KEYS = {'process': {'description': 'Explicitly set the process for notes that can be added.', 'category': 'Options', 'order': 0}, 'context': {'description': 'Explicitly set the context(s) for notes that can be added.  This can be a list separated by commas', 'category': 'Options', 'order': 1}, 'use_parent': {'description': 'Determine whether or not to enter notes for parent sObject', 'category': 'Options', 'type': 'SelectWdg', 'values': 'true|false', 'order': 2}, 'show_fullscreen_button': {'description': 'Determine whether or not to show the expand notes icon button', 'category': 'Options', 'type': 'SelectWdg', 'values': 'true|false', 'order': 3}, 'note_format': {'description': 'Determine if the notes are shown in compact or full mode. Full- shows thumbnail, login-info, email and notes. Compact- shows just the notes.', 'category': 'Options', 'type': 'SelectWdg', 'values': 'compact|full', 'order': 4}, 'show_note_status': {'description': 'Determine whether or not to show the note status in abbreviated form.', 'category': 'Options', 'type': 'SelectWdg', 'values': 'true|false', 'order': 5}, 'show_context_notes': {'description': '(DEPRECATED) Determine if the notes in the context are hidden', 'category': 'Options', 'type': 'SelectWdg', 'values': 'true|false', 'order': 6}, 'note_expandable': {'description': 'Determine whether or not a note is expandable. True- shows a short version of the note that can be expanded. False- shows the full note', 'category': 'Options', 'type': 'SelectWdg', 'values': 'true|false', 'order': 7}, 'append_process': {'description': 'Append a list of comma separated processes in addition of the ones defined in the pipeline', 'category': 'Options', 'type': 'TextWdg', 'order': 8}, 'allow_email': {'description': 'Allow email to be sent out directly in this widget', 'category': 'Options', 'type': 'SelectWdg', 'values': 'true|false', 'order': 9}, 'show_task_process': {'description': 'Determine if Add Note widget only shows the processes of existing tasks', 'category': 'Options', 'type': 'SelectWdg', 'values': 'true|false', 'order': 10}, 'mode': {'description': 'Determine if the table shows small icons or process names', 'values': 'default|icon', 'type': 'SelectWdg', 'category': 'Options', 'order': 10}, 'dialog_position': {'description': 'Determine where the popup dialog will appear for the nots', 'values': 'side|center', 'type': 'SelectWdg', 'category': 'Options', 'order': 10}}

    @classmethod
    def is_editable(cls):
        return False

    def get_width(self):
        mode = self.kwargs.get('mode')
        if mode == 'icon':
            return 75
        else:
            return 150

    def get_required_columns(self):
        """method to get the require columns for this"""
        return []

    def get_text_value(self):
        """for csv export"""
        from dateutil import parser
        comment_area = []
        idx = self.get_current_index()
        self.discussion.set_current_index(idx)
        self.discussion.preprocess_notes()
        notes = self.discussion.get_notes()
        if not notes:
            return ''
        last_context = None
        for i, note in enumerate(notes):
            context = note.get_value('context')
            if last_context == None or context != last_context:
                comment_area.append('[ %s ] ' % context)
            last_context = context
            child_notes = [child for child in notes if child.get_parent_id() == note.get_id()]
            date = note.get_value('timestamp')
            value = date if isinstance(date, datetime.datetime) else parser.parse(date)
            setting = '%Y-%m-%d %H:%M'
            date_value = value.strftime(setting)
            comment_area.append(note.get_value('login'))
            comment_area.append(date_value)
            comment_area.append(note.get_value('note'))
            comment_area.append('\n')
            if child_notes:
                for child_note in child_notes:
                    child_note_value = child_note.get_value('note')
                    comment_area.append('Reply: %s' % child_note_value)
                    comment_area.append('\n')
        return ' '.join(comment_area)


class DiscussionAddNoteCmd(Command):
    def check_security(self):
        from pyasm.security.security import _require_admin
        _require_admin()
        return True

    def validate_inputs(self):
        if self.kwargs.get('mail_cc') or self.kwargs.get('mail_bcc'):
            raise UnsupportedContract('Discussion email delivery is not migrated')
        target = discussion_target(self.kwargs.get('search_key'))
        value = self.kwargs.get('note')
        if not isinstance(value, str) or (not value.strip() and not self.kwargs.get('files')) or len(value.encode()) > 1024 * 1024:
            raise ValueError('A note cannot be empty or larger than 1 MiB')
        for name in ('context', 'process'):
            value = self.kwargs.get(name)
            if value is not None and (not isinstance(value, str) or len(value) > 256 or any(ord(c) < 32 for c in value)):
                raise ValueError('Invalid note process or context')
        if self.kwargs.get('ticket') not in (None, '', Environment.get_ticket()):
            raise SecurityException('Attachments belong to another ticket')
        files = self.kwargs.get('files') or []
        if not isinstance(files, list) or len(files) > 100 or any(not isinstance(path, str) or not path for path in files):
            raise ValueError('Choose at most 100 uploaded files')
        upload_dir = Path(Environment.get_upload_dir()).resolve()
        names = []
        for path in files:
            name = Common.get_filesystem_name(os.path.basename(path.replace('\\', '/')))
            file = upload_dir / name
            if not file.resolve().is_relative_to(upload_dir) or not file.is_file() or name in names:
                raise ValueError('An uploaded file is missing or duplicated')
            names.append(name)
        self.kwargs['files'] = names
        parent_id = self.kwargs.get('parent_id')
        self.reply = None
        if parent_id:
            reply = Search.get_by_id('sthpw/note', parent_id)
            if not reply or not same_note_target(reply, target):
                raise ValueError('Reply belongs to another object')
            self.kwargs['process'] = reply.get_process()
            self.kwargs['context'] = reply.get_value('context')
            self.reply = reply

    def get_title(self):
        return 'Added a note'

    def execute(self):
        self.validate_inputs()
        search_key = self.kwargs.get('search_key')
        sobject = Search.get_by_search_key(search_key)
        ticket = self.kwargs.get('ticket')
        note = self.kwargs.get('note')
        process = self.kwargs.get('process')
        context = self.kwargs.get('context')
        if not context:
            context = process
        elif '/' in context:
            parts = context.split('/')
            if parts:
                try:
                    subcontext = int(parts[1])
                    context = parts[0]
                except (ValueError, IndexError):
                    pass
        from pyasm.biz import Note
        note_sobj = Note.create(sobject, note, context=context, process=process, parent_id=self.kwargs.get('parent_id') or 0,
                               access=self.reply.get_value('access') if self.reply else None)
        process = note_sobj.get_process()
        from pyasm.checkin import FileCheckin
        files = self.kwargs.get('files') or []
        upload_dir = Environment.get_upload_dir(ticket)
        for i, path in enumerate(files):
            path = path.replace('\\', '/')
            basename = os.path.basename(path)
            basename = Common.get_filesystem_name(basename)
            new_path = '%s/%s' % (upload_dir, basename)
            context = 'publish'
            file_paths = [new_path]
            source_paths = [new_path]
            file_types = ['main']
            if os.path.isfile(new_path):
                icon_creator = IconCreator(new_path)
                icon_creator.execute()
                web_path = icon_creator.get_web_path()
                icon_path = icon_creator.get_icon_path()
                if web_path:
                    file_paths = [new_path, web_path, icon_path]
                    file_types = ['main', 'web', 'icon']
                    source_paths.append(web_path)
                    source_paths.append(icon_path)
            attachment_process = '%s/attachment' % process
            attachment_context = 'attachment/%s/%s' % (process, basename)
            checkin = FileCheckin(sobject, file_paths=file_paths, file_types=file_types, source_paths=source_paths, process=attachment_process, context=attachment_context, checkin_type='strict')
            checkin.execute()
            snapshot = checkin.get_snapshot()
            snapshot.connect(note_sobj, context='attachment')
        self.call_triggers(note_sobj)
        self.info = {'note': note_sobj.get_sobject_dict()}

    def call_triggers(self, note_sobj):
        prefix = 'note'
        sobject = note_sobj.get_parent()
        context = note_sobj.get('context')
        process = note_sobj.get('process')
        self.sobjects = [sobject]
        from pyasm.command import Trigger
        output = {}
        output['search_key'] = SearchKey.build_by_sobject(note_sobj)
        output['update_data'] = note_sobj.data.copy()
        output['note'] = note_sobj.get_sobject_dict()
        base_search_type = sobject.get_base_search_type()
        Trigger.call(self, prefix, output)
        Trigger.call(self, '%s|%s' % (prefix, base_search_type), output)
        Trigger.call(self, '%s|%s|%s' % (prefix, base_search_type, context), output)
        pipeline = None
        if process:
            Trigger.call(self, '%s|%s' % (prefix, base_search_type), output, process=process)
            pipeline_code = sobject.get_value('pipeline_code', no_exception=True)
            if pipeline_code:
                pipeline = Pipeline.get_by_code(pipeline_code)
            if pipeline and process:
                search = Search('config/process')
                search.add_filter('pipeline_code', pipeline_code)
                search.add_filter('process', process)
                process_sobj = search.get_sobject()
                if process_sobj:
                    process_code = process_sobj.get_code()
                    Trigger.call(self, '%s|%s' % (prefix, base_search_type), output, process=process_code)


class DiscussionReadCmd(Command):
    """Typed discussion records for renderers, using the original note selector."""
    def check_security(self):
        from pyasm.security.security import _require_admin
        _require_admin()
        return True

    def execute(self):
        target = discussion_target(self.kwargs.get('search_key'))
        widget = DiscussionWdg(process=self.kwargs.get('process'), context=self.kwargs.get('context'))
        widget.set_sobject(target)
        notes = widget.get_notes()
        from pyasm.biz import SObjectConnection
        from pyasm.widget import ThumbWdg
        from tactic_stream.server.table_cells import safe_link
        connections, snapshots = SObjectConnection.get_connected_sobjects(notes, direction='dst', context='attachment', filters=[('search_type', target.get_search_type())])
        snapshots = [snapshot for snapshot in snapshots if isinstance(snapshot, Snapshot)]
        direct_snapshots = Snapshot.get_by_sobjects(notes) if notes else []
        snapshots = list({snapshot.get_id(): snapshot for snapshot in [*snapshots, *direct_snapshots]}.values())
        file_objects = {file.get_code(): file for file in File.get_by_snapshots(snapshots)} if snapshots else {}
        snapshot_files = {}
        for snapshot in snapshots:
            files = []
            ThumbWdg.get_file_info(snapshot.get_snapshot_xml(), file_objects, snapshot.get_sobject(), snapshot, files=files)
            for file in files:
                file['href'] = safe_link(file['href'])
                file['snapshot_key'] = snapshot.get_search_key()
            snapshot_files[snapshot.get_id()] = files
        attachments = {}
        note_codes = {note.get_code(): note.get_id() for note in notes}
        for snapshot in direct_snapshots:
            note_id = note_codes.get(snapshot.get_value('search_code')) or snapshot.get_value('search_id')
            attachments.setdefault(note_id, []).extend(snapshot_files.get(snapshot.get_id(), []))
        for connection in connections:
            files = snapshot_files.get(connection.get_value('src_search_id'))
            if files and connection.get_value('src_search_type') == 'sthpw/snapshot':
                attachments.setdefault(connection.get_value('dst_search_id'), []).extend(files)
        records = []
        for note in notes:
            records.append(dict(id=note.get_id(), search_key=note.get_search_key(), body=note.get_value('note'),
                login=note.get_login(), timestamp=note.get_value('timestamp'), process=note.get_process(),
                context=note.get_value('context'), parent_id=note.get_parent_id() or 0,
                revision=note_revision(note), can_change=can_change_note(note),
                attachments=attachments.get(note.get_id(), []), metadata=note.get_metadata_dict()))
        logins = {record['login'] for record in records if record['login']}
        users = []
        if logins and self.kwargs.get('include_identities', True):
            from tactic_stream.server.security_groups import user_identities
            search = Search('sthpw/login'); search.set_show_retired(True); search.add_filters('login', list(logins))
            users = user_identities(search.get_sobjects())
        return dict(search_key=target.get_search_key(), notes=records, identities=users,current_user=Environment.get_user_name())


class DiscussionChangeNoteCmd(Command):
    """Handler change_note ownership/history semantics with optimistic revision."""
    def check_security(self):
        from pyasm.security.security import _require_admin
        _require_admin()
        return True

    def execute(self):
        target = discussion_target(self.kwargs.get('search_key'))
        action = self.kwargs.get('action')
        if action not in ('edit', 'delete'):
            raise ValueError('Unsupported note action')
        search = Search('sthpw/note')
        # ponytail: table lock; use row locks if concurrent note editing warrants it.
        sql = search.get_sql()
        sql.get_database_impl().lock_collection_table(sql, SearchType.get('sthpw/note').get_table())
        note = Search.get_by_id('sthpw/note', self.kwargs.get('id'))
        if not note or not same_note_target(note, target):
            raise LookupError('Note does not belong to this object')
        if not can_change_note(note):
            raise SecurityException('Note cannot be changed by this user')
        if self.kwargs.get('expected_revision') != note_revision(note):
            raise ValueError('Note changed. Reload before saving.')
        if action == 'delete':
            if note.get_child_notes():
                raise ValueError('Delete replies before deleting this note')
            note.delete()
            return dict(deleted=True)
        body = self.kwargs.get('body')
        if not isinstance(body, str) or not body.strip() or len(body.encode()) > 1024 * 1024:
            raise ValueError('A note cannot be empty or larger than 1 MiB')
        previous = note.get_value('note') or ''
        if body == previous:
            return dict(edited=False)
        metadata = note.get_value('metadata') or {}
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except (TypeError, ValueError):
                metadata = {}
        metadata = dict(metadata) if isinstance(metadata, dict) else {}
        history = list(metadata.get('editHistory') or [])
        history.append(dict(body=previous, editedBy=Environment.get_user_name(),
            editedAt=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')))
        metadata['editHistory'] = history
        note.set_value('note', body)
        note.set_value('metadata', metadata)
        note.commit()
        return dict(edited=True)
