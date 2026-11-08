import concurrent.futures,json,struct,urllib.request,urllib.error,uuid,zlib
base='http://127.0.0.1:18090/prod-api'
def call(path,data=None,token=None):
 h={'Content-Type':'application/json'}
 if token:h['Authorization']='Bearer '+token
 req=urllib.request.Request(base+path,None if data is None else json.dumps(data).encode(),h,method='GET' if data is None else 'POST')
 with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)
def login(n):return call('/login',{'username':n,'password':'admin123'})['token']
def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
def png(w,h):
 comp=zlib.compressobj();data=b''.join(comp.compress(b'\x00'+b'\x00'*(w*3)) for _ in range(h))+comp.flush()
 return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',data)+chunk(b'IEND',b'')
a=login('admin');w=login('role_worker_test');code='CAPACITY-'+uuid.uuid4().hex[:8]
assert call('/equipment/assets',{'code':code,'name':'image capacity test'},a)['code']==200
id=next(x['id'] for x in call('/equipment/assets?keyword='+code,token=a)['data'] if x['code']==code)
r=call('/equipment/orders',{'equipmentId':id,'description':'image capacity test'},w);oid=r['data']['id'];body=png(4000,4000)
def send(_):
 boundary='---ems'+uuid.uuid4().hex
 payload=('--'+boundary+'\r\nContent-Disposition: form-data; name="file"; filename="test.png"\r\nContent-Type: image/png\r\n\r\n').encode()+body+('\r\n--'+boundary+'--\r\n').encode()
 req=urllib.request.Request(base+f'/equipment/orders/{oid}/photos',payload,{'Authorization':'Bearer '+w,'Content-Type':'multipart/form-data; boundary='+boundary},method='POST')
 try:
  with urllib.request.urlopen(req,timeout=90) as r:
   payload=json.load(r);return (r.status if payload.get("code")==200 else 500),None
 except urllib.error.HTTPError as e:return e.code,e.headers.get('Retry-After')
with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool: results=list(pool.map(send,range(12)))
assert any(x[0]==200 for x in results),results
assert any(x==(503,'2') for x in results),results
assert all(x[0] in (200,503) for x in results),results
print('photo decode concurrency admission and Retry-After passed:',sum(x[0]==200 for x in results),'accepted,',sum(x[0]==503 for x in results),'rejected')
