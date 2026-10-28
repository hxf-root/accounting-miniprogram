"""Identity binding primitives; no HTTP routes and no external token exchange.

Callers must authenticate the local account and obtain a provider-verified subject
on the server. Never construct VerifiedIdentity directly from a client request.
"""
from dataclasses import dataclass
import hashlib
import hmac
import re

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from models import ExternalIdentity, User

_PROVIDER = re.compile(r'^[a-z][a-z0-9_]{1,31}$')


class BindingConflict(Exception):
    """Identity or account is already bound to a different counterpart."""


@dataclass(frozen=True)
class VerifiedIdentity:
    provider: str
    subject: str


def subject_digest(identity: VerifiedIdentity, key: bytes) -> str:
    if not isinstance(identity, VerifiedIdentity) or not isinstance(identity.provider, str) or not _PROVIDER.fullmatch(identity.provider):
        raise ValueError('invalid identity provider')
    if not isinstance(identity.subject, str) or not identity.subject or len(identity.subject.encode('utf-8')) > 512:
        raise ValueError('invalid identity subject')
    if not isinstance(key, bytes) or len(key) < 32:
        raise ValueError('identity key must contain at least 32 bytes')
    message = b'baobu-identity-v1\0' + identity.provider.encode('ascii') + b'\0' + identity.subject.encode('utf-8')
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def bind(db: Session, user_id: int, identity: VerifiedIdentity, key: bytes) -> None:
    """Bind a verified identity to a previously authenticated local account."""
    digest = subject_digest(identity, key)
    if not db.query(User.id).filter_by(id=user_id).first():
        raise ValueError('account does not exist')
    by_subject = db.query(ExternalIdentity).filter_by(provider=identity.provider, subject_digest=digest).first()
    by_account = db.query(ExternalIdentity).filter_by(provider=identity.provider, user_id=user_id).first()
    if by_subject or by_account:
        if by_subject and by_account and by_subject.id == by_account.id:
            return
        raise BindingConflict('identity already bound')
    db.add(ExternalIdentity(user_id=user_id, provider=identity.provider, subject_digest=digest))
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise BindingConflict('identity already bound') from exc


def resolve(db: Session, identity: VerifiedIdentity, key: bytes) -> int | None:
    digest = subject_digest(identity, key)
    row = db.query(ExternalIdentity).filter_by(provider=identity.provider, subject_digest=digest).first()
    if not row or not db.query(User.id).filter_by(id=row.user_id).first():
        return None
    return row.user_id


def unbind(db: Session, user_id: int, provider: str) -> bool:
    if not isinstance(provider, str) or not _PROVIDER.fullmatch(provider):
        raise ValueError('invalid identity provider')
    row = db.query(ExternalIdentity).filter_by(user_id=user_id, provider=provider).first()
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True
