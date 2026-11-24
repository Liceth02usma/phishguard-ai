#!/usr/bin/env python
import json
from fastapi.testclient import TestClient
from src.api.app import create_app

app = create_app()
client = TestClient(app)

# Test EML mode with multipart form data
print('=== Test: EML mode ===')
files = {
    'modo': (None, 'eml'),
    'archivo': ('test.eml', 'From: sender@test.com\r\nSubject: Test\r\n\r\nHello world, this is a test email.'),
    'dry_run': (None, 'true'),
}
resp = client.post('/api/analyses', files=files)
print('Status:', resp.status_code)
if resp.status_code == 201:
    r = resp.json().get('resultado', {})
    print('Score:', r.get('score'), 'Veredicto:', r.get('veredicto'), 'Severidad:', r.get('nivel_severidad'))
else:
    print('Error:', resp.text[:200])