###########################################################
#
# Copyright (c) 2005, Southpaw Technology
#                     All Rights Reserved
#
#
#

__all__ = ['UploadMultipart', 'TacticUploadException']

import socket
import base64

try:
    import urlparse
except:
    from urllib import parse as urlparse

try:
    import httplib
except:
    from http import client as httplib


import os, sys

class TacticUploadException(Exception):
    pass

class UploadMultipart(object):
    '''Handles the multipart content type for uploading files.  Will break up
    a file into chunks and upload separately for huge files'''

    def __init__(self):
        self.tries = 0
        self.chunk_size = 10*1024*1024
        self.ticket = None
        self.subdir = None

        self.server_url = None

        self.offset = 0


    def set_offset(self, offset):
        self.offset = offset


    def set_upload_server(self, server_url):
        self.server_url = server_url


    def set_chunk_size(self, size):
        '''set the chunk size of each upload'''
        self.chunk_size = size

    def set_ticket(self, ticket):
        '''set the ticket for security'''
        self.ticket = ticket

    def set_subdir(self, subdir):
        self.subdir = subdir


    def execute(self, path):
        if not self.server_url or not isinstance(self.chunk_size, int) or self.chunk_size <= 0:
            raise ValueError("An upload URL and positive chunk size are required")
        if not isinstance(self.offset, int) or self.offset < 0:
            raise ValueError("Upload offset must be a nonnegative chunk index")
        with open(path, 'rb') as f:
            f.seek(self.offset * self.chunk_size)
            while True:
                buffer = f.read(self.chunk_size)
                if not buffer and (self.offset or f.tell()):
                    break
                action = "create" if self.offset == 0 else "append"
                fields = [("ajax", "true"), ("action", action)]
                if self.ticket:
                    fields.extend([("ticket", self.ticket), ("login_ticket", self.ticket)])
                from json import dumps
                fields.append(("file_name0", dumps(os.path.basename(path), ensure_ascii=True)[1:-1]))
                if self.subdir:
                    fields.append(("subdir", self.subdir))
                status, reason, content = self.upload(self.server_url, fields, [("file", path, buffer)])
                if status != 200:
                    raise TacticUploadException("Upload of '%s' failed: %s %s" % (path, status, reason))
                self.offset += 1
                if not buffer:
                    break


    def upload(self, url, fields, files):

        # Append has no idempotency token in the original protocol: retrying may duplicate bytes.
        attempts = 5 if dict(fields).get('action') == 'create' else 1
        for attempt in range(attempts):
            try:
                result = self.posturl(url, fields, files)
            except (OSError, httplib.HTTPException) as error:
                if attempt + 1 == attempts:
                    raise TacticUploadException("Upload connection failed") from error
            else:
                if result[0] != 200:
                    raise TacticUploadException("Upload failed: %s %s" % result[:2])
                return result


    # Repurposed from:
    # http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/146306

    def posturl(self, url, fields, files):
        #print("URL ", url)
        urlparts = urlparse.urlsplit(url)
        protocol = urlparts[0]
 
        return self.post_multipart(urlparts[1], urlparts[2], fields,files, protocol)
                


    def post_multipart(self, host, selector, fields, files, protocol):
        '''
        Post fields and files to an http host as multipart/form-data.
        fields is a sequence of (name, value) elements for regular form fields.
        files is a sequence of (name, filename, value) elements for data to be uploaded as files.dirk.noteboom@sympatico.ca
        '''
        content_type, body = self.encode_multipart_formdata(fields, files)
        if protocol == 'https':
            h = httplib.HTTPSConnection(host, timeout=60)  
        else:
            h = httplib.HTTPConnection(host, timeout=60)  
        headers = {
            'User-Agent': 'Tactic Client',
            'Content-Type': content_type
            }

        # prevent upgrading the method + url in the httplib module to turn it 
        # into a unicode string before sending the request
        selector = str(selector)
        try:
            h.request('POST', selector, body.encode('utf-8'), headers)
            res = h.getresponse()
            return res.status, res.reason, res.read()
        finally:
            h.close()    


    def encode_multipart_formdata(self, fields, files):
        '''
        fields is a sequence of (name, value) elements for regular form fields.
        files is a sequence of (name, filename, value) elements for data to be uploaded as files.
        Return (content_type, body) ready for httplib.HTTPConnection instance
        '''
        from json import dumps
        files = [(key, dumps(filename, ensure_ascii=True)[1:-1], value) for key, filename, value in files]
        BOUNDARY = '----------ThIs_Is_tHe_bouNdaRY_---$---'
        CRLF = '\r\n'
        L = []

        mode = "base64"
        if mode != "base64":
            CRLF = CRLF.encode("UTF8")

        try:
            from cStringIO import StringIO as Buffer
        except:
            if mode == "base64":
                from io import StringIO as Buffer
            else:
                from io import BytesIO as Buffer


        import sys
        for (key, value) in fields:
            L.append('--' + BOUNDARY)
            L.append('Content-Disposition: form-data; name="%s"' % key)
            L.append('')
            L.append(value)
        for (key, filename, value) in files:
            #print("len of value: ", len(value))
            L.append('--' + BOUNDARY)
            L.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, filename))
            L.append('')


            if mode == "base64":
                # put in a fake header to show that it is base64 to the server
                L.append("data:xyz/xyz;base64,")
                L.append(base64.b64encode(value))
            else:
                L.append(value)
        L.append('--' + BOUNDARY + '--')
        L.append('')

        M = []
        for l in L:
            try:
                if mode == "binary":
                    l = l.encode("UTF8")
                    #l = bytes(l)
                else:
                    l = l.decode()
            except UnicodeDecodeError as e:
                pass
            except AttributeError as e:
                pass
            M.append(l)
            M.append(CRLF)

        # This fails
        #body = "".join(M)

        buf = Buffer()
        buf.writelines(M)
        body = buf.getvalue()
        #print("len of body: ", len(body), type(body))

        content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
        return content_type, body 





