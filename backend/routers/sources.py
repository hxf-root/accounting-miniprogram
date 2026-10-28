"""Local COROS scheduling status; this is not an OAuth connection flow."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import text
from sqlalchemy.orm import Session

from auth import get_current_user, security
from database import get_db
from integrations.source_control import SourceUnavailable, set_status
from models import SourceControl, SyncState

router = APIRouter(prefix='/api/sources', tags=['sources'])


@router.get('/coros')
def coros_status(response: Response, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    row = db.query(SourceControl).filter_by(user_id=user['user_id'], source='coros').first()
    checkpoint = db.query(SyncState).filter_by(user_id=user['user_id'], source='coros').first()
    response.headers['Cache-Control'] = 'no-store'
    return {'status': row.status if row else 'unconfigured',
            'last_success_date': checkpoint.last_success_date if checkpoint else None}


@router.post('/coros/{operation}')
def change_coros_status(operation: Literal['pause', 'resume'], response: Response,
                        db: Session = Depends(get_db), user: dict = Depends(get_current_user),
                        credential: HTTPAuthorizationCredentials = Depends(security)):
    if db.get_bind().dialect.name != 'sqlite':
        raise HTTPException(503, '同步控制暂不可用')
    with Session(bind=db.get_bind()) as dedicated:
        dedicated.execute(text('BEGIN IMMEDIATE'))
        checked = get_current_user(cred=credential, db=dedicated)
        try:
            control = set_status(dedicated, checked['user_id'], 'paused' if operation == 'pause' else 'active')
        except SourceUnavailable:
            raise HTTPException(404, '尚未配置高驰同步') from None
        status = control.status
        dedicated.commit()
    response.headers['Cache-Control'] = 'no-store'
    return {'status': status}
