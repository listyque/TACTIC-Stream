"""Browser preparation/staging for the native Handler extended check-in (EPL-1.0)."""
import copy
import json
import os
import re
from pathlib import Path, PurePosixPath

from pyasm.command import Command
from pyasm.common import Environment, Config, Container
from pyasm.biz import Snapshot, IconCreator, Project, ProjectSetting
from pyasm.search import FileUndo, Search, SearchKey
from pyasm.checkin.repo import _check_file_name
from pyasm.common.errors import UserException
from tactic_client_lib import TacticServerStub
from tactic_stream.server.api import upload_file_name, check_ticket_paths
from tactic_stream.server.result_items import objects
from tactic_stream.server.file_matching import MatchTemplate
from tactic_stream.server.checkin_query import get_virtual_snapshot_extended, create_snapshot_extended
from tactic_stream.server.file_presentation import metadata_paths

DEFAULT_TEMPLATES = ['$FILENAME', '$FILENAME.$EXT', '$FILENAME.$FRAME.$EXT', '$FILENAME_$UDIM.$EXT',
                     '$FILENAME_$UV.$EXT', '$FILENAME.$FRAME_$UDIM.$EXT', '$FILENAME.$FRAME_$UV.$EXT', '$FILENAME_$UV.$FRAME.$EXT']


def _check_existing_file(path, root, replaceable, dir_cache=None):
    target = Path(path)
    if not os.path.lexists(target):
        return
    if target.is_dir():
        raise UserException('Repository path is a directory: %s' % target)
    if target.absolute() in replaceable:
        return
    relative = target.parent.relative_to(root).as_posix()
    if dir_cache is not None and relative in dir_cache:
        existing_paths = dir_cache[relative]
    else:
        files = Search('sthpw/file')
        files.add_op('begin')
        files.add_filters('relative_dir', [relative, target.parent.as_posix()])
        if relative == '.':
            files.add_empty_filter('relative_dir')
        files.add_op('or')
        existing_paths = {member.absolute() for file in files.get_sobjects() for member in metadata_paths(file)}
        if dir_cache is not None:
            dir_cache[relative] = existing_paths
    if target.absolute() in existing_paths:
        raise UserException('Repository path already exists in a saved snapshot: %s' % target)


def check_templates(templates, padding):
    if type(padding) is not int or not 1 <= padding <= 9:
        raise UserException('Frame padding must be between 1 and 9')
    templates = DEFAULT_TEMPLATES if templates is None else templates
    if not isinstance(templates, list) or not 1 <= len(templates) <= 32:
        raise UserException('Choose matching templates')
    for pattern in templates:
        tokens = re.split(r'([._])', pattern) if isinstance(pattern, str) else []
        if '$FILENAME' not in tokens or len(pattern) > 200 or any(token not in ('$FILENAME', '$EXT', '$FRAME', '$UDIM', '$UV', '$LAYER', '.', '_') for token in tokens):
            raise UserException('Invalid matching template')
        names = [token for token in tokens if token.startswith('$')]
        if len(names) != len(set(names)):
            raise UserException('A matching token may only occur once')
    return templates


def matched_files(records, templates=None, padding=3, max_files=1000):
    if not isinstance(records, list) or not 1 <= len(records) <= max_files:
        raise UserException('Choose up to %s files' % max_files)
    templates = check_templates(templates, padding)
    templates = list(dict.fromkeys([*templates, '$FILENAME', '$FILENAME.$EXT']))
    paths = {}
    for index, record in enumerate(records):
        path = record.get('path') if isinstance(record, dict) else None
        if not isinstance(path, str) or not path or len(path) > 1024 or '\\' in path or '\0' in path or ':' in path or path.startswith('/') or any(part in ('', '.', '..') for part in path.split('/')):
            raise UserException('Invalid source file path')
        _check_file_name(PurePosixPath(path).name)
        if path in paths:
            raise UserException('The same file is already on Drop Plate')
        size = record.get('size', 0)
        if type(size) is not int or size < 0:
            raise UserException('Invalid file size')
        paths[path] = index
    result = []
    for kind, groups in MatchTemplate(templates, padding=padding).get_files_objects(list(paths)).items():
        for group in groups:
            members = group.get_all_files_list()
            group.set_sizes_list([records[paths[path]].get('size', 0) for path in members])
            result.append((group, [paths[path] for path in members]))
    return result


class BrowserCheckinCmd(Command):
    def execute(self):
        from tactic_stream.server.navigation_links import check_project
        check_project(Project.get_project_code())
        action = self.kwargs.get('action', 'checkin')
        if action == 'templates':
            patterns = self.kwargs.get('templates')
            if not isinstance(patterns,list) or not 1 <= len(patterns) <= 32:
                raise UserException('Choose matching templates')
            example = self.kwargs.get('example', '')
            if not isinstance(example, str):
                raise UserException('Invalid source file path')
            if example:
                _check_file_name(example)
            self.info['templates'] = []
            for pattern in patterns:
                try:
                    check_templates([pattern],self.kwargs.get('padding',3))
                except UserException as error:
                    self.info['templates'].append(dict(pattern=pattern,preview='',matchingType='',matched='',validationError=str(error)))
                    continue
                matcher = MatchTemplate([pattern], padding=self.kwargs.get('padding', 3))
                matched = list(matcher.get_files([example])) if example else []
                self.info['templates'].append(dict(pattern=pattern, matchingType=matcher.get_type_string(),
                    preview=matcher.get_preview_string(), matched=matched[0][1]['type'] if matched else '',validationError=''))
            return self.info
        groups = matched_files(self.kwargs.get('source_files'), self.kwargs.get('templates'), self.kwargs.get('padding', 3),
                               max_files=getattr(self, 'max_files', 1000))
        if action == 'match':
            self.info['groups'] = [dict(title=group.get_pretty_file_name(), path=group.get_file_path(),
                extension=group.get_file_ext(), matchingType=group.get_type(), indices=indices,
                fileCount=len(indices), size=group.get_sizes_list(together=True), metadata=group.get_metadata(),
                sequenceInfo=group.get_sequence_frameranges_string('[]') or '') for group, indices in groups]
            return self.info
        if action not in ('plan', 'checkin'):
            raise UserException('Unknown check-in action')
        key = self.kwargs.get('search_key')
        if not isinstance(key, str) or not key:
            raise UserException('Choose an object for check-in')
        owner = next(iter(objects(SearchKey.extract_base_search_type(key), [key], read_access=True).values()))
        context, process = self.kwargs.get('context'), self.kwargs.get('process')
        if not isinstance(context, str) or not context.strip() or len(context) > 256 or not isinstance(process, str) or not process or len(process) > 256:
            raise UserException('Choose a process and context for check-in')
        description = self.kwargs.get('description', '')
        if not isinstance(description, str):
            raise UserException('Invalid description')
        flags = {name: self.kwargs.get(name, default) for name, default in
                 (('keep_file_name', False), ('update_versionless', True), ('only_versionless', False), ('is_revision', False), ('create_icon', True))}
        if any(type(value) is not bool for value in flags.values()):
            raise UserException('Invalid check-in option')
        if flags['only_versionless'] and flags['is_revision']:
            raise UserException('A revision requires a numbered version')
        version = self.kwargs.get('version')
        if type(version) is int and version == 0:
            version = None
        if version is not None and (type(version) is not int or version < 1):
            raise UserException('Version must be a positive whole number')
        explicit = self.kwargs.get('explicit_filename') or None
        if explicit is not None:
            if not isinstance(explicit, str):
                raise UserException('Invalid repository file name')
            _check_file_name(explicit)
        alias = self.kwargs.get('repository_alias') or 'default'
        if not isinstance(alias, str) or alias == 'plugins' or alias != 'default' and alias not in Environment.get_asset_dirs():
            raise UserException('Choose a configured repository alias')
        if flags['is_revision']:
            previous = Snapshot.get_snapshot(owner.get_search_type(), owner.get_id(), context=context, version=version)
            if not previous or previous.get_version() < 0:
                raise UserException('Choose a versioned snapshot for a revision')
            aliases = {file.get_value('base_dir_alias') or 'default' for file in previous.get_all_file_objects()}
            if aliases != {alias}:
                raise UserException('A revision must use its existing repository')
        server = TacticServerStub.get()
        # Allocate under the same native version lock that protects snapshot writes.
        if action == 'checkin':
            owner._check_business_write('edit')
            Container.put('Checkin:writing', {'parent':owner})
            FileUndo._check_access()
            Snapshot(Snapshot.SEARCH_TYPE)._lock_versions()
        files_dict = []
        records = self.kwargs['source_files']
        kinds = self.kwargs.get('file_types', [records[indices[0]].get('file_type', 'main') for group, indices in groups])
        if not isinstance(kinds, list) or len(kinds) != len(groups) or any(not isinstance(kind, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', kind) for kind in kinds):
            raise UserException('Each file group requires its file type')
        if any(not isinstance(record.get('file_type', 'main'), str) for record in records):
            raise UserException('Each file group requires its file type')
        if any(len({records[index].get('file_type', 'main') for index in indices}) != 1 for group, indices in groups):
            raise UserException('A file group cannot mix main files and previews')
        for (group, indices), kind in zip(groups, kinds):
            application_info = self.kwargs.get('application_info') or {}
            if not isinstance(application_info, dict):
                raise UserException('DCC application metadata must be an object')
            if application_info:
                group.set_app_info(application_info)
            metadata = group.get_metadata()
            metadata['name_part'] = group.get_name_part()
            files_dict.append([group.get_file_name(True), dict(t=[kind], e=[group.get_file_ext()], s=[''], p=['' if kind == 'main' else kind], m=metadata)])
        plan = json.loads(get_virtual_snapshot_extended(server, key, context, json.dumps(files_dict),
            process=process, is_revision=flags['is_revision'], keep_file_name=flags['keep_file_name'], explicit_filename=explicit,
            version=version, update_versionless=flags['update_versionless'] or flags['only_versionless']))
        actual_version = Snapshot.create(owner, 'file', context, commit=False,
            is_revision=flags['is_revision'], version=version).get_version()
        if action == 'plan':
            reserved = self.kwargs.get('reserved_versions', [])
            if not isinstance(reserved, list) or any(type(value) is not int or value < 1 for value in reserved) or len(reserved) > 1000:
                raise UserException('Invalid queued versions')
            if not version and not flags['is_revision'] and reserved:
                actual_version = max(actual_version, max(reserved) + 1)
                plan = json.loads(get_virtual_snapshot_extended(server, key, context, json.dumps(files_dict),
                    process=process, keep_file_name=flags['keep_file_name'], explicit_filename=explicit, version=actual_version,
                    update_versionless=flags['update_versionless'] or flags['only_versionless']))
        root = Path(Environment.get_asset_dir(alias=alias)).resolve()
        projections = []
        for (group, indices), (_name, predicted) in zip(groups, plan):
            row = dict(title=group.get_pretty_file_name(), indices=indices, type=kinds[len(projections)])
            for destination in ('versioned', 'versionless'):
                value = predicted[destination]
                if not value['names']:
                    row[destination] = []; continue
                base, part, extension = value['names'][0]
                directory = root / value['paths'][0]
                paths = group.get_all_new_files_list(new_filename=(base, part, extension), new_filepath=directory.as_posix(), new_frame_padding=group.get_sequence_padding() or 4)
                if any(not Path(path).resolve().is_relative_to(root) for path in paths):
                    raise UserException('Naming points outside the selected repository')
                if len(set(os.path.normcase(path) for path in paths)) != len(paths):
                    raise UserException('Naming creates duplicate file paths')
                row[destination] = paths
            projections.append(row)
        self.info['plan'] = dict(version=actual_version, files=projections, repository=alias)
        if action == 'plan':
            return self.info
        names = self.kwargs.get('files')
        if not isinstance(names, list) or len(names) != len(records) or any(not isinstance(name, str) or upload_file_name(name) != name for name in names) or len(set(names)) != len(names):
            raise UserException('Each source file requires its uploaded file')
        directory = getattr(self, 'upload_directory', None) or Environment.get_upload_dir()
        uploads = [(Path(directory) / name).as_posix() for name in names]
        check_ticket_paths(uploads, directory)
        if any(not Path(path).is_file() for path in uploads):
            raise UserException('An uploaded file is missing')
        destinations = ['versionless'] if flags['only_versionless'] else ['versioned'] + (['versionless'] if flags['update_versionless'] and context != 'icon' else [])
        old = Snapshot.get_by_sobjects([owner], context=context, version=-1)
        replaceable = {'versionless': {path.absolute() for snapshot in old for file in snapshot.get_all_file_objects() for path in metadata_paths(file)},
                       'versioned': {path.absolute() for file in previous.get_all_file_objects() for path in metadata_paths(file)} if flags['is_revision'] else set()}
        planned = [path for row in projections for dest in destinations for path in row[dest]]
        if len(set(os.path.normcase(path) for path in planned)) != len(planned):
            raise UserException('Naming creates duplicate file paths')
        existing_dir_cache = {}
        for row in projections:
            for dest in destinations:
                for path in row[dest]:
                    _check_existing_file(path, root, replaceable[dest], dir_cache=existing_dir_cache)
        versionless_mode = ProjectSetting.get_value_by_key('versionless_mode') or Config.get_value('checkin','versionless_mode') or ('symlink' if os.name == 'posix' else 'copy')
        if 'versionless_mode' in self.kwargs:
            versionless_mode = self.kwargs['versionless_mode']
            if versionless_mode not in ('copy', 'symlink', 'hardlink'):
                raise UserException('Versionless files must use copy, symlink or hardlink')
        info = dict(files_types=kinds, file_sizes=[], version_files=[], versionless_files=[],
                    version_files_paths=[], versionless_files_paths=[], version_metadata=[], versionless_metadata=[])
        for (group, indices), row, (_name, predicted) in zip(groups, projections, plan):
            info['file_sizes'].append(sum(Path(uploads[index]).stat().st_size for index in indices))
            for dest in destinations:
                for member, (index, path) in enumerate(zip(indices, row[dest])):
                    FileUndo.mkdir(str(Path(path).parent))
                    if dest == 'versionless' and 'versioned' in destinations and versionless_mode != 'copy':
                        FileUndo.symlink(row['versioned'][member], path, mode=versionless_mode)
                    else:
                        FileUndo.copy(uploads[index], path)
            for dest in ('versioned', 'versionless'):
                value = predicted[dest]
                if not value['names']:
                    continue
                base, part, extension = value['names'][0]
                group.get_all_new_files_list(new_filename=(base, part, extension), new_filepath=(root / value['paths'][0]).as_posix(), new_frame_padding=group.get_sequence_padding() or 4)
                info['version_files' if dest == 'versioned' else 'versionless_files'].append(row[dest][0])
                info['version_files_paths' if dest == 'versioned' else 'versionless_files_paths'].append(value['paths'][0])
                info['version_metadata' if dest == 'versioned' else 'versionless_metadata'].append(copy.deepcopy(group.get_metadata()))
        # Derivatives are native IconCreator output; their file identity is separate from main.
        if flags['create_icon']:
            preview_source = next((indices[0] for (group, indices), kind in zip(groups, kinds) if kind == 'preview'), 0)
            preview = IconCreator(uploads[preview_source]); preview.execute()
            for kind, source in (('web', preview.get_web_path()), ('icon', preview.get_icon_path())):
                if not source:
                    continue
                derivative = json.loads(get_virtual_snapshot_extended(server, key, context,
                    json.dumps([[files_dict[0][0], dict(t=[kind], e=[Path(source).suffix.lstrip('.')], s=[''], p=[kind], m={})]]),
                    process=process, version=actual_version, explicit_filename=explicit, keep_file_name=flags['keep_file_name'], update_versionless=bool('versionless' in destinations)))[0][1]
                info['files_types'].append(kind); info['file_sizes'].append(Path(source).stat().st_size)
                for dest in ('versioned', 'versionless'):
                    value = derivative[dest]
                    if not value['names']:
                        continue
                    target = root / value['paths'][0] / ''.join(value['names'][0])
                    if not target.resolve().is_relative_to(root) or target.as_posix() in planned:
                        raise UserException('Repository path already exists: %s' % target)
                    if dest in destinations:
                        _check_existing_file(target, root, replaceable[dest], dir_cache=existing_dir_cache)
                        FileUndo.mkdir(str(target.parent))
                        if dest == 'versionless' and 'versioned' in destinations and versionless_mode != 'copy':
                            original = root / derivative['versioned']['paths'][0] / ''.join(derivative['versioned']['names'][0])
                            FileUndo.symlink(str(original),str(target),mode=versionless_mode)
                        else:
                            FileUndo.copy(source, str(target))
                        planned.append(target.as_posix())
                    info['version_files' if dest == 'versioned' else 'versionless_files'].append(target.as_posix())
                    info['version_files_paths' if dest == 'versioned' else 'versionless_files_paths'].append(value['paths'][0])
                    info['version_metadata' if dest == 'versioned' else 'versionless_metadata'].append({})
        self.info['snapshot'] = create_snapshot_extended(server, key, context, project_code=Project.get_project_code(),
            process=process, description=description, version=actual_version, is_revision=flags['is_revision'],
            is_current=True, repo_name='base' if alias == 'default' else alias, update_versionless='versionless' in destinations and not flags['only_versionless'],
            only_versionless=flags['only_versionless'], files_info=json.dumps(info), mode='inplace', create_icon=False)
        if any(not Path(path).is_file() for path in planned):
            raise UserException('An inplace check-in file is missing')
        return self.info
