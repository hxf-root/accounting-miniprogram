import pytest
from identity.bindings import BindingConflict, VerifiedIdentity, bind, resolve, subject_digest, unbind
from models import ExternalIdentity, User


KEY = b'example-key-for-tests-only-32-bytes-long'


def test_binding_requires_existing_user_and_verified_identity(db_session):
    identity = VerifiedIdentity('wechat', 'example-subject')
    with pytest.raises(ValueError):
        bind(db_session, 1, identity, KEY)
    with pytest.raises(ValueError):
        subject_digest(identity, b'weak')
    with pytest.raises(ValueError):
        subject_digest({'provider': 'wechat', 'subject': 'untrusted'}, KEY)
    assert resolve(db_session, identity, KEY) is None


def test_uniqueness_isolation_idempotence_and_unbind(db_session):
    db_session.add_all([User(id=1, username='one', password_hash='unused'),
                        User(id=2, username='two', password_hash='unused')])
    db_session.commit()
    first = VerifiedIdentity('wechat', 'subject-one')
    second = VerifiedIdentity('wechat', 'subject-two')
    bind(db_session, 1, first, KEY)
    bind(db_session, 1, first, KEY)
    assert resolve(db_session, first, KEY) == 1
    assert db_session.query(ExternalIdentity).one().subject_digest != first.subject
    with pytest.raises(BindingConflict):
        bind(db_session, 2, first, KEY)
    with pytest.raises(BindingConflict):
        bind(db_session, 1, second, KEY)
    assert not unbind(db_session, 2, 'wechat')
    assert resolve(db_session, first, KEY) == 1
    assert unbind(db_session, 1, 'wechat')
    assert resolve(db_session, first, KEY) is None
    bind(db_session, 2, first, KEY)
    assert resolve(db_session, first, KEY) == 2


def test_provider_namespaces_are_separate(db_session):
    db_session.add(User(id=1, username='one', password_hash='unused'))
    db_session.commit()
    assert subject_digest(VerifiedIdentity('wechat', 'same'), KEY) != subject_digest(VerifiedIdentity('other', 'same'), KEY)
    bind(db_session, 1, VerifiedIdentity('wechat', 'same'), KEY)
    assert resolve(db_session, VerifiedIdentity('other', 'same'), KEY) is None
