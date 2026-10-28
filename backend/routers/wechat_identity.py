"""Experimental WeChat identity flow, disabled unless explicitly configured.

Do not enable in production until provider protocol, trusted proxy configuration, legacy JWT
revocation and database migration have been verified.
"""
import base64
import binascii
import hmac
import os

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from models import User

from auth import get_current_user, security, verify_password
from database import get_db
from identity.bindings import BindingConflict
from identity.service import UnboundIdentity, bind_for_account, issue_for_identity, unbind_and_revoke_sessions
from identity.wechat import WeChatCodeExchange, WeChatConfig, WeChatExchangeError
from identity.rate_limit import consume, client_address, RateLimitExceeded, UntrustedAddress

router = APIRouter(prefix='/api/auth/wechat', tags=['wechat-identity'])


class LoginCode(BaseModel):
    code: str = Field(min_length=1, max_length=512, repr=False)


class BindingCode(LoginCode):
    password: str = Field(min_length=1, max_length=128, repr=False)


def config() -> tuple[WeChatCodeExchange, bytes]:
    if os.environ.get('BAOBU_WECHAT_EXPERIMENTAL') != '1':
        raise HTTPException(503, '微信身份功能未启用')
    try:
        key = base64.b64decode(os.environ.get('BAOBU_IDENTITY_HMAC_KEY', ''), validate=True)
        if len(key) < 32:
            raise ValueError('invalid identity key')
        provider = WeChatCodeExchange(WeChatConfig(
            app_id=os.environ.get('BAOBU_WECHAT_APP_ID', ''),
            app_secret=os.environ.get('BAOBU_WECHAT_APP_SECRET', '')))
        return provider, key
    except (ValueError, binascii.Error):
        raise HTTPException(503, '微信身份功能未配置') from None


def _rate(db: Session, key: bytes, scope: str, subject: str, limit: int):
    try:
        with Session(bind=db.get_bind()) as dedicated:
            consume(dedicated, key=key, scope=scope, subject=subject, limit=limit, window_seconds=60)
    except RateLimitExceeded as exc:
        raise HTTPException(429, '请求过于频繁，请稍后再试', headers={'Retry-After': str(exc.retry_after)}) from None
    except (SQLAlchemyError, ValueError):
        raise HTTPException(503, '微信身份服务暂不可用') from None


def rate_ip(request: Request, db: Session = Depends(get_db), settings=Depends(config)):
    try:
        peer = request.client.host if request.client else None
        address = client_address(peer, request.headers.get('x-forwarded-for'),
                                 os.environ.get('BAOBU_TRUSTED_PROXY_CIDRS', ''))
    except UntrustedAddress:
        raise HTTPException(503, '微信身份服务暂不可用') from None
    _rate(db, settings[1], 'wechat_ip', address, 20)


def rate_account(user: dict = Depends(get_current_user), db: Session = Depends(get_db), settings=Depends(config)):
    _rate(db, settings[1], 'wechat_bind_user', str(user['user_id']), 10)


def verified(provider: WeChatCodeExchange, code: str):
    try:
        return provider.exchange(code)
    except WeChatExchangeError:
        raise HTTPException(401, '微信身份验证失败') from None


@router.post('/bind', dependencies=[Depends(rate_ip), Depends(rate_account)])
def bind_existing(data: BindingCode, user: dict = Depends(get_current_user),
                  credential: HTTPAuthorizationCredentials = Depends(security),
                  db: Session = Depends(get_db), settings=Depends(config)):
    provider, key = settings
    account = db.query(User).filter_by(id=user['user_id']).first()
    if not account or not verify_password(data.password, account.password_hash):
        raise HTTPException(401, '账户验证失败')
    verified_hash = account.password_hash
    identity = verified(provider, data.code)
    def revalidate(locked_db):
        checked = get_current_user(cred=credential, db=locked_db)
        current = locked_db.query(User).filter_by(id=user['user_id']).first()
        if checked['user_id'] != user['user_id'] or not current or not hmac.compare_digest(verified_hash, current.password_hash):
            raise HTTPException(401, '账户验证失败')
    try:
        with Session(bind=db.get_bind()) as dedicated:
            bind_for_account(dedicated, user['user_id'], identity, key, revalidate=revalidate)
    except BindingConflict:
        raise HTTPException(409, '身份绑定冲突') from None
    return {'ok': True}


@router.post('/login', dependencies=[Depends(rate_ip)])
def login(data: LoginCode, response: Response, db: Session = Depends(get_db), settings=Depends(config)):
    provider, key = settings
    identity = verified(provider, data.code)
    try:
        with Session(bind=db.get_bind()) as dedicated:
            token = issue_for_identity(dedicated, identity, key)
    except UnboundIdentity:
        raise HTTPException(401, '身份未绑定') from None
    response.headers['Cache-Control'] = 'no-store'
    return {'token': token, 'expires_in': 43200}


@router.delete('/bind')
def unbind(user: dict = Depends(get_current_user), db: Session = Depends(get_db), settings=Depends(config)):
    # get_current_user may have queried using db; coordination requires a fresh session.
    with Session(bind=db.get_bind()) as dedicated:
        removed = unbind_and_revoke_sessions(dedicated, user['user_id'], 'wechat')
    return {'ok': True, 'was_bound': removed}
