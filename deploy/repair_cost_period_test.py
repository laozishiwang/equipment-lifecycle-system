import decimal,io,json,urllib.error,urllib.request,uuid,zipfile,xml.etree.ElementTree as ET

base='http://127.0.0.1:18090/prod-api'
def call(path,token=None,data=None):
    headers={'Content-Type':'application/json'}
    if token: headers['Authorization']='Bearer '+token
    req=urllib.request.Request(base+path,None if data is None else json.dumps(data).encode(),headers,method='GET' if data is None else 'POST')
    try:
        with urllib.request.urlopen(req,timeout=30) as response:return json.load(response,parse_float=decimal.Decimal)
    except urllib.error.HTTPError as error:return {'code':error.code}
def login(user):return call('/login',data={'username':user,'password':'admin123'})['token']
admin,worker,tech=(login(x) for x in ('admin','role_worker_test','role_tech_test'))
period='?startDate=2026-01-10&endDate=2026-01-10'
before=call('/equipment/overview/costs'+period,admin)['data']
assert call('/equipment/overview/costs'+period,worker)['code']!=200
assert call('/equipment/overview/costs?startDate=2026-01-01',admin)['code']!=200
assert call('/equipment/overview/costs?startDate=2026-02-01&endDate=2026-01-01',admin)['code']!=200
created=call('/equipment/orders',worker,{'equipmentId':1,'description':'cost-period-'+uuid.uuid4().hex[:8]})
assert created['code']==200,created
order=created['data']['id']
assert call(f'/equipment/orders/{order}/accept',tech,{})['code']==200
assert call(f'/equipment/orders/{order}/arrive',tech,{})['code']==200
assert call(f'/equipment/orders/{order}/complete',tech,{'repairDate':'2026-01-10','description':'维修测试','costs':[{'category':'LABOR','description':'人工','amount':35.5},{'category':'PARTS','description':'配件','amount':12.25},{'category':'OTHER','description':'其他','amount':2}]})['code']==200
after=call('/equipment/overview/costs'+period,admin)['data']
for key,delta in [('labor','35.50'),('parts','12.25'),('other','2.00'),('total','49.75')]:
    assert decimal.Decimal(str(after[key]))-decimal.Decimal(str(before[key]))==decimal.Decimal(delta),(key,before,after)
assert after['order_count']-before['order_count']==1 and after['repair_count']-before['repair_count']==1
rows=call('/equipment/overview/costs/orders'+period,admin)['data']
row=next(x for x in rows if x['id']==order)
for key,value in [('labor','35.50'),('parts','12.25'),('other','2.00'),('total','49.75')]:assert decimal.Decimal(str(row[key]))==decimal.Decimal(value),row
assert call('/equipment/overview/costs/orders'+period,worker)['code']!=200
assert call('/equipment/overview/costs/orders?beforeId=0',admin)['code']!=200
assert not any(x['id']==order for x in call('/equipment/overview/costs/orders?startDate=2026-01-11&endDate=2026-01-11',admin)['data'])
assert not any(x['id']>=order for x in call('/equipment/overview/costs/orders'+period+'&beforeId='+str(order),admin)['data'])
assert call(f'/equipment/orders/{order}/trial',tech,{'result':'FAIL','notes':'需返修'})['code']==200
assert call(f'/equipment/orders/{order}/complete',tech,{'repairDate':'2026-01-11','description':'再次维修','costs':[{'category':'LABOR','description':'人工','amount':5}]})['code']==200
row=next(x for x in call('/equipment/overview/costs/orders'+period,admin)['data'] if x['id']==order)
assert decimal.Decimal(str(row['total']))==decimal.Decimal('49.75')
other=next(x for x in call('/equipment/overview/costs/orders?startDate=2026-01-11&endDate=2026-01-11',admin)['data'] if x['id']==order)
assert decimal.Decimal(str(other['total']))==decimal.Decimal('5.00')
assert call(f'/equipment/orders/{order}/cancel',admin,{'reason':'核对取消费用口径'})['code']==200
assert call('/equipment/overview/costs'+period,admin)['data']==after
assert next(x for x in call('/equipment/overview/costs/orders'+period,admin)['data'] if x['id']==order)['status']=='CANCELLED'
request=urllib.request.Request(base+'/equipment/overview/costs/export'+period,headers={'Authorization':'Bearer '+admin})
with urllib.request.urlopen(request,timeout=60) as response:
    assert response.headers.get_content_type()=='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    export=response.read()
with zipfile.ZipFile(io.BytesIO(export)) as workbook:
    ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    shared=ET.fromstring(workbook.read('xl/sharedStrings.xml'))
    strings=[''.join(t.text or '' for t in item.findall('.//m:t',ns)) for item in shared.findall('m:si',ns)]
    sheet=ET.fromstring(workbook.read('xl/worksheets/sheet1.xml'))
    def value(cell):
        node=cell.find('m:v',ns)
        if node is None:return None
        return strings[int(node.text)] if cell.get('t')=='s' else node.text
    rows=[{c.get('r').rstrip('0123456789'):value(c) for c in row.findall('m:c',ns)} for row in sheet.findall('.//m:sheetData/m:row',ns)]
    match=next(row for row in rows if row.get('A')==str(order))
    assert match['D']=='已取消' and decimal.Decimal(match['F'])==decimal.Decimal('35.5') and decimal.Decimal(match['G'])==decimal.Decimal('12.25') and decimal.Decimal(match['I'])==decimal.Decimal('49.75'),match
try:
    with urllib.request.urlopen(urllib.request.Request(base+'/equipment/overview/costs/export'+period,headers={'Authorization':'Bearer '+worker}),timeout=30) as response:
        assert response.headers.get_content_type()!='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        assert json.load(response)['code']!=200
except urllib.error.HTTPError as error: assert error.code in (401,403)
outside=call('/equipment/overview/costs?startDate=2026-01-11&endDate=2026-01-11',admin)
assert outside['code']==200
print('cost date totals, role scope, validation and cancelled-cost policy passed')
