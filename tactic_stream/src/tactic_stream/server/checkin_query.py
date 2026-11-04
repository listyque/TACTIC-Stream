"""Handler tactic_query.py extended naming/check-in procedures (EPL-1.0).

The request-bound local SDK is passed explicitly instead of the Mako global.
"""

def get_virtual_snapshot_extended(server, search_key, context, files_dict, snapshot_type="file", is_revision=False, level_key=None, keep_file_name=False, explicit_filename=None, version=None, update_versionless=True, ignore_keep_file_name=False, checkin_type='file', process=None):
    '''creates a virtual snapshot and returns a path that this snapshot
    would generate through the naming conventions''

    @params
    snapshot creation:
    -----------------
    search_key - a unique identifier key representing an sobject
    context - the context of the checkin
    snapshot_type - [optional] descibes what kind of a snapshot this is.
        More information about a snapshot type can be found in the
        prod/snapshot_type sobject
    level_key - the unique identifier of the level that this
        is to be checked into

    path creation:
    --------------
    file_type: the type of file that will be checked in.  Some naming
        conventions make use of this information to separate directories
        for different file types
    file_name: the desired file name of the preallocation.  This information
        may be ignored by the naming convention or it may use this as a
        base for the final file name
    ext: force the extension of the file name returned

    @return
    path as determined by the naming conventions
    '''
    # getting virtual snapshots
    import json
    from pyasm.biz import Snapshot
    from pyasm.biz import Project
    from pyasm.search import SearchType, SearchKey, Search

    api = server.server

    sobject = SearchKey.get_by_search_key(search_key)

    # get the level object
    if level_key:
        levels = api._get_sobjects(level_key)
        level = levels[0]
        level_type = level.get_search_type()
        level_id = level.get_id()
    else:
        level_type = None
        level_id = None

    description = "No description"
    files_dict = json.loads(files_dict)

    # this is only to avoid naming intersection
    if checkin_type == 'file':
        if len(files_dict) > 1 and not ignore_keep_file_name:
            keep_file_name = True

    # if checkin_type == 'multi_file':
    #     keep_file_name = False

    # if len(set(file_type)) != 1:
    #     keep_file_name = False

    def get_max_version(context, search_key):
        # faster way to get max snapshot version
        search = Search('sthpw/snapshot')
        search.add_sobject_filter(sobject)
        search.add_filter('context', context)
        search.add_column('version')
        search.add_order_by('version desc')
        search.set_limit(1)
        snaps = search.get_sobjects()
        if snaps:
            return snaps[0].get_attr_value('version')

    if not version:
        ver = get_max_version(context=context, search_key=search_key)
        if ver is not None:
            if is_revision:
                version = int(ver)
            else:
                version = int(ver) + 1
        else:
            version = 1

    file_naming = Project.get_file_naming()
    file_naming.set_sobject(sobject)

    snapshot_versioned = Snapshot.create(sobject, snapshot_type=snapshot_type, process=process, context=context, description=description,
                                         is_revision=is_revision, level_type=level_type, level_id=level_id,
                                         commit=False, version=version)

    if is_revision:
        snapshot_versioned.set_value('version', version)

    if update_versionless:
        snapshot_versionless = Snapshot.create(sobject, snapshot_type=snapshot_type, process=process, context=context,
                                               description=description, is_revision=False, level_type=level_type,
                                               level_id=level_id, commit=False, version=-1)

    def prepare_filename(filenaming, f_l, ext, postfix, metadata):

        if keep_file_name:
            file_type = filenaming.get_file_type()
            if file_type in ['web', 'icon']:
                postfix = file_type
            if postfix:
                result_file_name = f_l + '_' + postfix + '.' + ext
            else:
                if ext:
                    result_file_name = f_l + '.' + ext
                else:
                    result_file_name = f_l
        else:
            name_ext = filenaming.get_file_name()

            # filenaming.get_file_name()
            if postfix:
                result_file_name = name_ext.replace(filenaming.get_ext(), '_{0}.{1}'.format(postfix, ext))
            else:
                result_file_name = name_ext

        # first_part = result_file_name.replace(filenaming.get_ext(), '')
        first_part = result_file_name.split('.')
        if len(first_part) > 1:
            first_part = '.'.join(first_part[:-1])
        else:
            first_part = first_part[0]

        if metadata:
            return first_part, metadata.get('name_part'), filenaming.get_ext()
        else:
            return first_part, '', filenaming.get_ext()

    def prepare_folder(d, sub):
        if sub:
            return d + '/' + sub
        else:
            return d

    file_object = SearchType.create("sthpw/file")

    result_list = []

    # fl::file, t::type, e::extension, s::sub-folder, p::postfix, m::metadata
    for fl, val in files_dict:

        result_dict = {'versionless': {'paths': [], 'names': []}, 'versioned': {'paths': [], 'names': []}}

        if not fl:
            fl = sobject.get_code()
        elif not fl:
            fl = sobject.get_name()
        elif not fl:
            fl = "unknown"

        if explicit_filename:
            keep_file_name = True
            fl = explicit_filename

        for t, e, s, p in zip(val['t'], val['e'], val['s'], val['p']):
            file_object.set_value("file_name", fl)
            file_object.set_value("type", t)
            if val['m']:
                file_object.set_value("metadata", json.dumps(val['m'], separators=(',', ':')))

            file_naming.set_snapshot(snapshot_versioned)
            # snapshot_versioned.add_file('', t)
            file_naming.set_ext(e)
            file_naming.set_file_object(file_object)
            result_dict['versioned']['paths'].append(prepare_folder(snapshot_versioned.get_dir('relative', file_type=str(t), file_object=file_object), s))
            result_dict['versioned']['names'].append(prepare_filename(file_naming, fl, e, p, val['m']))
            # result_dict['versioned']['names'].append(file_naming.get_file_name())

            if update_versionless:
                file_naming.set_snapshot(snapshot_versionless)
                # snapshot_versionless.add_file('', t)
                file_naming.set_ext(e)
                file_naming.set_file_object(file_object)

                result_dict['versionless']['paths'].append(prepare_folder(snapshot_versionless.get_dir('relative', file_type=str(t), file_object=file_object), s))
                result_dict['versionless']['names'].append(prepare_filename(file_naming, fl, e, p, val['m']))
                # result_dict['versionless']['names'].append(file_naming.get_file_name())

        result_list.append((fl, result_dict))

    return json.dumps(result_list, separators=(',', ':'))

def create_snapshot_extended(server, search_key, context, project_code=None, snapshot_type=None, is_revision=False, is_latest=True, is_current=False, description=None, version=None, level_key=None, update_versionless=True, only_versionless=False, keep_file_name=True, repo_name=None, files_info=None, mode=None, create_icon=True, transaction_title=None, transaction_description=None, process=None):
    import os
    import shutil
    import json
    from pyasm.biz import Snapshot, IconCreator
    from pyasm.checkin import FileAppendCheckin
    from pyasm.search import Search
    from pyasm.common import Environment

    if project_code:
        server.set_project(project_code)

    if transaction_title:
        # Local SDK start names the enclosing Command; it does not open another RPC.
        server.start(transaction_title, transaction_description)

    api = server.server

    sobject = api._get_sobjects(search_key)[0]

    # get the level object
    if level_key:
        levels = api._get_sobjects(level_key)
        level = levels[0]
        level_type = level.get_search_type()
        level_id = level.get_id()
    else:
        level_type = None
        level_id = None

    if not description:
        description = 'No description'
    if not snapshot_type:
        snapshot_type = 'file'

    files_info = json.loads(files_info, strict=False)

    def get_max_version(context, search_key):
        # faster way to get max snapshot version
        search = Search('sthpw/snapshot')
        search.add_sobject_filter(sobject)
        search.add_filter('context', context)
        search.add_column('version')
        search.add_order_by('version desc')
        search.set_limit(1)
        snaps = search.get_sobjects()
        if snaps:
            return snaps[0].get_attr_value('version')

    if not version:
        ver = get_max_version(context=context, search_key=search_key)
        if ver is not None:
            if is_revision:
                version = int(ver)
            else:
                version = int(ver) + 1
        else:
            version = 1

    snapshot = Snapshot.create(sobject, snapshot_type=snapshot_type, process=process, context=context, description=description, is_revision=is_revision, is_latest=is_latest, is_current=is_current, level_type=level_type, level_id=level_id, commit=False, version=version)

    if repo_name:
        snapshot.set_value('repo', repo_name)
    if is_latest:
        snapshot.set_value('is_latest', 1)
    if is_current:
        snapshot.set_value('is_current', 1)

    if context.startswith('icon'):
        # This is for TACTIC 4.8 >
        update_versionless = False

    if is_revision:
        snapshot_code = server.eval("@GET(sthpw/snapshot['version', {0}].code)".format(version),
                                    search_keys=[search_key], single=True)
        revision = server.eval("@MAX(sthpw/snapshot.revision)",
                               search_keys=['sthpw/snapshot?code={0}'.format(snapshot_code)])

        snapshot.set_value('version', version)
        snapshot.set_value('revision', revision + 1)

    if mode == 'upload':
        checkin_mode = 'uploaded'

        # SOME KIND OF HACK!
        if is_revision:
            checkin_mode = 'preallocate'

        env = Environment.get()
        lib_dir = env.get_upload_dir()

        file_paths = []
        original_files_paths = []
        file_types = []

        upload_file_names = files_info.get('upload_file_names') or []

        def file_name_with_extension(name, extension):
            name = os.path.basename(str(name or '').replace('\\', '/'))
            extension = os.path.basename(
                str(extension or '').replace('\\', '/')
            ).lstrip('.')
            if extension:
                return '{0}.{1}'.format(name, extension)
            return name

        from pyasm.biz import FileUndo
        from .api import check_ticket_paths

        for index, (metadata, types) in enumerate(zip(
                files_info['version_metadata'], files_info['files_types'])):
            original_name = file_name_with_extension(
                metadata.get('filename'), metadata.get('new_file_ext'))
            upload_name = (
                os.path.basename(str(upload_file_names[index]).replace('\\', '/'))
                if index < len(upload_file_names) and upload_file_names[index]
                else file_name_with_extension(
                    metadata.get('new_filename'), metadata.get('new_file_ext'))
            )
            original_files_paths.append('{0}/{1}'.format(lib_dir, original_name))
            file_paths.append('{0}/{1}'.format(lib_dir, upload_name))
            file_types.append(types)

        check_ticket_paths(file_paths, lib_dir)

        # generating previews if it's not explicitly passed
        if any(i in file_types for i in ['web', 'icon']):
            create_icon = False

        for original_file in file_paths[:]:
            # if this is a file, then try to create an icon
            if os.path.isfile(original_file) and create_icon:
                icon_creator = IconCreator(original_file)
                icon_creator.execute()

                web_path = icon_creator.get_web_path()
                icon_path = icon_creator.get_icon_path()

                # If this is pure icon context, then don't check in icon
                # as the main file.
                if context == 'icon':
                    if web_path:
                        FileUndo.copy(web_path, original_file)
                    elif icon_path:
                        FileUndo.copy(icon_path, original_file)

                # If web file is not generated and icon is, use original as web.
                if icon_path and not web_path:
                    base, ext = os.path.splitext(original_file)
                    web_path = "%s_web.%s" % (base, ext)
                    FileUndo.copy(original_file, web_path)

                if web_path:
                    file_paths.append(web_path)
                    file_types.append('web')
                    original_files_paths.append(web_path)
                    files_info['file_sizes'].append(65536)
                    files_info['version_metadata'].append('')
                    files_info['versionless_metadata'].append('')

                if icon_path:
                    file_paths.append(icon_path)
                    file_types.append('icon')
                    original_files_paths.append(icon_path)
                    files_info['file_sizes'].append(65536)
                    files_info['version_metadata'].append('')
                    files_info['versionless_metadata'].append('')

        snapshot.commit(triggers=True, log_transaction=True)

        # we keep file name as we already got name from virtual snapshot
        checkin = FileAppendCheckin(snapshot.get_code(), file_paths, file_types,
                                    keep_file_name=True, mode=checkin_mode, source_paths=file_paths,
                                    checkin_type='auto', do_update_versionless=False)

        checkin.file_sizes = files_info['file_sizes']
        checkin.execute()
        files_list = checkin.get_file_objects()

        for i, fl in enumerate(files_list):
            fl.set_value(name='source_path', value=original_files_paths[i])
            fl.set_value(name='metadata', value=json.dumps(files_info['version_metadata'][i], separators=(',', ':')))
            fl.commit(triggers=False, log_transaction=False)

        if update_versionless:

            snapshot.update_versionless('latest', sobject=sobject, checkin_type='strict')
            versionless_snapshot = snapshot.get_by_sobjects([sobject], context, version=-1)

            if repo_name:
                versionless_snapshot[0].set_value('repo', repo_name)
            versionless_snapshot[0].set_value('login', snapshot.get_attr_value('login'))
            versionless_snapshot[0].set_value('timestamp', snapshot.get_attr_value('timestamp'))
            versionless_snapshot[0].set_value('description', description)
            versionless_snapshot[0].commit(triggers=False, log_transaction=False)
            file_objects = versionless_snapshot[0].get_all_file_objects()

            for i, file_object in enumerate(file_objects):
                file_object.set_value(name='project_code', value=snapshot.get_project_code())
                file_object.set_value(name='metadata',
                                      value=json.dumps(files_info['versionless_metadata'][i], separators=(',', ':')))
                file_object.set_value(name='source_path', value=original_files_paths[i])
                file_object.commit(triggers=False, log_transaction=False)
    elif mode == 'inplace':

        if only_versionless:
            snapshot.set_value('version', -1)
            snapshot.set_value('is_current', 1)
            snapshot.set_value('is_latest', 1)
            update_versionless = False
            existing_versionless_snapshot = snapshot.get_by_sobjects([sobject], context, version=-1)
            if existing_versionless_snapshot:
                from tactic.ui.tools import DeleteCmd
                cmd = DeleteCmd(sobject=existing_versionless_snapshot[0], auto_discover=True)
                cmd.execute()

            snapshot.commit(triggers=True, log_transaction=True)

            checkin = FileAppendCheckin(snapshot.get_code(), files_info['versionless_files'], files_info['files_types'],
                                        keep_file_name=True, mode=mode, source_paths=files_info['versionless_files'],
                                        checkin_type='auto', do_update_versionless=False)
            checkin.execute()

            files_list = checkin.get_file_objects()

            for i, fl in enumerate(files_list):
                fl.set_value(name='st_size', value=files_info['file_sizes'][i])
                fl.set_value(name='relative_dir', value=files_info['versionless_files_paths'][i])
                fl.set_value(name='metadata', value=json.dumps(files_info['versionless_metadata'][i], separators=(',', ':')))
                fl.commit(triggers=False, log_transaction=False)

        else:

            snapshot.commit(triggers=True, log_transaction=True)
            # we keep file name as we already got name from virtual snapshot
            checkin = FileAppendCheckin(snapshot.get_code(), files_info['version_files'], files_info['files_types'],
                                        keep_file_name=True, mode=mode, source_paths=files_info['version_files'],
                                        checkin_type='auto', do_update_versionless=False)
            checkin.execute()

            files_list = checkin.get_file_objects()

            for i, fl in enumerate(files_list):
                fl.set_value(name='st_size', value=files_info['file_sizes'][i])
                fl.set_value(name='relative_dir', value=files_info['version_files_paths'][i])
                fl.set_value(name='metadata', value=json.dumps(files_info['version_metadata'][i], separators=(',', ':')))
                fl.commit(triggers=False, log_transaction=False)

        if update_versionless:
            existing_versionless_snapshot = snapshot.get_by_sobjects([sobject], context, version=-1)
            if existing_versionless_snapshot:
                from tactic.ui.tools import DeleteCmd
                cmd = DeleteCmd(sobject=existing_versionless_snapshot[0], auto_discover=True)
                cmd.execute()

            versionless = Snapshot.create(sobject, snapshot_type=snapshot_type, process=process, context=context, description=description,
                                       is_revision=is_revision, is_latest=is_latest, is_current=is_current,
                                       level_type=level_type, level_id=level_id, commit=False, version=version)

            if repo_name:
                versionless.set_value('repo', repo_name)
            versionless.set_value('version', -1)
            # snapshot.set_value('is_current', 1)
            versionless.set_value('is_latest', 1)

            versionless.commit(triggers=False, log_transaction=False)

            checkin = FileAppendCheckin(versionless.get_code(), files_info['versionless_files'], files_info['files_types'],
                                        keep_file_name=True, mode=mode, source_paths=files_info['versionless_files'],
                                        checkin_type='auto', do_update_versionless=False)
            checkin.execute()

            from pyasm.checkin import SnapshotBuilder
            builder = SnapshotBuilder()

            files_list = checkin.get_file_objects()

            for i, fl in enumerate(files_list):
                fl.set_value(name='st_size', value=files_info['file_sizes'][i])
                fl.set_value(name='relative_dir', value=files_info['versionless_files_paths'][i])
                fl.set_value(name='metadata', value=json.dumps(files_info['versionless_metadata'][i], separators=(',', ':')))
                info = {'type': files_info['files_types'][i]}
                builder.add_file(fl, info=info)
                fl.commit(triggers=False, log_transaction=False)

            builder.add_root_attr('ref_snapshot_code', snapshot.get_code())

            versionless.set_value("snapshot", builder.to_string())

            versionless.commit(triggers=False, log_transaction=False)

    snapshot_dict = api._get_sobject_dict(snapshot)

    return snapshot_dict
