###########################################################
#
# Copyright (c) 2005-2008, Southpaw Technology
#                     All Rights Reserved
#
# PROPRIETARY INFORMATION.  This software is proprietary to
# Southpaw Technology, and is not to be reproduced, transmitted,
# or disclosed in any way without written permission.
#
#
#

from pathlib import Path
import os, re, shutil
from pyasm.common import Environment, jsonloads, TacticException, Common
from pyasm.command import Command
from pyasm.search import SearchType, Search, FileUndo
from pyasm.biz import File, Project, FileGroup, FileRange, Snapshot, ProjectSetting
from tactic_client_lib import TacticServerStub
from tactic_stream.server.api import upload_file_name, check_ticket_paths

__all__ = ['IngestUploadCmd']

class IngestUploadCmd(Command):

    def validate_uploads(self):
        FileUndo._check_access()
        if self.kwargs.get('project_code') not in (None, '', Project.get_project_code()):
            raise ValueError('Ingest belongs to another project')
        from tactic_stream.server.result_items import objects
        from pyasm.search import SearchKey
        for name in ('search_key', 'parent_key'):
            key = self.kwargs.get(name)
            if key:
                objects(SearchKey.extract_base_search_type(key), [key])
        target = self.kwargs.get('search_type')
        if target and SearchType.breakup_search_type(target).get('project') not in (None, '', Project.get_project_code()):
            raise ValueError('Ingest belongs to another project')
        for option in ('base_dir', 'unzip', 'zip_mode', 'library_mode', 'collection_key', 'collection_code', 'category', 'category_script_path'):
            if self.kwargs.get(option):
                raise ValueError('This ingest operation requires a server-side ingest rule: %s' % option)
        if self.kwargs.get('update_mode') not in (None, '', True, False, 'true', 'false', 'update', 'insert'):
            raise ValueError('Choose insert or update for uploaded ingest')
        filenames = self.kwargs.get('filenames')
        if not isinstance(filenames, list) or not 1 <= len(filenames) <= 100 or any(not isinstance(name, str) or upload_file_name(name) != name for name in filenames):
            raise ValueError('Choose up to 100 uploaded files')
        if len(set(filenames)) != len(filenames):
            raise ValueError('Choose different file names for a group check-in')
        directory = Environment.get_upload_dir()
        paths = [str(Path(directory) / name) for name in filenames]
        check_ticket_paths(paths, directory)
        if any(not Path(path).is_file() for path in paths):
            raise ValueError('An uploaded file is missing')

    # FOLDER_LIMIT can be adjusted as desired.
    FOLDER_LIMIT = 500

    def get_server(self):

        if not self.server:
            project_code = self.kwargs.get("project_code")
            if not project_code:
                self.server = TacticServerStub.get()

            else:
                self.server = TacticServerStub(protocol="local")
                self.server.set_project(project_code)

        return self.server

    def execute(self):

        import time
        start = time.time()

        self.server = None

        self.message_key = self.kwargs.get("message_key")
        try:
            ret_val = self._execute()
        except Exception as e:
            if self.message_key:
                msg = {
                    'progress': 100,
                    'error': '%s' % e,
                    'description': 'Error: %s' % e
                }

                server = self.get_server()
                server.log_message(self.message_key, msg, status="in progress")

            raise


        end = time.time()
        return ret_val


    def _execute(self):

        self.validate_uploads()
        library_mode = self.kwargs.get("library_mode")
        current_folder = 0

        dated_dirs = self.kwargs.get("dated_dirs")

        filenames = self.kwargs.get("filenames")
        relative_dir = self.kwargs.get("relative_dir")


        base_dir = self.kwargs.get("base_dir")
        if not base_dir:
            upload_dir = Environment.get_upload_dir()
            base_dir = upload_dir

        context_mode = self.kwargs.get("context_mode")
        if not context_mode:
            context_mode = "case_sensitive"
        update_mode = self.kwargs.get("update_mode")
        ignore_ext = self.kwargs.get("ignore_ext")
        column = self.kwargs.get("column")
        if not column:
            column = "name"


        search_key = self.kwargs.get("search_key")
        if search_key:
            self.sobject = Search.get_by_search_key(search_key)
            search_type = self.sobject.get_base_search_type()
        else:
            search_type = self.kwargs.get("search_type")
            self.sobject = None


        if not relative_dir:
            project_code = Project.get_project_code()
            search_type_obj = SearchType.get(search_type)
            table = search_type_obj.get_table()
            relative_dir = "%s/%s" % (project_code, table)

        server = self.get_server()

        parent_key = self.kwargs.get("parent_key")
        category = self.kwargs.get("category")
        keywords = self.kwargs.get("keywords")
        update_process = self.kwargs.get("update_process")
        ignore_path_keywords = self.kwargs.get("ignore_path_keywords")
        if ignore_path_keywords:
            ignore_path_keywords = ignore_path_keywords.split(",")
            ignore_path_keywords = [x.strip() for x in ignore_path_keywords]

        update_data = self.kwargs.get("update_data")
        extra_data = self.kwargs.get("extra_data")
        if extra_data:
            extra_data = jsonloads(extra_data)
        else:
            extra_data = {}

        update_sobject_found = False
        # TODO: use this to generate a category
        category_script_path = self.kwargs.get("category_script_path")
        """
        ie:
            from pyasm.checkin import ExifMetadataParser
            parser = ExifMetadataParser(path=file_path)
            tags = parser.get_metadata()

            date = tags.get("EXIF DateTimeOriginal")
            return date.split(" ")[0]
        """


        # remap the filenames for sequences
        if update_mode == "sequence":
            sequences = FileRange.get_sequences(filenames)
            filenames = []
            for sequence in sequences:

                if sequence.get('is_sequence'):
                    filename = sequence.get("template")
                else:
                    filename = sequence.get("filenames")[0]
                filenames.append(filename)



        input_prefix = update_data.get('input_prefix')
        non_seq_filenames = []


        if library_mode:
            relative_dir = "%s/001" % relative_dir


        collection_key = self.kwargs.get("collection_key")
        collection_code = self.kwargs.get("collection_code")
        collection = None
        if collection_key:
            collection = Search.get_by_search_key(collection)
        elif collection_code:
            collection = Search.get_by_code(search_type, collection_code)


        snapshots = []

        for count, filename in enumerate(filenames):
            # Check if files should be updated.
            # If so, attempt to find one to update.
            # If more than one is found, do not update.



            if filename.endswith("/"):
                # this is a folder:
                continue


            # remove leading /
            filename = filename.lstrip("/")


            new_keywords = keywords

            if filename.startswith("search_key:"):
                mode = "search_key"
                tmp, search_key = filename.split("search_key:")
                snapshot = Search.get_by_search_key(search_key)

                source_keywords = snapshot.get_value("keywords", no_exception=True)
                if source_keywords:
                    new_keywords = "%s %s" % (new_keywords, source_keywords)

                if snapshot.get_base_search_type() == "sthpw/snapshot":
                    lib_path = snapshot.get_lib_path_by_type()
                    filename = os.path.basename(lib_path)
                    new_filename = re.sub(r"_v\d+", "", filename)
                else:
                    snapshot = Snapshot.get_latest_by_sobject(snapshot, process="publish")
                    lib_path = snapshot.get_lib_path_by_type()
                    filename = os.path.basename(lib_path)
                    new_filename = re.sub(r"_v\d+", "", filename)

                if not snapshot:
                    raise Exception("Must pass in snapshot search_key")



            else:
                mode = "multi"
                new_filename = filename

            if library_mode:

                # get count of number of files in the current asset ingest dir
                import glob
                abs_path = Environment.get_asset_dir() + "/" + relative_dir + "/*"

                if len(glob.glob(abs_path)) > self.FOLDER_LIMIT:
                    current_folder = current_folder + 1
                    relative_dir = "%s/%03d" % (relative_dir[:-4], current_folder)


            unzip = self.kwargs.get("unzip")
            zip_mode = self.kwargs.get("zip_mode")
            if zip_mode in ['unzip'] or unzip in ["true", True] and filename.endswith(".zip"):
                from pyasm.common import ZipUtil
                unzip_dir = Environment.get_upload_dir()

                if not os.path.exists(unzip_dir):
                    os.makedirs(unzip_dir)

                zip_path = "%s/%s" % (base_dir, filename)
                ZipUtil.extract(zip_path, base_dir=unzip_dir)

                paths = ZipUtil.get_file_paths(zip_path)

                new_kwargs = self.kwargs.copy()
                new_kwargs['filenames'] = paths
                new_kwargs['base_dir'] = unzip_dir
                new_kwargs['zip_mode'] = "single"
                ingest = IngestUploadCmd(**new_kwargs)
                ingest.execute()

                continue


            if self.sobject:
                sobject = self.sobject

            elif update_mode in ["true", True, "update"]:

                # first see if this sobjects still exists
                search = Search(search_type)
                # ingested files into search type applies filename without i.e. _v001 suffix
                search.add_filter(column, new_filename)

                # add job_code as a search filter
                job_code = extra_data.get("job_code")
                if job_code:
                    search.add_filter("job_code", job_code)

                if relative_dir and search.column_exists("relative_dir"):
                    if not dated_dirs:
                        search.add_filter("relative_dir", relative_dir)

                sobjects = search.get_sobjects()

                if len(sobjects) > 1:
                    sobject = None
                elif len(sobjects) == 1:
                    sobject = sobjects[0]
                    update_sobject_found = True
                else:
                    sobject = None

            elif update_mode == "sequence":
                # This check is not needed anymore as the sequence analyzer
                # can handle a mix of sequence and non sequences
                #if not FileGroup.is_sequence(filename):
                #    raise TacticException('Please modify sequence naming to have at least three digits [%s].' % filename)
                search = Search(search_type)
                search.add_filter(column, filename)

                if relative_dir and search.column_exists("relative_dir"):
                    if not dated_dirs:
                        search.add_filter("relative_dir", relative_dir)
                sobjects = search.get_sobjects()
                if sobjects:
                    sobject = sobjects[0]
                else:
                    sobject = None

            else:
                sobject = None


            # Create a new entry
            if not sobject:
                if update_mode not in ['true', True, "update"]:
                    sobjects = []


                sobject = SearchType.create(search_type)

                if ignore_ext in ['true', True]:
                    name, ext = os.path.splitext(new_filename)
                else:
                    name = new_filename

                # if the name contains a path, the only take basename
                name = os.path.basename(name)

                sobject.set_value(column, name)
                if relative_dir and sobject.column_exists("relative_dir"):
                    sobject.set_value("relative_dir", relative_dir)

            if mode == "search_key":
                path = lib_path

            elif relative_dir:
                path = "%s/%s" % (relative_dir, filename)
            else:
                path = filename

            # Handle update data
            # for some unknown reason, this input prefix is ignored
            new_data = {}
            for name, value in update_data.items():
                if name == "input_prefix":
                    continue

                name = name.replace("%s|"%input_prefix, "")
                new_data[name] = value

            if new_data:
                from tactic.ui.panel import EditCmd

                cmd = EditCmd(
                        view="edit",
                        sobject=sobject,
                        data=new_data,
                        commit="false",
                )
                cmd.execute()


            # Don't want the keywords being extracted from lib_path, extract the relative dir path instead
            # Using new_filename because it is the filename without version numbers
            if relative_dir:
                path_for_keywords = "%s/%s" % (relative_dir, new_filename)
            else:
                path_for_keywords = new_filename

            cmd_keyword_mode = self.kwargs.get("keyword_mode")

            if cmd_keyword_mode == "simplified":
                file_keywords = []
            else:
                file_keywords = Common.extract_keywords_from_path(path_for_keywords)

            # Extract keywords from the path to be added to keywords_data,
            # if ignore_path_keywords is found, remove the specified keywords
            # from the path keywords

            if ignore_path_keywords:
                for ignore_path_keyword in ignore_path_keywords:
                    if ignore_path_keyword in file_keywords:
                        file_keywords.remove(ignore_path_keyword)

            file_keywords.append(filename.lower())
            file_keywords = " ".join(file_keywords)


            new_file_keywords = ""

            # handle setting keywords to parent
            if SearchType.column_exists(search_type, "keywords"):

                old_keywords = sobject.get_value("keywords")

                if new_keywords:
                    new_file_keywords = "%s %s" % (new_keywords, file_keywords)
                else:
                    new_file_keywords = file_keywords

                if new_file_keywords:
                    new_file_keywords = "%s %s" % (old_keywords, new_file_keywords)

                # remove duplicated
                new_file_keywords = set( new_file_keywords.split(" ") )
                new_file_keywords = " ".join(new_file_keywords)

                if not cmd_keyword_mode == "none":
                    sobject.set_value("keywords", new_file_keywords)


            if SearchType.column_exists(search_type, "user_keywords"):
                if new_keywords:
                    if not cmd_keyword_mode == "none":
                        sobject.set_value("user_keywords", new_keywords)


            if SearchType.column_exists(search_type, "keywords_data"):
                data = sobject.get_json_value("keywords_data", {})
                data['user'] = new_keywords
                data['path'] = file_keywords
                sobject.set_json_value("keywords_data", data)



            # extract metadata
            #file_path = "%s/%s" % (base_dir, File.get_filesystem_name(filename))
            if update_mode == "sequence":
                sequence = sequences[count]
                file_path = "%s/%s" % (base_dir, sequence.get("filenames")[0])

            elif mode == "search_key":
                file_path = path
            else:
                file_path = "%s/%s" % (base_dir, filename)

            """
            # TEST: convert on upload
            try:
                convert = self.kwargs.get("convert")
                if convert:
                    message_key = "IngestConvert001"
                    cmd = ConvertCbk(**convert)
                    cmd.execute()
            except Exception as e:
                print("WARNING: ", e)
            """


            # check if the file exists
            if mode != "search_key" and not os.path.exists(file_path):
                raise Exception("Path [%s] does not exist" % file_path)

            # get the metadata from this image
            if SearchType.column_exists(search_type, "relative_dir"):
                if category and category not in ['none', None]:
                    from pyasm.checkin import ExifMetadataParser
                    parser = ExifMetadataParser(path=file_path)
                    tags = parser.get_metadata()

                    date = tags.get("EXIF DateTimeOriginal")
                    if not date:
                        date_str = "No-Date"
                    else:
                        date_str = str(date)
                        # this can't be parsed correctly by dateutils
                        parts = date_str.split(" ")
                        date_str = parts[0].replace(":", "-")
                        date_str = "%s %s" % (date_str, parts[1])

                        from dateutil import parser
                        orig_date = parser.parse(date_str)

                        if category == "by_day":
                            date_str = orig_date.strftime("%Y/%Y-%m-%d")
                        elif category == "by_month":
                            date_str = orig_date.strftime("%Y-%m")
                        elif category == "by_week":
                            date_str = orig_date.strftime("%Y/Week-%U")

                    full_relative_dir = "%s/%s" % (relative_dir, date_str)
                    sobject.set_value("relative_dir", full_relative_dir)

            # Add parent sObject
            if parent_key and parent_key != search_key:
                parent = Search.get_by_search_key(parent_key)
                if parent:
                    try:
                        sobject.set_sobject_value(parent)
                    except:
                        pass


            # Handle extra_data
            for key, value in extra_data.items():
                if SearchType.column_exists(search_type, key):
                    sobject.set_value(key, value, allow_none=True)


            """
            if category:

                if SearchType.column_exists(search_type, "category"):
                    sobject.set_value("category", category)


                if SearchType.column_exists(search_type, "relative_dir"):
                    full_relative_dir = "%s/%s" % (relative_dir, category)
                    sobject.set_value("relative_dir", category)
            """


            # commit sobject
            sobject.commit()
            search_key = sobject.get_search_key()





            # add to a collection if specified
            last_collection = collection
            parts = filename.split("/")
            for collection_name in parts[:-1]:
                collection_type = SearchType.get_collection_type(search_type)

                # find out if the subcollection already exits
                search = Search(search_type)
                search.add_filter("_is_collection", "true")
                search.add_filter("name", collection_name)

                if last_collection:
                    subsearch = Search(collection_type)
                    subsearch.add_column("search_code")
                    subsearch.add_filter("parent_code", last_collection.get_code() )
                    search.add_search_filter("code", subsearch)

                subcollection = search.get_sobject()

                # if this subcollection does not exist, create it
                if not subcollection:
                    subcollection = SearchType.create(search_type)
                    subcollection.set_value("_is_collection", "true")
                    subcollection.set_value("name", collection_name)
                    subcollection.set_value("status", "Verified")
                    subcollection.commit()

                    if last_collection:
                        subcollection.add_to_collection(last_collection)

                last_collection = subcollection

            # finally add to the last collection
            if last_collection:
                sobject.add_to_collection(last_collection)




            status = sobject.get_value("status", no_exception=True)
            is_verified = status in ['Verified', 'Complete']
            # for now, ignore the update when not verified
            is_verified = True


            create_icon = self.kwargs.get("create_icon")
            if create_icon in ['false', False]:
                create_icon = False
            else:
                create_icon = True


            # use API to check in file

            process = self.kwargs.get("process")
            if not process:
                process = "publish"


            context = self.kwargs.get("context")
            if not context:
                context = process

            if process == "icon":
                context = "icon"
            else:
                format_context = ProjectSetting.get_value_by_key("checkin/format_context", search_type=search_type)
                if format_context not in ['false', "False", False]:
                    if new_filename:
                        context = "%s/%s" % (context, new_filename)
                    else:
                        context = "%s/%s" % (context, filename)


            if context_mode == "case_insensitive":
                context = context.lower()


            version = None
            if not is_verified and update_process and update_sobject_found:
                process = update_process

                # find what the version number should be
                search = Search("sthpw/snapshot")
                search.add_parent_filter(sobject)
                search.add_filter("context", context)
                search.add_order_by("version desc")
                max_snapshot = search.get_sobject()
                version = max_snapshot.get_value("version")
                if not version:
                    version = 1
                else:
                    version += 1


            if update_mode == "sequence":

                file_range = sequence.get("range")
                if file_range == "":
                    raise Exception("Error: %s" % sequence.get("error"))

                if sequence.get("is_sequence"):
                    file_path = "%s/%s" % (base_dir, sequence.get("template"))
                    snapshot = server.group_checkin(search_key, context, file_path, file_range, mode='move', version=version)
                else:
                    file_path = "%s/%s" % (base_dir, sequence.get("filenames")[0])
                    snapshot = server.simple_checkin(search_key, context, file_path, mode='uploaded', version=version, create_icon=create_icon)

            elif mode == "search_key":

                if lib_path.find("##") != -1:
                    file_range = snapshot.get_file_range().get_display
                    file_path = lib_path
                    snapshot = server.group_checkin(search_key, context, file_path, file_range, mode='copy')
                else:
                    # copy the file to a temporary location
                    tmp_dir = Environment.get_tmp_dir()
                    tmp_path = "%s/%s" % (tmp_dir, new_filename)
                    shutil.copy(file_path, tmp_path)
                    # auto create icon
                    snapshot = server.simple_checkin(search_key, context, tmp_path, process=process, mode='move', create_icon=create_icon)

            elif self.kwargs.get("base_dir"):
                # auto create icon
                snapshot = server.simple_checkin(search_key, context, file_path, process=process, mode='move', version=version, create_icon=create_icon)

            else:
                snapshot = server.simple_checkin(search_key, context, filename, process=process, mode='uploaded', version=version, create_icon=create_icon)


            snapshots.append(snapshot)

            #server.update(snapshot, {"user_keywords": "abc 123"} )

            percent = int((float(count)+1) / len(filenames)*100)


            if self.message_key:
                msg = {
                    'progress': percent,
                    'description': 'Checking in file [%s]' % filename,
                }

                server.log_message(self.message_key, msg, status="in progress")


            if self.info.get("snapshots"):
                self.info["snapshots"].append(snapshot)
            else:
                self.info["snapshots"] = [snapshot]



        if self.message_key:
            msg = {
                'progress': '100',
                'description': 'Check-ins complete'
            }
            server.log_message(self.message_key, msg, status="complete")


        return


    def check_existing_file(self, search_type, new_filename, relative_dir, update_mode, sobjects):
        project_code = Project.get_project_code()
        file_search_type = SearchType.build_search_type(search_type, project_code)

        search_name, search_ext = os.path.splitext(new_filename)
        search_name = "%s.%%" % search_name

        search_file = Search("sthpw/file")
        search_file.add_filter("search_type", file_search_type)
        search_file.add_filter("relative_dir", relative_dir)
        search_file.add_filter("file_name", search_name, op='like')

        #print(search_file.get_statement())

        file_sobjects = search_file.get_sobjects()

        if file_sobjects and update_mode in ['true', True] and len(sobjects) > 1:
            raise TacticException('Multiple files with the same name as "%s" already exist. Uncertain as to which file to update. Please individually update each file.' % new_filename)
        elif file_sobjects:
            raise TacticException('A file with the same name as "%s" already exists in the file table with path "%s". Please rename the file and ingest again.' % (new_filename, relative_dir))

    def natural_sort(self,l):
        '''
        natural sort will makesure a list of names passed in is
        sorted in an order of 1000 to be after 999 instead of right after 101
        '''
        convert = lambda text: int(text) if text.isdigit() else text.lower()
        alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key) ]
        return sorted(l, key = alphanum_key)


    r"""
    def find_sequences(self, filenames):
        '''
        Parse a list of filenames into a dictionary of sequences.  Filenames not
        part of a sequence are returned in the None key

        :param      filenames | [<str>, ..]

        :return     {<str> sequence: [<str> filename, ..], ..}
        '''
        local_filenames   = filenames[:]
        sequence_patterns = {}
        sequences         = {None: []}

        # sort the files (by natural order) so we always generate a pattern
        # based on the first potential file in a sequence

        local_filenames = self.natural_sort(local_filenames)

        for filename in local_filenames:
            count = re.findall(r'\d+', filename)

            if not count:
                raise TacticException("Please ingest sequences only.")

            base, file_ext = os.path.splitext(filename)

            if file_ext:
                file_ext = file_ext[1:]

            # if last set of digits is not a file extension, and is less than 3 digits
            # because common.get_dir_info only works with 3 of more digits
            if len(count[-1]) <= 1 and file_ext.isalpha():
                raise TacticException('Please modify sequence naming to have at least three digits.')


            # if file extension found, and contains a number in the extension (but also not completely numbers)
            # grab the second last set of digits
            # ie. .mp3, .mp4, .23p

            if file_ext and not file_ext.isalpha() and not file_ext.isdigit():
                seq_digit_length = len(count[-2])
            else:
                seq_digit_length = len(count[-1])



            # if file_ext is empty, or if file_ext[1] is all numbers, use expression below
            # abc0001, abc.0001 ...etc
            if not file_ext or file_ext.isdigit():
                try:
                    pattern_expr = re.compile('^(.*)(\d{%d})([^\d]*)$'%seq_digit_length)
                except:
                    sequences[None].append(filename)
                    continue

            # then for regular filenames, try grabbing filenames by looking at the digits before the last dot
            # for files with extensions:
            # abc.0001.png, abc.0001.mp3, abc0001.mp3,
            else:
                try:
                    pattern_expr = re.compile('^(.*)(\d{%d})(\..*)$'%seq_digit_length)
                except:
                    sequences[None].append(filename)
                    continue


            pound_length = seq_digit_length
            pounds = "#" * pound_length

            # first, check to see if this filename matches a sequence
            found = False

            for key, pattern in sequence_patterns.items():
                match = pattern.match(filename)
                if not match:
                    continue

                sequences[key].append(filename)
                found = True
                break

            # if we've already been matched, then continue on
            if found:
                continue

            # next, see if this filename should start a new sequence
            basename = os.path.basename(filename)

            pattern_match = pattern_expr.match(basename)

            if pattern_match:
                opts = (pattern_match.group(1), pattern_match.group(3))
                key  = '%s%s%s' % (opts[0], pounds, opts[1])

                # create a new pattern based on the filename
                sequence_pattern = re.compile('^%s\d+%s$' % opts)

                sequence_patterns[key] = sequence_pattern
                sequences[key] = [filename]
                continue

            # otherwise, add it to the list of non-sequences
            sequences[None].append(filename)

        # now that we have grouped everything, we'll merge back filenames
        # that were potential sequences, but only contain a single file to the
        # non-sequential list
        for key, filenames in sequences.items():
            if ( key is None or len(filenames) > 1 ):
                continue

            sequences.pop(key)
            sequences[None] += filenames

        return sequences, seq_digit_length
    """
