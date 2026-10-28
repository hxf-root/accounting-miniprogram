"""Experimental WeChat identity flow, disabled unless explicitly configured.

Do not enable in production until provider protocol, rate limits, legacy JWT
revocation and database migration have been verified.
"""
import base64
import binascii
import os

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from identity.bindings import BindingConflict, bind
from identity.service import UnboundIdentity, issue_for_identity, unbind_and_revoke_sessions
from identity.wechat import WeChatCodeExchange, WeChatConfig, WeChatExchangeError

router = APIRouter(prefix='/api/auth/wechat', tags=['wechat-identity'])


class LoginCode(BaseModel):
    code: str = Field(min_length=1, max_length=512, repr=False)


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


def verified(provider: WeChatCodeExchange, code: str):
    try:
        return provider.exchange(code)
    except WeChatExchangeError:
        raise HTTPException(401, '微信身份验证失败') from None


@router.post('/bind')
def bind_existing(data: LoginCode, user: dict = Depends(get_current_user),
                  db: Session = Depends(get_db), settings=Depends(config)):
    provider, key = settings
    identity = verified(provider, data.code)
    try:
        bind(db, user['user_id'], identity, key)
    except BindingConflict:
        raise HTTPException(409, '身份绑定冲突') from None
    return {'ok': True}


@router.post('/login')
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
