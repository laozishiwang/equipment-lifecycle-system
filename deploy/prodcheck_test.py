import json,urllib.request,urllib.error
base='http://127.0.0.1:18092/prod-api'
def call(path,data=None,token=None):
 h={'Content-Type':'application/json'}
 if token:h['Authorization']='Bearer '+token
 req=urllib.request.Request(base+path,None if data is None else json.dumps(data).encode(),h,method='POST' if data is not None else 'GET')
 try:
  with urllib.request.urlopen(req,timeout=90) as r:return json.load(r)
 except urllib.error.HTTPError as e:return {'code':e.code}
assert call('/login',{'username':'admin','password':'admin123'}).get('token') is None
assert call('/login',{'username':'ry','password':'admin123'}).get('token') is None
login=call('/login',{'username':'admin','password':'Ems-Test-2026-OK!'})
assert login.get('token'), 'new admin login failed'
token=login['token'];assert call('/getInfo',token=token)['code']==200
assert call('/equipment/assets',token=token)['code']==200
assert call('/equipment/maintenance',token=token)['code']==200
print('default password rejected, test account disabled, new admin login and business APIs passed')

