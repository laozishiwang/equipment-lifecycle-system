import base64,datetime,json,urllib.request,urllib.error,uuid
base='http://127.0.0.1:18090/prod-api'
def call(path,method='GET',data=None,token=None,raw=False,content_type='application/json'):
 h={'Content-Type':content_type}
 if token:h['Authorization']='Bearer '+token
 body=data if raw else (None if data is None else json.dumps(data).encode())
 req=urllib.request.Request(base+path,body,h,method=method)
 try:
  with urllib.request.urlopen(req,timeout=30) as r:
   payload=r.read();return (r.status,r.headers,payload) if raw and method=='GET' else json.loads(payload)
 except urllib.error.HTTPError as e:return {'code':e.code}
def login(name):return call('/login','POST',{'username':name,'password':'admin123'})['token']
def upload(oid,token,body):
 boundary='---ems'+uuid.uuid4().hex
 payload=('--'+boundary+'\r\nContent-Disposition: form-data; name="file"; filename="test.png"\r\nContent-Type: image/png\r\n\r\n').encode()+body+('\r\n--'+boundary+'--\r\n').encode()
 return call(f'/equipment/orders/{oid}/photos','POST',payload,token,raw=True,content_type='multipart/form-data; boundary='+boundary)
a=login('admin');w=login('role_worker_test');other=login('smoke_worker');tech=login('role_tech_test');code='PHOTO-'+uuid.uuid4().hex[:8]
assert call('/equipment/assets','POST',{'code':code,'name':'photo test'},a)['code']==200
eid=next(x['id'] for x in call('/equipment/assets?keyword='+code,token=a)['data'] if x['code']==code)
created=call('/equipment/orders','POST',{'equipmentId':eid,'description':'photo test'},w);assert created['code']==200;oid=created['data']['id']
png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/6x0AAAAASUVORK5CYII=')
assert upload(oid,w,b'not an image')['code']!=200
assert upload(oid,w,png[:33])['code']!=200, 'truncated PNG accepted'
assert upload(oid,w,b'x'*(5*1024*1024+1))['code']!=200
assert upload(oid,other,png)['code']!=200
assert upload(oid,w,png)['code']==200
photos=call(f'/equipment/orders/{oid}/photos',token=w)['data'];assert len(photos)==1
pid=photos[0]['id'];status,headers,content=call(f'/equipment/orders/photos/{pid}',token=w,raw=True);assert status==200 and content==png and headers['X-Content-Type-Options']=='nosniff'
# More than one page must remain visible without duplicates or cross-order leakage.
for _ in range(20): assert upload(oid,w,png)['code']==200
first=call(f'/equipment/orders/{oid}/photos',token=w)['data']
assert len(first)==20
second=call(f'/equipment/orders/{oid}/photos?afterId={first[-1]["id"]}',token=w)['data']
assert len(second)==1 and second[0]['id']>first[-1]['id']
assert call(f'/equipment/orders/{oid}/photos?afterId={second[-1]["id"]}',token=w)['data']==[]
assert not set(x['id'] for x in first).intersection(x['id'] for x in second)
assert call(f'/equipment/orders/{oid}/photos?afterId=0',token=w)['code']!=200
jpeg=base64.b64decode('/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAAEAAQDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwDDooor6g+TP//Z')
assert upload(oid,w,jpeg)['code']==200
assert call(f'/equipment/orders/{oid}/photos',token=other)['code']!=200
assert call(f'/equipment/orders/photos/{pid}',token=other)['code']==404
assert call(f'/equipment/orders/{oid}/photos',token=tech)['code']==200
assert call(f'/equipment/orders/{oid}/accept','POST',{},a)['code']==200
assert call(f'/equipment/orders/{oid}/arrive','POST',{},a)['code']==200
assert call(f'/equipment/orders/{oid}/complete','POST',{'repairDate':datetime.date.today().isoformat(),'description':'done','costs':[]},a)['code']==200
assert call(f'/equipment/orders/{oid}/trial','POST',{'result':'PASS'},a)['code']==200
assert call(f'/equipment/orders/{oid}/close','POST',{},a)['code']==200
assert upload(oid,w,png)['code']!=200
print('photo upload, size/type validation, authorization, download and closed-order restriction passed')
