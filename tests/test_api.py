import os

from fastapi.testclient import TestClient

from server.api import app


client = TestClient(app)


def test_health() -> None:
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


def test_extract() -> None:
    response = client.post('/extract', json={'preset': 'balanced'})
    assert response.status_code == 200
    payload = response.json()
    assert 'formats' in payload
    assert 'svg' in payload['formats']

