from conftest import register

def test_logout_revokes_token(client):
 token=register(client,'logout@example.com','Logout User');headers={'Authorization':f'Bearer {token}'};assert client.get('/auth/me',headers=headers).status_code==200
 r=client.post('/auth/logout',headers=headers,json={'token':token});assert r.status_code==204;assert client.get('/auth/me',headers=headers).status_code==401

def test_notification_settings_persist_and_delivery_is_honest(client,headers):
 r=client.put('/notifications',headers=headers,json={'email':'alerts@example.com','frequency':'weekly','enabled':True,'locale':'en'});assert r.status_code==200;assert r.json()['delivery_available'] is False
 r=client.get('/notifications',headers=headers);assert r.status_code==200;assert r.json()['email']=='alerts@example.com';assert r.json()['frequency']=='weekly'
 r=client.post('/notifications/test',headers=headers);assert r.status_code==503;assert r.json()['error']['code']=='EMAIL_NOT_CONFIGURED'
