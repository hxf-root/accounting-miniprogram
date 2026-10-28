"""Optional SQLite limits for legacy password endpoints; disabled until configured."""
import base64
import binascii
import os

from fastapi import Depends, HTTPException, Request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database import get_db
from identity.rate_limit import client_address, consume, RateLimitExceeded, UntrustedAddress


def _check(request: Request, db: Session, scope: str, limit: int):
    enabled = os.environ.get('BAOBU_PASSWORD_RATE_LIMIT', '')
    if not enabled:
        return
    try:
        if enabled != '1':
            raise ValueError('invalid setting')
        key = base64.b64decode(os.environ.get('BAOBU_IDENTITY_HMAC_KEY', ''), validate=True)
        if len(key) < 32:
            raise ValueError('invalid key')
        peer = request.client.host if request.client else None
        address = client_address(peer, request.headers.get('x-forwarded-for'),
                                 os.environ.get('BAOBU_TRUSTED_PROXY_CIDRS', ''))
        with Session(bind=db.get_bind()) as dedicated:
            consume(dedicated, key=key, scope=scope, subject=address, limit=limit, window_seconds=60)
    except RateLimitExceeded as exc:
        raise HTTPException(429, '请求过于频繁，请稍后再试', headers={'Retry-After': str(exc.retry_after)}) from None
    except (ValueError, binascii.Error, UntrustedAddress, SQLAlchemyError):
        raise HTTPException(503, '账户服务暂不可用') from None


def login_limit(request: Request, db: Session = Depends(get_db)):
    _check(request, db, 'password_login_ip', 20)


def register_limit(request: Request, db: Session = Depends(get_db)):
    _check(request, db, 'password_register_ip', 5)
