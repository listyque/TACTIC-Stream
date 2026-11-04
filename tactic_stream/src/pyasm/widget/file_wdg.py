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

"""Native TACTIC thumbnail selection and file paths; no HTML runtime."""
import re
from urllib.parse import quote, urlsplit, urlunsplit
from pyasm.common import Xml, Environment
from pyasm.search import Search, SearchException, SearchKey, SqlException
from pyasm.biz import Snapshot, File, ExpressionParser, PrefSetting, ProjectSetting
from pyasm.biz.snapshot import SObjectNotFoundException
from .table_element_wdg import BaseTableElementWdg

basestring = str


class ThumbWdg(BaseTableElementWdg):
    DEFAULT_CONTEXT = DEFAULT_PROCESS = 'publish'
    ICON_SIZE = 120
    SQL_ERROR = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.init()
        if kwargs.get('name'):
            self.name = kwargs['name']

    def set_sobjects(self, sobjects, search=None):
        super().set_sobjects(sobjects, search)
        self.data = {}; self.file_objects = {}; self.info = {}
        self.is_preprocess_run = False

    ARGS_KEYS = {'script_path': {'description': 'Javascript path override for action when preview is clicked',
                     'type': 'TextWdg',
                     'order': 1,
                     'category': 'Action'},
     'detail_class_name': {'description': 'Python widget to display in a new tab when preview is '
                                          'clicked',
                           'type': 'TextWdg',
                           'order': 2,
                           'category': 'Action'},
     'icon_context': {'description': 'context on which the search is applied',
                      'type': 'TextWdg',
                      'order': 1,
                      'category': 'Display'},
     'icon_size': {'description': 'control the icon size by percentage. e.g. 80%',
                   'type': 'TextWdg',
                   'order': 2,
                   'category': 'Display'},
     'min_icon_size': {'description': 'The smallest size the icon will become on resize',
                       'type': 'TextWdg',
                       'order': 3,
                       'category': 'Display'},
     'cascade_search': {'description': 'determines whether to keep looking for any image to use as an '
                                       'icon',
                        'type': 'SelectWdg',
                        'values': 'true|false',
                        'category': 'Display'},
     'filename': {'description': 'whether to display the main file name for download',
                  'type': 'SelectWdg',
                  'order': 5,
                  'category': 'Display',
                  'values': 'true|false'},
     'latest_icon': {'description': 'whether to display the latest version under any context',
                     'type': 'SelectWdg',
                     'order': 4,
                     'category': 'Display',
                     'values': 'true|false'},
     'original': {'description': 'whether to display the original file when clicked on',
                  'type': 'SelectWdg',
                  'order': 6,
                  'category': 'Display',
                  'values': 'true|false'},
     'file_type': {'description': 'whether to display the file type for download',
                   'type': 'SelectWdg',
                   'order': 7,
                   'category': 'Display',
                   'values': 'true|false'},
     'detail': {'description': 'whether to display the single asset view when clicked on',
                'type': 'SelectWdg',
                'order': 8,
                'category': 'Display',
                'values': 'true|false'},
     'protocol': {'description': 'whether to open the link over http or file system',
                  'type': 'SelectWdg',
                  'order': 9,
                  'category': 'Display',
                  'values': 'http|file'},
     'search_key': {'description': 'search_key of sobject to use for displaying icon',
                    'type': 'TextWdg',
                    'order': 0,
                    'category': 'Search'},
     'redirect_expr': {'description': 'expression to control another image related to this sobject. '
                                      'This is slower in performance. e.g. @SOBJECT(project/entity)',
                       'type': 'TextWdg',
                       'order': 1,
                       'category': 'Search'}}

    def init(self):
        self.icon_size = None
        self.show_filename_flag = False
        self.show_clipboard_flag = True
        self.show_orig_icon = False
        self.show_file_type = False
        self.show_versionless = False
        self.show_latest_icon = False
        self.has_img_link = True
        self.context = None
        self.version = None
        self.name = 'snapshot'
        self.data = {}
        self.file_objects = {}
        self.info = {}
        self.image_link_order = []
        self.is_preprocess_run = False
        self.icon_type = 'default'
        self.aspect = 'width'

    def preprocess(self):
        self.is_preprocess_run = True
        object_count = len({SearchKey.get_by_sobject(obj) for obj in self.sobjects if obj})
        if self.get_option('filename') == 'true':
            self.show_filename_flag = True
        if self.get_option('file_type') == 'true':
            self.show_file_type = True
        if self.get_option('original') == 'true':
            self.show_orig_icon = True
        if self.get_option('versionless') == 'true':
            self.show_versionless = True
        if self.get_option('latest_icon') == 'true':
            self.show_latest_icon = True
        context = self.get_option('icon_context')
        if not context and self.sobjects:
            sobject = self.sobjects[0]
            assert sobject
            if sobject:
                context = sobject.get_icon_context(self.context)
        if context:
            self.context = context
        if not self.image_link_order:
            order = self.get_option('image_link_order')
            if order:
                order = order.split('|')
            self.set_image_link_order(order)
        redirect = self.get_option('redirect')
        redirect_expr = self.get_option('redirect_expr')
        if not redirect and (not redirect_expr) and self.sobjects:
            if not self.sobjects[0]:
                return
            snapshots = []
            if isinstance(self.sobjects[0], Snapshot):
                snapshots = self.sobjects
            else:
                if self.show_latest_icon:
                    icon_context = None
                else:
                    icon_context = self.sobjects[0].get_icon_context(self.context)
                cascade_search = self.get_option('cascade_search') or 'true'
                try:
                    if self.version == None:
                        self.data = Snapshot.get_by_sobjects(self.sobjects, icon_context, is_latest=True, return_dict=True)
                        if cascade_search != 'false':
                            if len(self.data) < object_count:
                                publish_data = Snapshot.get_by_sobjects(self.sobjects, self.DEFAULT_CONTEXT, is_latest=True, return_dict=True)
                                self._update_data(publish_data)
                            if len(self.data) < object_count:
                                publish_data = Snapshot.get_by_sobjects(self.sobjects, process=self.DEFAULT_PROCESS, is_latest=True, return_dict=True)
                                self._update_data(publish_data)
                            if len(self.data) < object_count:
                                publish_data = Snapshot.get_by_sobjects(self.sobjects, is_latest=True, return_dict=True)
                                self._update_data(publish_data)
                    else:
                        self.data = Snapshot.get_by_sobjects(self.sobjects, icon_context, version=self.version, return_dict=True)
                        if cascade_search != 'false':
                            if len(self.data) < object_count:
                                publish_data = Snapshot.get_by_sobjects(self.sobjects, self.DEFAULT_CONTEXT, version=self.version, return_dict=True)
                                self._update_data(publish_data)
                            if len(self.data) < object_count:
                                publish_data = Snapshot.get_by_sobjects(self.sobjects, process=self.DEFAULT_PROCESS, version=self.version, return_dict=True)
                                self._update_data(publish_data)
                            if len(self.data) < object_count:
                                publish_data = Snapshot.get_by_sobjects(self.sobjects, version=self.version, return_dict=True)
                                self._update_data(publish_data)
                except SqlException:
                    raise
                snapshots = self.data.values()
            file_objects = File.get_by_snapshots(snapshots)
            for file_object in file_objects:
                file_code = file_object.get_code()
                self.file_objects[file_code] = file_object

    def _update_data(self, publish_data):
        """update self.data with 2nd choice publish context data to display an icon"""
        publish_data.update(self.data)
        self.data = publish_data

    def is_editable(self):
        return False

    def get_info(self):
        return self.info

    def set_icon_size(self, size):
        self.icon_size = str(size)

    def get_icon_size(self):
        ICON_SIZE = 120
        if not self.icon_size:
            self.icon_size = 120
        unit = None
        icon_size = self.icon_size
        if isinstance(self.icon_size, basestring):
            icon_size, unit = self.split_icon_size(self.icon_size)
        icon_mult = PrefSetting.get_value_by_key('thumb_multiplier')
        if not icon_mult:
            icon_mult = 1
        else:
            icon_mult = float(icon_mult)
        if not icon_size:
            size = float(ICON_SIZE * icon_mult)
        else:
            size = float(icon_size * icon_mult)
        if size < 15:
            size = 15
        if unit:
            size = '%s%s' % (icon_size, unit)
        return size

    def set_aspect(self, aspect):
        self.aspect = aspect

    def set_show_filename(self, flag):
        self.show_filename_flag = flag

    def set_show_clipboard(self, flag):
        self.show_clipboard_flag = flag

    def set_show_orig_icon(self, flag):
        self.show_orig_icon = flag

    def set_show_latest_icon(self, flag):
        self.show_latest_icon = flag

    def set_show_file_type(self, flag):
        self.show_file_type = flag

    def set_has_img_link(self, show):
        self.has_img_link = show

    def set_icon_type(self, icon_type):
        self.icon_type = icon_type

    def set_image_link_order(self, order):
        if order:
            self.image_link_order = order

    def set_context(self, context):
        """ if set externally, the sobject's icon_context will be ignored """
        self.context = context

    def set_version(self, version):
        self.version = version

    def get_data(self, sobject):
        redirect = self.get_option('redirect')
        redirect_expr = self.get_option('redirect_expr')
        self.info = {}
        self.files = []
        self.snapshot = None
        if redirect and sobject:
            if redirect == 'true':
                for i in range(0, 2):
                    if not sobject:
                        return ''
                    if sobject.has_value('search_type'):
                        search_type = sobject.get_value('search_type')
                        if not search_type:
                            break
                        search_code = sobject.get_value('search_code', no_exception=True)
                        if search_code:
                            sobject = Search.get_by_code(search_type, search_code)
                        else:
                            search_id = sobject.get_value('search_id', no_exception=True)
                            sobject = Search.get_by_id(search_type, search_id)
                        if sobject:
                            break
            elif redirect.count('|') == 2:
                search_type, col1, col2 = redirect.split('|')
                search = Search(search_type)
                search.add_filter(col1, sobject.get_value(col2))
                sobject = search.get_sobject()
                if not sobject:
                    return ''
        elif redirect_expr and sobject:
            redirect_sobject = ExpressionParser().eval(redirect_expr, sobjects=[sobject], single=True)
            if redirect_sobject:
                sobject = redirect_sobject
            else:
                return ''
        icon_context = self.get_option('icon_context')
        if not icon_context:
            icon_context = sobject.get_icon_context(self.context)
        if isinstance(sobject, Snapshot):
            snapshot = sobject
            try:
                snapshot.get_sobject()
            except SObjectNotFoundException as e:
                return ''
            except SearchException as e:
                return ''
        else:
            snapshot = None
            if self.data:
                search_key = SearchKey.get_by_sobject(sobject, use_id=False)
                snapshot = self.data.get(search_key)
            elif not self.is_preprocess_run or redirect or redirect_expr:
                if self.show_latest_icon:
                    icon_context = None
                snapshot = Snapshot.get_latest_by_sobject(sobject, icon_context, show_retired=False)
                if not snapshot and icon_context == 'icon':
                    snapshot = Snapshot.get_latest_by_sobject(sobject, show_retired=False)
        if not snapshot:
            return ''
        self.snapshot = snapshot
        xml = snapshot.get_xml_value('snapshot')
        self.info = {}
        if not self.file_objects and (not self.is_preprocess_run or redirect or redirect_expr or isinstance(sobject, Snapshot)):
            file_objects = {}
            snapshot_file_objects = File.get_by_snapshot(snapshot)
            for file_object in snapshot_file_objects:
                file_objects[file_object.get_code()] = file_object
        else:
            file_objects = self.file_objects
        protocol = self.get_option('protocol')
        if not protocol:
            protocol = ProjectSetting.get_value_by_key('thumbnail_protocol')
        self.info = ThumbWdg.get_file_info(xml, file_objects, sobject, snapshot, self.show_versionless, protocol=protocol, files=self.files)
        link_path = ThumbWdg.get_link_path(self.info, image_link_order=self.image_link_order)
        if link_path == None:
            snapshots = snapshot.get_all_ref_snapshots()
            snapshot_file_objects = []
            if snapshots:
                snapshot = snapshots[0]
                sobject = snapshot.get_sobject()
                xml = snapshot.get_xml_value('snapshot')
                snapshot_file_objects = File.get_by_snapshot(snapshot)
            for file_object in snapshot_file_objects:
                file_objects[file_object.get_code()] = file_object
            self.files = []
            self.info = ThumbWdg.get_file_info(xml, file_objects, sobject, snapshot, self.show_versionless, protocol=protocol, files=self.files)
            link_path = ThumbWdg.get_link_path(self.info, image_link_order=self.image_link_order)
        self.snapshot = snapshot
        self.file_objects = file_objects
        return link_path

    def get_link_path(info, image_link_order=None):
        """ get the link for the thumbnail """
        image_link = None
        default_image_link_order = ['web', 'main', '.swf']
        if image_link_order:
            default_image_link_order = image_link_order
        for item in default_image_link_order:
            if item in info:
                image_link = info[item]
                break
        else:
            for key, value in info.items():
                if key in ['icon', '_repo']:
                    continue
                image_link = info[key]
                break
        if not image_link:
            image_link = info.get('icon')
        return image_link

    get_link_path = staticmethod(get_link_path)

    def get_file_info(xml, file_objects, sobject, snapshot, show_versionless=False, is_list=False, protocol='http', files=None):
        info = {}
        if is_list:
            info = []
        else:
            repo_info = {}
            info['_repo'] = repo_info
        nodes = xml.get_nodes('snapshot/file')
        for node in nodes:
            type = Xml.get_attribute(node, 'type')
            file_code = Xml.get_attribute(node, 'file_code')
            file_object = file_objects.get(file_code)
            if not file_object:
                if isinstance(info, dict):
                    info[type] = ThumbWdg.get_no_image()
                else:
                    info.append((type, ThumbWdg.get_no_image()))
                Environment.add_warning('No file object', "No file object found for file code '%s'" % file_code)
                continue
            file_name = file_object.get_full_file_name()
            web_dir = sobject.get_web_dir(snapshot, file_object=file_object)
            file_range = file_object.get_value('file_range')
            if file_range:
                from pyasm.biz import FileGroup, FileRange
                file_range = FileRange.get(file_range)
                start = file_range.get_frame_start()
                file_names = FileGroup.expand_paths(file_name, FileRange(start, start))
                if file_names:
                    file_name = file_names[0]
            path = ('%s/%s' % (web_dir, file_name)).replace('\\', '/')
            if protocol != 'file':
                url = urlsplit(web_dir.replace('\\', '/'))
                path = urlunsplit((url.scheme, url.netloc, quote(url.path + '/' + file_name, safe='/:'), url.query, url.fragment))
            lib_dir = sobject.get_lib_dir(snapshot, file_object=file_object) if isinstance(info, dict) or files is not None else ''
            repo_path = ('%s/%s' % (lib_dir, file_name)).replace('\\', '/')
            if files is not None:
                files.append(dict(code=file_object.get_code(), type=type, filename=file_object.get_full_file_name(), href=path,
                                  path=repo_path, size=file_object.get_value('st_size', no_exception=True)))
            if isinstance(info, dict):
                info[type] = path
                repo_info[type] = repo_path
            else:
                info.append((type, path))
        return info

    get_file_info = staticmethod(get_file_info)

    def get_file_info_list(xml, file_objects, sobject, snapshot, show_versionless=False):
        info = ThumbWdg.get_file_info(xml, file_objects, sobject, snapshot, show_versionless=show_versionless, is_list=True)
        return info

    get_file_info_list = staticmethod(get_file_info_list)

    def split_icon_size(self, icon_size):
        m = re.match('(\\d+\\.?\\d*)(pt|em|%|px)*', icon_size)
        num = 0
        unit = ''
        if m:
            num, unit = m.groups()
            icon_size = float(num)
        return (icon_size, unit)

    @classmethod
    def get_args_keys(cls):
        return cls.ARGS_KEYS

    @staticmethod
    def get_no_image():
        return '/context/icons/common/no_image.png'

    @staticmethod
    def get_missing_image():
        return '/context/icons/common/missing_files.png'

    def get_text_value(self):
        return self.get_data(self.get_current_sobject())

    def get_cell_value(self):
        """Expose the same selected snapshot/files to any browser renderer."""
        sobject = self.get_current_sobject()
        link = self.get_data(sobject)
        if not self.snapshot:
            return dict(text='', image='', files=[])
        files = self.files
        image = link if self.show_orig_icon else self.info.get('icon') or self.info.get('web') or link
        if image == self.get_no_image() or urlsplit(image or '').path.lower().rsplit('.', 1)[-1] not in ('png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'avif'):
            image = ''
        return dict(text=link or '', image=image, files=files, context=self.snapshot.get_value('context'),
                    version=self.snapshot.get_value('version'), snapshot_key=self.snapshot.get_search_key(),
                    filename=files[0]['filename'] if files else '')
