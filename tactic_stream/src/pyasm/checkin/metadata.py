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

__all__ = ['ParserImportError', 'CheckinMetadataHandler', 'BaseMetadataParser', 'PILMetadataParser', 'ExifMetadataParser', 'ImageMagickMetadataParser', 'FFProbeMetadataParser', 'IPTCMetadataParser','XMPMetadataParser', 'XMPKeywordsParser']


import os, sys, re, subprocess, shutil
import six
import xml.etree.ElementTree as ET

from pyasm.common import Common, Xml
from pyasm.biz import File

# OS-specific import checks
identify_exe = "identify"
ffprobe_exe = "ffprobe"

IS_Pv3 = sys.version_info[0] > 2

if os.name == "nt":
    identify_exe+= ".exe"
    ffprobe_exe+= ".exe"

try:
    from PIL import Image
    HAS_PIL = True
    # Test to see if imaging actually works
    from PIL import _imaging
except:
    HAS_PIL = False

if shutil.which(identify_exe):
    HAS_IMAGEMAGICK = True
else:
    HAS_IMAGEMAGICK = False

if shutil.which(ffprobe_exe):
    HAS_FFMPEG = True
else:
    HAS_FFMPEG = False


try:
    import exifread
    HAS_EXIF = True
except:
    HAS_EXIF = False

try:
    import iptcinfo3
    HAS_IPTC = True
except:
    HAS_IPTC = False

try:
    import libxmp
    HAS_XMP = True
except:
    HAS_XMP = False


class ParserImportError(ImportError):
    def __init__(self,*args,**kwargs):
        ImportError.__init__(self,*args,**kwargs)

class CheckinMetadataHandler():
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def execute(self):

        # extra data from the file check-in

        commit = self.kwargs.get("commit")
        if commit in ['false', False]:
            commit = False
        else:
            commit = True

        # metadata can only be associated with a single file on the
        # snapshot.
        files = self.kwargs.get("files")
        file_objects = self.kwargs.get("file_objects")

        if files is None or file_objects is None or len(files) != len(file_objects):
            raise ValueError('Each metadata file requires its File object')
        configured_parser = self.kwargs.get("parser")

        for i, file in enumerate(files):
            path = file
            ext = File.get_extension(path)
            file_object = file_objects[i]

            if not os.path.exists(path):
                raise FileNotFoundError(path)
            parser_type = configured_parser
            if parser_type not in ("auto", "true"):
                pass
            elif ext in File.VIDEO_EXT:
                parser_type = "FFMPEG"
            elif ext in File.NORMAL_EXT:
                continue
            else:
                if HAS_IMAGEMAGICK:                    
                    parser_type = "ImageMagick" 
                else:
                    parser_type = "PIL"
            metadata = {}

            parser = BaseMetadataParser.get_parser(parser_type, path)
            if parser is None:
                raise ParserImportError('Unknown metadata parser: %s' % parser_type)
            metadata = parser.get_metadata()

            metadata['__parser__'] = parser_type

            # add some default metadata
            basename = os.path.basename(path)
            # During check-in the File has a destination but no snapshot_code yet.
            dirname = file_object.get_value('checkin_dir') or os.path.dirname(file_object.get_lib_path())
            parts = basename.split(".")
            ext = parts[-1]
            try:
                # occasionally, people will put frame numbers as the last
                # part
                ext = int(ext)
                ext = parts[-2]
            except:
                pass

            metadata['Ext'] = ext
            metadata['Basename'] = basename
            metadata['Dirname'] = dirname


            if metadata and not file_object.get_value("metadata"):
                file_object.add_metadata(metadata, replace=True)
                searchable = self.get_searchable(metadata)
                file_object.set_value("metadata_search", searchable)

                if commit:
                    file_object.commit()


                if i == 0:
                    snapshot = self.kwargs.get("snapshot")
                    snapshot.add_metadata(metadata, replace=True)
                    if commit:
                        snapshot.commit()



    def get_searchable(self, metadata):
        pairs = []
        pairs_set = set()
        for name, value in metadata.items():
            # get rid of the spaces
            if name == "__keys__":
                continue

            # ignore attributes that are numbers only
            try:
                name = int(name)
                continue
            except:
                pass

            # clean up the names for indexed searching
            name = name.lower()
            name = name.replace(" ", "_")
            name = name.replace(":", "_")
            
            keys = [] 
            # otherwise it could an int or float
            if isinstance(value, six.string_types):
                value = value.lower()
                value = value.replace("(", "")
                value = value.replace(")", "")
                value = value.replace(" ", "_")
                keys = value.split(" ")
            
            if len(keys) > 1:
                for key in keys:
                    pair = "%s=%s" % (name, key)
                    if pair in pairs_set:
                        continue
                    pairs.append(pair)
                    pairs_set.add(pair)

            
            pair = "%s=%s" % (name, value)
            pairs.append(pair)



        searchable = " ".join(pairs)

        return searchable



#
# Common file types
#
#from PIL import Image
#from PIL.ExifTags import TAGS

class BaseMetadataParser(object):
    def __init__(self, **kwargs):
        self.kwargs = kwargs


    def get_title(self):
        return "Base"

    def get_media_type(self):
        return "image"

    def get_metadata(self):
        return {}

    def get_tactic_mapping(self):
        return {}

    def process_tactic_mapping(self, tactic_data, metadata):
        pass


    def get_initial_data(self):
        return {
        }

    def get_tactic_metadata(self):

        tactic_data = self.get_initial_data()

        metadata = self.get_metadata()

        mapping = self.get_tactic_mapping()
        for name, name2 in mapping.items():
            tactic_data[name] = metadata.get(name2)

        self.process_tactic_mapping(tactic_data, metadata)

        return tactic_data
    
    def sanitize_data(self, data):
        # Python 3 follows the original fast branch.
        return data
    
   
    def get_parser_by_path(cls, path, prefs={}):
        ext = File.get_extension(path)

        # video parsers and availability
        video_parser_mapping = {
            "FFMPEG": HAS_FFMPEG,
            "PIL": HAS_PIL
        }

        # image parsers and availability
        image_parser_mapping = {
            "ImageMagick": HAS_IMAGEMAGICK,
            "PIL": HAS_PIL,
            "EXIF": HAS_EXIF,
            "FFMPEG" : HAS_FFMPEG
        }
        # parsers for other file types and availability
        other_parser_mapping = {
            "ImageMagick": HAS_IMAGEMAGICK,
            "PIL": HAS_PIL,
            "EXIF": HAS_EXIF,
            "FFMPEG" : HAS_FFMPEG
        }

        parser_str = None

        # for each file type, check if preferred (in order) parsers are available,
        # otherwise check in a default order
        if ext in File.VIDEO_EXT:
            for pref in prefs.get("video", []):
                if video_parser_mapping.get(pref, False):
                    return cls.get_parser(pref, path)

            if HAS_FFMPEG:
                parser_str = "FFMPEG"
            else:
                parser_str = "PIL"

        elif ext in File.IMAGE_EXT:
            for pref in prefs.get("image", []):
                if image_parser_mapping.get(pref, False):
                    return cls.get_parser(pref, path)

            if HAS_IMAGEMAGICK:
                parser_str = "ImageMagick"
            elif HAS_PIL:
                parser_str = "PIL"
            elif HAS_EXIF:
                parser_str = "EXIF"
            elif HAS_FFMPEG:
                parser_str = "FFMPEG"

        else:
            for pref in prefs.get("other", []):
                if other_parser_mapping.get(pref, False):
                    return cls.get_parser(pref, path)

            if HAS_IMAGEMAGICK:
                parser_str = "ImageMagick"
            elif HAS_PIL:
                parser_str = "PIL"
            elif HAS_EXIF:
                parser_str = "EXIF"
            elif HAS_FFMPEG:
                parser_str = "FFMPEG"

        return cls.get_parser(parser_str, path)
    get_parser_by_path = classmethod(get_parser_by_path)


    def get_parser(cls, parser_str, path):
        if parser_str == "EXIF":
            parser = ExifMetadataParser(path=path)
        elif parser_str == "IPTC":
            parser = IPTCMetadataParser(path=path)
        elif parser_str == "XMP":
            parser = XMPMetadataParser(path=path)
        elif parser_str == "ImageMagick":
            parser = ImageMagickMetadataParser(path=path)
        elif parser_str == "PIL":
            parser = PILMetadataParser(path=path)
        elif parser_str == "FFMPEG":
            parser = FFProbeMetadataParser(path=path)
        elif parser_str == "XMP Keywords":
            parser = XMPKeywordsParser(path=path)
        else:
            parser = None

        return parser
    get_parser = classmethod(get_parser)




class PILMetadataParser(BaseMetadataParser):

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def get_title(self):
        return "PIL"

    def get_initial_data(self):
        return {
            'media_type': 'image',
            'parser': 'PIL'
        }

    def get_metadata(self):
        if not HAS_PIL:
            raise ParserImportError("Unable to import PIL parser.")

        path = self.kwargs.get("path")
        try:
            from PIL import Image
            with Image.open(path) as im:
                return self._get_data(im)
        except Exception as e:
            print("WARNING: ", e)
            return {}

 
    def _get_data(self, im):
        #info = im._getexif()
        ret = {}
        #if info:
        #    for tag, value in info.items():
        #        decoded = TAGS.get(tag, tag)
        #        ret[decoded] = value

        size = im.size
        ret['width'] = size[0]
        ret['height'] = size[1]
        ret['format'] = im.format
        ret['format_description'] = im.format_description

        return ret


    def get_tactic_mapping(self):
        return {
            'width': 'width',
            'height': 'height',
            'format': 'format',
            'format_description': 'format_description'
        }




class ExifMetadataParser(BaseMetadataParser):

    def __init__(self, **kwargs):
        self.kwargs = kwargs


    def get_title(self):
        return "EXIF"



    def get_initial_data(self):
        return {
            'media_type': 'image',
            'parser': 'Exif'
        }



    def get_metadata(self):
        if not HAS_EXIF:
            raise ParserImportError("Unable to import EXIF parser.")

        path = self.kwargs.get("path")

        try:
            import exifread
        except:
            from pyasm.checkin import exifread

        with open(path, 'rb') as source:
            return exifread.process_file(source)



class IPTCMetadataParser(BaseMetadataParser):

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def get_title(self):
        return "IPTC"

    def get_initial_data(self):
        return {
            'media_type': 'image',
            'parser': 'IPTC'
        }



    def get_metadata(self):
        if not HAS_IPTC:
            raise ParserImportError("Unable to import IPTC parser.")

        path = self.kwargs.get("path")

        #from pyasm.checkin.iptcinfo import IPTCInfo, c_datasets, c_datasets_r
        from iptcinfo3 import IPTCInfo, c_datasets, c_datasets_r

        try:
            info = IPTCInfo(path, force=True)

            #data = info.data 
            data = info._data 

            metadata = {}
            for key, value in data.items():
                real_key = c_datasets.get(key)
                if not real_key:
                    real_key = key


                if isinstance(value, list):
                    value = " ".join(item.decode('utf-8', errors='replace') if isinstance(item, bytes) else str(item) for item in value)
                elif isinstance(value, bytes):
                    try:
                        value = value.decode()
                    except:
                        value = value.decode("latin-1")
                else:
                    value = str(value)

                if value != "":
                    metadata[real_key] = value

            return metadata
        except Exception as e:
            info = {
                    "Message": str(e),
            }
            raise
            return info



class XMPMetadataParser(BaseMetadataParser):

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def get_title(self):
        return "XMP"

    def get_initial_data(self):
        return {
            'media_type': 'image',
            'parser': 'XMP'
        }



    def get_metadata(self):
        if not HAS_XMP:
            raise ParserImportError("Unable to import XMP parser.")

        path = self.kwargs.get("path")

        from libxmp.utils import file_to_dict
        from libxmp import consts

        try:

            metadata = {}

            xmp = file_to_dict(path)
            for space in xmp.keys():
                #dc = xmp[consts.XMP_NS_DC]
                dc = xmp[space]

                for key, value, options in dc:
                    metadata[key] = value


            return metadata
        except Exception as e:
            info = {
                    "Message": str(e)
            }
            return info






class ImageMagickMetadataParser(BaseMetadataParser):

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def get_title(self):
        return "ImageMagick"


    def get_initial_data(self):
        return {
            'media_type': 'image',
            'parser': 'ImageMagick'
        }

    def get_metadata(self):
        if not HAS_IMAGEMAGICK:
            raise ParserImportError("Unable to import IMAGEMAGICK parser.")

        path = self.kwargs.get("path")

        import subprocess, re

        ret = {}

        process = subprocess.run([identify_exe, '-verbose', path], stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=self.kwargs.get('timeout', 30))
        ret_val = process.stdout

        ret_val = self.sanitize_data(ret_val)
        try:
            ret_val = ret_val.decode()
        except Exception as e:
            ret_val = ret_val.decode("latin-1")


        p = re.compile(r":\ +")

        level = 0
        names = set()
        curr_ret = ret
        for line in ret_val.split("\n"):
            line = line.strip()
            if not line:
                continue

            index = 0
            while 1:
                if index >= len(line):
                    break
                if line[index] != ' ':
                    break
                index += 1
            level = index / 2
            line = line.strip()

            if not line:
                continue

            if line.endswith(":"):
                name = line.rstrip(":")
                curr_ret = {}
                ret[name] = "None"
                continue

            parts = re.split(p, line)
            if len(parts) < 2:
                print("WARNING: Skipping an ImageMagick line [%s] due to inconsistent formatting." % line)
                continue
            name = parts[0]
            value = parts[1]
            try:
                if not Common.IS_Pv3:
                    if isinstance(value, unicode):
                        value = value.encode('utf-8', 'ignore')
                    else:
                        value = unicode(value, errors='ignore').encode('utf-8')

                ret[name] = value
                names.add(name)
            except Exception as e:
                print("WARNING: Cannot handle line [%s] with error: " % line, e)


        if names:
            ret['__keys__'] = list(names)


        return ret



    def get_tactic_mapping(self):
        return {
            'format_description': 'Format',
            'colorspace': 'Colorspace',
            'depth': 'Depth',
        }


    def process_tactic_mapping(self, tactic_data, metadata):

        geometry = metadata.get("Geometry")

        if geometry:
            if not isinstance(geometry, six.string_types):
                geometry = str(geometry)
                
            p = re.compile(r"(\d+)x(\d+)\+(\d+)\+(\d+)")
            m = p.match(geometry)
            if m:
                groups = m.groups()
                tactic_data['width'] = float(groups[0])
                tactic_data['height'] = float(groups[1])
        



class FFProbeMetadataParser(BaseMetadataParser):
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def get_initial_data(self):
        return {
            'media_type': 'video',
            'parser': 'FFProbe'
        }


    def get_title(self):
        return "FFProbe"

    def get_metadata(self):
        path = self.kwargs.get("path")
        if not HAS_FFMPEG:
            raise ParserImportError("Unable to import FFMPEG parser.")
        out = self.probe_file(path)

        # sanitize output
        
        out = self.sanitize_data(out)

        metadata = self.parse_output(out)

        return metadata

        
        


    def probe_file(self, fpath):
        cmd = [ffprobe_exe, '-show_streams', '-pretty', '-loglevel', 'quiet', fpath]
        return subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=True, timeout=self.kwargs.get('timeout', 30)).stdout


    def parse_output(self, out):

        index = 0
        metadata_list = {}

        metadata = {}
        data = {}
        out = out.decode('utf-8', errors='replace')

        for line in out.split("\n"):
            if line.find("STREAM") != -1:
                continue
            if not line:
                continue

            line = line.strip()
            parts = line.split("=", 1)
            if len(parts) < 2:
                continue

            name = parts[0]
            value = parts[1]

            if name == "index":
                index = value
                data = {}

            elif name == "codec_type":
                metadata[value] = data

            data[str(name)] = str(value)

        flat_metadata = {}
        for prefix, data in metadata.items():
            for name, value in data.items():
                key = "%s:%s" % (prefix, name)
                flat_metadata[key] = value

        return flat_metadata


    def get_tactic_mapping(self):
        return {
            'width': 'video:width',
            'height': 'video:height',
            'frames': 'video:nb_frames',
            'fps': 'video:r_frame_rate',
            'codec': 'video:codec_name',
            'video_codec': 'video:codec_name',
            'video_bitrate': 'video:bit_rate',
            'audio_codec': 'audio:codec_name',
            'audio_bitrate': 'audio:bit_rate',
        }

class XMPKeywordsParser(BaseMetadataParser):

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def get_title(self):
        return "XMP Keywords"


    def get_initial_data(self):
        return {
            'media_type': 'image',
            'parser': 'XMP Keywords'
        }

    def check_xmpmetadata(self):
        '''Look for an x:xmpmeta tag within the first 512000 bytes.'''
        with open(self.kwargs.get('path'), 'rb') as source:
            return b'<x:xmpmeta' in source.read(512000)

    def get_metadata(self):
        '''Extract lowercase Lightroom keywords from at most 1 MB of XMP XML.'''

        with open(self.kwargs.get('path'), 'rb') as source:
            data = source.read(512000)
            start = data.find(b'<x:xmpmeta')
            if start < 0:
                return {'keywords': ''}
            data = data[start:]
            closing = b'</x:xmpmeta>'
            if closing not in data:
                data += source.read(1024 * 1024 - len(data))
        end = data.find(closing)
        if end < 0:
            raise ValueError('XMP metadata is incomplete or exceeds 1 MB')
        # Keep XML namespaces and real UTF-8 bytes; str(bytes) broke this on Python 3.
        xml = data[:end + len(closing)]
        if b'<!DOCTYPE' in xml or b'<!ENTITY' in xml:
            raise ValueError('DTD/entities are not accepted')
        root = ET.fromstring(xml)
        keywords = []
        for subject in root.iter():
            if isinstance(subject.tag, str) and subject.tag.rsplit('}', 1)[-1] == 'subject':
                for node in subject.iter():
                    if isinstance(node.tag, str) and node.tag.rsplit('}', 1)[-1] == 'li' and node.text:
                        keywords.append(node.text.lower())
        return {'keywords': ' '.join(keywords)}

