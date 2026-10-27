"""Transactional, explicitly invoked import of a validated COROS MCP result.

Network polling, OAuth credentials, media and production scheduling are separate.
"""
from sqlalchemy.dialects.sqlite import insert
from integrations.coros_records import CorosResponseError, parse_sport_records
from models import Memory, MemorySuppression


def import_sport_records(db, user_id: int, response: dict, *, requested_limit: int) -> dict:
    if requested_limit < 1:
        raise ValueError('requested_limit must be positive')
    records = parse_sport_records(response)
    # The MCP tool does not expose an offset or total. A full response may be
    # truncated, so leave the database unchanged until the query is narrowed.
    if len(records) >= requested_limit:
        raise CorosResponseError('Result may be truncated; narrow the date range')
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
    db.commit()
    return {'received': len(records), 'inserted': inserted, 'suppressed': suppressed}
