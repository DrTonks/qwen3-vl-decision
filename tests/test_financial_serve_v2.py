import copy
import threading
import unittest

from qwenlab.financial_serve_v2 import FixtureEngine, create_app, protocol, validate_input


class FinancialServeTests(unittest.TestCase):
    def setUp(self):
        self.spec, self.digest = protocol()
        self.headers = {'Authorization': 'Bearer test-only-token'}
        self.value = dict(message='请查询我的申请', history=[], state={'authenticated': True},
                          service_scope='loan_platform', capability_profile='current-node-no-kb',
                          capabilities={'knowledge_collections': [], 'handoff_available': False},
                          available_tools=list(self.spec['tools']), images=[])

    def body(self, task='action'):
        return dict(protocolVersion=self.spec['protocolVersion'], policyHash=self.digest, task=task, input=copy.deepcopy(self.value))

    def engine(self, action='answer'):
        return FixtureEngine(self.spec, self.digest, action, 'queryMyApplications')

    def test_all_actions_and_separate_tool_request(self):
        for action in self.spec['actions']:
            with self.subTest(action=action):
                client = create_app(self.engine(action), 'test-only-token').test_client()
                result = client.post('/decide', json=self.body(), headers=self.headers)
                self.assertEqual(result.status_code, 200)
                self.assertEqual(result.json['prediction']['choice'], action)
                self.assertTrue(result.json['fixture'])
                self.assertTrue(result.json['experimental'])
        result = client.post('/decide', json=self.body('tool'), headers=self.headers)
        self.assertEqual(result.json['prediction']['choice'], 'queryMyApplications')

    def test_protocol_token_and_legacy_engine_rejected(self):
        with self.assertRaises(ValueError):
            create_app(self.engine(), '')
        with self.assertRaises(ValueError):
            create_app(self.engine(), '测试')
        bad = self.engine(); bad.policy_hash = 'legacy'
        with self.assertRaises(ValueError):
            create_app(bad, 'test-only-token')
        client = create_app(self.engine(), 'test-only-token').test_client()
        self.assertEqual(client.get('/ready').status_code, 401)
        self.assertEqual(client.get('/ready', headers={'Authorization': 'Bearer 测试'}).status_code, 401)
        self.assertTrue(client.get('/ready', headers=self.headers).json['fixture'])
        body = self.body(); body['protocolVersion'] = 'support-classifier-v1'
        self.assertEqual(client.post('/decide', json=body, headers=self.headers).status_code, 409)
        body = self.body(); body['policyHash'] = 'wrong'
        self.assertEqual(client.post('/decide', json=body, headers=self.headers).status_code, 409)

    def test_identity_capability_and_limits(self):
        changes = [dict(images=['file']), dict(state={'authenticated': True, 'userphone': 'private'}),
                   dict(state={'authenticated': True, 'application_id': True}), dict(message='a' * 2001), dict(message=' ' + 'a' * 2000 + ' '),
                   dict(history=[{}] * 5), dict(available_tools=['deleteUser']),
                   dict(capabilities={'knowledge_collections': ['loan_service_docs'], 'handoff_available': False}),
                   dict(capabilities={'knowledge_collections': [], 'handoff_available': True})]
        client = create_app(self.engine(), 'test-only-token').test_client()
        for change in changes:
            body = self.body(); body['input'].update(change)
            with self.subTest(change=change):
                self.assertEqual(client.post('/decide', json=body, headers=self.headers).status_code, 400)
        body = self.body('tool'); body['input']['state']['authenticated'] = False
        self.assertEqual(client.post('/decide', json=body, headers=self.headers).status_code, 400)
        self.assertEqual(client.post('/decide', data='x' * 40000, content_type='application/json', headers=self.headers).status_code, 413)

    def test_malformed_predictions_do_not_escape(self):
        for bad_result in [dict(choice='deleteUser', probabilities={}), dict(choice='answer', probabilities={'answer': float('nan')}),
                           dict(choice='answer', probabilities={a: 1 for a in self.spec['actions']})]:
            engine = self.engine(); engine.predict = lambda value, task: bad_result
            client = create_app(engine, 'test-only-token').test_client()
            self.assertEqual(client.post('/decide', json=self.body(), headers=self.headers).json, {'error': 'INFERENCE_FAILED'})
        engine = self.engine()
        client = create_app(engine, 'test-only-token').test_client()
        body = self.body('tool'); body['input']['available_tools'] = ['queryMyCreditScore']
        self.assertEqual(client.post('/decide', json=body, headers=self.headers).status_code, 503)

    def test_busy_and_recovery_do_not_queue_gpu_work(self):
        entered, release = threading.Event(), threading.Event()
        engine = self.engine(); original = engine.predict
        def slow(value, task):
            entered.set(); release.wait(3)
            return original(value, task)
        engine.predict = slow
        app = create_app(engine, 'test-only-token')
        thread = threading.Thread(target=lambda: app.test_client().post('/decide', json=self.body(), headers=self.headers))
        thread.start()
        try:
            self.assertTrue(entered.wait(2))
            self.assertEqual(app.test_client().post('/decide', json=self.body(), headers=self.headers).json, {'error': 'BUSY'})
        finally:
            release.set(); thread.join()
        self.assertEqual(app.test_client().post('/decide', json=self.body(), headers=self.headers).status_code, 200)


if __name__ == '__main__':
    unittest.main()
