from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy.orm import sessionmaker
from identity.rate_limit import client_address, consume, RateLimitExceeded, UntrustedAddress
from models import IdentityRateBucket

KEY = b'example-key-for-tests-only-32-bytes-long'


def test_proxy_trust_and_spoofed_headers():
    assert client_address('8.8.8.8', '1.1.1.1', '') == '8.8.8.8'  # untrusted forwarded ignored
    assert client_address('127.0.0.1', '1.1.1.1, 10.0.0.2', '127.0.0.1/32,10.0.0.0/8') == '1.1.1.1'
    for peer, forwarded, trusted in [
        ('127.0.0.1', '1.1.1.1', ''), ('127.0.0.1', None, '127.0.0.1/32'),
        ('127.0.0.1', 'nonsense', '127.0.0.1/32'), ('127.0.0.1', '1.1.1.1', '0.0.0.0/0'), ('127.0.0.1', '10.0.0.2', '127.0.0.1/32,10.0.0.0/8'),
        ('127.0.0.1', ','.join(['1.1.1.1'] * 11), '127.0.0.1/32'),
    ]:
        with pytest.raises(UntrustedAddress): client_address(peer, forwarded, trusted)


def test_window_reset_isolation_and_no_raw_subject(db_session):
    def hit(subject, now=120):
        consume(db_session, key=KEY, scope='wechat_ip', subject=subject, limit=2, window_seconds=60, now=now)
    hit('8.8.8.8'); hit('8.8.8.8')
    with pytest.raises(RateLimitExceeded) as error: hit('8.8.8.8', 121)
    assert error.value.retry_after == 59
    hit('1.1.1.1', 121)
    db_session.rollback()
    rows = db_session.query(IdentityRateBucket).all()
    assert all('8.8.8.8' not in row.key_digest for row in rows)
    db_session.rollback()
    hit('8.8.8.8', 180)
    with pytest.raises(ValueError, match='clock moved backwards'): hit('8.8.8.8', 120)


def test_simultaneous_requests_cannot_exceed_limit(db_session):
    factory = sessionmaker(bind=db_session.get_bind())
    barrier = Barrier(6)
    def attempt():
        with factory() as db:
            barrier.wait(timeout=5)
            try:
                consume(db, key=KEY, scope='wechat_ip', subject='8.8.8.8', limit=3, window_seconds=60, now=120)
                return True
            except RateLimitExceeded:
                return False
    with ThreadPoolExecutor(max_workers=6) as pool:
        assert sum(pool.map(lambda _: attempt(), range(6))) == 3
