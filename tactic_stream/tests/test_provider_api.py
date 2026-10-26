"""Provider wire formats and destination binding without paid API calls."""
import unittest
from unittest.mock import patch

try:
    from tactic_stream import provider_api as api
except ImportError:
    api=None


@unittest.skipIf(api is None,'Install tactic-stream[agent] for provider tests')
class Protocols(unittest.TestCase):
    def test_all_four_tool_protocols_keep_native_ids_and_content(self):
        tools=[dict(name='ts_records',description='Fixture reader',schema=dict(type='object',properties={}))]
        cases={
            'local':dict(choices=[dict(message=dict(role='assistant',content='Reading',tool_calls=[dict(id='c1',type='function',function=dict(name='ts_records',arguments='{}'))]))]),
            'openai':dict(output=[dict(type='reasoning',id='reason',summary=[]),dict(type='function_call',call_id='c1',name='ts_records',arguments='{}')]),
            'anthropic':dict(content=[dict(type='thinking',thinking='private reasoning',signature='fixture'),dict(type='tool_use',id='c1',name='ts_records',input={})]),
            'gemini':dict(candidates=[dict(content=dict(role='model',parts=[dict(functionCall=dict(name='ts_records',args={}),thoughtSignature='fixture')]))]),
        }
        for kind,response in cases.items():
            with self.subTest(kind=kind):
                profile=dict(id='fixture',kind=kind,url='http://127.0.0.1/v1' if kind=='local' else 'https://api.example/v1',enabled=True,secret='private-fixture')
                target={key:profile[key] for key in ('id','kind','url')}
                history=[api.user_message(kind,[dict(type='text',text='Public fixture task')])]
                with patch.object(api,'request',return_value=response) as send:
                    message,calls,text=api.generate(profile,'fixture-model','Bound task instructions',history,tools,target)
                self.assertEqual(calls[0]['name'],'ts_records')
                self.assertEqual(calls[0]['arguments'],{})
                self.assertNotIn('private-fixture',str(send.call_args.args[2]))
                self.assertNotIn('private reasoning',text)
                if kind=='gemini':self.assertIn('thoughtSignature',str(message))
                if kind=='openai':self.assertEqual(message[0]['type'],'reasoning')
                result=api.tool_result(kind,calls[0],dict(objects=[]))
                self.assertTrue(result)

    def test_changed_destination_or_disabled_profile_never_sends(self):
        profile=dict(id='p',kind='local',url='http://127.0.0.1:1234/v1',enabled=True)
        target=dict(id='p',kind='local',url='http://127.0.0.1:1235/v1')
        with patch.object(api,'request') as send:
            with self.assertRaisesRegex(ValueError,'destination changed'):
                api.generate(profile,'m','instructions',[],[],target)
            with self.assertRaisesRegex(ValueError,'destination changed'):
                api.generate(dict(profile,enabled=False),'m','instructions',[],[],profile)
        send.assert_not_called()

    def test_images_remain_image_parts_and_catalogue_reads_have_no_chat(self):
        for kind in ('local','compatible','openai','anthropic','gemini'):
            value=api.user_message(kind,[dict(type='text',text='Fixture'),dict(type='image',url='data:image/png;base64,ZmFrZQ==')])
            parts=value.get('content',value.get('parts'))
            self.assertEqual(len(parts),2)
            self.assertNotEqual(parts[1].get('type'),'text')
        with patch.object(api,'request',return_value=dict(data=[dict(id='fixture-model')])) as send:
            models=api.models(dict(kind='local',url='http://127.0.0.1:1234/v1'))
        self.assertEqual(models[0]['id'],'fixture-model')
        self.assertEqual(len(send.call_args.args),2)
