"""Handler global_functions.py: native FileObject/MatchTemplate (EPL-1.0).

Desktop launch actions and missing-frame enumeration are excluded. Frame ranges
retain native metadata without allocating gaps. Path/size helpers are platform functions.
"""
import collections
import os
import re

def form_path(path, tp=None):
    return path.replace('\\', '/')

def extract_filename(path, no_ext=False):
    name = path.replace('\\', '/').rsplit('/', 1)[-1]
    return os.path.splitext(name)[0] if no_ext else name

def extract_dirname(path):
    return path.replace('\\', '/').rsplit('/', 1)[0] if '/' in path.replace('\\', '/') else ''

def extract_extension(path):
    extension = os.path.splitext(path)[1].lstrip('.')
    return extension, extension.upper(), 'file', 'main'

def get_st_size(path):
    return os.path.getsize(path)

def natural_sort_key(value):
    return tuple(
        int(part) if part.isdigit() else part.casefold()
        for part in re.split(r'(\d+)', value)
    )

class FileObject(object):
    """Meta File Object"""
    def __init__(self, file_=None, template_=None):

        self._file = file_
        self._template = template_
        self._type = None
        self._previewable = None
        self._file_type = None
        self._files_list = []
        self._file_path = None
        self._file_name = None
        self._sizes_list = []
        self._new_filename = None
        self._new_filepath = None
        self._new_frame_padding = None
        self._new_template = None
        self._abs_file_name = None
        self._pretty_file_name = None
        self._file_ext = None
        self._layer = None
        self._base_file_type_pretty_name = None
        self._base_file_type = None
        self._tactic_file_type = None
        self._sequence_length = None
        self._sequence_padding = None
        self._sequence_frames = []
        self._sequence_start = None
        self._sequence_end = None
        self._sequence_missing_frames = None
        self._app_info = None

        self._tiles_count = None
        self._tiles = []

        if self._file:
            self.init_files()

    def get_abs_file_name(self, file_dict=None, pretty=False, filename=False, no_ext=False):

        if not file_dict:
            file_dict = self.get_all_files_dicts(True)

        if not file_dict and self._abs_file_name:
            return self._abs_file_name

        separators = self._template['pattern_separators']
        order = self._template['order']

        if len(order) - len(separators) > 0:
            separators.insert(0, '')

        order_format = u''.join('%s{%s}' % (k, j) for j, k in zip(order, separators))

        if pretty:
            self._abs_file_name = order_format.format(**self.get_pretty_frames_and_udims(file_dict.copy()))
        else:
            self._abs_file_name = order_format.format(**file_dict)
        if filename:
            if no_ext:
                return self.__get_filename(file_dict.copy(), no_ext=True).get('filename')
            else:
                return order_format.format(**self.__get_filename(file_dict.copy()))

        return self._abs_file_name

    @staticmethod
    def __get_filename(file_dict, no_ext=False):
        if file_dict.get('filename'):
            file_dict['filename'] = file_dict.get('filename').split('/')[-1]
            if no_ext and file_dict.get('ext'):
                file_dict['filename'].replace('.{0}'.format(file_dict['ext']), '')
        return file_dict

    def get_pretty_frames_and_udims(self, file_dict):
        if file_dict.get('frame'):
            file_dict['frame'] = '[{}]'.format('#' * self.get_sequence_padding())
        if file_dict.get('udim'):
            file_dict['udim'] = '[UUVV]'
        if file_dict.get('uv'):
            file_dict['uv'] = '[u<>_v<>]'

        return file_dict

    def get_metadata(self):
        metadata_dict = {}
        if self.get_file_name(True):
            metadata_dict['filename'] = self.get_file_name(True)
        if self.get_file_ext():
            metadata_dict['ext'] = self.get_file_ext()
        if self.get_layer():
            metadata_dict['layer'] = self.get_layer()
        if self.get_sequence_frameranges():
            metadata_dict['frameranges'] = self.get_sequence_frameranges()
        if self.get_sequence_frame_range():
            metadata_dict['frame_range'] = self.get_sequence_frame_range()
        if self.get_sequence_padding():
            metadata_dict['padding'] = self.get_sequence_padding()
        if self.get_tiles():
            metadata_dict['udims'] = self.get_tiles()
        if self.get_type():
            metadata_dict['type'] = self.get_type()
        if not self._sizes_list:
            metadata_dict['st_sizes'] = self.get_sizes_list()
        if self._sizes_list:
            metadata_dict['st_size'] = self.get_sizes_list(together=True)
        if self.get_app_info():
            metadata_dict['app_info'] = self.get_app_info()
        if self._template:
            metadata_dict['template'] = self._template['pattern_string']
        if self._new_filename:
            metadata_dict['new_filename'] = self._new_filename[0]
            metadata_dict['new_file_part'] = self._new_filename[1]
            metadata_dict['new_file_ext'] = self._new_filename[2].replace('.', '')
        if self._new_template:
            metadata_dict['new_template'] = self._new_template
        if self._new_frame_padding:
            metadata_dict['new_padding'] = self._new_frame_padding

        return metadata_dict

    def get_app_info(self):
        return self._app_info

    def set_app_info(self, app_info_dict):
        if app_info_dict:
            self._app_info = app_info_dict
        else:
            self._app_info = None

    def get_type(self):
        return self._type

    def set_type(self, type_):
        if type_:
            self._type = type_['type']
        else:
            self._type = 'file'

    def get_sizes_list(self, together=False, files_list=None):
        if self._sizes_list:
            if together:
                return sum(self._sizes_list)
            else:
                return self._sizes_list

        sizes_list = []
        if not files_list:
            files_list = self.get_all_files_list()
        for fl in files_list:
            size = get_st_size(fl)
            if size:
                sizes_list.append(size)

        if sizes_list:
            if together:
                return sum(sizes_list)
            else:
                return sizes_list

    def set_sizes_list(self, _sizes_list):
        if _sizes_list:
            self._sizes_list = _sizes_list

    def get_file_type(self):
        return extract_extension(self.get_abs_file_name())

    def get_file_path(self):
        return extract_dirname(self.get_abs_file_name())

    def get_all_files_list(self, first=False, filenames=False, no_ext=False):

        if filenames:
            # Only for external calls
            file_names_list = []
            for fld in self.get_all_files_dicts():
                file_names_list.append(form_path(self.get_abs_file_name(fld, filename=True, no_ext=no_ext)))
            return sorted(file_names_list)

        if not self._files_list:
            for fld in self.get_all_files_dicts():
                self._files_list.append(form_path(self.get_abs_file_name(fld)))
            self._files_list = sorted(self._files_list)

        if first:
            return form_path(self._files_list[0])
        else:
            return sorted(self._files_list)

    def get_all_files_dicts(self, first=False):
        if first:
            return self._file[1][0]
        else:
            return self._file[1]

    def get_file_name(self, no_ext=False):
        if not self._file_name:
            self._file_name = self.get_abs_file_name(filename=True, no_ext=no_ext)
        return self._file_name

    def get_name_part(self, frame_padding=4, template='.$LAYER_$UDIM/UV.$FRAME'):
        pattern, separators = self.split_template(template)

        order_format = ''
        for file_dict in self.get_all_files_dicts():
            order_format = ''
            for item, sep in zip(reversed(pattern), reversed(separators)):
                if item == '$UDIM/UV':
                    if file_dict.get('udim'):
                        item = '[UUVV]'
                    elif file_dict.get('uv'):
                        item = 'u<>_v<>'
                if item == '$FRAME':
                    item = '[{}]'.format('#' * frame_padding)
                if item == '$LAYER':
                    item = file_dict['layer']

                order_format = sep + item + order_format

        return order_format

    def get_all_new_files_list(self, new_filename=None, new_filepath=None, new_frame_padding=None, no_ext=False, new_template='$FILENAME.$LAYER_$UDIM/UV.$FRAME.$EXT'):
        """
        This can only be used once, it creates metadata with new data, and returning list with new file names.

        :param new_filename:
        :param new_filepath:
        :param new_frame_padding:
        :param no_ext:
        :param new_template:
        :return:
        """
        if new_filename:
            self._new_filename = new_filename
        if new_filepath:
            self._new_filepath = new_filepath
        if new_frame_padding:
            self._new_frame_padding = new_frame_padding

        pattern, separators = self.split_template(new_template)

        order_format_list = []

        for file_dict in self.get_all_files_dicts():
            order_format = ''
            template = ''
            for item, sep in zip(reversed(pattern), reversed(separators)):
                temp = ''
                if item == '$FILENAME':
                    item = u'{0}/{1}'.format(self._new_filepath, self._new_filename[0])
                    temp = '$FILENAME'
                if item == '$UDIM/UV':
                    if file_dict.get('udim'):
                        item = file_dict['udim']
                        temp = '$UDIM'
                    elif file_dict.get('uv'):
                        item = file_dict['uv']
                        temp = '$UV'
                if item == '$FRAME':
                    item = file_dict['frame'].zfill(self._new_frame_padding)
                    temp = '$FRAME'
                if item == '$LAYER':
                    item = file_dict['layer']
                    temp = '$LAYER'
                if item == '$EXT' and not no_ext:
                    item = self._new_filename[2].replace('.', '')
                    temp = '$EXT'

                order_format = sep + item + order_format
                template = sep + temp + template

            order_format_list.append(order_format)

            self._new_template = template

        return order_format_list

    def split_template(self, template):
        match_template = MatchTemplate([template])

        template = list(match_template.split_patterns.values())[0][0]

        pattern = template[0]
        separators = template[1]
        if len(pattern) - len(separators) > 0:
            separators.insert(0, '')

        new_pattern = []
        new_separators = []
        for cp, cp_sep in zip(pattern, separators):
            for i, op in enumerate(self._template['pattern']):
                if op in ['$UDIM', '$UV']:
                    op = '$UDIM/UV'
                if cp == op:
                    new_pattern.append(cp)
                    new_separators.append(cp_sep)

        return new_pattern, new_separators

    def get_file_id(self):
        return self._file[0]

    def get_pretty_file_name(self):
        if self.get_type() not in ['layer_file', 'file', 'no_ext']:
            return extract_filename(self.get_abs_file_name(pretty=True))
        return extract_filename(self.get_abs_file_name())

    def get_file_ext(self):
        if not self._file_ext:
            self._file_ext = self.get_file_type()[0]
        return self._file_ext

    def get_layer(self):
        return self._layer

    def get_base_file_type_pretty_name(self):
        if not self._base_file_type_pretty_name:
            self._base_file_type_pretty_name = self.get_file_type()[1]
        return self._base_file_type_pretty_name

    def get_base_file_type(self):
        if not self._base_file_type:
            self._base_file_type = self.get_file_type()[2]
        return self._base_file_type

    def get_tactic_file_type(self):
        if not self._tactic_file_type:
            self._tactic_file_type = self.get_file_type()[3]
        return self._tactic_file_type

    def get_sequence_frameranges(self, padding=False):
        if not self._sequence_frames:
            return None
        tiled = self.get_type() in ('layer_uv_sequence', 'layer_udim_sequence', 'uv_sequence', 'udim_sequence')
        groups = self._sequence_frames if tiled else [('', self._sequence_frames)]
        output = collections.defaultdict(list)
        self._sequence_start = collections.defaultdict(list) if tiled else None
        self._sequence_end = collections.defaultdict(list) if tiled else None
        self._sequence_length = collections.defaultdict(list) if tiled else None
        for tile, frames in groups:
            present = sorted(set(frames))
            start = end = present[0]
            intervals = []
            for frame in present[1:]:
                if frame == end + 1:
                    end = frame
                else:
                    intervals.append((start, end)); start = end = frame
            intervals.append((start, end))
            render = self.get_frame_with_padding if padding else str
            output[tile] = [render(start) if start == end else render(start) + '-' + render(end) for start, end in intervals]
            if tiled:
                self._sequence_start[tile].append(present[0])
                self._sequence_end[tile].append(present[-1])
                self._sequence_length[tile].append(len(frames))
            else:
                self._sequence_start, self._sequence_end, self._sequence_length = present[0], present[-1], len(frames)
        return list(output.items()) if tiled else output['']

    def get_sequence_frame_range(self):
        if self._sequence_frames:
            if self.get_type() in ['layer_uv_sequence', 'layer_udim_sequence', 'uv_sequence', 'udim_sequence']:
                sequence_ranges = []
                for start, end in zip(self.get_sequence_start().items(), self.get_sequence_end().items()):
                    sequence_ranges.append((start[0], '{0}-{1}'.format(start[1][0], end[1][-1])))
                return sequence_ranges
            elif self.get_type() in ['sequence', 'layer_sequence']:
                return '{0}-{1}'.format(self.get_sequence_start(), self.get_sequence_end())

    def get_frame_with_padding(self, frame):
        return '%0*d' % (self.get_sequence_padding(), int(frame))

    def get_sequence_frameranges_string(self, brackets=None):
        frames = self.get_sequence_frameranges()
        if frames:
            if self.get_type() in ['layer_uv_sequence', 'layer_udim_sequence', 'uv_sequence', 'udim_sequence']:
                framerange_strings = []
                for uv, frame in frames:
                    framerange_string = '{1} ({0})'.format(uv, ', '.join(frame))
                    if brackets:
                        framerange_string = '%s%s%s' % (brackets[0], framerange_string, brackets[1])
                    framerange_strings.append(framerange_string)

                return ', '.join(framerange_strings)

            elif self.get_type() in ['sequence', 'layer_sequence']:
                framerange_string = ', '.join(frames)
                if brackets:
                    return '%s%s%s' % (brackets[0], framerange_string, brackets[1])

                return framerange_string

    def init_files(self):
        if self._template:
            self.set_type(self._template)
        if self._sequence_frames:
            return self._sequence_frames
        else:
            all_files_dicts = self.get_all_files_dicts()
            if self.get_type() in ['layer_file', 'file', 'no_ext']:
                for fld in all_files_dicts:
                    self._layer = fld.get('layer')

            elif self.get_type() in ['layer_uv', 'layer_udim', 'uv', 'udim']:
                for fld in all_files_dicts:
                    udim = fld.get('udim')
                    if not udim:
                        udim = fld.get('uv')
                    self._tiles.append(udim)
                    self._layer = fld.get('layer')
                self._tiles_count = len(self._tiles)

            elif self.get_type() in ['sequence', 'layer_sequence']:
                for fld in all_files_dicts:
                    self._sequence_padding = len(fld['frame'])
                    self._sequence_frames.append(int(fld['frame']))
                    self._layer = fld.get('layer')

            elif self.get_type() in ['layer_uv_sequence', 'layer_udim_sequence', 'uv_sequence', 'udim_sequence']:
                frames_by_udims = collections.defaultdict(list)
                for fld in all_files_dicts:
                    self._sequence_padding = len(fld['frame'])
                    udim = fld.get('udim')
                    if not udim:
                        udim = fld.get('uv')
                    frames_by_udims[udim].append(int(fld['frame']))
                    self._layer = fld.get('layer')
                self._sequence_frames = frames_by_udims.items()
                self._tiles = list(frames_by_udims.keys())
                self._tiles_count = len(self._tiles)

            return self._sequence_frames

    def get_sequence_lenght(self):
        return self._sequence_length

    def get_sequence_padding(self):
        return self._sequence_padding

    def get_sequence_start(self):
        return self._sequence_start

    def get_sequence_end(self):
        return self._sequence_end


    def get_tiles_count(self):
        return self._tiles_count

    def get_tiles(self):
        return self._tiles

    def is_exists(self, check_all_files=False):
        if check_all_files:
            exists = False
            for fl in self.get_all_files_list():
                exists = os.path.isfile(fl)
            return exists
        else:
            return os.path.isfile(self.get_all_files_list(True))

    def is_previewable(self):
        if self._previewable:
            return True

        ext = self.get_file_type()
        if ext[3] == 'preview':
            self._previewable = True

        return self._previewable



class MatchTemplate(object):
    default_patterns = [
        '$FILENAME',
        '$FILENAME.$EXT'
    ]

    def __init__(self, patterns=None, padding=3, add_default_patterns=False):

        if patterns:
            self.patterns = list(dict.fromkeys(patterns))
        else:
            self.patterns = None
        if add_default_patterns:
            if patterns:
                patterns.extend(self.default_patterns)
                self.patterns = list(dict.fromkeys(patterns))
            else:
                self.patterns = list(self.default_patterns)
        self.padding = padding
        self.split_patterns = None

        if self.patterns:
            self.parse_patterns()

    def get_preview_string(self):

        return self.patterns.pop()\
            .replace('$FILENAME', 'Filename')\
            .replace('$EXT', 'tif')\
            .replace('$UDIM', '[UUVV]')\
            .replace('$UV', '[u<>_v<>]')\
            .replace('$FRAME', '[###]')\
            .replace('$LAYER', 'layer')

    def get_type_string(self):
        return list(self.split_patterns.keys())[0].replace('_', ' | ')

    def get_template(self, template):
        templates = {
            '$EXT': ['(?P<ext>[0-9A-z]+)', 'ext'],
            '$FILENAME': ['(?P<filename>.+)', 'filename'],
            '$UDIM': ['(?P<udim>(?P<u>[0-9]{2})(?P<v>[0-9]{2}))', 'udim'],
            '$UV': ['(?P<uv>u(?P<u>[0-9]{1,2})_v(?P<v>[0-9]{1,2}))', 'uv'],
            '$FRAME': ['(?P<frame>[0-9]{%s,})' % self.padding, 'frame'],  # must be at least 3 frames by default
            '$LAYER': ['(?P<layer>[A-z0-9]*[A-z]+[A-z0-9]*)', 'layer'],  # layer must not have digits only
        }

        return templates.get(template)

    @staticmethod
    def get_type(keys_list):
        if all(('$UV' in keys_list, '$FRAME' in keys_list, '$LAYER' in keys_list)):
            return 'layer_uv_sequence'
        if all(('$UDIM' in keys_list, '$FRAME' in keys_list, '$LAYER' in keys_list)):
            return 'layer_udim_sequence'
        if all(('$UV' in keys_list, '$FRAME' in keys_list)):
            return 'uv_sequence'
        if all(('$UDIM' in keys_list, '$FRAME' in keys_list)):
            return 'udim_sequence'
        if all(('$LAYER' in keys_list, '$FRAME' in keys_list)):
            return 'layer_sequence'
        if all(('$LAYER' in keys_list, '$UV' in keys_list)):
            return 'layer_uv'
        if all(('$LAYER' in keys_list, '$UDIM' in keys_list)):
            return 'layer_udim'
        if '$FRAME' in keys_list:
            return 'sequence'
        if '$UV' in keys_list:
            return 'uv'
        if '$UDIM' in keys_list:
            return 'udim'
        if '$LAYER' in keys_list:
            return 'layer_file'
        if '$EXT' in keys_list:
            return 'file'
        return 'no_ext'

    def parse_patterns(self, patterns=None):
        if patterns:
            self.patterns = patterns

        values_pattern = re.compile('[.|_]')
        split_patterns = collections.defaultdict(list)

        for ptn in self.patterns:
            key = re.split(values_pattern, ptn)
            split_patterns[self.get_type(key)].append((key, re.findall(values_pattern, ptn), ptn))

        self.split_patterns = split_patterns

        return self.split_patterns

    def get_re_patterns(self, patterns):
        re_temp = []
        re_seps = []
        order = []

        for i, key in enumerate(patterns[0]):
            if len(patterns[1]) > i and patterns[1][i]:
                re_seps.append('[{}]'.format(patterns[1][i]))
            else:
                re_seps.append('')
            template = self.get_template(key)
            if template:
                re_temp.append(template[0])
                order.append(template[1])
            else:
                re_temp.append(key)

        pattern = '^{0}$'.format(''.join(j + k for j, k in zip(re_temp, re_seps)))

        return pattern, order

    @staticmethod
    def get_unique_name(group_dict, order, separators):

        if len(order) - len(separators) > 0:
            separators.insert(0, '')

        order_format = ''
        for item, sep in zip(order, separators):
            if item == 'frame':
                item = '[$FRAME' + str(len(group_dict['frame'])) + '$]'
            if item == 'uv':
                item = '[$UV$]'
            if item == 'udim':
                item = '[$UDIM$]'
            if item == 'ext':
                item = group_dict['ext']
            if item == 'filename':
                item = group_dict['filename']
            if item == 'layer':
                item = group_dict['layer']

            order_format = order_format + sep + item

        return order_format

    def match_by_template(self, files_list, templates, template_names):
        match_dicts = []
        tpls_names = []

        for i, template in enumerate(templates):
            values_pattern = re.compile(template[0])
            def_dict = collections.OrderedDict()
            not_matched = []
            while files_list:
                fl = files_list.pop()
                # for windows os
                fl_norm = fl.replace('\\', '/')
                search_result = re.search(values_pattern, fl_norm)
                if search_result:
                    group_dict = search_result.groupdict()
                    unique_filename = self.get_unique_name(group_dict, template[1], template_names[i][1][1])
                    group_dict['orig_file'] = fl_norm
                    def_dict.setdefault(unique_filename, []).append(group_dict)
                else:
                    not_matched.append(fl_norm)

            # if not found, match with next template
            files_list = not_matched
            if def_dict:
                match_dicts.append(def_dict)
                template_dict = {
                    'type': template_names[i][0],
                    're_string': template[0],
                    'order': template[1],
                    'pattern': template_names[i][1][0],
                    'pattern_separators': template_names[i][1][1],
                    'pattern_string': template_names[i][1][2],
                }
                tpls_names.append(template_dict)

        return zip(match_dicts, tpls_names)

    def get_files(self, files_list=None, default_types=False):
        templates = []
        template_names = []

        # this is needed, because we need to get uv sequences first, then others
        types = [
            'layer_uv_sequence',
            'layer_udim_sequence',
            'uv_sequence',
            'udim_sequence',
            'layer_sequence',
            'layer_uv',
            'layer_udim',
            'sequence',
            'uv',
            'udim',
            'layer_file',
            'file',
            'no_ext'
        ]

        def_types = [
            'file',
            'no_ext'
        ]

        if default_types:
            types = def_types

        for tp in types:
            if self.split_patterns.get(tp):
                for patterns in self.split_patterns.get(tp):
                    templates.append(self.get_re_patterns(patterns))
                    template_names.append((tp, patterns))

        return self.match_by_template(files_list, templates, template_names)

    def get_files_objects(self, files_list, allow_single_sequence=False, allow_single_udim=False, sort=True):
        if sort:
            found_files = self.get_files(sorted(files_list, key=natural_sort_key))
        else:
            found_files = self.get_files(files_list)
        out_dict = collections.OrderedDict()

        single_sequences_and_udims = []

        for files, tpl in found_files:
            for fl in files.items():
                if not allow_single_sequence or allow_single_udim:
                    if tpl['type'] in ['layer_uv_sequence', 'layer_udim_sequence', 'uv_sequence', 'udim_sequence', 'layer_sequence', 'sequence'] and len(fl[1]) == 1:
                        single_sequences_and_udims.append(fl[1][0]['orig_file'])
                    elif tpl['type'] in ['layer_uv', 'layer_udim', 'sequence', 'uv', 'udim'] and len(fl[1]) == 1:
                        single_sequences_and_udims.append(fl[1][0]['orig_file'])
                    else:
                        file_obj = FileObject(fl, tpl)
                        out_dict.setdefault(tpl['type'], []).append(file_obj)

        # getting all single sequences or udims/uvs
        if single_sequences_and_udims:
            single_found_files = self.get_files(single_sequences_and_udims, default_types=True)
            for files, tpl in single_found_files:
                for fl in files.items():
                    file_obj = FileObject(fl, tpl)
                    out_dict.setdefault(tpl['type'], []).append(file_obj)

        return out_dict

    def init_from_tactic_file_object(self, tactic_file_object):
        metadata = tactic_file_object.get_metadata()
        path = tactic_file_object.get_abs_path()
        template = list(self.parse_patterns([metadata.get('new_template')]).values())[0][0]
        pattern = template[0]
        separators = template[1]
        if len(pattern) - len(separators) > 0:
            separators.insert(0, '')

        files_list = []
        if metadata.get('type') in ['layer_uv_sequence', 'layer_udim_sequence', 'uv_sequence', 'udim_sequence']:
            udims_list = self.unpack_udims(metadata.get('frameranges'))
            for udim, frames in udims_list:
                for frame in frames:
                    name = self.unpack_name(
                        pattern,
                        separators,
                        metadata.get('new_filename'),
                        metadata.get('new_file_ext'),
                        udim,
                        '%0*d' % (metadata.get('new_padding'), int(frame)),
                        metadata.get('layer'),
                    )
                    files_list.append('%s/%s' % (path, name))
        elif metadata.get('type') in ['layer_uv', 'layer_udim', 'uv', 'udim']:
            udims_list = metadata.get('udims')
            for udim in udims_list:
                name = self.unpack_name(
                    pattern,
                    separators,
                    metadata.get('new_filename'),
                    metadata.get('new_file_ext'),
                    udim,
                    None,
                    metadata.get('layer'),
                )
                files_list.append('%s/%s' % (path, name))
        elif metadata.get('type') in ['sequence', 'layer_sequence']:
            frames_list = self.unpack_frames(metadata.get('frameranges'))
            for frame in frames_list:
                name = self.unpack_name(
                    pattern,
                    separators,
                    metadata.get('new_filename'),
                    metadata.get('new_file_ext'),
                    None,
                    '%0*d' % (metadata.get('new_padding'), int(frame)),
                    metadata.get('layer'),
                )
                files_list.append('%s/%s' % (path, name))
        elif metadata.get('type') in ['layer_file', 'file', 'no_ext']:
            name = self.unpack_name(
                pattern,
                separators,
                metadata.get('new_filename'),
                metadata.get('new_file_ext'),
                None,
                None,
                metadata.get('layer'),
            )
            files_list.append('%s/%s' % (path, name))

        self.__init__(
            [metadata.get('new_template')],
            padding=metadata.get('new_padding'),
            # add_default_patterns=True
        )
        files_objects_dict = self.get_files_objects(files_list)

        return files_objects_dict

    @staticmethod
    def unpack_name(pattern, separators, file_name=None, file_ext=None, udim=None, frame=None, layer=None):
        result_name = []

        for p, s in zip(pattern, separators):
            if p == '$FILENAME':
                result_name.append(s + file_name)
            if p in ['$UDIM', '$UV']:
                result_name.append(s + udim)
            if p == '$LAYER':
                result_name.append(s + layer)
            if p == '$FRAME':
                result_name.append(s + frame)
            if p == '$EXT':
                result_name.append(s + file_ext)

        return ''.join(result_name)

    def unpack_udims(self, udims):

        udims_list = []
        for udim, frames in udims:
            udims_list.append((udim, self.unpack_frames(frames)))

        return udims_list

    @staticmethod
    def unpack_frames(frameranges):
        # does not support negative values
        frames = []
        for frame in frameranges:
            split = frame.split('-')
            if len(split) > 1:
                frames.extend(range(int(split[0]), int(split[1])+1))
            else:
                frames.append(int(frame))
        return frames
