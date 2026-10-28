import fcntl
import hashlib
import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from coros_preflight import preflight
from models import Memory, SourceControl, SyncState, User


@pytest.fixture
def setup(db_session, tmp_path):
    db_session.add(User(id=1, username='fictional', password_hash='unused'))
    db_session.commit()
    state = tmp_path / 'state'
    state.mkdir(mode=0o700)
    (state / 'token.json').write_text('fictional credential')
    (state / 'token.json').chmod(0o600)
    helper = tmp_path / 'helper.py'
    helper.write_text('# fictional helper')
    digest = hashlib.sha256(helper.read_bytes()).hexdigest()
    database = Path(db_session.get_bind().url.database)
    return database, helper, state, digest


def result(text):
    return SimpleNamespace(returncode=0, stdout=json.dumps({'content': [{'type': 'text', 'text': json.dumps(text)}], 'isError': False}))


def test_preflight_query_does_not_import_or_configure(db_session, setup):
    database, helper, state, digest = setup
    sample = ('Sport Records (1 records)\n1. Fictional run\n'
              '   Time Window: startTimestamp=1793011716\n   LabelId: 123 | SportType: 100\n')
    with patch('coros_worker.subprocess.run', return_value=result(sample)) as run:
        answer = preflight(database, 1, helper, state, digest, today=date(2026, 10, 27))
    assert answer == {'account_exists': True, 'source_status': 'unconfigured', 'provider_query': 'ok', 'coverage': 'not_capped'}
    assert 'fictional credential' not in json.dumps(answer)
    assert 'Fictional run' not in json.dumps(answer)
    assert json.loads(run.call_args.args[0][-1]) == {'startDate': '20261021', 'endDate': '20261027', 'limit': 20}
    db_session.expire_all()
    assert db_session.query(Memory).count() == 0
    assert db_session.query(SyncState).count() == 0
    assert db_session.query(SourceControl).count() == 0


def test_preflight_rejects_unmatched_helper_and_account_before_network(db_session, setup):
    database, helper, state, digest = setup
    with patch('coros_worker.subprocess.run') as run:
        with pytest.raises(ValueError):
            preflight(database, 1, helper, state, '0' * 64)
        with pytest.raises(ValueError):
            preflight(database, 2, helper, state, digest)
        run.assert_not_called()


def test_preflight_uses_same_credential_lock_and_reports_truncation(db_session, setup):
    database, helper, state, digest = setup
    sample = ('Sport Records (2 records)\n1. Fictional run\n'
              '  Time Window: startTimestamp=1793011716\n  LabelId: 123 | SportType: 100\n'
              '2. Fictional walk\n  Time Window: startTimestamp=1793011716\n  LabelId: 124 | SportType: 900\n')
    with (state / 'sync.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with patch('coros_worker.subprocess.run') as run:
            with pytest.raises(RuntimeError, match='already running'):
                preflight(database, 1, helper, state, digest, today=date(2026, 10, 27), limit=2)
            run.assert_not_called()
    with patch('coros_worker.subprocess.run', return_value=result(sample)):
        answer = preflight(database, 1, helper, state, digest, today=date(2026, 10, 27), limit=2)
    assert answer['coverage'] == 'may_be_truncated'
