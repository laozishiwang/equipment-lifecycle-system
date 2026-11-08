import base64,json,urllib.request,urllib.error,uuid
base='http://127.0.0.1:18090/prod-api'
def call(path,method='GET',data=None,token=None,raw=False,content_type='application/json'):
 h={'Content-Type':content_type}
 if token:h['Authorization']='Bearer '+token
 req=urllib.request.Request(base+path,data if raw else (None if data is None else json.dumps(data).encode()),h,method=method)
 try:
  with urllib.request.urlopen(req,timeout=30) as r:
   payload=r.read();return (r.status,r.headers,payload) if raw and method=='GET' else json.loads(payload)
 except urllib.error.HTTPError as e:return {'code':e.code}
def login(name):return call('/login','POST',{'username':name,'password':'admin123'})['token']
def upload(id,token,body):
 boundary='---ems'+uuid.uuid4().hex
 payload=('--'+boundary+'\r\nContent-Disposition: form-data; name="file"; filename="test.png"\r\nContent-Type: image/png\r\n\r\n').encode()+body+('\r\n--'+boundary+'--\r\n').encode()
 return call(f'/equipment/inspections/{id}/photos','POST',payload,token,True,'multipart/form-data; boundary='+boundary)
a=login('admin');w=login('role_worker_test');other=login('smoke_worker')
r=call('/equipment/inspections','POST',{'equipmentId':1,'result':'ABNORMAL','remark':'inspection photo test'},w);assert r['code']==200;id=r['data']['inspectionId']
png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/6x0AAAAASUVORK5CYII=')
assert upload(id,w,png[:33])['code']!=200
assert upload(id,w,b'x'*(5*1024*1024+1))['code']!=200
assert upload(id,other,png)['code']!=200
assert upload(id,w,png)['code']==200
rows=call(f'/equipment/inspections/{id}/photos',token=w)['data'];assert len(rows)==1
pid=rows[0]['id'];status,headers,body=call(f'/equipment/inspections/photos/{pid}',token=w,raw=True);assert status==200 and body==png and headers['X-Content-Type-Options']=='nosniff'
for _ in range(20): assert upload(id,w,png)['code']==200
first=call(f'/equipment/inspections/{id}/photos',token=w)['data'];assert len(first)==20
second=call(f'/equipment/inspections/{id}/photos?afterId={first[-1]["id"]}',token=w)['data'];assert len(second)==1 and second[0]['id']>first[-1]['id']
assert call(f'/equipment/inspections/{id}/photos?afterId=0',token=w)['code']!=200
assert call(f'/equipment/inspections/{id}/photos',token=other)['code']!=200
assert call(f'/equipment/inspections/photos/{pid}',token=other)['code']==404
assert call(f'/equipment/inspections/{id}/photos',token=a)['code']==200
print('inspection photo upload, validation, download and scope passed')
