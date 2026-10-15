"""Messages and shared Inspector windows against a private, disposable server."""
import os
import shutil
import subprocess
import unittest
import io
import json
import uuid
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from test_foundation import ROOT
import test_transport


class Collaboration(unittest.TestCase):
    def setUp(self):
        test_transport.Transport.setUpClass()
        self.url = test_transport.Transport.url
        self.addCleanup(test_transport.Transport.tearDownClass)

    def browser(self, script, timeout=120):
        result = subprocess.run([shutil.which('node'), str(ROOT / 'frontend/tests' / script), test_transport.Transport.url],
            cwd=ROOT / 'frontend', env=dict(os.environ, PLAYWRIGHT_BROWSERS_PATH=str(ROOT / '.browser-cache'),
            STREAM_CHECK_PASSWORD='private-test-password', STREAM_CHECK_PROJECT='one'),
            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_messages_in_chromium(self):
        self.browser('messages.mjs', 180)

    def test_common_windows_in_chromium(self):
        self.browser('window_controls.mjs')

    def test_global_profile_links_and_own_avatar(self):
        from pyasm.security.authenticator import hash_password
        with test_transport.Transport.proxy(self) as proxy:
            admin = dict(ticket=proxy.get_ticket('admin','private-test-password'),project='one')
            rules = '<rules><rule group="project" code="one" access="allow"/>'
            rules += ''.join('<rule group="search_type" code="%s" access="%s"/>' % pair for pair in
                [('sthpw/login','view'),('sthpw/login_group','view'),('sthpw/login_in_group','view'),
                 ('sthpw/snapshot','edit'),('sthpw/file','edit'),('contract/entity','view')]) + '</rules>'
            proxy.insert(admin,'sthpw/login_group',dict(code='collaboration',login_group='collaboration',access_rules=rules))
            proxy.insert(admin,'sthpw/login',dict(code='collaborator',login='collaborator',password=hash_password('collaboration-password')))
            proxy.insert(admin,'sthpw/login_in_group',dict(login='collaborator',login_group='collaboration'))
            auth = dict(ticket=proxy.get_ticket('collaborator','collaboration-password'),project='')
            def read(path,expected=200,**values):
                request = Request(test_transport.Transport.url+path,data=json.dumps(dict(auth,**values)).encode(),headers={'Content-Type':'application/json'})
                try: response = urlopen(request,timeout=20)
                except HTTPError as error: response = error
                with response:
                    result = json.load(response); self.assertEqual(response.status,expected,result)
                    return result.get('result',result)
            profile = read('/admin/user-profile/read',login='collaborator')
            self.assertEqual(profile['profile']['login'],'collaborator')
            self.assertTrue(profile['permissions']['edit']); self.assertFalse(profile['permissions']['manage'])
            read('/admin/navigation-link',expected=400,link='skey://contract/entity?project=one&code=A')
            link = read('/admin/navigation-link',project='one',link='skey://contract/entity?project=one&code=A')
            self.assertEqual(link['object']['code'],'A')
            read('/admin/navigation-link',expected=403,project='two',link='skey://contract/entity?project=two&code=A')
            boundary='collaboration-avatar'
            body=b''
            for name,value in dict(auth,login='collaborator',token=str(uuid.uuid4()),revision=profile['revision']).items():
                body+=('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n' % (boundary,name,value)).encode()
            from PIL import Image
            image=io.BytesIO(); Image.new('RGB',(16,16),'blue').save(image,format='PNG'); png=image.getvalue()
            body+=('--%s\r\nContent-Disposition: form-data; name="file"; filename="avatar.png"\r\nContent-Type: image/png\r\n\r\n' % boundary).encode()+png+('\r\n--%s--\r\n' % boundary).encode()
            request=Request(test_transport.Transport.url+'/admin/user-profile/avatar',data=body,headers={'Content-Type':'multipart/form-data; boundary='+boundary})
            with urlopen(request,timeout=20) as response: self.assertEqual(response.status,200)
            avatar=read('/admin/user-profile/read',login='collaborator')['profile']['avatarUrl']
            self.assertTrue(avatar)
            with urlopen(request,timeout=20) as response: self.assertEqual(response.status,200)
            self.assertEqual(read('/admin/user-profile/read',login='collaborator')['profile']['avatarUrl'],avatar)
            forbidden=body.replace(b'name="login"\r\n\r\ncollaborator\r\n',b'name="login"\r\n\r\nadmin\r\n')
            with self.assertRaises(HTTPError) as failure:
                urlopen(Request(request.full_url,data=forbidden,headers={'Content-Type':'multipart/form-data; boundary='+boundary}),timeout=20)
            self.assertEqual(failure.exception.code,403); failure.exception.close()
