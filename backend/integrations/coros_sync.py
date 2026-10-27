"""Transactional, explicitly invoked import of a validated COROS MCP result.

Network polling, OAuth credentials, media and production scheduling are separate.
"""
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy.dialects.sqlite import insert
from integrations.coros_records import CorosResponseError, parse_sport_records
from models import Memory, MemorySuppression


def import_sport_records(db, user_id: int, response: dict, *, requested_limit: int, commit: bool = True,
                         start_date=None, end_date=None) -> dict:
    if requested_limit < 1:
        raise ValueError('requested_limit must be positive')
    records = parse_sport_records(response)
    # The MCP tool does not expose an offset or total. A full response may be
    # truncated, so leave the database unchanged until the query is narrowed.
    if len(records) >= requested_limit:
        raise CorosResponseError('Result may be truncated; narrow the date range')
    if start_date is not None and end_date is not None:
        for record in records:
            local_date = datetime.fromisoformat(record['occurred_at']).astimezone(ZoneInfo('Asia/Shanghai')).date()
            if not start_date <= local_date <= end_date:
                raise CorosResponseError('Result contains a record outside the requested date range')
    inserted = 0
    suppressed = 0
    for record in records:
        if db.query(MemorySuppression).filter_by(user_id=user_id, source='coros', source_id=record['source_id']).first():
            suppressed += 1
            continue
        stmt = insert(Memory).values(
            user_id=user_id, source='coros', source_id=record['source_id'],
            occurred_at=record['occurred_at'], text=record['text'], hidden=False,
        ).on_conflict_do_nothing(index_elements=['user_id', 'source', 'source_id'])
        inserted += db.execute(stmt).rowcount
    if commit:
        db.commit()
    return {'received': len(records), 'inserted': inserted, 'suppressed': suppressed}
