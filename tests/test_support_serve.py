import threading
import unittest
from qwenlab.serve import create_app, validate_input, POLICY_HASH, PROTOCOL


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
