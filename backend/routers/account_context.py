"""Minimal capability and account state; no provider identities or secrets returned."""
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from auth import get_current_user, security
from database import get_db
from identity.sessions import is_session_token, revoke
from models import ExternalIdentity
from routers.wechat_identity import config as wechat_config

router = APIRouter(prefix='/api', tags=['account-context'])


@router.get('/capabilities')
def capabilities(response: Response):
    try:
        wechat_config()
        configured = True
    except HTTPException:
        configured = False
    response.headers['Cache-Control'] = 'no-store'
    # Configuration is not proof that the upstream or proxy is functional.
    return {'wechat_identity_configured': configured, 'current_session_logout': True}


@router.get('/me')
def me(response: Response, user: dict = Depends(get_current_user),
       credential: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    bound = db.query(ExternalIdentity.id).filter_by(user_id=user['user_id'], provider='wechat').first() is not None
    response.headers['Cache-Control'] = 'no-store'
    return {'user_id': user['user_id'], 'username': user['username'], 'wechat_bound': bound,
            'session_type': 'short' if is_session_token(credential.credentials) else 'legacy'}


@router.post('/auth/logout')
def logout(response: Response, user: dict = Depends(get_current_user),
           credential: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    response.headers['Cache-Control'] = 'no-store'
    if not is_session_token(credential.credentials):
        raise HTTPException(409, '旧版凭据不支持单设备撤销', headers={'Cache-Control': 'no-store'})
    if not revoke(db, user['user_id'], credential.credentials):
        raise HTTPException(401, '登录凭证已失效', headers={'Cache-Control': 'no-store'})
    return {'ok': True}
