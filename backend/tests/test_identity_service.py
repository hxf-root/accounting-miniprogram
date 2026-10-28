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
    db_session.rollback()  # start a fresh transaction for the coordinated operation
    assert not unbind_and_revoke_sessions(db_session, 1, 'wechat')


def test_unbind_and_revoke_roll_back_together(db_session):
    first, _ = setup_accounts(db_session)
    with patch.object(db_session, 'commit', side_effect=RuntimeError('simulated failure')):
        with pytest.raises(RuntimeError):
            unbind_and_revoke_sessions(db_session, 1, 'wechat')
    db_session.expire_all()
    assert resolve_identity(db_session, VerifiedIdentity('wechat', 'first'), KEY) == 1
    assert resolve_session(db_session, first, now=NOW) == 1


def test_identity_issuance_and_unbind_are_serialized(db_session):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from sqlalchemy.orm import sessionmaker
    from identity.service import issue_for_identity, UnboundIdentity

    db_session.add(User(id=1, username='race-user', password_hash='unused'))
    db_session.commit()
    factory = sessionmaker(bind=db_session.get_bind())
    identity = VerifiedIdentity('wechat', 'race-subject')
    for _ in range(8):
        with factory() as db:
            bind(db, 1, identity, KEY)
        barrier = Barrier(2)
        def create():
            with factory() as db:
                barrier.wait(timeout=5)
                try:
                    return issue_for_identity(db, identity, KEY, now=NOW)
                except UnboundIdentity:
                    return None
        def remove():
            with factory() as db:
                barrier.wait(timeout=5)
                return unbind_and_revoke_sessions(db, 1, 'wechat')
        with ThreadPoolExecutor(max_workers=2) as pool:
            issued = pool.submit(create)
            removed = pool.submit(remove)
            token = issued.result(timeout=10)
            assert removed.result(timeout=10)
        with factory() as db:
            assert resolve_identity(db, identity, KEY) is None
            if token:
                assert resolve_session(db, token, now=NOW) is None


def test_coordinated_operations_require_fresh_session(db_session):
    from identity.service import issue_for_identity
    setup_accounts(db_session)
    db_session.add(User(id=3, username='pending', password_hash='unused'))
    db_session.flush()
    with pytest.raises(ValueError, match='fresh dedicated'):
        issue_for_identity(db_session, VerifiedIdentity('wechat', 'first'), KEY, now=NOW)
    assert db_session.query(User).filter_by(id=3).count() == 1
    db_session.rollback()


def test_both_serial_orders_fail_closed(db_session):
    from identity.service import issue_for_identity, UnboundIdentity
    db_session.add(User(id=1, username='ordered', password_hash='unused'))
    db_session.commit()
    identity = VerifiedIdentity('wechat', 'ordered-subject')
    bind(db_session, 1, identity, KEY)
    token = issue_for_identity(db_session, identity, KEY, now=NOW)
    assert unbind_and_revoke_sessions(db_session, 1, 'wechat')
    assert resolve_session(db_session, token, now=NOW) is None
    db_session.rollback()
    with pytest.raises(UnboundIdentity):
        issue_for_identity(db_session, identity, KEY, now=NOW)
