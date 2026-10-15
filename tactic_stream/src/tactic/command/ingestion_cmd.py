###########################################################
#
# Copyright (c) 2005-2008, Southpaw Technology
#                     All Rights Reserved
#
# PROPRIETARY INFORMATION.  This software is proprietary to
# Southpaw Technology, and is not to be reproduced, transmitted,
# or disclosed in any way without written permission.
#
###########################################################

__all__ = ['IngestionCmd', 'IngestException', 'CheckinRuleSaveCmd', 'CheckinRuleCmd']

import os
import re

from pyasm.common import jsondumps, jsonloads
from pyasm.common.errors import UnsupportedContract
from pyasm.command import Command
from pyasm.search import Search, SearchType
from tactic.command.python_cmd import check_script_execution

class IngestException(Exception):
    pass

class CheckinRuleCmd(Command):
    def execute(self):
        rule = Search.get_by_code('config/ingest_rule', self.kwargs.get('rule_code'))
        if not rule:
            raise LookupError('Ingest rule does not exist')
        cmd = IngestionCmd(**dict(self.kwargs, rule=rule))
        Command.execute_cmd(cmd)
        self.info.update(cmd.info)

class CheckinRuleSaveCmd(Command):
    def execute(self):
        check_script_execution()
        rule_code = self.kwargs.get('rule_code')
        if rule_code:
            rule = Search.get_by_code('config/ingest_rule', rule_code)
            if not rule:
                raise LookupError('Ingest rule does not exist')
        else:
            rule = SearchType.create('config/ingest_rule')
        for column in ('base_dir', 'rule', 'title'):
            rule.set_value(column, self.kwargs.get(column))
        rule.set_value('data', jsondumps(self.kwargs))
        rule.commit()

class IngestionCmd(Command):
    ARGS_KEYS = {}

    def init(self):
        self.sobject_tags = {}
        self.snapshot_tags = {}
        self.paths_not_matched = []
        self.paths_matched = []
        self.paths_invalid = []
        self.paths_irregular = []
        self.tags = {}
        self.data = {}

    def execute(self):
        # Ingest reads server paths and may execute stored Python scripts.
        check_script_execution()
        rule = self.kwargs.get('rule')
        if rule and not isinstance(rule, str):
            data = rule.get_json_value('data') or {}
            data['pattern'] = data.get('rule')
            data.update(self.kwargs)
            self.kwargs = data
            if not self.kwargs.get('session_code') and rule.get_value('spt_ingest_session_code'):
                self.kwargs['session_code'] = rule.get_value('spt_ingest_session_code')
        scan_type = self.kwargs.get('scan_type')
        checkin_type = self.kwargs.get('action')
        if scan_type not in ('rule', 'list'):
            raise UnsupportedContract('Ingest scan type is not migrated: %s' % scan_type)
        if checkin_type not in ('file', 'directory'):
            raise ValueError('Ingest action must be file or directory')
        if self.kwargs.get('mode') not in ('scan', 'checkin'):
            raise ValueError('Ingest mode must be scan or checkin')
        if self.kwargs.get('action_type') not in (None, '', 'checkin', 'ignore'):
            raise ValueError('Ingest action_type must be checkin or ignore')
        base_dir = self.kwargs.get('base_dir') or ''
        pattern = self.kwargs.get('pattern') or base_dir
        session_base_dir = self.kwargs.get('session_base_dir')
        session_code = self.kwargs.get('session_code')
        if session_code:
            session = Search.get_by_code('config/ingest_session', session_code)
            if not session:
                raise LookupError('Ingest session does not exist')
            session_base_dir = session.get_value('base_dir')
        if not session_base_dir:
            raise ValueError('No session found')
        # Patterns use forward slashes on both platforms, as in TACTIC paths.
        base_dir = session_base_dir.rstrip('/\\') + '/' + base_dir.lstrip('/\\')
        pattern = session_base_dir.rstrip('/\\').replace('\\', '/') + '/' + pattern.lstrip('/\\').replace('\\', '/')
        if scan_type == 'list':
            self.kwargs['files'] = [path.strip() for path in self.kwargs.get('file_list', '').splitlines() if path.strip()]
            if not self.kwargs['files']:
                raise ValueError('Ingest file list is empty')
        ignore = self.kwargs.get('ignore') or []
        filter = self.kwargs.get('filter') or []
        if isinstance(ignore, str):
            ignore = [value.strip() for value in ignore.split(',') if value.strip()]
        if isinstance(filter, str):
            filter = [value.strip() for value in filter.split(',') if value.strip()]
        self.apply_pattern(base_dir, pattern, checkin_type, ignore=ignore, filter=filter)

    def apply_pattern(self, base_dir, pattern, checkin_type, depth=1, ignore=[], filter=[]):
        check_script_execution()
        self.init()
        base_dir = os.path.normpath(base_dir).replace('\\', '/')
        files = self.kwargs.get('files')
        if files is not None:
            paths = files
        else:
            paths = []
            if checkin_type == 'directory':
                paths.append(base_dir + ('/' if pattern.endswith('/') else ''))
            for root, dirs, names in os.walk(base_dir):
                if checkin_type == 'directory':
                    for name in dirs:
                        path = '%s/%s/' % (root, name)
                        if 0 <= len(path.split('/')) - len(pattern.split('/')) <= depth:
                            # Once a directory is published, its children belong to that tree.
                            paths.append(path)
                else:
                    paths.extend('%s/%s' % (root, name) for name in names)
                if len(paths) > 100000:
                    raise ValueError('Ingest scan exceeds 100000 paths; narrow the base directory')
        for path in paths:
            path = os.fspath(path).replace('\\', '/')
            if checkin_type == 'directory' and pattern.endswith('/'):
                path = path.rstrip('/') + '/'
            name = os.path.basename(path.rstrip('/'))
            self.check_irregular(path)
            excluded = any(name.endswith(value) for value in ignore)
            included = not filter or any(
                re.match(value[1:-1], name) if value.startswith('/') and value.endswith('/') else value in name
                for value in filter)
            self.sobject_tags = {}
            self.snapshot_tags = {}
            if excluded or not included:
                self.paths_not_matched.append(path)
                continue
            if checkin_type == 'directory' and any(path != matched and path.startswith(matched.rstrip('/') + '/') for matched in self.paths_matched):
                continue
            self.process_path(path, pattern, checkin_type)
            self.tags[path] = {'sobject': self.sobject_tags, 'snapshot': self.snapshot_tags}
        for key in ('paths_matched', 'paths_not_matched', 'paths_invalid', 'paths_irregular', 'tags', 'data'):
            self.info[key] = getattr(self, key)
        # Local check-in attaches its internal Snapshot to the active command.
        # Ingest returns its path report, not a recursive Python object graph.
        self.info.pop('snapshot', None)
        # The report is request-local; never read/write the source's shared /tmp/scan.

    def check_irregular(self, path):
        if '!' in path:
            self.paths_irregular.append(path)
            return True

    def process_pattern(self, path, pattern):
        parts = re.split(r'(\{[^{}]+\})', pattern)
        expressions = []
        regex = []
        for part in parts:
            if part.startswith('{') and part.endswith('}'):
                expr = part[1:-1]
                if not re.fullmatch(r'[A-Za-z_][\w]*(?:\.[A-Za-z_][\w]*)?', expr):
                    raise ValueError('Invalid ingest expression: %s' % expr)
                expressions.append(expr)
                regex.append('(.+?)')
            else:
                if '{' in part or '}' in part:
                    raise ValueError('Unbalanced ingest pattern')
                regex.append(re.escape(part))
        match = re.fullmatch(''.join(regex), path)
        if not match:
            self.paths_not_matched.append(path)
            return False
        for expr, value in zip(expressions, match.groups()):
            self.handle_expr(expr, value)
        self.paths_matched.append(path)
        return True

    def scan_path(self, path, pattern):
        '''simple scan of the file system'''
        is_matched = self.process_pattern(path, pattern)
        if not is_matched:
            return

        (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat(path)

        status = 'scan'

        self.data[path] = {
            'size': size,
            'ctime': ctime,
            'status': 'scan'
        }

    def process_path(self, path, pattern, checkin_type):
        check_script_execution()
        is_matched = self.process_pattern(path, pattern)
        if not is_matched:
            return

        status = self.kwargs.get("mode")
        action_type = self.kwargs.get("action_type")
        if action_type == 'ignore':
            (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat(path)
            self.data[path] = {
                'size': size,
                'ctime': ctime,
                'status': status
            }
            return

        search_key = self.kwargs.get("search_key")
        search_type = self.kwargs.get("search_type")

        # create an sobject to store data
        if search_key:
            self.sobject = Search.get_by_search_key(search_key)

        elif search_type:
            code = self.sobject_tags.get("code")
            id = self.sobject_tags.get("id")
            if code:
                self.sobject = Search.get_by_code(search_type, code)
            elif id:
                self.sobject = Search.get_by_id(search_type, id)
            else:
                self.sobject = None

            if not self.sobject:
                # create a new sobject
                self.sobject = SearchType.create(search_type)

        else:
            raise ValueError('Ingest requires search_key or search_type')
        if not self.sobject:
            raise LookupError('Ingest object does not exist')
        self.parent = self.sobject.get_parent()
        search_type = self.sobject.get_search_type()

        # create a snapshot to store snapshot data
        snapshot = SearchType.create("sthpw/snapshot")

        # extras
        keywords = []

        # create the new sobject
        for name, value in self.sobject_tags.items():
            if SearchType.column_exists(search_type, name):
                self.sobject.set_value(name, value)
            keywords.append(value)

        extra_names = self.kwargs.get("extra_name") or []
        extra_values = self.kwargs.get("extra_value") or []
        if isinstance(extra_names, str) or isinstance(extra_values, str) or len(extra_names) != len(extra_values):
            raise ValueError('Ingest extra_name/extra_value must be equal-length lists')
        for name, value in zip(extra_names, extra_values):
            if not name:
                continue

            if SearchType.column_exists(search_type, name):
                self.sobject.set_value(name, value)
            keywords.append(value)

        extra_keywords = self.kwargs.get("keywords")
        if extra_keywords:
            extra_keywords = extra_keywords.split(",")
            for k in extra_keywords:
                keywords.append(k)

        if SearchType.column_exists(search_type, 'keywords'):
            keywords = " ".join(str(value) for value in keywords)
            self.sobject.set_value("keywords", keywords)

        self.validation_script = self.kwargs.get("validation_script")
        if self.validation_script:
            from tactic.command import PythonCmd
            input = {
                "path": path,
                "sobject": self.sobject,
                "parent": self.parent,
                "snapshot": snapshot
            }
            validation_cmd = PythonCmd(script_path=self.validation_script, input=input, IngestException=IngestException)
            try:
                result = validation_cmd.execute()
            except IngestException:
                result = None

            if not result:
                self.paths_invalid.append(path)
                return

        # handle metadata for the files
        (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat(path)
        metadata = snapshot.get_value("metadata")
        if not metadata:
            metadata = {}
        else:
            metadata = jsonloads(metadata)

        metadata['size'] = size
        metadata['ctime'] = ctime
        metadata['mtime'] = mtime

        # add metadata if there is any
        self.sobject_tags['metadata'] = metadata

        mode = self.kwargs.get("mode")
        self.data[path] = {
            'size': size,
            'ctime': ctime,
            'status': mode
        }

        # skip if no action takes place
        if mode == 'scan':
            return

        self.process_script = self.kwargs.get("process_script")
        if self.process_script:
            from tactic.command import PythonCmd
            input = {
                "path": path,
                "sobject": self.sobject,
                "parent": self.parent,
                "snapshot": snapshot
            }
            process_cmd = PythonCmd(script_path=self.process_script, input=input)
            result = process_cmd.execute()

            if not result:
                return

        #
        #

        # first commit the data that has changed to the sobject
        self.sobject.commit()

        # check in the files to the new sobject
        context = self.snapshot_tags.get("context")
        if not context:
            context = "publish"

        from tactic_client_lib import TacticServerStub
        server = TacticServerStub.get(protocol='local')
        if checkin_type == "directory":
            # The client directory helper deletes the entire ticket handoff.
            # Server-side ingest already has the tree: use the same core check-in
            # directly, preserving unrelated uploads and transactional file undo.
            from pyasm.checkin import FileCheckin
            Command.execute_cmd(FileCheckin(self.sobject, [path.rstrip('/')], context=context,
                snapshot_type='directory', description='No description', mode='copy', checkin_type='strict'))
 

        elif checkin_type == "file":

            # use the client api
            snapshot = server.simple_checkin( self.sobject.get_search_key(), context, path, mode='copy', metadata=metadata)

    def handle_expr(self, expr, value):
        parts = expr.split(".")

        if len(parts) == 1:
            self.sobject_tags[expr] = value
            return

        key = parts[0]
        attr = parts[1]

        if key == 'sobject':
            self.sobject_tags[attr] = value

        elif key == 'snapshot':
            self.snapshot_tags[attr] = value
            
        elif key == 'parent':
            pass

        elif key == 'project':
            # ignore the project
            pass


