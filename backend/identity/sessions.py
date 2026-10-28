"""Revocable short-lived sessions; not yet used by the existing HTTP API.

Callers must authenticate identity before issuing and use a dedicated DB session;
these functions commit. Older JWTs are intentionally unaffected.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import re
import secrets

from sqlalchemy.orm import Session
from models import AccessSession, User

_TOKEN = re.compile(r'^[A-Za-z0-9_-]{43}$')


def _utc_now(now: datetime | None) -> datetime:
    now = now or datetime.now(timezone.utc)
    if now.utcoffset() is None:
        raise ValueError('timestamp must include timezone')
    return now.astimezone(timezone.utc)


def is_session_token(token: str) -> bool:
    return isinstance(token, str) and bool(_TOKEN.fullmatch(token))


def _digest(token: str) -> str | None:
    if not is_session_token(token):
        return None
    return hashlib.sha256(token.encode('ascii')).hexdigest()


def issue(db: Session, user_id: int, *, lifetime: timedelta = timedelta(hours=12),
          now: datetime | None = None) -> str:
    if not isinstance(lifetime, timedelta) or not timedelta(0) < lifetime <= timedelta(hours=24):
        raise ValueError('session lifetime must be between zero and 24 hours')
    if not db.query(User.id).filter_by(id=user_id).first():
        raise ValueError('account does not exist')
    expires = _utc_now(now) + lifetime
    token = secrets.token_urlsafe(32)
    db.add(AccessSession(user_id=user_id, token_digest=_digest(token),
                         expires_at=expires.isoformat(timespec='microseconds'), revoked=False))
    db.commit()
    return token


def resolve(db: Session, token: str, *, now: datetime | None = None) -> int | None:
    digest = _digest(token)
    if digest is None:
        return None
    row = db.query(AccessSession).filter_by(token_digest=digest, revoked=False).first()
    if not row:
        return None
    try:
        expires = datetime.fromisoformat(row.expires_at)
        if expires.utcoffset() is None or _utc_now(now) >= expires.astimezone(timezone.utc):
            return None
    except (ValueError, OverflowError):
        return None
    return row.user_id if db.query(User.id).filter_by(id=row.user_id).first() else None


def revoke(db: Session, user_id: int, token: str) -> bool:
    digest = _digest(token)
    if digest is None:
        return False
    row = db.query(AccessSession).filter_by(user_id=user_id, token_digest=digest, revoked=False).first()
    if not row:
        return False
    row.revoked = True
    db.commit()
    return True


def revoke_all(db: Session, user_id: int) -> int:
    count = db.query(AccessSession).filter_by(user_id=user_id, revoked=False).update({'revoked': True})
    db.commit()
    return count
