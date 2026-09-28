import threading
import unittest
from unittest.mock import patch
from qwenlab.serve import create_app, validate_input, POLICY_HASH, PROTOCOL, SPEC, TASKS, QwenEngine


class Engine:
    def metadata(self):
        return {'model': 'unit-test', 'adapter': 'fixture', 'projection': 'candidate'}
    def predict(self, value):
        return {'predictions': {}, 'inferenceMs': 1}


class SupportServeTests(unittest.TestCase):
    def body(self):
        return {'protocolVersion': PROTOCOL, 'policyHash': POLICY_HASH,
                'input': {'message': '查信用分', 'history': [], 'state': {'authenticated': True}, 'available_tools': ['queryMyCreditScore']}}

    def test_auth_and_protocol(self):
        app = create_app(Engine(), 'local-test')
        with app.test_client() as client:
            self.assertEqual(client.get('/ready').status_code, 401)
            headers = {'Authorization': 'Bearer local-test'}
            self.assertTrue(client.get('/ready', headers=headers).json['ready'])
            body = self.body(); body['policyHash'] = 'wrong'
            self.assertEqual(client.post('/decide', json=body, headers=headers).status_code, 409)
            self.assertEqual(client.post('/decide', json=self.body(), headers=headers).status_code, 200)

    def test_limits_and_no_images_or_identity(self):
        for extra in ({'images': ['anything']}, {'state': {'authenticated': True, 'userphone': 'private'}}, {'message': 'x' * 2001}, {'available_tools': ['deleteUser']}, {'history': [{}] * 5}):
            with self.assertRaises(ValueError):
                validate_input({**self.body()['input'], **extra})
        self.assertEqual(create_app(Engine()).test_client().post('/decide', data='x'*40000, content_type='application/json').status_code, 413)

    def test_pending_status_code_keeps_state_validation(self):
        body = self.body()
        body['input']['state'].update(pending='statusCode', status_code=2)
        self.assertEqual(create_app(Engine()).test_client().post('/decide', json=body).status_code, 200)
        for extra in ({'pending': 'unknown'}, {'pending': []}, {'status_code': True}, {'status_code': '2'}, {'status_code': -1}):
            with self.assertRaises(ValueError):
                validate_input({**body['input'], 'state': {**body['input']['state'], **extra}})

    def test_prediction_uses_startup_policy_snapshot_without_gpu(self):
        import torch
        from qwenlab.joint_v5 import encode

        class CpuBatch(dict):
            def to(self, device):
                self_device.append(device)
                return self  # The fake scorer consumes no CUDA tensors.

        class Tokenizer:
            def __init__(self): self.messages = []
            def encode(self, text, **kwargs): return [ord(text)]
            def apply_chat_template(self, messages, **kwargs):
                self.messages.append(messages)
                return 'test input'
            def __call__(self, text, **kwargs): return {'input_ids': [1], 'attention_mask': [1]}
            def pad(self, tokens, **kwargs): return CpuBatch()

        class Scorer:
            def scores(self, inputs, ids): return torch.zeros((1, len(ids)))

        self_device = []
        engine = QwenEngine.__new__(QwenEngine)
        engine.encode, engine.tok, engine.scorer = encode, Tokenizer(), Scorer()
        # Any reload would permit policy drift after the service advertised its hash.
        with patch('qwenlab.joint_v5.load_json', side_effect=AssertionError('Policy must not be reread')), \
                patch('torch.cuda.synchronize'):
            result = engine.predict(self.body()['input'])
        self.assertEqual(len(self_device), len(TASKS))
        for task, messages in zip(TASKS, engine.tok.messages):
            self.assertTrue(messages[0]['content'].startswith(SPEC['policy']))
            self.assertEqual(list(result['predictions'][task]['probabilities']), list(SPEC['questions'][task]['criteria']))

        # Ordinary experiment callers still load their original policy by default.
        row = {'id': 'test', 'dataset': 'business', 'message': 'test', 'labels': {'intent': 'general'}}
        with patch('qwenlab.joint_v5.load_json', return_value=SPEC) as read:
            encode(engine.tok, row, 'intent')
            read.assert_called_once()

    def test_concurrency_and_error_recovery(self):
        entered, release = threading.Event(), threading.Event()
        class Slow(Engine):
            def predict(self, value):
                entered.set(); release.wait(3)
                return super().predict(value)
        app = create_app(Slow())
        thread = threading.Thread(target=lambda: app.test_client().post('/decide', json=self.body()))
        thread.start(); self.assertTrue(entered.wait(2))
        try:
            self.assertEqual(app.test_client().post('/decide', json=self.body()).status_code, 503)
        finally:
            release.set(); thread.join()
        self.assertEqual(app.test_client().post('/decide', json=self.body()).status_code, 200)
        class Broken(Engine):
            def predict(self, value):
                raise RuntimeError('private details must not appear')
        response = create_app(Broken()).test_client().post('/decide', json=self.body())
        self.assertEqual(response.json, {'error': 'INFERENCE_FAILED'})


if __name__ == '__main__':
    unittest.main()
