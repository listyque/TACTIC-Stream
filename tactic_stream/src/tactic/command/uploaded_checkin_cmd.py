"""Browser multi-file check-in through the same FileCheckin as Handler."""
from pathlib import Path

from pyasm.command import Command
from pyasm.common import Environment
from pyasm.search import FileUndo, SearchKey
from pyasm.checkin import FileCheckin
from pyasm.biz import IconCreator
from tactic_stream.server.api import upload_file_name, check_ticket_paths
from tactic_stream.server.result_items import objects


class UploadedCheckinCmd(Command):
    def execute(self):
        FileUndo._check_access()
        key = self.kwargs.get('search_key')
        if not isinstance(key, str) or not key:
            raise ValueError('Choose an object for check-in')
        owner = next(iter(objects(SearchKey.extract_base_search_type(key), [key]).values()))
        names = self.kwargs.get('files')
        if not isinstance(names, list) or not 1 <= len(names) <= 100 or any(not isinstance(name, str) or upload_file_name(name) != name for name in names):
            raise ValueError('Choose up to 100 uploaded files')
        if len(set(names)) != len(names):
            raise ValueError('Choose different file names for a group check-in')
        context = self.kwargs.get('context')
        process = self.kwargs.get('process')
        description = self.kwargs.get('description', '')
        if not isinstance(context, str) or not context.strip() or len(context) > 256 or not isinstance(process, str) or not process or len(process) > 256 or not isinstance(description, str):
            raise ValueError('Choose a process and context for check-in')
        for flag in ('is_revision', 'keep_file_name'):
            if type(self.kwargs.get(flag, False)) is not bool:
                raise ValueError('Invalid check-in option')
        version = self.kwargs.get('version')
        if version is not None and (type(version) is not int or version < 0):
            raise ValueError('Choose a versioned snapshot for a revision')
        alias = self.kwargs.get('repository_alias')
        if alias is not None and (not isinstance(alias, str) or alias == 'plugins' or alias not in Environment.get_asset_dirs()):
            raise ValueError('Choose a configured repository alias')
        if self.kwargs.get('is_revision', False):
            from pyasm.biz import Snapshot
            previous = Snapshot.get_snapshot(owner.get_search_type(), owner.get_id(), context=context, version=version)
            if previous:
                aliases = {file.get_value('base_dir_alias') or 'default' for file in previous.get_all_file_objects()}
                if len(aliases) == 1:
                    saved_alias = next(iter(aliases))
                    if alias is not None and alias != saved_alias:
                        raise ValueError('A revision must use its existing repository')
                    alias = saved_alias
        directory = Environment.get_upload_dir()
        paths = [(Path(directory) / name).as_posix() for name in names]
        check_ticket_paths(paths, directory)
        if any(not Path(path).is_file() for path in paths):
            raise ValueError('An uploaded file is missing')
        types = ['main'] * len(paths)
        create_icon = self.kwargs.get('create_icon', True)
        if type(create_icon) is not bool:
            raise ValueError('Invalid check-in option')
        if create_icon:
            preview = IconCreator(paths[0])
            preview.execute()
            for kind, path in (('web', preview.get_web_path()), ('icon', preview.get_icon_path())):
                if path:
                    paths.append(path); types.append(kind)
        checkin = FileCheckin(owner, paths, file_types=types, context=context,
            process=process, description=description, mode='create', source_paths=paths,
            keep_file_name=self.kwargs.get('keep_file_name', False),
            is_revision=self.kwargs.get('is_revision', False), version=version, checkin_type='strict', base_dir_alias=alias)
        checkin.execute()
        self.info['snapshot'] = checkin.get_snapshot().get_sobject_dict()
        return self.info
