import xmlrpc.client

url = 'http://localhost:8069'
db = 'odoo' 
username = 'jcwm.peters@student.han.nl' 
password = 'ONXwUSjlyO0Qk7'

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})

if uid:
    print(f"🎯 HET WERKT! Je bent binnen. User ID: {uid}")
else:
    print("❌ Inloggen mislukt. Controleer de naam in de Database Manager.")

models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

partners = models.execute_kw(
    db, uid, password,
    'res.partner',
    'search_read',
    [[['name', 'ilike', 'a']]],
    {'limit': 5}
)

for p in partners:
    print(p['name'])