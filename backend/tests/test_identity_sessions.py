from datetime import datetime, timedelta, timezone
import pytest
from identity.sessions import issue, resolve, revoke, revoke_all
from models import AccessSession, User

NOW = datetime(2026, 10, 28, tzinfo=timezone.utc)


def test_sessions_are_private_expiring_and_revocable(db_session):
    db_session.add_all([User(id=1, username='one', password_hash='unused'), User(id=2, username='two', password_hash='unused')])
    db_session.commit()
    token = issue(db_session, 1, lifetime=timedelta(hours=1), now=NOW)
    another = issue(db_session, 1, now=NOW)
    other = issue(db_session, 2, now=NOW)
    assert token != another
    assert all(row.token_digest not in (token, another, other) for row in db_session.query(AccessSession).all())
    assert resolve(db_session, token, now=NOW) == 1
    assert resolve(db_session, token, now=NOW + timedelta(hours=1)) is None
    assert revoke(db_session, 2, token) is False
    assert revoke(db_session, 1, token) is True
    assert resolve(db_session, token, now=NOW) is None
    assert revoke_all(db_session, 1) == 1
    assert resolve(db_session, another, now=NOW) is None
    assert resolve(db_session, other, now=NOW) == 2


def test_invalid_and_dangling_sessions_fail_closed(db_session):
    with pytest.raises(ValueError): issue(db_session, 999, now=NOW)
    db_session.add(User(id=1, username='one', password_hash='unused'))
    db_session.commit()
    with pytest.raises(ValueError): issue(db_session, 1, lifetime=timedelta(days=2), now=NOW)
    with pytest.raises(ValueError): issue(db_session, 1, now=datetime(2026, 1, 1))
    assert resolve(db_session, 'not-a-valid-token', now=NOW) is None
    token = issue(db_session, 1, now=NOW)
    db_session.query(User).filter_by(id=1).delete()
    db_session.commit()
    assert resolve(db_session, token, now=NOW) is None
