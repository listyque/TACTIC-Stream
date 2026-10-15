###########################################################
#
# Copyright (c) 2005, Southpaw Technology
#                     All Rights Reserved
#
# PROPRIETARY INFORMATION.  This software is proprietary to
# Southpaw Technology, and is not to be reproduced, transmitted,
# or disclosed in any way without written permission.
#
#
#

__all__ = ["FileUpload", "FileUploadException"]

import os

from pyasm.common import Base, Environment, TacticException
from pyasm.biz import IconCreator
from pyasm.search import FileUndo
import base64
import re
import shutil
import tempfile
from pathlib import Path
from pyasm.common.errors import SecurityException


def get_upload_path(file_name, ticket=None):
    """Resolve the authenticated UploadServer handoff, never another session's file."""
    from pyasm.checkin.repo import _check_file_name
    current = Environment.get_security().get_ticket_key()
    if ticket and ticket != current:
        raise SecurityException('Upload ticket must belong to the current session')
    file_name = os.path.basename(file_name.replace('\\', '/'))
    _check_file_name(file_name)
    root = Path(Environment.get_upload_dir(current)).resolve()
    path = root / file_name
    if not path.resolve().is_relative_to(root):
        raise SecurityException('Upload path must stay inside the ticket directory')
    if not path.is_file():
        raise FileUploadException('Uploaded Path [%s] does not exist' % path)
    return str(path)

 
class FileUploadException(TacticException):
    pass


class FileUpload(Base):
    '''utility class that handles a single file upload'''
    def __init__(self):
        self.field_storage = None
        self.file_name = None
        self.file_path = None
        self.file_dir = None

        # full paths to all of the files
        self.files = []

        self.file_types = []
        #self.tmp_dir = "%s/%s" % (Environment.get_tmp_dir(), "upload")
        self.tmp_dir = Environment.get_upload_dir()

        self.write_mode = "wb"
        self.create_icon = True
        self.default_type = 'main'
  
        self.base_decode = None

    def set_append_mode(self, flag):
        if flag:
            self.write_mode = "ab"
        else:
            self.write_mode = "wb"

    # DEPRECATED: use set_create_icon
    def set_create_icon_flag(self, flag):
        self.create_icon = flag

    def set_create_icon(self, flag):
        self.create_icon = flag


    def set_field_storage(self, field_storage, file_name=None):
        '''set the field storage taken from the web adapter'''
        self.field_storage = field_storage
        # if a particular file_name is given with the field_storage
        self.file_name = file_name

    def set_file_path(self, file_path):
        self.file_path = file_path

    def set_file_dir(self, file_dir):
        self.file_dir = file_dir

    def set_default_type(self, type):
        self.default_type = type

    def set_decode(self, decode):
        self.base_decode = decode
    
    def get_file_path(self):
        from pyasm.checkin.repo import _check_file_name
        if self.file_path:
            return self.file_path
        filename = self.file_name or self.field_storage.filename
        filename = os.path.basename(filename.replace("\\", "/"))
        _check_file_name(filename)
        return os.path.join(self.file_dir or self.tmp_dir, filename)



    def get_files(self):
        '''gets all of the resulting files'''
        return self.files

    def get_file_types(self):
        return self.file_types



    def execute(self):
        '''main function that does all the work based on the set
        parameters'''
        FileUndo._check_access()
        if self.field_storage is None and not self.file_path:
            raise FileUploadException("Field storage is None")


        if self.field_storage is not None:
            self._dump_file_to_temp()
        else:
            # Additive handoff for files already staged by the existing UploadServer.
            path = get_upload_path(self.file_path)
            if Path(self.file_path).resolve() != Path(path).resolve():
                raise SecurityException('Staged file must belong to the current upload directory')
            self.file_path = path

        file_path = self.get_file_path()

        if not file_path:
            return

        self._add_file(self.default_type, file_path)

        # create icons
        if self.create_icon:
            icon_creator = IconCreator(file_path)
            icon_creator.create_icons()

            web_path = icon_creator.get_web_path()
            icon_path = icon_creator.get_icon_path()

            if web_path:
                self._add_file("web", web_path)

            if icon_path:
                self._add_file("icon", icon_path)



    def _add_file(self, type, file_path):
        self.file_types.append( type )
        self.files.append( file_path )



    def _dump_file_to_temp(self):

        FileUndo._check_access()
        destination = self.get_file_path()
        if self.write_mode == 'ab' and not os.path.isfile(destination):
            raise FileUploadException('Append requires an existing uploaded file')
        data = self.field_storage.file
        payload = data.read()
        encoded = re.match(br'^data:[\w_-]+/[\w_-]+;base64,', payload[:100])
        if self.base_decode or encoded:
            if not encoded:
                raise FileUploadException('Invalid Base64 upload header')
            payload = base64.b64decode(payload[encoded.end():].strip(), validate=True)
        staged = None
        try:
            with tempfile.NamedTemporaryFile(dir=Environment.get_tmp_dir(), delete=False) as file:
                staged = file.name
                # ponytail: chunk append copies the previous file for journal rollback; use a resumable
                # protocol with explicit byte offsets if huge-file uploads make this too costly.
                if self.write_mode == 'ab':
                    with open(destination, 'rb') as previous:
                        shutil.copyfileobj(previous, file)
                file.write(payload)
            FileUndo.create(staged, destination)
        finally:
            if staged and os.path.exists(staged):
                os.unlink(staged)
