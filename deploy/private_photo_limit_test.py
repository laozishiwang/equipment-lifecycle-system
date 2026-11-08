"""Run only against isolation with quota or free-space reserve configured to reject uploads."""
import json
import urllib.request
import uuid

BASE = 'http://127.0.0.1:18090/prod-api'
IMAGE = bytes.fromhex('89504e470d0a1a0a0000000d4948445200000001000000010804000000b51c0c020000000b4944415478da63fcff1f0003030200efbfeb1d0000000049454e44ae426082')

def call(path, method='GET', data=None, token=None, content_type='application/json'):
    headers = {'Content-Type': content_type}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    request = urllib.request.Request(BASE + path, data, headers, method=method)
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)

def json_call(path, method, data, token=None):
    return call(path, method, json.dumps(data).encode(), token)

worker = json_call('/login', 'POST', {'username': 'role_worker_test', 'password': 'admin123'})['token']
order = json_call('/equipment/orders', 'POST', {'equipmentId': 1, 'description': 'isolated storage limit test'}, worker)['data']['id']
inspection = json_call('/equipment/inspections', 'POST', {'equipmentId': 1, 'result': 'NORMAL', 'remark': 'isolated storage limit test'}, worker)['data']['inspectionId']

def upload(path, extra=None):
    boundary = 'test' + uuid.uuid4().hex
    body = b''
    if extra:
        body += ('--' + boundary + '\r\nContent-Disposition: form-data; name="equipmentId"\r\n\r\n1\r\n').encode()
    body += ('--' + boundary + '\r\nContent-Disposition: form-data; name="file"; filename="test.png"\r\nContent-Type: image/png\r\n\r\n').encode() + IMAGE
    body += ('\r\n--' + boundary + '--\r\n').encode()
    return call(path, 'POST', body, worker, 'multipart/form-data; boundary=' + boundary)

for endpoint, extra in [(f'/equipment/orders/{order}/photos', False), (f'/equipment/inspections/{inspection}/photos', False), ('/equipment/inspections/staged-photos', True)]:
    result = upload(endpoint, extra)
    assert result.get('code') != 200 and '存储空间不足' in result.get('msg', ''), (endpoint, result)

assert not call(f'/equipment/orders/{order}/photos', token=worker)['data']
assert not call(f'/equipment/inspections/{inspection}/photos', token=worker)['data']
print('all three photo endpoints reject safely when storage quota is exceeded')
