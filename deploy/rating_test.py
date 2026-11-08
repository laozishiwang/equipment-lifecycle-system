import runpy
s=runpy.run_path('deploy/smoke_test.py')
call, token, order=s['call'],s['token'],s['order']
assert call(f'/equipment/orders/{order}/rating','POST',{'stars':0},token).get('code')!=200
worker=call('/login','POST',{'username':'role_worker_test','password':'admin123'})['token']
assert call(f'/equipment/orders/{order}/rating','POST',{'stars':5},worker).get('code')!=200
assert call(f'/equipment/orders/{order}/rating','POST',{'stars':4,'remark':'ok'},token).get('code')==200
assert call(f'/equipment/orders/{order}/rating','POST',{'stars':5},token).get('code')!=200
director=call('/login','POST',{'username':'role_director_test','password':'admin123'})['token']
assert call(f'/equipment/orders/{order}',token=director)['data']['rating']['stars']==4
print('rating closed reporter only, validation, once, director view passed')
