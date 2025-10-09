import requests

BACKEND = 'http://127.0.0.1:8000'

endpoints = ['/', '/api/logo', '/api/video']

for e in endpoints:
    try:
        r = requests.get(BACKEND + e, timeout=5)
        print(e, r.status_code, r.headers.get('content-type'))
        try:
            print('   ', r.json())
        except Exception:
            print('   ', r.text[:200])
    except Exception as ex:
        print(e, 'ERROR', ex)
