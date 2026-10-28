"""SQLite-backed identity throttling with explicit reverse-proxy trust.

Limiters are fail-closed. Raw client addresses are not persisted. Forwarded
headers are trusted only from explicitly configured proxy networks.
"""
import hashlib
import hmac
import ipaddress
import math
import re
import time

from sqlalchemy import text
from sqlalchemy.orm import Session
from models import IdentityRateBucket

_SCOPE = re.compile(r'^[a-z][a-z0-9_]{1,31}$')


class RateLimitExceeded(Exception):
    def __init__(self, retry_after: int):
        super().__init__('rate limit exceeded')
        self.retry_after = retry_after


class UntrustedAddress(Exception):
    pass


def client_address(peer: str, forwarded: str | None, trusted_cidrs: str) -> str:
    """Resolve client IP using only explicitly trusted reverse proxies."""
    try:
        peer_ip = ipaddress.ip_address(peer)
        networks = [ipaddress.ip_network(part.strip(), strict=False)
                    for part in trusted_cidrs.split(',') if part.strip()]
        if any(network.prefixlen == 0 for network in networks):
            raise UntrustedAddress('wildcard proxy trust is not allowed')
        trusted = lambda ip: any(ip in network for network in networks if network.version == ip.version)
        if not trusted(peer_ip):
            # Private or loopback peers are ambiguous without explicit proxy setup.
            if not peer_ip.is_global:
                raise UntrustedAddress('proxy configuration required')
            return str(peer_ip)
        if not forwarded or len(forwarded) > 1024:
            raise UntrustedAddress('forwarded address required')
        parts = forwarded.split(',')
        if len(parts) > 10:
            raise UntrustedAddress('forwarded chain too long')
        chain = [ipaddress.ip_address(part.strip()) for part in parts]
        for address in reversed(chain):
            if not trusted(address):
                if not address.is_global:
                    raise UntrustedAddress('ambiguous client address')
                return str(address)
        raise UntrustedAddress('no untrusted client address')
    except (ValueError, TypeError, AttributeError):
        raise UntrustedAddress('invalid client address') from None


def consume(db: Session, *, key: bytes, scope: str, subject: str,
            limit: int, window_seconds: int, now: float | None = None) -> None:
    if db.in_transaction() or db.get_bind().dialect.name != 'sqlite':
        raise ValueError('fresh SQLite session required')
    if (not isinstance(key, bytes) or len(key) < 32 or not isinstance(scope, str)
            or not _SCOPE.fullmatch(scope) or not isinstance(subject, str) or not subject
            or len(subject.encode('utf-8')) > 256 or isinstance(limit, bool) or not isinstance(limit, int)
            or isinstance(window_seconds, bool) or not isinstance(window_seconds, int)
            or not 1 <= limit <= 10000 or not 1 <= window_seconds <= 86400):
        raise ValueError('invalid rate limit configuration')
    timestamp = time.time() if now is None else now
    if not isinstance(timestamp, (int, float)) or not math.isfinite(timestamp) or timestamp < 0:
        raise ValueError('invalid time')
    start = int(timestamp // window_seconds) * window_seconds
    digest = hmac.new(key, b'baobu-rate-v1\0' + scope.encode('ascii') + b'\0' + subject.encode('utf-8'), hashlib.sha256).hexdigest()
    try:
        db.execute(text('BEGIN IMMEDIATE'))
        # Old state is removable; do not let unbounded abandoned buckets accumulate.
        db.query(IdentityRateBucket).filter(IdentityRateBucket.window_start < start - 86400).delete(synchronize_session=False)
        row = db.query(IdentityRateBucket).filter_by(scope=scope, key_digest=digest).first()
        if row is None:
            row = IdentityRateBucket(scope=scope, key_digest=digest, window_start=start, attempts=1)
            db.add(row)
        elif row.window_start > start:
            raise ValueError('rate limiter clock moved backwards')
        elif row.window_start < start:
            row.window_start, row.attempts = start, 1
        elif row.attempts >= limit:
            db.rollback()
            raise RateLimitExceeded(max(1, math.ceil(start + window_seconds - timestamp)))
        else:
            row.attempts += 1
        db.commit()
    except Exception:
        db.rollback()
        raise
