import json,urllib.request,urllib.error
from pathlib import Path
base='http://127.0.0.1:18090/prod-api'
def call(path,data=None,token=None):
 headers={'Content-Type':'application/json'}
 if token:headers['Authorization']='Bearer '+token
 req=urllib.request.Request(base+path,None if data is None else json.dumps(data).encode(),headers)
 try:
  with urllib.request.urlopen(req,timeout=20) as response:return json.load(response)
 except urllib.error.HTTPError as error:return {'code':error.code}
def login(name):return call('/login',{'username':name,'password':'admin123'})['token']
def find_path(nodes,path):
 for n in nodes:
  if n.get('path')==path:return n
  r=find_path(n.get('children') or [],path)
  if r:return r
 return None
source=Path('frontend/src/router/index.js').read_text(encoding='utf-8')
for obsolete in ('/system/dict-data','/monitor/job-log','/tool/gen-edit'):assert obsolete not in source
for required in ('/system/user-auth','/system/role-auth','/user'):assert required in source
admin=login('admin');director=login('role_director_test');worker=login('role_worker_test')
info=call('/getInfo',token=admin);assert info['user']['nickName']!='若依'
routes=call('/getRouters',token=admin)['data']
for path in ('/tool','/monitor','http://ruoyi.vip','post','dict','config','notice'):
 item=find_path(routes,path)
 assert item is None or item.get('hidden') is True,(path,item)
for path in ('/equipment','/system','user','role','dept'):
 item=find_path(routes,path);assert item is not None and not item.get('hidden'),(path,item)
for path in ('/tool/gen/list','/monitor/job/list','/monitor/jobLog/list','/monitor/server','/monitor/cache','/monitor/online/list'):
 assert call(path,token=admin)['code']!=200,path
for path in ('/system/user/list','/system/role/list','/system/dept/list','/monitor/operlog/list','/monitor/logininfor/list'):
 assert call(path,token=admin)['code']==200,path
for token in (director,worker):
 assert call('/equipment/assets',token=token)['code']==200
 assert call('/equipment/orders',token=token)['code']==200
print('unused menu entries hidden, user/role/department and equipment access preserved')
