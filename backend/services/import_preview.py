"""Stateless, account-bound import previews tied to a consistent SQLite snapshot."""
from datetime import date, datetime, timedelta, timezone
import hashlib
import hmac
import json

from fastapi import HTTPException
from jose import JWTError, jwt
from sqlalchemy import inspect

from auth import SECRET_KEY
from models import Bill, Category, FitnessRecord, Memory, MemorySuppression, Settings, SyncState, SourceControl

_TABLES = (Bill, Category, FitnessRecord, Memory, MemorySuppression, Settings, SyncState, SourceControl)
_PURPOSE = 'baobu-import-preview-v1'
_LIFETIME = 600
_MAX_IMPORT_BYTES = 10 * 1024 * 1024


def _json(value):
    def encode(value):
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        raise TypeError('unsupported value')
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                          default=encode, allow_nan=False).encode('utf-8')
    except (TypeError, ValueError, OverflowError):
        raise HTTPException(422, '导入内容格式无效') from None


def _fingerprint(label, value):
    content = _json(value)
    if label == 'data' and len(content) > _MAX_IMPORT_BYTES:
        raise HTTPException(413, '导入数据超过大小限制')
    message = (_PURPOSE + '\0' + label + '\0').encode('utf8') + content
    return hmac.new(SECRET_KEY.encode('utf8'), message, hashlib.sha256).hexdigest()


def _snapshot(db, user_id):
    result = {}
    for model in _TABLES:
        columns = [col.key for col in inspect(model).columns]
        rows = db.query(model).filter(model.user_id == user_id).order_by(model.id).all()
        result[model.__tablename__] = [{col: getattr(row, col) for col in columns} for row in rows]
    return result


def _validate(data, snapshot):
    def fail():
        raise HTTPException(422, '导入数据字段或分类关联无效')

    def is_int(value):
        return isinstance(value, int) and not isinstance(value, bool)

    def has_strings(item, fields):
        return all(isinstance(item.get(key), str) and item[key].strip() for key in fields)

    category_ids = set()
    if data.categories is None:
        category_ids = {row['id'] for row in snapshot['categories']}
    else:
        for item in data.categories:
            if not has_strings(item, ('type', 'name')):
                fail()
            if any(key in item and item[key] is not None and not isinstance(item[key], str)
                   for key in ('icon', 'color')):
                fail()
            if 'is_custom' in item and item['is_custom'] is not None and not isinstance(item['is_custom'], bool):
                fail()
            if 'sort_order' in item and item['sort_order'] is not None and not is_int(item['sort_order']):
                fail()
            old_id = item.get('id')
            if old_id is not None:
                if not is_int(old_id) or old_id <= 0 or old_id in category_ids:
                    fail()
                category_ids.add(old_id)
    for item in data.bills or []:
        if (not has_strings(item, ('type', 'category_name', 'date', 'time')) or
                not is_int(item.get('category_id')) or item['category_id'] not in category_ids or
                not isinstance(item.get('amount'), (int, float)) or isinstance(item['amount'], bool)):
            fail()
        if any(key in item and item[key] is not None and not isinstance(item[key], str)
               for key in ('payment_method', 'remark')):
            fail()
    for item in data.fitness or []:
        if not has_strings(item, ('exercise_type', 'date', 'time')) or not is_int(item.get('duration_minutes')):
            fail()
        if 'calories' in item and item['calories'] is not None and not is_int(item['calories']):
            fail()
        if 'note' in item and item['note'] is not None and not isinstance(item['note'], str):
            fail()
    for key in ('fitness_daily_goal_minutes', 'fitness_daily_goal_calories'):
        if key in data.settings and not is_int(data.settings[key]):
            fail()
    if 'monthly_budget' in data.settings and (not isinstance(data.settings['monthly_budget'], (int, float)) or
                                               isinstance(data.settings['monthly_budget'], bool)):
        fail()
    if any(key not in ('monthly_budget', 'fitness_daily_goal_minutes', 'fitness_daily_goal_calories')
           for key in data.settings):
        fail()


def preview(db, user_id, data):
    snapshot = _snapshot(db, user_id)
    if data.categories is not None and data.bills is None and snapshot['bills']:
        raise HTTPException(422, '替换分类时须同时提供账单，避免账单分类关联失效')
    _validate(data, snapshot)
    suppressed = {(row['source'], row['source_id']) for row in snapshot['memory_suppressions']}
    suppressed.update((item.source, item.source_id) for item in data.memory_suppressions or [])
    skipped = sum(1 for item in data.memories or [] if item.source_id and (item.source, item.source_id) in suppressed)
    replacements = {}
    for field, table in [('categories', 'categories'), ('bills', 'bills'),
                         ('fitness', 'fitness_records'), ('memories', 'memories')]:
        incoming = getattr(data, field)
        replacements[field] = {'action': 'replace' if incoming is not None else 'preserve',
                               'current': len(snapshot[table]),
                               'incoming': len(incoming) if incoming is not None else None}
    payload = data.model_dump(mode='json')
    token = jwt.encode({'purpose': _PURPOSE, 'user_id': user_id,
                        'data': _fingerprint('data', payload),
                        'state': _fingerprint('state', snapshot),
                        'exp': datetime.now(timezone.utc) + timedelta(seconds=_LIFETIME)},
                       SECRET_KEY, algorithm='HS256')
    warnings = []
    if data.memories is not None:
        warnings.append('回忆将按备份替换；未被删除标记保护的来源记录可能在后续同步时再次导入。')
    return {'preview_token': token, 'expires_in': _LIFETIME, 'replacements': replacements,
            'memories_skipped_by_suppression': skipped,
            'settings_updated': bool(data.settings),
            'suppression_count_after': len(suppressed),
            'sync_checkpoint_reset': data.memories is not None, 'warnings': warnings}


def verify(db, user_id, data, token):
    try:
        claims = jwt.decode(token, SECRET_KEY, algorithms=['HS256'], options={'require_exp': True})
        if (claims.get('purpose') != _PURPOSE or claims.get('user_id') != user_id or
                not hmac.compare_digest(claims.get('data', ''), _fingerprint('data', data.model_dump(mode='json'))) or
                not hmac.compare_digest(claims.get('state', ''), _fingerprint('state', _snapshot(db, user_id)))):
            raise ValueError('preview changed')
    except (JWTError, ValueError, TypeError):
        raise HTTPException(409, '导入预览已过期或数据已变化，请重新预览') from None
