"""
AjaiaDocs — test suite (stdlib unittest)
Run: python test_server.py -v
"""
import os
import sys
import io
import json
import unittest
import tempfile

_tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
_tmp.close()
os.environ['DB_PATH'] = _tmp.name
sys.path.insert(0, os.path.dirname(__file__))

import server
from server import app, init_db

ALICE = 'token-alice-123'
BOB   = 'token-bob-456'

def auth(token):
    return {'Authorization': f'Bearer {token}'}


class BaseTest(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        with app.app_context():
            init_db()

    def post_json(self, path, data, token=ALICE):
        return self.client.post(path, json=data,
            headers=auth(token), content_type='application/json')

    def put_json(self, path, data, token=ALICE):
        return self.client.put(path, json=data,
            headers=auth(token), content_type='application/json')


class TestAuth(BaseTest):
    def test_login_valid(self):
        r = self.post_json('/api/auth/login', {'email': 'alice@test.com'})
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.data)
        self.assertEqual(data['token'], ALICE)
        self.assertEqual(data['user']['name'], 'Alice Chen')

    def test_login_unknown_email(self):
        r = self.post_json('/api/auth/login', {'email': 'nobody@test.com'})
        self.assertEqual(r.status_code, 404)

    def test_me(self):
        r = self.client.get('/api/auth/me', headers=auth(ALICE))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(json.loads(r.data)['email'], 'alice@test.com')

    def test_missing_token_rejected(self):
        r = self.client.get('/api/auth/me')
        self.assertEqual(r.status_code, 401)


class TestDocuments(BaseTest):
    def _create(self, title='Test Doc', token=ALICE):
        r = self.post_json('/api/documents', {'title': title, 'content': ''}, token)
        self.assertEqual(r.status_code, 201)
        return json.loads(r.data)

    def test_create_and_fetch(self):
        doc = self._create('My Doc')
        r = self.client.get(f'/api/documents/{doc["id"]}', headers=auth(ALICE))
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.data)
        self.assertEqual(data['title'], 'My Doc')
        self.assertEqual(data['relation'], 'owned')

    def test_rename(self):
        doc = self._create('Old Name')
        r = self.put_json(f'/api/documents/{doc["id"]}', {'title': 'New Name'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(json.loads(r.data)['title'], 'New Name')

    def test_bob_cannot_access_private_doc(self):
        doc = self._create('Private')
        r = self.client.get(f'/api/documents/{doc["id"]}', headers=auth(BOB))
        self.assertEqual(r.status_code, 403)

    def test_delete_document(self):
        doc = self._create('To Delete')
        r = self.client.delete(f'/api/documents/{doc["id"]}', headers=auth(ALICE))
        self.assertEqual(r.status_code, 200)
        r2 = self.client.get(f'/api/documents/{doc["id"]}', headers=auth(ALICE))
        self.assertEqual(r2.status_code, 404)

    def test_list_owned(self):
        self._create('Doc A')
        r = self.client.get('/api/documents', headers=auth(ALICE))
        data = json.loads(r.data)
        self.assertIn('owned', data)
        self.assertTrue(len(data['owned']) >= 1)


class TestSharing(BaseTest):
    def _create_and_share(self):
        r = self.post_json('/api/documents', {'title': 'Shared'}, ALICE)
        doc_id = json.loads(r.data)['id']
        r2 = self.post_json(f'/api/documents/{doc_id}/share', {'email': 'bob@test.com'}, ALICE)
        self.assertEqual(r2.status_code, 200)
        return doc_id

    def test_share_and_access(self):
        doc_id = self._create_and_share()
        r = self.client.get(f'/api/documents/{doc_id}', headers=auth(BOB))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(json.loads(r.data)['relation'], 'shared')

    def test_shared_in_list(self):
        doc_id = self._create_and_share()
        r = self.client.get('/api/documents', headers=auth(BOB))
        data = json.loads(r.data)
        self.assertTrue(any(d['id'] == doc_id for d in data['shared']))

    def test_share_with_self_rejected(self):
        r = self.post_json('/api/documents', {'title': 'Self'}, ALICE)
        doc_id = json.loads(r.data)['id']
        r2 = self.post_json(f'/api/documents/{doc_id}/share', {'email': 'alice@test.com'}, ALICE)
        self.assertEqual(r2.status_code, 400)

    def test_non_owner_cannot_share(self):
        r = self.post_json('/api/documents', {'title': 'X'}, ALICE)
        doc_id = json.loads(r.data)['id']
        self.post_json(f'/api/documents/{doc_id}/share', {'email': 'bob@test.com'}, ALICE)
        r2 = self.post_json(f'/api/documents/{doc_id}/share', {'email': 'carol@test.com'}, BOB)
        self.assertEqual(r2.status_code, 403)


class TestUpload(BaseTest):
    def _upload(self, content, filename, token=ALICE):
        data = {'file': (io.BytesIO(content), filename)}
        return self.client.post('/api/upload', data=data,
            content_type='multipart/form-data', headers=auth(token))

    def test_upload_txt(self):
        r = self._upload(b'# Hello\nThis is content', 'hello.txt')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(json.loads(r.data)['title'], 'hello')

    def test_upload_md(self):
        r = self._upload(b'## Section\nSome text', 'notes.md')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(json.loads(r.data)['title'], 'notes')

    def test_upload_unsupported_rejected(self):
        r = self._upload(b'data', 'file.pdf')
        self.assertEqual(r.status_code, 400)

    def test_uploaded_doc_in_list(self):
        self._upload(b'content', 'myfile.txt')
        r = self.client.get('/api/documents', headers=auth(ALICE))
        data = json.loads(r.data)
        self.assertTrue(any(d['title'] == 'myfile' for d in data['owned']))


if __name__ == '__main__':
    unittest.main(verbosity=2)
