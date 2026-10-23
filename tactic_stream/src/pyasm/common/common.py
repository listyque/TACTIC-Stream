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


"""Standalone JSON helpers, adapted from pyasm/common/common.py."""
from datetime import date, datetime
import json
import re
import importlib
import os
import binascii
import zlib
import secrets
import random
import colorsys
import string
import zipfile
import tempfile
import shutil
import stat
import ntpath
from pathlib import Path

from pyasm.common.container import Container
from pyasm.common.base import Base
from pyasm.common.errors import SecurityException, TacticException, UnsupportedContract


class Common:
    @staticmethod
    def unzip_file(file_path, dir=None):
        """Original extraction API with bounded, validated and journaled writes."""
        from pyasm.search import FileUndo
        from pyasm.common.environment import Environment
        FileUndo._check_access()
        root = Path(dir) if dir else Path(file_path).parent
        root = root.resolve()
        if dir and root.exists():
            raise FileExistsError(root)
        files = []
        with zipfile.ZipFile(file_path) as archive:
            entries = archive.infolist()
            # ponytail: fixed safety bounds; expose limits in server config if real archives need more.
            if len(entries) > 10000 or sum(item.file_size for item in entries) > 512 * 1024 * 1024:
                raise TacticException('ZIP exceeds extraction limits (10000 entries / 512 MiB)')
            targets = {}
            destinations = set()
            for item in entries:
                name = item.orig_filename
                parts = name.removesuffix('/').split('/')
                mode = stat.S_IFMT(item.external_attr >> 16)
                if (not name or any(part in ('', '.', '..') or ntpath.isreserved(part) for part in parts)
                        or '\\' in name or ':' in name or '\0' in name
                        or mode not in (0, stat.S_IFREG, stat.S_IFDIR)):
                    raise SecurityException('Unsafe ZIP entry: %r' % name)
                path = root.joinpath(*parts)
                resolved = path.resolve()
                if not resolved.is_relative_to(root):
                    raise SecurityException('ZIP entry leaves its extraction directory: ' + name)
                key = '/'.join(parts).casefold()
                destination = str(resolved).casefold()
                if key in targets or destination in destinations:
                    raise TacticException('Duplicate ZIP entry: ' + name)
                if (path.exists() or path.is_symlink()) and (not item.is_dir() or not path.is_dir()):
                    raise FileExistsError(path)
                for parent in path.parents:
                    if parent == root:
                        break
                    if parent.exists() and not parent.is_dir():
                        raise FileExistsError(parent)
                targets[key] = (item, path)
                destinations.add(destination)
            for key in targets:
                parts = key.split('/')
                for index in range(1, len(parts)):
                    parent = targets.get('/'.join(parts[:index]))
                    if parent and not parent[0].is_dir():
                        raise TacticException('ZIP file/directory collision: ' + key)
            FileUndo.mkdir(str(root))
            with tempfile.TemporaryDirectory(dir=Environment.get_tmp_dir()) as staged:
                for index, (item, path) in enumerate(targets.values()):
                    if item.is_dir():
                        FileUndo.mkdir(str(path))
                        continue
                    FileUndo.mkdir(str(path.parent))
                    temporary = Path(staged) / str(index)
                    with archive.open(item) as source, temporary.open('wb') as output:
                        shutil.copyfileobj(source, output)
                    FileUndo.create(str(temporary), str(path))
                    files.append(str(path))
        return files

    @staticmethod
    def get_next_code(code, min_padding=3):
        '''function to get the next code with a minimum padding: chr001 -> chr002'''
        matches = re.findall(r'(.*?)(\d+)$', code)
        if matches:
            base, number = matches[0]
            padding = len(number)
            number = int(number)
        else:
            number, padding, base = 0, 1, code
        padding = max(padding, min_padding)
        return '%s%s' % (base, '%%0.%sd' % padding % (number + 1))

    @staticmethod
    def get_dir_info(dir, skip_dir_details=False, file_range=None, follow_symlinks=True):
        '''Finds the disk size of a path'''

        dir = os.fspath(dir)
        info = {}

        count = 0
        dir_size = 0


        if follow_symlinks and os.path.islink(dir):
            dir = os.path.realpath(dir)


        if dir.find("##") != -1:
            dir_size = 0
            file_type = 'sequence'
            if file_range:
                from pyasm.biz import FileGroup
                file_paths = FileGroup.expand_paths(dir, file_range)
                for file_path in file_paths:
                    # gets total size of sequence
                    dir_size += os.path.getsize(file_path)
        elif not os.path.exists(dir):
            dir_size = 0
            file_type = 'missing'
        elif os.path.islink(dir):
            count = 0
            dir_size = 0
            dir_size += os.path.getsize(dir)
            file_type = 'link'
        elif os.path.isdir(dir):
            # this part is too slow
            if not skip_dir_details:
                walk = os.walk(dir)
                for (path, dirs, files) in walk:
                    for file in files:
                        filename = os.path.join(path, file)
                        if os.path.islink(filename):
                            # ignore links
                            pass                        
                        else:
                            try: 
                                dir_size += os.path.getsize(filename)
                            except OSError:
                                continue

                                
                        count += 1
            file_type = 'directory'
        else:
            dir_size = os.path.getsize(dir)
            count = 1
            file_type = 'file'

        info['size'] = dir_size

        from .format_value import FormatValue
        display_size = FormatValue().get_format_value(dir_size, "KB")
        info['display_size'] = display_size

        info['count'] = count
        info['file_type'] = file_type
            
        return info


    @staticmethod
    def randint(lower, upper):
        return secrets.randbelow(upper - lower) + lower

    @staticmethod
    def get_unique_list(list):
        seen = set()
        return [x for x in list if x not in seen and not seen.add(x)]

    @staticmethod
    def get_display_title(title):
        title = title.strip()
        if title.find("_") == -1:
            # camelcase
            p = re.compile("([A-Z])")
            replace = " \\1"
            title = p.sub(replace, title).strip().title()
            title = re.sub(' +', ' ', title)
            return title.title()

        else:
            title = title.replace("_", " ")
            return title.title()
    IS_Pv3 = True

    @staticmethod
    def generate_alphanum_key(num_digits=10, mode="alpha", delimit=0):
        # Original randrange excluded the final character; use the full alphabet.
        alphabet = {'alpha': string.ascii_uppercase, 'hex': '0123456789ABCDEF',
                    'numeric': string.digits}.get(mode, string.digits + string.ascii_uppercase)
        key = []
        for index in range(num_digits):
            if index and delimit and index % delimit == 0:
                key.append('-')
            key.append(secrets.choice(alphabet))
        return ''.join(key)

    @staticmethod
    def compress_transaction(transaction_data):
        return 'zlib:' + binascii.hexlify(zlib.compress(transaction_data.encode())).decode()

    @staticmethod
    def decompress_transaction(ztransaction_data):
        return zlib.decompress(binascii.unhexlify(ztransaction_data[5:])).decode()

    @staticmethod
    def generate_random_key(digits=None):
        digits = digits or 19
        return os.urandom(digits).hex()[:digits]

    @staticmethod
    def get_full_class_name(object):
        return "%s.%s" % (object.__module__, object.__class__.__name__)

    @staticmethod
    def breakup_class_path(class_path):
        parts = class_path.split('.')
        return '.'.join(parts[:-1]), parts[-1]

    @staticmethod
    def get_dict_list(dct):
        '''get a tuple sorted list given a dictionary'''
        keys = dct.keys()
        keys = sorted(keys)
        return [(x, dct[x]) for x in keys]

    @staticmethod
    def resolve_class(class_path):
        """Resolve trusted server configuration; never exposed as an RPC method."""
        if not isinstance(class_path, str) or not class_path or any(
                not part.isidentifier() for part in class_path.split('.')):
            raise ValueError('Invalid TACTIC class path: %r' % (class_path,))
        module_name, class_name = Common.breakup_class_path(class_path)
        if not module_name or module_name.startswith('tactic.plugins.'):
            raise UnsupportedContract('Short class names and TACTIC plugin loading are not migrated')
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError as exc:
            if module_name.startswith(('pyasm.', 'tactic.')) and (
                    exc.name == module_name or module_name.startswith(exc.name + '.')):
                raise UnsupportedContract('TACTIC module is not migrated: ' + module_name) from exc
            raise
        try:
            return getattr(module, class_name)
        except AttributeError as exc:
            if module_name.startswith(('pyasm.', 'tactic.')):
                raise UnsupportedContract('TACTIC class is not migrated: ' + class_path) from exc
            raise

    @staticmethod
    def create_from_class_path(class_path, args=[], kwargs={}):
        assert class_path
        return Common.resolve_class(class_path)(*args, **{str(name): value for name, value in kwargs.items()})


    @staticmethod
    def create_from_method(class_path, method, kwargs=None):
        """Original zero-argument construction and method call, without eval."""
        if not isinstance(method, str) or not method.isidentifier() or method.startswith('_'):
            raise ValueError('Invalid public method name')
        obj = Common.create_from_class_path(class_path)
        return getattr(obj, method)(**(kwargs or {}))

    @staticmethod
    def is_ascii(value):
        '''check if a value is ASCII'''
        is_ascii = True   
        try:
            value.encode('ascii')
        except UnicodeEncodeError:
            is_ascii = False
        except Exception as e:
            is_acii = False
        else:
            is_ascii = True

        return is_ascii


    @staticmethod
    def extract_keywords(data, lower=True):

        if not isinstance(data, str):
            data = str(data)

        is_ascii = Common.is_ascii(data)

        data = re.sub(r'([\/_|,\n])+', ' ', data)
        if is_ascii:
            # other non ASCII languages don't need these
            data = re.sub(r'([^\s\w\'/\.])+', '', data)
        # lowercase is still needed for a mix of ASCII and non-ASCII like a french word
        if lower:
            data = data.lower()
        data = data.split(" ")
        data = [x for x in data if x]
        return data


    @classmethod
    def extract_keywords_from_path(cls, rel_path):

        # delimiters
        P_delimiters = re.compile(r"[- _\.]")
        # special characters
        P_special_chars = re.compile(r"[\[\]{}\(\)\,]")
        # camel case
        P_camel_case = re.compile('((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))')

        P_capital_word = re.compile(r'([A-Z]{2,})')


        #parts = rel_path.split("/")
        parts =  re.split(r'/|\\', rel_path)
        keywords = set()

        for item in parts:
            if not item:
                continue

            item = item.replace(" ", "_")

            keywords.add(item)


            # preprocess capital words
            item = P_capital_word.sub(r'\1_', item)

            item = P_camel_case.sub(r'_\1', item)
            parts2 = re.split(P_delimiters, item)
            for item2 in parts2:
                if not item2:
                    continue

                item2 = re.sub(P_special_chars, "", item2)

                # skip 1 letter keywords
                if len(item2) == 1:
                    continue

                try:
                    int(item2)
                    continue
                except:
                    pass


                #print("item: ", item2)
                item2 = item2.lower()

                keywords.add(item2)

        keywords_list = list(keywords)
        keywords_list.sort()
        return keywords_list


    @staticmethod
    def get_filesystem_dir(dirname):
        '''Get a file system friendly dir without multiple adjacent slashes'''
        return re.sub(r'//+', '/', dirname)


    @staticmethod
    def get_filesystem_name(filename):
        # FIXME: for now, turn it off
        return filename

    @staticmethod
    def match_ip(a_ip, b_ip, mask='255.255.255.0'):
        if not a_ip or not b_ip:
            return False
        if not mask:
            mask = '255.255.255.0'
        try:
            a_parts = [int(x) for x in str(a_ip).split(',')[0].strip().split('.')]
            b_parts = [int(x) for x in str(b_ip).strip().split('.')]
            m_parts = [int(x) for x in str(mask).strip().split('.')]
        except ValueError:
            return False
        if len(a_parts) != 4 or len(b_parts) != 4 or len(m_parts) != 4:
            return False
        return all((a_parts[i] & m_parts[i]) == b_parts[i] for i in range(4))


    @staticmethod
    def randchoice(obj):
            num = len(obj)
            index = Common.randint(0, num)
            return obj[index]

    @staticmethod
    def process_unicode_string( in_string ):
        return in_string

    @staticmethod
    def modify_color(color, modifier):
    
            if not modifier:
                return color
                
            if not color:
                return None
    
            color = color.replace("#", '')
    
            if color in ['grey', 'blue', 'red']:
                return color
    
            if len(color) == 3:
                first = "%s%s" % (color[0], color[0])
                second = "%s%s" % (color[1], color[1])
                third = "%s%s" % (color[2], color[2])
            elif len(color) == 6:
                first = "%s" % color[0:2]
                second = "%s" % color[2:4]
                third = "%s" % color[4:6]
            else:
                return color
    
    
    
            first =  float(int(first, 16) ) / 256
            second = float(int(second, 16) ) / 256
            third =  float(int(third, 16) ) / 256
    
            #if isinstance(modifier, list):
            if isinstance(modifier, list):
                rgb = []
                rgb.append( 0.01*modifier[0] + first )
                rgb.append( 0.01*modifier[1] + second )
                rgb.append( 0.01*modifier[2] + third )
            else:
    
                hsv = colorsys.rgb_to_hsv(first, second, third)
                value = 0.01*modifier + hsv[2]
                if value < 0:
                    value = 0
                if value > 1:
                    value = 1
                hsv = (hsv[0], hsv[1], value )
                rgb = colorsys.hsv_to_rgb(*hsv)
    
    
            first =  hex(int(rgb[0]*256))[2:]
            if len(first) == 1:
                first = "0%s" % first
            second = hex(int(rgb[1]*256))[2:]
            if len(second) == 1:
                second = "0%s" % second
            third =  hex(int(rgb[2]*256))[2:]
            if len(third) == 1:
                third = "0%s" % third
    
            if len(first) == 3:
                first = "FF"
            if len(second) == 3:
                second = "FF"
            if len(third) == 3:
                third = "FF"
    
            color = "#%s%s%s" % (first, second, third)
            return color


def _json_default(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, type({}.keys())):
        # Original SPTJSONEncoder delegates the converted list to default(),
        # which raises TypeError rather than serializing dict_keys.
        return json.JSONEncoder().default(list(value))
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def jsondumps(value, ensure_ascii=True):
    return json.dumps(value, ensure_ascii=ensure_ascii, default=_json_default)


jsonloads = json.loads
