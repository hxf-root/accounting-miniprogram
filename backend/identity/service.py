"""Coordinated SQLite identity operations; no HTTP routes or legacy JWT changes.

These functions require their own fresh session. All identity-based session
issuance and identity unbinding must use this same boundary; lower-level binding
and session primitives do not have its concurrency guarantee.
"""
from datetime import datetime, timedelta, timezone
import re
import secrets

from sqlalchemy import text
from sqlalchemy.orm import Session
from identity.bindings import VerifiedIdentity, subject_digest
from identity.sessions import _digest, _utc_now
from models import AccessSession, ExternalIdentity, User

_PROVIDER = re.compile(r'^[a-z][a-z0-9_]{1,31}$')


class UnboundIdentity(Exception):
    """The provider identity is no longer bound to a local account."""


def _require_fresh_sqlite(db: Session) -> None:
    if db.in_transaction():
        raise ValueError('a fresh dedicated database session is required')
    if db.get_bind().dialect.name != 'sqlite':
        raise ValueError('coordinated identity operations require SQLite')


def _begin_serialized_write(db: Session) -> None:
    # Both operations acquire SQLite's write reservation before reading binding.
    db.execute(text('BEGIN IMMEDIATE'))


def issue_for_identity(db: Session, identity: VerifiedIdentity, key: bytes, *,
                       lifetime: timedelta = timedelta(hours=12), now: datetime | None = None) -> str:
    """Issue only while a provider-verified identity remains bound."""
    digest = subject_digest(identity, key)
    if not isinstance(lifetime, timedelta) or not timedelta(0) < lifetime <= timedelta(hours=24):
        raise ValueError('session lifetime must be between zero and 24 hours')
    expires = _utc_now(now) + lifetime
    _require_fresh_sqlite(db)
    try:
        _begin_serialized_write(db)
        binding = db.query(ExternalIdentity).filter_by(provider=identity.provider, subject_digest=digest).first()
        if not binding or not db.query(User.id).filter_by(id=binding.user_id).first():
            raise UnboundIdentity('identity is not bound')
        token = secrets.token_urlsafe(32)
        db.add(AccessSession(user_id=binding.user_id, token_digest=_digest(token),
                             expires_at=expires.astimezone(timezone.utc).isoformat(timespec='microseconds'), revoked=False))
        db.commit()
        return token
    except Exception:
        db.rollback()
        raise


def unbind_and_revoke_sessions(db: Session, user_id: int, provider: str) -> bool:
    """Remove binding and revoke new sessions atomically, serializing issuance."""
    if not isinstance(provider, str) or not _PROVIDER.fullmatch(provider):
        raise ValueError('invalid identity provider')
    _require_fresh_sqlite(db)
    try:
        _begin_serialized_write(db)
        identity = db.query(ExternalIdentity).filter_by(user_id=user_id, provider=provider).first()
        if identity is None:
            db.rollback()
            return False
        db.delete(identity)
        db.query(AccessSession).filter_by(user_id=user_id, revoked=False).update({'revoked': True})
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
