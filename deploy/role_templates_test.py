import json,urllib.request,urllib.error
base='http://127.0.0.1:18090/prod-api'
def call(path,method='GET',data=None,token=None):
 h={'Content-Type':'application/json'}
 if token:h['Authorization']='Bearer '+token
 req=urllib.request.Request(base+path,None if data is None else json.dumps(data).encode(),h,method=method)
 try:
  with urllib.request.urlopen(req,timeout=15) as r:return json.load(r)
 except urllib.error.HTTPError as e:return {'code':e.code}
def login(user):
 r=call('/login','POST',{'username':user,'password':'admin123'});assert r.get('token');return r['token']
w=login('role_worker_test');t=login('role_tech_test');d=login('role_director_test')
assert call('/equipment/assets',token=w)['code']==200
assert call('/equipment/assets/qr-base',token=w)['data']['baseUrl']==''
assert call('/equipment/maintenance',token=w)['code'] in (401,403)
assert call('/equipment/maintenance',token=t)['code']==200
assert call('/equipment/maintenance/1/deactivate','POST',{},t)['code'] in (401,403)
assert call('/equipment/maintenance',token=d)['code']==200
assert call('/equipment/maintenance/due-summary',token=d)['code']==200
print('worker, technician and director template permissions verified')
