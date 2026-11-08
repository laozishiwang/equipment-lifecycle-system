import json,urllib.request,urllib.error
base='http://127.0.0.1:18090/prod-api'
def call(path,method='GET',data=None,token=None):
 h={'Content-Type':'application/json'}
 if token:h['Authorization']='Bearer '+token
 req=urllib.request.Request(base+path,None if data is None else json.dumps(data).encode(),h,method=method)
 try:
  with urllib.request.urlopen(req,timeout=15) as response:return json.load(response)
 except urllib.error.HTTPError as e:return {'code':e.code}
login=call('/login','POST',{'username':'smoke_worker','password':'admin123'})
assert login.get('token'), 'test login failed'
token=login['token']
for path,method,payload in [('/equipment/assets','GET',None),('/equipment/orders/1/accept','POST',{}),('/equipment/orders/1/close','POST',{})]:
 result=call(path,method,payload,token)
 print(path,result.get('code'))
 assert result.get('code') in (401,403), 'operation was not denied'
print('restricted role checks passed')
assert call('/equipment/maintenance',token=token).get('code') in (401,403)
assert call('/equipment/maintenance/1/deactivate','POST',{},token).get('code') in (401,403)
assert call('/equipment/maintenance/1/complete','POST',{'completedDate':'2026-11-02','notes':'test'},token).get('code') in (401,403)
print('maintenance permissions denied for unauthorized worker')

