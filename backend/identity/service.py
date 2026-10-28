"""Coordinated account identity operations; not exposed through HTTP yet."""
import re

from sqlalchemy.orm import Session
from models import AccessSession, ExternalIdentity

_PROVIDER = re.compile(r'^[a-z][a-z0-9_]{1,31}$')


def unbind_and_revoke_sessions(db: Session, user_id: int, provider: str) -> bool:
    """Remove one external binding and revoke all new sessions atomically.

    Uses a dedicated session and commits or rolls back as one operation. Existing
    legacy JWTs remain valid; callers must not imply otherwise.
    """
    if not isinstance(provider, str) or not _PROVIDER.fullmatch(provider):
        raise ValueError('invalid identity provider')
    try:
        identity = db.query(ExternalIdentity).filter_by(user_id=user_id, provider=provider).first()
        if identity is None:
            return False
        db.delete(identity)
        db.query(AccessSession).filter_by(user_id=user_id, revoked=False).update({'revoked': True})
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
