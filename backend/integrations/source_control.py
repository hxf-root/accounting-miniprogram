"""SQLite-only source permission and bounded, fenced worker leases.

Use a fresh Session and serialize all transitions with BEGIN IMMEDIATE.
Control rows must be provisioned by a trusted, separately verified setup flow;
these primitives do not establish or revoke provider authorization.
"""
import secrets
import time
import re

from sqlalchemy import text
from sqlalchemy.orm import Session
from models import SourceControl, User

LEASE_SECONDS = 120


class SourceUnavailable(RuntimeError):
    pass


class SourceBusy(RuntimeError):
    pass


def _begin(db):
    if db.in_transaction() or db.get_bind().dialect.name != 'sqlite':
        raise ValueError('source control requires a fresh SQLite session')
    db.execute(text('BEGIN IMMEDIATE'))


def acquire(engine, user_id, source='coros', *, now=None):
    now = int(time.time() if now is None else now)
    with Session(bind=engine) as db:
        _begin(db)
        row = db.query(SourceControl).filter_by(user_id=user_id, source=source).first()
        if not row or row.status != 'active' or not db.query(User.id).filter_by(id=user_id).first():
            raise SourceUnavailable('source is not active')
        if (row.lease_token is None) != (row.lease_expires_at is None):
            raise SourceUnavailable('source lease is invalid')
        if row.lease_token is not None:
            if (not isinstance(row.lease_token, str) or not re.fullmatch(r'[0-9a-f]{64}', row.lease_token) or
                    not isinstance(row.lease_expires_at, int)):
                raise SourceUnavailable('source lease is invalid')
            if row.lease_expires_at > now:
                raise SourceBusy('source sync already running')
        token = secrets.token_hex(32)
        row.lease_token = token
        row.lease_expires_at = now + LEASE_SECONDS
        generation = row.generation
        db.commit()
        return token, generation


def assert_lease(db, user_id, token, generation, source='coros', *, now=None):
    """Must be called inside the caller's SQLite IMMEDIATE transaction."""
    now = int(time.time() if now is None else now)
    row = db.query(SourceControl).filter_by(user_id=user_id, source=source).first()
    if (not row or not db.query(User.id).filter_by(id=user_id).first() or
            row.status != 'active' or row.generation != generation or
            row.lease_token != token or row.lease_expires_at is None or row.lease_expires_at <= now):
        raise SourceUnavailable('source permission or lease changed')
    return row


def renew(engine, user_id, token, generation, source='coros', *, now=None):
    now = int(time.time() if now is None else now)
    with Session(bind=engine) as db:
        _begin(db)
        row = assert_lease(db, user_id, token, generation, source, now=now)
        row.lease_expires_at = now + LEASE_SECONDS
        db.commit()


def release(engine, user_id, token, source='coros'):
    with Session(bind=engine) as db:
        _begin(db)
        row = db.query(SourceControl).filter_by(user_id=user_id, source=source, lease_token=token).first()
        if row:
            row.lease_token = None
            row.lease_expires_at = None
        db.commit()


def set_status(db, user_id, status, source='coros'):
    """Caller holds BEGIN IMMEDIATE and has reauthenticated the account."""
    if status not in ('paused', 'active'):
        raise ValueError('invalid source status')
    row = db.query(SourceControl).filter_by(user_id=user_id, source=source).first()
    if row is None:
        raise SourceUnavailable('source has not been configured')
    if row.status != status:
        row.status = status
        row.generation += 1
        row.lease_token = None
        row.lease_expires_at = None
    return row
