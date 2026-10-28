"""回忆接口、账号隔离和旧备份兼容。"""


def import_with_preview(client, headers, data):
    preview = client.post('/api/data/import/preview', headers=headers, json=data)
    if preview.status_code != 200:
        return preview
    return client.post('/api/data/import/commit', headers=headers,
                       json={'data': data, 'preview_token': preview.json()['preview_token']})


def payload(source='manual', source_id=None, text='普通的一天'):
    return {'source': source, 'source_id': source_id,
            'occurred_at': '2026-10-26T10:00:00+08:00', 'text': text}


def test_privacy_visibility_and_deduplication(client, auth_headers):
    first = client.post('/api/memories', headers=auth_headers, json=payload('manual', 'manual-1'))
    assert first.status_code == 201
    item = first.json()
    assert item['occurred_at'].startswith('2026-10-26T02:00:00')
    assert client.post('/api/memories', headers=auth_headers, json=payload('manual', 'manual-1')).status_code == 409
    assert client.post('/api/memories', headers=auth_headers, json=payload('coros', 'run-1')).status_code == 403
    other = client.post('/api/auth/register', json={'username': 'another', 'password': 'test1234'}).json()
    headers2 = {'Authorization': 'Bearer ' + other['token']}
    assert client.get('/api/memories', headers=headers2).json() == []
    assert client.delete(f"/api/memories/{item['id']}", headers=headers2).status_code == 404
    assert client.patch(f"/api/memories/{item['id']}", headers=auth_headers, json={'hidden': True}).status_code == 200
    assert client.get('/api/memories', headers=auth_headers).json() == []
    assert len(client.get('/api/memories?include_hidden=true', headers=auth_headers).json()) == 1
    assert client.delete(f"/api/memories/{item['id']}", headers=auth_headers).status_code == 200


def test_export_restore_and_old_import(client, auth_headers):
    created = client.post('/api/memories', headers=auth_headers, json=payload())
    assert created.status_code == 201
    legacy = {'bills': [], 'fitness': [], 'settings': {}}
    assert import_with_preview(client, auth_headers, legacy).status_code == 200
    assert len(client.get('/api/memories', headers=auth_headers).json()) == 1
    backup = client.get('/api/data/export', headers=auth_headers).json()
    assert len(backup['memories']) == 1
    assert client.delete(f"/api/memories/{created.json()['id']}", headers=auth_headers).status_code == 200
    assert client.get('/api/memories', headers=auth_headers).json() == []
    assert import_with_preview(client, auth_headers, backup).status_code == 200
    assert client.get('/api/memories', headers=auth_headers).json()[0]['text'] == '普通的一天'


def test_requires_auth_and_timezone(client, auth_headers):
    assert client.get('/api/memories').status_code == 401
    invalid = payload()
    invalid['occurred_at'] = '2026-10-26T10:00:00'
    assert client.post('/api/memories', headers=auth_headers, json=invalid).status_code == 422
    assert client.post('/api/memories', headers=auth_headers, json=payload('coros')).status_code == 422


def test_discover_is_private_and_includes_older_visible_memories(client, auth_headers):
    assert client.get('/api/memories/discover').status_code == 401
    assert client.get('/api/memories/discover', headers=auth_headers).json() is None
    old = client.post('/api/memories', headers=auth_headers, json=payload(text='较早')).json()
    new = client.post('/api/memories', headers=auth_headers, json=payload(text='最近')).json()
    hidden = client.post('/api/memories', headers=auth_headers, json=payload(text='隐藏')).json()
    client.patch(f"/api/memories/{hidden['id']}", headers=auth_headers, json={'hidden': True})
    other = client.post('/api/auth/register', json={'username': 'discover-other', 'password': 'test1234'}).json()
    other_headers = {'Authorization': 'Bearer ' + other['token']}
    client.post('/api/memories', headers=other_headers, json=payload(text='其他账户'))
    response = client.get('/api/memories/discover', headers=auth_headers, params={'exclude_id': new['id']})
    assert response.json()['id'] == old['id']
    assert response.headers['cache-control'] == 'no-store'
    client.delete(f"/api/memories/{new['id']}", headers=auth_headers)
    assert client.get('/api/memories/discover', headers=auth_headers, params={'exclude_id': old['id']}).json()['id'] == old['id']
    assert client.get('/api/memories/discover', headers=auth_headers, params={'exclude_id': 0}).status_code == 422


def test_cursor_pagination_survives_concurrent_changes(client, auth_headers):
    rows = [client.post('/api/memories', headers=auth_headers, json=payload(text=str(i))).json() for i in range(4)]
    first = client.get('/api/memories?limit=2', headers=auth_headers).json()
    assert [r['id'] for r in first] == [rows[3]['id'], rows[2]['id']]
    assert client.delete(f"/api/memories/{rows[3]['id']}", headers=auth_headers).status_code == 200
    client.post('/api/memories', headers=auth_headers, json=payload(text='new'))
    last = first[-1]
    response = client.get('/api/memories', headers=auth_headers, params={
        'limit': 2, 'before': last['occurred_at'], 'before_id': last['id']})
    assert [r['id'] for r in response.json()] == [rows[1]['id'], rows[0]['id']]
    assert client.get('/api/memories?before_id=1', headers=auth_headers).status_code == 422
    assert client.get('/api/memories', headers=auth_headers, params={'before': '2026-01-01T00:00:00', 'before_id': 1}).status_code == 422
    assert client.get('/api/memories', headers=auth_headers, params={'before': last['occurred_at'], 'before_id': last['id'], 'offset': 1}).status_code == 422
