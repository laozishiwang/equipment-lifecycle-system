"""Run only in isolation, with free photo quota equal to one test image."""
import base64
import concurrent.futures
import json
import urllib.error
import urllib.request
import uuid

BASE = 'http://127.0.0.1:18090/prod-api'
IMAGE = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/6x0AAAAASUVORK5CYII=')

def call(path, method='GET', body=None, token=None, content_type='application/json'):
    headers = {'Content-Type': content_type}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    try:
        with urllib.request.urlopen(urllib.request.Request(BASE + path, body, headers, method=method), timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        return {'code': error.code}

def post_json(path, data, token=None):
    return call(path, 'POST', json.dumps(data).encode(), token)

worker = post_json('/login', {'username': 'role_worker_test', 'password': 'admin123'})['token']
order = post_json('/equipment/orders', {'equipmentId': 1, 'description': 'isolated photo quota race'}, worker)['data']['id']

def upload(_):
    boundary = 'test' + uuid.uuid4().hex
    body = ('--' + boundary + '\r\nContent-Disposition: form-data; name="file"; filename="test.png"\r\nContent-Type: image/png\r\n\r\n').encode() + IMAGE
    body += ('\r\n--' + boundary + '--\r\n').encode()
    return call(f'/equipment/orders/{order}/photos', 'POST', body, worker, 'multipart/form-data; boundary=' + boundary)

with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    results = list(pool.map(upload, range(2)))
results = [upload(0) if result.get('code') == 503 else result for result in results]
assert sum(result.get('code') == 200 for result in results) == 1, results
assert any('存储空间不足' in result.get('msg', '') for result in results), results
assert len(call(f'/equipment/orders/{order}/photos', token=worker)['data']) == 1
print('concurrent photo uploads stay within the one-image quota')
