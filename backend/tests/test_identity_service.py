from datetime import datetime, timezone
from unittest.mock import patch
import pytest
from identity.bindings import VerifiedIdentity, bind, resolve as resolve_identity
from identity.sessions import issue, resolve as resolve_session
from identity.service import unbind_and_revoke_sessions
from models import User

KEY = b'example-key-for-tests-only-32-bytes-long'
NOW = datetime(2026, 10, 28, tzinfo=timezone.utc)


def setup_accounts(db):
    db.add_all([User(id=1, username='one', password_hash='unused'), User(id=2, username='two', password_hash='unused')])
    db.commit()
    bind(db, 1, VerifiedIdentity('wechat', 'first'), KEY)
    bind(db, 2, VerifiedIdentity('wechat', 'second'), KEY)
    return issue(db, 1, now=NOW), issue(db, 2, now=NOW)


def test_unbind_revokes_only_same_account(db_session):
    first, second = setup_accounts(db_session)
    assert unbind_and_revoke_sessions(db_session, 1, 'wechat')
    assert resolve_identity(db_session, VerifiedIdentity('wechat', 'first'), KEY) is None
    assert resolve_session(db_session, first, now=NOW) is None
    assert resolve_identity(db_session, VerifiedIdentity('wechat', 'second'), KEY) == 2
    assert resolve_session(db_session, second, now=NOW) == 2
    assert not unbind_and_revoke_sessions(db_session, 1, 'wechat')


def test_unbind_and_revoke_roll_back_together(db_session):
    first, _ = setup_accounts(db_session)
    with patch.object(db_session, 'commit', side_effect=RuntimeError('simulated failure')):
        with pytest.raises(RuntimeError):
            unbind_and_revoke_sessions(db_session, 1, 'wechat')
    db_session.expire_all()
    assert resolve_identity(db_session, VerifiedIdentity('wechat', 'first'), KEY) == 1
    assert resolve_session(db_session, first, now=NOW) == 1
