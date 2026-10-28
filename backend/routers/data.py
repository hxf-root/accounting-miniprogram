"""数据导入导出 API 路由层（薄层，委托给 service）"""

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_db
from auth import get_current_user, security
from schemas import ImportData, ImportCommit
from services import data as data_service
from services import import_preview

router = APIRouter(prefix="/api/data", tags=["data"])


@router.get("/export")
def export_data(response: Response, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    response.headers['Cache-Control'] = 'no-store'
    return data_service.export_data(db, user["user_id"])


@router.post("/import")
def import_data(data: ImportData, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    raise HTTPException(409, '旧导入接口已停用，请先预览并确认导入')


def _sqlite_session(db):
    if db.get_bind().dialect.name != 'sqlite':
        raise HTTPException(503, '导入暂只支持 SQLite')
    return Session(bind=db.get_bind())


@router.post('/import/preview')
def preview_import(data: ImportData, response: Response, db: Session = Depends(get_db),
                   credential: HTTPAuthorizationCredentials = Depends(security),
                   user: dict = Depends(get_current_user)):
    with _sqlite_session(db) as dedicated:
        dedicated.execute(text('BEGIN'))
        checked = get_current_user(cred=credential, db=dedicated)
        result = import_preview.preview(dedicated, checked['user_id'], data)
    response.headers['Cache-Control'] = 'no-store'
    return result


@router.post('/import/commit')
def commit_import(payload: ImportCommit, response: Response, db: Session = Depends(get_db),
                  credential: HTTPAuthorizationCredentials = Depends(security),
                  user: dict = Depends(get_current_user)):
    with _sqlite_session(db) as dedicated:
        # Hold the write reservation across reauthentication, snapshot check and
        # replacement so a deletion/sync cannot slip in between check and write.
        dedicated.execute(text('BEGIN IMMEDIATE'))
        checked = get_current_user(cred=credential, db=dedicated)
        import_preview.verify(dedicated, checked['user_id'], payload.data, payload.preview_token)
        result = data_service.import_data(dedicated, checked['user_id'], payload.data)
    response.headers['Cache-Control'] = 'no-store'
    return result


@router.delete("")
def clear_data(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    # Until source pausing and in-flight job fencing exist, clearing can cause
    # an authorized worker to reimport deleted data immediately afterward.
    raise HTTPException(status_code=503, detail="暂不能清空数据：同步暂停和删除保护尚未完成")
