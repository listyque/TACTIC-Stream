# Copyright (c) 2005, Southpaw Technology. MIT; see LICENSE.TACTIC.
"""Original field actions, independent of the HTML renderer."""
__all__ = ['DatabaseAction', 'DefaultValueDatabaseAction', 'MultiDatabaseAction',
           'NonEmptyAction', 'RegexAction', 'NullAction', 'UniqueValueAction', 'XmlAction']
import os
import re
import zipfile
from pathlib import Path
from pyasm.biz import IconCreator
from pyasm.search import FileUndo
from .file_upload import FileUpload
import six
from pyasm.common import Common, Environment, UserException, TimeCode, Xml, TacticException
from pyasm.biz import PrefSetting
from pyasm.search import Search, SearchType
from .command import Command
from .trigger import Trigger
from pyasm.common.errors import SecurityException


def get_web_container():
    from pyasm.web import WebContainer
    return WebContainer.get_web()


class DatabaseAction(Command):
    """takes the value and adds it to the current sobject.  It does
    not commit to the database"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sobject = None
        self.name = None
        self.input_prefix = None
        self.value = None
        self.commit_flag = False
        self.options = {}
        self.data = None

    def set_data(self, data):
        self.data = data

    def get_data(self):
        return self.data

    def check(self):
        self.web = get_web_container()
        value = self.get_value(self.name)
        no_action = self.get_option('save') == 'false'
        if no_action:
            return False
        no_empty = self.get_option('empty') == 'false'
        if no_empty:
            if value == '':
                name = self._get_name()
                raise UserException('The input for [%s] cannot be empty' % name.capitalize())
        regexm = self.get_option('regexm')
        regexs = self.get_option('regexs')
        if regexm and value:
            m = re.match('%s' % regexm, value)
            if not m:
                name = self._get_name()
                raise UserException('The input for [%s] is invalid for expression [%s]' % (name.capitalize(), regexm))
        if regexs and value:
            m = re.search('%s' % regexs, value)
            if m:
                name = self._get_name()
                raise UserException('The input for [%s] contains invalid characters [%s]' % (name.capitalize(), regexs))
        if not value:
            default = self.get_option('default_col')
            if default:
                column_value = self.get_value(default)
                if column_value:
                    self.value = column_value
        return True

    def _get_name(self):
        name = self.get_input_name()
        if '|' in name:
            name = name.split('|', 1)[1]
        return name

    def set_name(self, name):
        self.name = name

    def has_option(self, key):
        return key in self.options

    def set_option(self, key, value):
        self.options[key] = value

    def get_option(self, key):
        """gets the value of the specified option"""
        if key in self.options:
            return self.options[key]
        else:
            return ''

    def get_options(self):
        return self.options

    def set_commit_flag(self, flag):
        """determines whether a commit is made by the action or it
        is done externally to the action"""
        if flag == True or flag == 'True':
            self.commit_flag = True
        else:
            self.commit_flag = False

    def commit(self):
        """does nothing"""
        pass

    def rollback(self):
        """does nothing"""
        pass

    def set_input_prefix(self, input_prefix):
        self.input_prefix = input_prefix

    def get_name(self):
        return self.name

    def get_input_name(self):
        if self.input_prefix:
            return '%s|%s' % (self.input_prefix, self.name)
        else:
            return self.name

    def set_sobject(self, sobject):
        self.sobject = sobject

    def get_values(self, name=None):
        if self.value:
            return [self.value]
        if not name:
            name = self.name
        if self.input_prefix:
            input_name = '%s|%s' % (self.input_prefix, name)
        else:
            input_name = name
        if self.data != None:
            self.values = [self.data]
        else:
            web = get_web_container()
            self.values = web.get_form_values(input_name)
        return self.values

    def get_value(self, name=None):
        if self.value:
            return self.value
        values = self.get_values(name)
        if isinstance(values, list):
            if values:
                return values[0]
            else:
                return ''
        elif values:
            return values
        else:
            return ''

    def set_value(self, value):
        self.value = value

    def execute(self):
        column = self.get_option('column')
        if not column:
            column = self.name
        value = self.get_value(self.name)
        expr = self.get_option('expression')
        parent_key_action = self.get_option('parent_key') == 'true'
        if expr:
            vars = {'VALUE': value}
            Search.eval(expr, self.sobject, vars=vars)
        else:
            search_type = self.sobject.get_search_type()
            col_type = SearchType.get_tactic_type(search_type, column)
            value = self.convert_value(col_type, value)
            if value == None:
                pass
            elif parent_key_action:
                self.sobject.add_relationship(value)
            else:
                self.sobject.set_value(column, value)
            if self.commit_flag == True:
                self.sobject.commit()
        '\n        if self.data:\n\n            for s_key, item_data in self.data.items():\n                s = Search.get_by_search_key(s_key)\n                if not s:\n                    continue\n\n                for name, value in item_data.items():\n                    s.set_value(name, value)\n                s.commit()\n        '

    def post_execute(self):
        return

    def convert_value(self, col_type, value):
        if col_type == 'timecode':
            timecode = TimeCode(timecode=value)
            value = timecode.get_frames()
        elif col_type in ['time', 'timestamp']:
            from pyasm.common import SPTDate
            if not value:
                value = ''
            elif not SPTDate.has_timezone(value):
                timezone = PrefSetting.get_value_by_key('timezone')
                if timezone:
                    value = SPTDate.add_timezone(value, timezone)
                else:
                    value = SPTDate.add_local_timezone(value)
        elif col_type in ['float', 'integer']:
            if isinstance(value, six.string_types):
                value = value.replace(',', '')
                if value.startswith('$'):
                    value = value.lstrip('$')
            try:
                if value is None or value == '':
                    value = None
                elif col_type == 'float':
                    value = float(value)
                else:
                    value = int(value)
            except:
                raise UserException('[%s] must a number.' % value)
        return value


class DefaultValueDatabaseAction(DatabaseAction):
    """This element is executed on every element execution"""

    def execute(self):
        default_values = {'login_id': Environment.get_login().get_id(), 'login': Environment.get_login().get_value('login')}
        for column, value in default_values.items():
            cur_value = self.sobject.get_value(column, value)
            if not cur_value:
                self.sobject.set_value(column, value)


class MultiDatabaseAction(DatabaseAction):
    """Stores the value in the database as a || separated list.  There
    is also a || at the beginning and end so that the full string can
    be searched up."""

    def execute(self):
        values = self.data if isinstance(self.data, list) else self.get_values()
        new_values = [i for i in values if i]
        new_values.sort()
        value_string = '||'.join(new_values)
        if value_string and '||' in value_string:
            value_string = '||%s||' % value_string
        self.sobject.set_value(self.name, value_string)
        if self.commit_flag == True:
            self.sobject.commit()


class NonEmptyAction(DatabaseAction):
    """ Make sure the value is not empty """

    def check(self):
        self.web = get_web_container()
        value = self.get_value()
        if not value:
            name = self.get_input_name()
            if '|' in name:
                name = name.split('|')[1]
            raise UserException('[%s] cannot be empty.' % name.capitalize())
        return True


class RegexAction(DatabaseAction):
    """ Make sure the value matches the given expression defined in the option <regex> """

    def check(self):
        self.web = get_web_container()
        value = self.get_value()
        regex = self.get_option('regex')
        if value and regex:
            name = self.get_input_name()
            if '|' in name:
                name = name.split('|', 1)[1]
            m = re.match('%s' % regex, value)
            if not m:
                raise UserException('The input for [%s] is invalid for expression [%s]' % (name.capitalize(), regex))
        return True


class NullAction(DatabaseAction):

    def execute(self):
        pass


class UniqueValueAction(DatabaseAction):
    """ Ensure the value entered does not violate the Unique Constraint for a column """

    def check(self):
        self.web = get_web_container()
        name = self.get_value()
        search_type = self.sobject.get_search_type()
        column = self.get_name()
        search = Search(search_type)
        search.add_filter(column, name)
        if not self.sobject.is_insert():
            search.add_filter(self.sobject.get_id_col(), self.sobject.get_id(), op='!=')
        sobject = search.get_sobject()
        if sobject:
            raise UserException('%s [%s] has been taken!' % (column.capitalize(), name))
        super(UniqueValueAction, self).check()
        return True


class XmlAction(DatabaseAction):
    """simple class to update the task dependencies"""

    def check(self):
        value = self.get_value()
        try:
            from pyasm.common import Xml, XmlException
            Xml(string=value)
        except XmlException as e:
            error = e.__str__()
            raise TacticException('Invalid XML: %s' % error)
        return True


class UploadAction(DatabaseAction):
    """action which saves a file to the tmp directory and processes
    it according to its file type"""
    def __init__(self):
        self.checkin = None
        super(UploadAction, self).__init__()

    def get_title(self):
        return "Upload"

    def set_value(self, value):
        self.value = value

    def execute(self):
        '''Do nothing'''
        pass


    def postprocess(self):
        web = get_web_container()

        keys = web.get_form_keys()

        from pyasm.search import Transaction
        transaction = Transaction.get()
        assert transaction

        # first get some data based in
        column = self.get_value("%s|column" % self.name)
        if column == "":
            column = self.name

        # NOTE: why did this change?
        #prefix = self.get_input_name()
        prefix = self.get_name()


        context = self.get_value("%s|context" % prefix)
        subcontext = self.get_value('%s|subcontext' % prefix)
        if subcontext:
            if not context:
                raise UserException('A context should be filled in first before entering a subcontext.')
            context = '%s/%s' % (context, subcontext)
        description = self.get_value("%s|description" % prefix)

        field_storage = self.get_value(prefix)
        handoff_path = self.get_value("%s|path" % prefix )
        custom_ticket = self.get_value("%s|ticket" % prefix )

        # Source CheckboxWdg.is_checked ignores submitted values and the input prefix.
        is_rev = self.get_value("%s|is_revision" % prefix) in (True, 1, '1', 'on', 'true')

        if handoff_path:
            from .file_upload import get_upload_path
            handoff_path = get_upload_path(handoff_path, custom_ticket)

            self.files = [handoff_path]
            file_types = ['main']

            # create an icon
            icon_creator = IconCreator(handoff_path)
            icon_creator.execute()
            icon_path = icon_creator.get_web_path()
            if icon_path:
                self.files.append(icon_path)
                file_types.append("web")

            web_path = icon_creator.get_icon_path()
            if web_path:
                self.files.append(web_path)
                file_types.append("icon")


        elif field_storage != "":

            # process and get the uploaded files
            upload = FileUpload()
            upload.set_field_storage(field_storage)
            upload.execute()

            # get files and file types
            self.files = upload.get_files()
            if not self.files:
                return
            file_types = upload.get_file_types()
        else:
            if self.get_option("file_required") == "true":
                err_msg = "upload is required"
                raise TacticException("%s %s" % (self.name, err_msg))
            else:
                return


        checkin_class = self.get_option("checkin")
        if checkin_class:
            snapshot_type = self.get_option("snapshot_type")
            from tactic.command.python_cmd import check_script_execution
            from pyasm.checkin import BaseCheckin
            check_script_execution()
            handler = Common.resolve_class(checkin_class)
            if not isinstance(handler, type) or not issubclass(handler, BaseCheckin):
                raise TypeError("Check-in class must derive from BaseCheckin")
            self.checkin = handler(self.sobject, self.files, file_types, context, snapshot_type)

        else:

            from pyasm.checkin import FileCheckin
            self.checkin = FileCheckin.get( self.sobject, self.files, file_types,
                context=context, column=column, snapshot_type="file", mode="uploaded" )

        self.sobjects.append(self.sobject)

        self.checkin.set_description(description)
        self.checkin.set_revision(is_rev)
        self.checkin.execute()

        # remove the files in upload area
        for file in self.files:
            if os.path.exists(file):
                FileUndo.remove(file)

class DateAction(DatabaseAction):
    '''special action class to handle dates'''

    def execute(self):
        value = self.get_value()
        if value == "now":
            from datetime import datetime
            date = datetime.now()
            value = str(date)
            self.set_value(value)



        super(DateAction, self).execute()

class TimeAction(DatabaseAction):
    '''special action class to handle dates'''

    def execute(self):
        column = self.get_option("column")

        name = self.get_name()
        hour_name = "%s|hour" % name
        min_name = "%s|minute" % name

        hour_value = int(self.get_value(hour_name))
        min_value = int(self.get_value(min_name))


        from dateutil import parser
        from datetime import datetime

        sobject = self.sobject
        date_value = sobject.get_value(column)
        if not date_value:
            date = datetime.now()
        else:
            date = parser.parse(date_value)

        date = datetime(date.year, date.month, date.day, hour_value, min_value)
        self.set_value(date)

        super(TimeAction, self).execute()

class TaskDateAction(DatabaseAction):
    '''simple class to update the task dependencies'''

    def postprocess(self):
        # The original action disables dependent-task updates here.
        return

class InitialTaskCreateAction(DatabaseAction):
    '''simple class to update the task dependencies'''

    def execute(self):
        # do nothing
        pass

    def postprocess(self):
        value = self.get_value()
        if not value:
            return

        from pyasm.biz import Task
        Task.add_initial_tasks(self.sobject)

__all__ += ['UploadAction', 'DateAction', 'TimeAction', 'TaskDateAction', 'InitialTaskCreateAction']


class MultiUploadAction(DatabaseAction):

    def set_value(self, value):
        self.value = value


    def execute(self):
        '''do nothing'''
        pass

    def postprocess(self):
        self.files = []
        self.file_types = []
        if self.get_option('upload_type') == 'arbitrary':
            self._upload_arbitrary_files()
        else:
            self._upload_specified_files()

        context = self.get_value("%s|context" % self.name)
        subcontext = self.get_value("%s|subcontext" % self.name)
        if subcontext:
            context = '%s/%s' %(context, subcontext)
        description = self.get_value("%s|description" % self.name)
        is_rev = self.get_value('%s|is_revision' % self.name) in (True, 1, '1', 'on', 'true')
        if not self.files:
            raise UserException('You need to browse for a valid main file.')

        # let checkin take care of moving files to the lib
        from pyasm.checkin import FileCheckin
        self.checkin = FileCheckin.get( self.sobject, self.files, self.file_types,  \
            context=context, snapshot_type="file" )
        self.checkin.set_description(description)
        self.checkin.set_revision(is_rev)
        self.checkin.execute()


        self.sobjects.append(self.sobject)
        self.info['context'] = context
        self.add_description('File Publish for [%s]' %self.sobject.get_code())
        # remove the files in upload area
        for file in self.files:
            if os.path.exists(file):
                FileUndo.remove(file)

        Trigger.call(self, "email")

    def _upload_arbitrary_files(self):
        ''' upload an arbitrary list of files'''
        web = get_web_container()
        pattern = re.compile(re.escape(self.get_input_name()) + r'\d*')
        names = []
        for key in web.get_form_keys():
            candidate = key[:-5] if key.endswith('|path') else key
            if pattern.fullmatch(candidate) and candidate not in names:
                names.append(candidate)
        uploads = [self._get_upload(name, prefixed=True) for name in names]
        self._check_upload_names(uploads)
        for upload in uploads:
            if upload is None:
                continue
            create_icon = False
            file_path = upload.get_file_path()
            root, ext = os.path.splitext(file_path)
            if ext.lower() in ['.tif', '.jpg', '.png']:
                create_icon = True
            if not ext:
                raise TacticException('file path with extension expected [%s]'\
                        %file_path)

            upload.set_default_type(ext)
            upload.set_create_icon_flag(create_icon)

            upload.execute()
            files = upload.get_files()

            if not files:
                continue


            self.files.extend(files)
            file_types = upload.get_file_types()
            self.file_types.extend(file_types)


    def _upload_specified_files(self):
        ''' upload predefined file types specified in the conf.xml file'''
        upload_names = self._get_option('names')

        # check for uniqueness in upload_names
        if len(set(upload_names)) != len(upload_names):
            raise TacticException('[names] in the config file must be unique')

        upload_types = self._get_option('types')

        if len(upload_names) != len(upload_types):
            raise TacticException('[names] and [types] must have the same length')

        uploads = [self._get_upload(name) for name in upload_names]
        self._check_upload_names(uploads)
        field_storage_dict = {}
        valid_upload_names = []
        valid_upload_types = []
        for name, upload_type, upload in zip(upload_names, upload_types, uploads):
            if upload is None:
                continue
            field_storage_dict[name] = upload
            valid_upload_names.append(name)
            valid_upload_types.append(upload_type)

        # process and get the uploaded files
        icon_created = False
        has_icon = "icon_main" in valid_upload_types

        # if no files or only icon_main is supplied, raise Exception
        if not valid_upload_types or valid_upload_types==['icon_main']:
            raise UserException('You need to browse for a valid main file.')

        for idx, name  in enumerate(valid_upload_names):
            upload_type = valid_upload_types[idx]
            create_icon = upload_type == 'icon_main'
            upload = field_storage_dict[name]
            upload.set_default_type(upload_type)

            # this ensures icon_main takes precedence for icon creation
            if icon_created or (has_icon and not create_icon):
                upload.set_create_icon_flag(False)


            upload.execute()
            files = upload.get_files()
            if not files:
                continue

            if create_icon and len(files) == 1:
                raise UserException('The uploaded icon file must be an image file. e.g. tif, png, jpg.')
            self.files.extend(files)
            file_types = upload.get_file_types()
            if len(file_types) > 1:
                icon_created = True
            self.file_types.extend(file_types)



    def _get_option(self, attr):
        ''' get option delimited by | '''
        upload_names = self.get_option(attr)
        if not upload_names:
            upload_names = [self.name]
        else:
            upload_names = upload_names.split('|')

        return upload_names

    def _get_upload(self, name, prefixed=False):
        from .file_upload import get_upload_path
        web = get_web_container()
        input_name = name if prefixed or not self.input_prefix else '%s|%s' % (self.input_prefix, name)
        field_storage = web.get_form_value(input_name) if prefixed else self.get_value(name)
        handoff = web.get_form_value(input_name + '|path')
        upload = FileUpload()
        if handoff:
            upload.set_file_path(get_upload_path(handoff, web.get_form_value(input_name + '|ticket')))
        elif field_storage not in ('', None) and field_storage.filename:
            upload.set_field_storage(field_storage)
        else:
            return None
        return upload

    def _check_upload_names(self, uploads):
        names = [os.path.basename(upload.get_file_path()).casefold() for upload in uploads if upload is not None]
        if len(names) != len(set(names)):
            raise UserException('Choose different file names for separate upload fields.')


__all__.append("MultiUploadAction")


class MultiZipUploadAction(MultiUploadAction):

    def check(self):
        self.naming = None
        self.sobject_dict = {}
        self._sobjects_by_key = {}
        self._extraction_dirs = []
        naming = self.get_option('naming')
        if naming:
            from tactic.command.python_cmd import check_script_execution
            check_script_execution()
            self.naming = Common.resolve_class(naming)()
            if not callable(getattr(self.naming, 'get_sobject_by_filename', None)):
                raise TacticException('Naming must implement get_sobject_by_filename')
        else:
            raise TacticException('A naming has to be specified in the action option')
        return True

    def postprocess(self):
        self.files = []
        self.file_types = []

        self._upload_zipped_files()
        if not self.sobject_dict:
            raise UserException('You need to browse for a valid main file.')

        context = self.get_value("%s|context" % self.name)
        subcontext = self.get_value('%s|subcontext' % self.name)
        if subcontext:
            context = '%s/%s' % (context, subcontext)
        description = self.get_value("%s|description" % self.name)
        is_revision = self.get_value('%s|is_revision' % self.name) in (True, 1, '1', 'on', 'true')

        # let checkin take care of moving files to the lib
        from pyasm.checkin import FileCheckin
        for sobject in self.sobject_dict.keys():
            files, file_types = self.sobject_dict.get(sobject)
            self.checkin = FileCheckin.get( sobject, files, file_types,  \
                context=context, snapshot_type="file" )
            self.checkin.set_description(description)
            self.checkin.set_revision(is_revision)
            self.checkin.execute()



        # remove the files in upload area
        for key in self.sobject_dict.keys():
            files, file_types = self.sobject_dict.get(key)
            for file in files:
                if os.path.exists(file):
                    FileUndo.remove(file)
        for directory in self._extraction_dirs:
            for path in sorted(Path(directory).rglob('*'), key=lambda path: len(path.parts), reverse=True):
                if path.is_dir():
                    FileUndo.rmdir(str(path))
            FileUndo.rmdir(directory)

    def _upload_zipped_files(self):
        ''' upload an arbitrary list of files'''
        web = get_web_container()
        pattern = re.compile(re.escape(self.get_input_name()) + r'\d*')
        names = dict.fromkeys(key[:-5] if key.endswith('|path') else key for key in web.get_form_keys()
                             if pattern.fullmatch(key[:-5] if key.endswith('|path') else key))
        uploads = [self._get_upload(name, prefixed=True) for name in names]
        self._check_upload_names(uploads)
        basenames = set()
        for upload in uploads:
            if upload is None:
                continue
            file_path = upload.get_file_path()
            _, ext = os.path.splitext(file_path)
            upload.set_default_type(ext)
            upload.set_create_icon_flag(self._create_icon(file_path))
            upload.execute()
            if zipfile.is_zipfile(file_path):
                # One private directory per archive prevents collisions with staged uploads.
                directory = os.path.join(Environment.get_upload_dir(), 'unzip_' + Common.generate_random_key())
                files = Common.unzip_file(file_path, directory)
                self._extraction_dirs.append(directory)
                for path in files:
                    name = os.path.basename(path).casefold()
                    if name in basenames:
                        raise UserException('Duplicate ZIP file name: ' + os.path.basename(path))
                    basenames.add(name)
                    self._process_file(None, path)
                FileUndo.remove(file_path)
            else:
                name = os.path.basename(file_path).casefold()
                if name in basenames:
                    raise UserException('Duplicate ZIP file name: ' + os.path.basename(file_path))
                basenames.add(name)
                self._process_file(upload, file_path)

    def _create_icon(self, file_path):
        '''return True if an icon can be created out of it'''
        name, ext = os.path.splitext(file_path)

        create_icon = False
        if ext.lower() in ['.tif', '.jpg', '.png']:
            create_icon = True
        if not ext:
            raise TacticException('file path with extension expected [%s]'\
                %file_path)

        return create_icon



    def _process_file(self, upload, file_path):
        ''' sort the files, file_types to the corresponding sobject'''
        files = []
        file_types = []
        if not file_path:
            raise TacticException('Empty file path encountered')

        if upload:
            files = upload.get_files()
            file_types = upload.get_file_types()
            if not files or not file_types:
                return

        else:
            name, ext = os.path.splitext(file_path)
            files.append(file_path)
            file_types.append(ext)

            if self._create_icon(file_path):
                icon_creator = IconCreator(file_path)
                icon_creator.create_icons()

                web_path = icon_creator.get_web_path()
                icon_path = icon_creator.get_icon_path()

                if web_path:
                    file_types.append("web")
                    files.append(web_path)

                if icon_path:
                    file_types.append("icon")
                    files.append(icon_path)

        head, file_name = os.path.split(file_path)


        sobject = self.naming.get_sobject_by_filename(file_name)
        if sobject:
            from pyasm.biz import Project
            if sobject.get_project_code() != Project.get_project_code():
                raise SecurityException('ZIP naming resolved an object in another project')
            sobject = self._sobjects_by_key.setdefault(sobject.get_search_key(), sobject)
            if self.sobject_dict.get(sobject):
                orig_files, orig_file_types = self.sobject_dict.get(sobject)
                files.extend(orig_files)
                file_types.extend(orig_file_types)
            self.sobject_dict[sobject] = (files, file_types)
            self.add_description("Published [%s] for [%s] " %(file_name, sobject.get_code()))
        else:
            raise UserException('Unrecognized uploaded file name [%s]' %file_name)

__all__.append("MultiZipUploadAction")
