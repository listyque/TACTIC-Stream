"""Real HTTP config/url resolution with normal project/URL/object permissions."""
import json
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import test_transport
from pyasm.security.authenticator import hash_password


class CustomUrls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_transport.Transport.setUpClass()
        cls.url = test_transport.Transport.url

    @classmethod
    def tearDownClass(cls):
        test_transport.Transport.tearDownClass()

    def post(self, auth, path, status=200, **values):
        payload = dict(auth, path=path, **values)
        try:
            response = urlopen(Request(self.url + '/admin/custom-url', data=json.dumps(payload).encode(),
                headers={'Content-Type': 'application/json'}), timeout=10)
        except HTTPError as error:
            response = error
        with response:
            self.assertEqual(response.status, status, response.read() if response.status != status else '')
            body = json.load(response)
        return body.get('result', body)

    def insert(self, proxy, auth, path, options='', handler='tactic.ui.panel.ViewPanelWdg'):
        return proxy.insert(auth, 'config/url', dict(url=path, description='Review page',
            widget=f'<element><display class="{handler}">{options}</display></element>'))

    def test_custom_page_patterns_literals_object_filter_and_http_entry(self):
        with test_transport.Transport.proxy(self) as proxy:
            auth = dict(ticket=proxy.get_ticket('admin', 'private-test-password'), project='one')
            self.insert(proxy, auth, '/review/{code}', '<search_type>contract/entity</search_type>'
                '<search_key>contract/entity?project=one&amp;code={code}</search_key>')
            resolved = self.post(auth, '/review/A', parameters=dict(code='not-the-path'))
            self.assertEqual((resolved['search_type'], resolved['filterField'], resolved['filterValue']), ('contract/entity', 'code', 'A'))
            self.assertIn('code=A', resolved['options']['search_key'])
            exact = self.insert(proxy, auth, '/review/A', '<search_type>contract/entity</search_type><view>definition</view>')
            self.assertEqual(self.post(auth, '/review/A')['view'], 'definition')
            proxy.update(auth, exact['__search_key__'], dict(s_status='retired'))
            self.assertEqual(self.post(auth, '/review/A')['filterValue'], 'A')
            self.insert(proxy, auth, '/literal.+', '<search_type>contract/entity</search_type>')
            self.assertEqual(self.post(auth, '/literal.+')['path'], '/literal.+')
            self.post(auth, '/literalZZ', 400)
            self.insert(proxy, auth, '/layout/{name}', '<view>review.page</view><label>{name}</label>', 'tactic.ui.panel.CustomLayoutWdg')
            value = self.post(auth, '/layout/Страница & <test>')
            self.assertEqual(value['layoutView'], 'review.page')
            self.assertEqual(value['options']['label'], 'Страница & <test>')
            for prefix in ('/projects/one', '/tactic/one'):
                with urlopen(Request(self.url + prefix + '/review/A', headers={'Accept':'text/html'})) as response:
                    self.assertIn(b'<html', response.read())
            self.insert(proxy, auth, '/review/{another}', '<search_type>contract/entity</search_type>')
            self.post(auth, '/review/A', 400)

    def test_no_script_execution_or_anonymous_cross_project_or_denied_url_access(self):
        with test_transport.Transport.proxy(self) as proxy:
            auth = dict(ticket=proxy.get_ticket('admin', 'private-test-password'), project='one')
            self.insert(proxy, auth, '/public', '<search_type>contract/entity</search_type>')
            self.insert(proxy, auth, '/rest', '<script_path>must/not/run</script_path>', 'tactic.protocol.PythonRestHandler')
            self.post(auth, '/rest', 501)
            self.post(dict(auth, ticket='expired'), '/public', 403)
            proxy.insert(auth, 'sthpw/login', dict(login='url_reader', password=hash_password('reader-password')))
            reader = dict(ticket=proxy.get_ticket('url_reader', 'reader-password'), project='one')
            self.post(reader, '/public', 403)
            group = proxy.insert(auth, 'sthpw/login_group', dict(login_group='url_access', access_rules=
                '<rules><rule group="project" code="one" access="allow"/>'
                '<rule group="search_type" code="contract/entity" project="one" access="view"/></rules>'))
            proxy.insert(auth, 'sthpw/login_in_group', dict(login='url_reader', login_group='url_access'))
            self.assertEqual(self.post(reader, '/public')['search_type'], 'contract/entity')
            proxy.update(auth, group['__search_key__'], dict(access_rules=
                '<rules><rule group="project" code="one" access="allow"/>'
                '<rule group="url" key="/tactic/one/public" access="deny"/></rules>'))
            self.post(reader, '/public', 403)
            for path in (None, 'relative', '/a/../public', '/public\n', '/public?code=A'):
                self.post(auth, path, 400)
            self.post(auth, '/public', 400, parameters=dict(code=['array']))
            self.insert(proxy, auth, '/foreign', '<search_type>contract/entity?project=two</search_type>')
            self.post(auth, '/foreign', 400)
            malformed = self.insert(proxy, auth, '/broken')
            proxy.update(auth, malformed['__search_key__'], dict(widget='<element>'))
            self.post(auth, '/broken', 400)

    def rest(self, auth, path, method='GET', data=None, status=200):
        headers={'Authorization':'Bearer '+auth['ticket'],'Content-Type':'application/json'}
        body=json.dumps(data).encode() if data is not None else None
        try:
            response=urlopen(Request(self.url+'/projects/one'+path,data=body,headers=headers,method=method),timeout=10)
        except HTTPError as error:
            response=error
        with response:
            value=json.load(response)
            self.assertEqual(response.status,status,value)
        return value

    def test_configured_rest_uses_native_api_rights_and_rolls_back_late_failure(self):
        with test_transport.Transport.proxy(self) as proxy:
            auth=dict(ticket=proxy.get_ticket('admin','private-test-password'),project='one')
            self.insert(proxy,auth,'/api','',handler='tactic.protocol.APIRestHandler')
            self.assertEqual(self.rest(auth,'/api'),'TACTIC REST Interface')
            rows=self.rest(auth,'/api','POST',dict(method='query',search_type='contract/entity',filters=[['code','A']]))
            self.assertEqual(rows[0]['code'],'A')
            self.rest(auth,'/api','POST',dict(method='set_ticket',args=['stolen']),400)
            self.insert(proxy,auth,'/script/{code}','<script_path>rest/echo</script_path>',handler='tactic.protocol.PythonRestHandler')
            proxy.insert(auth,'config/custom_script',dict(folder='rest',title='echo',language='python',script=
                "from pyasm.common import Container\nreturn dict(code=kwargs['code'],method=kwargs['Method'],body=Container.get('REST:body'))"))
            for method in ('GET','POST','PUT','DELETE'):
                value=self.rest(auth,'/script/A?script_path=wrong/path',method,dict(note='Body') if method!='GET' else None)
                self.assertEqual(value['code'],'A')
                self.assertEqual(value['method'],method)
            self.insert(proxy,auth,'/fail','<script_path>rest/fail</script_path>',handler='tactic.protocol.PythonRestHandler')
            original=proxy.get_by_code(auth,'contract/entity','A')
            proxy.insert(auth,'config/custom_script',dict(folder='rest',title='fail',language='python',script=
                "from pyasm.common import Environment\nfrom pyasm.search import FileUndo\n"
                "server.update('contract/entity?project=one&code=A', {'name':'MUST_ROLL_BACK'})\n"
                "FileUndo.mkdir(Environment.get_data_dir()+'/rest_rollback_directory')\nraise RuntimeError('late REST failure')"))
            self.rest(auth,'/fail','POST',{},500)
            self.assertEqual(proxy.get_by_code(auth,'contract/entity','A')['name'],original['name'])
            self.assertFalse((test_transport.Transport.store.data_dir/'rest_rollback_directory').exists())
            proxy.insert(auth,'sthpw/login',dict(login='rest_reader',password=hash_password('reader-password')))
            reader=dict(ticket=proxy.get_ticket('rest_reader','reader-password'),project='one')
            group=proxy.insert(auth,'sthpw/login_group',dict(login_group='rest_access',access_rules=
                '<rules><rule group="project" code="one" access="allow"/>'
                '<rule group="search_type" code="contract/entity" project="one" access="view"/></rules>'))
            proxy.insert(auth,'sthpw/login_in_group',dict(login='rest_reader',login_group='rest_access'))
            self.rest(reader,'/script/A',status=403)
            self.assertEqual(self.rest(reader,'/api','POST',dict(method='query',args=['contract/entity'],kwargs=dict(filters=[['code','A']])))[0]['code'],'A')
            self.rest(reader,'/api','POST',dict(method='update',args=[original['__search_key__'],dict(name='DENIED')]),403)
            proxy.update(auth,group['__search_key__'],dict(access_rules=
                '<rules><rule group="project" code="one" access="allow"/>'
                '<rule group="api_cmd" key="tactic.command.PythonCmd" access="allow"/></rules>'))
            self.assertEqual(self.rest(reader,'/script/A')['code'],'A')
            self.rest(dict(auth,ticket='expired'),'/script/A',status=403)
