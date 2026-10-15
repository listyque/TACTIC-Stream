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

__all__ = ["BaseRepo", "TacticRepo"]

import os, sys, re
from pathlib import Path

from pyasm.common import Environment
from pyasm.common.errors import UnsupportedContract
from pyasm.biz import File
from pyasm.search import FileUndo, Search
from .checkin import CheckinException

def _check_file_name(name):
    if not name or name in ('.', '..') or any(char in name for char in ('/', '\\', ':', '\0')):
        raise CheckinException('Invalid repository file name: %s' % name)

class BaseRepo(object):
    '''abstract class defining repositories'''

    def has_file_codes(self):
        return True

    def handle_system_commands(self, snapshot, files, file_objects, mode, md5s, source_paths=[], commit=False):
        raise NotImplementedError('Use the concrete TACTIC repository')




class TacticRepo(BaseRepo):

    def _revision_path(self, snapshot, path):
        # Handler revisions can retain the filename; replace only this owner's
        # existing version through FileUndo, never an unrelated path collision.
        if not snapshot.get_value('revision', no_exception=True) or snapshot.get_value('version') < 0:
            return False
        parent = snapshot.get_sobject()
        if parent is None:
            return False
        search = Search('sthpw/snapshot')
        search.add_parent_filter(parent)
        for field in ('context', 'process', 'version'):
            search.add_filter(field, snapshot.get_value(field))
        search.add_filter('code', snapshot.get_code(), op='!=')
        return any(Path(file.get_lib_path()).resolve() == Path(path).resolve()
                   for previous in search.get_sobjects() for file in previous.get_all_file_objects())

    def handle_system_commands(self, snapshot, files, file_objects, mode, md5s, source_paths=[], file_sizes=[], commit=False):
        '''move the tmp files in the appropriate directory'''
        if mode in (None, '', 'uploaded'):
            mode = 'create'
        if mode == 'local':
            return
        if mode not in ('inplace', 'preallocate', 'copy', 'move', 'create'):
            raise CheckinException('Unknown repository mode: %s' % mode)
        FileUndo._check_access()
        if len(files) != len(file_objects):
            raise ValueError('Each repository file requires its File object')
        if md5s and md5s != 'ignore' and len(md5s) != len(files):
            raise ValueError('Each repository file requires its checksum')
        if mode in ('copy', 'move') and len(source_paths) != len(files):
            raise ValueError('Each repository file requires its source path')
        if mode in ('copy', 'move', 'create'):
            for i, file in enumerate(file_objects):
                name = file.get_full_file_name()
                _check_file_name(name)
                source = source_paths[i] if mode in ('copy', 'move') else files[i]
                if not os.path.exists(source):
                    raise CheckinException('Source file not found: %s' % source)

        if mode == 'preallocate':
            for path in files:
                if not os.path.exists(path):
                    raise CheckinException('File not found in repo at [%s]' % path)

        if commit in ['false', False]:
            commit = False
        else:
            commit = True


        # inplace mode does not move the file.  It just registers the file
        # object
        if mode == 'inplace':
            for i, file in enumerate(files):
                file_object = file_objects[i]
                to_name = file_object.get_full_file_name()
                to_path = file

                # This is handled in create_file_types
                #file_type = snapshot.get_type_by_file_name(to_name)
                #file_object.set_value('type', file_type)


                if md5s != "ignore" and not os.path.isdir(to_path):
                    md5_checksum = None
                    if md5s:
                        md5_checksum = md5s[i]
                    if not md5_checksum:
                        md5_checksum = File.get_md5(to_path)

                    if md5_checksum:
                        file_object.set_value("md5", md5_checksum)

                if commit:
                    file_object.commit(triggers="none")
            return
            
   
        for i, file in enumerate(files):

            file_object = file_objects[i]
            to_name = file_object.get_full_file_name()
            file_type = snapshot.get_type_by_file_name(to_name)

            if mode == 'preallocate':
                to_path = file
            else:
                lib_dir = snapshot.get_lib_dir(file_type=file_type, file_object=file_object)
                # it should have been created in postprocess_snapshot
                FileUndo.mkdir(lib_dir)

                to_path = "%s/%s" % (lib_dir, to_name )


            #print "path: ", i, files[i]
            #print to_path, os.path.exists(to_path)

            # first make sure that the to path does not exist, if so, just skip
            if os.path.exists(to_path) and mode not in ['inplace','preallocate'] and not self._revision_path(snapshot, to_path):
                raise CheckinException('This path [%s] already exists'%to_path) 



            # add the file
            try:

                # inplace undo used to not touch the file, 
                # now it will be moved to cache on undo
                io_action = True
                if mode in ['preallocate']:
                    io_action = False

                
                if mode == 'move':
                    FileUndo.move( source_paths[i], to_path )
                #elif mode == 'copy': # was free_copy
                   
                    #FileUndo.create( source_paths[i], to_path, io_action=io_action )

                # make it look like the files was created in the repository
                else: # mode ='create'
                    
                    md5 = file_object.get_value("md5")
                    st_size = file_object.get_value("st_size")
                    rel_dir = file_object.get_value("relative_dir")
                    if mode == 'copy':
                        io_action = 'copy'
                        src_path = source_paths[i]
                    else:
                        src_path = files[i]

                    file_name = to_name
                    rel_path = "%s/%s" % (rel_dir, file_name)

                    FileUndo.create( src_path, to_path, io_action=io_action, extra={ "md5": md5, "st_size": st_size, "rel_path": rel_path } )


            except IOError as e:
                raise CheckinException('IO Error occurred. %s' %e.__str__())

            # check to see that the file exists.
            if not os.path.exists( to_path ):
                if mode in ["inplace", "preallocate"]:
                    raise CheckinException("File not found in repo at [%s]" % to_path )
                else:
                    raise CheckinException("Failed move [%s] to [%s]" % \
                (files[i], to_path) )

            file_object.set_value('type', file_type)
            if md5s != "ignore" and not os.path.isdir(to_path):
                md5_checksum = None
                if md5s:
                    md5_checksum = md5s[i]
                if not md5_checksum:
                    md5_checksum = File.get_md5(to_path)
                    #md5_checksum = ""

                if md5_checksum:
                    file_object.set_value("md5", md5_checksum)

            if commit:
                file_object.commit(triggers="none")
            



__all__.append("S3Repo")
class S3Repo(BaseRepo):
    '''This uploads the files to s3 directly'''

    def handle_system_commands(self, snapshot, files, file_objects, mode, md5s, source_paths=[], file_sizes=[], commit=False):

        raise UnsupportedContract('S3 repository is not migrated')
        try:
            import boto3
            from botocore.exceptions import ClientError
        except:
            raise("Python [boto3] module not installed")


        session = boto3.Session()
        s3_client = session.client('s3')
        s3_resource = session.client('s3')

        sobject = snapshot.get_parent()


        from pyasm.security import Site
        site = Site.get_site()
        project_code = sobject.get_project_code()

        #!!! TEST
        bucket = "tactic01"


        for i, file in enumerate(files):

            file_object = file_objects[i]
            to_name = file_object.get_full_file_name()
            file_type = snapshot.get_type_by_file_name(to_name)

            web_dir = snapshot.get_relative_dir(file_type=file_type, file_object=file_object)
            object_name = "%s/%s/%s" % (site, web_dir, to_name)
            print("objct: ", object_name)

            # push these files to s3
            try:
                s3_client.upload_file(source_paths[i], bucket, object_name)
            except ClientError as e:
                raise





